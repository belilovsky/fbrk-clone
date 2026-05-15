# Ingester And Cron Audit Notes

## 2026-05-05 Follow-up: Prod Sync + RSS Idempotency

### Checked

- Repo `admin/ingest_fbrk.py`: `524` lines, SHA256 `6dacd11354876ced7321b7081c494dad333126207c1673e72cc8ba3bb5ba1819`.
- Prod `/opt/fbrk-admin/ingest_fbrk.py`: `639` lines, SHA256 `5f6084c1557e37f10d4f6565b5322785485811b42d407ca2b6e8e7bcd185210b`.
- Cron: `*/10 * * * * cd /opt/fbrk-admin && ... /usr/bin/python3 /opt/fbrk-admin/ingest_fbrk.py rss >> /var/log/fbrk/rss-poll.log 2>&1`.
- Last log window: RSS normally processes 10 items as `unchanged`; one transient `fetch https://fbrk.kz/rss.xml -> 500 (retry 1)` recovered on retry.
- `journalctl -u fbrk-admin --since "24 hours ago"` showed graceful SIGTERM/restart around deploys.

### Finding Fixed

- **High / ingester / repo drift:** repo file was stale and still had an old double-extend bug in the list-return path (`blocks.extend(b)` twice). Prod already had safer inline tokenization, fbrk.kz URL validation, `FBRK_DB_PATH` support and SQLite busy timeout.
- **Medium / ingester / idempotency:** prod UPSERT allowed equal `sections_json` length to update rows even when content was identical. Logs said `unchanged`, but `updated_at` could churn every RSS poll.

### Fix

- Synced `admin/ingest_fbrk.py` from production into the repo.
- Tightened UPSERT `WHERE`: update only when the incoming parse is at least as complete **and** title/dek/date/category/image/source/body/sections actually changed.
- Kept better-body protection: shorter parses still cannot overwrite fuller existing content.

### Prod Safety

- Backup before script deploy: `/opt/fbrk-admin/backups/fbrk-20260505T035028Z-pre-ingester-idempotent-upsert.db`.
- Code snapshot before script deploy: `/opt/fbrk-admin/code-snapshots/20260505T035028Z/ingest_fbrk.py`.
- Backup before RSS idempotency check: `/opt/fbrk-admin/backups/fbrk-20260505T035058Z-pre-ingester-rss-idempotency-check.db`.

### Verification

- `/usr/bin/python3 -m py_compile /opt/fbrk-admin/ingest_fbrk.py`: OK.
- Parser regression checks on VPS:
  - single `<br>` stays inside paragraph;
  - double/triple `<br>` split paragraphs;
  - `<b>A<br><br>B</b>` becomes balanced `<b>A</b>` and `<b>B</b>`;
  - empty split parts are dropped;
  - nested `<div><p>...` bodies are walked;
  - non-`fbrk.kz` article URLs are rejected.
- SQLite upsert regression on temp DB: identical second upsert did not change `updated_at`; richer body updated from 1 to 2 blocks.
- Prod double run: `ingest_fbrk.py rss --no-regen` twice processed 10 items each, all `unchanged`; article count stayed `4589`, max `updated_at` stayed `2026-05-05 03:50:09`, and `data.js` SHA stayed unchanged.

## Finding

`ingest_fbrk.py` is absent from repo `master`, while README and production context describe it as the cron entrypoint at `/opt/fbrk-admin/ingest_fbrk.py`.

## Impact

- Cannot audit `_split_paragraph_on_double_br`, new UPSERT logic, RSS idempotency or SIGTERM behavior from source control.
- Cannot confirm repo/VPS sync without SSH.
- Old `import/scrape_fbrk.py` is not equivalent: it posts through Admin API, strips inline formatting more aggressively, and sets `source` to `"fbrk.kz"` rather than full URL.

## Required Next Step

After VPS access is restored, copy `/opt/fbrk-admin/ingest_fbrk.py` into a branch `audit/ingester/sync-prod-ingester`, compare against any local history and only then run parser/idempotency tests.
