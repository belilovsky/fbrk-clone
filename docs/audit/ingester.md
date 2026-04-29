# Ingester And Cron Audit Notes

## Finding

`ingest_fbrk.py` is absent from repo `master`, while README and production context describe it as the cron entrypoint at `/opt/fbrk-admin/ingest_fbrk.py`.

## Impact

- Cannot audit `_split_paragraph_on_double_br`, new UPSERT logic, RSS idempotency or SIGTERM behavior from source control.
- Cannot confirm repo/VPS sync without SSH.
- Old `import/scrape_fbrk.py` is not equivalent: it posts through Admin API, strips inline formatting more aggressively, and sets `source` to `"fbrk.kz"` rather than full URL.

## Required Next Step

After VPS access is restored, copy `/opt/fbrk-admin/ingest_fbrk.py` into a branch `audit/ingester/sync-prod-ingester`, compare against any local history and only then run parser/idempotency tests.
