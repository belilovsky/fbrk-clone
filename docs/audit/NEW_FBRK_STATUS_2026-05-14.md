# FBRK Front Split Status - 2026-05-14

## Scope

Goal: collect a fresh, evidence-based state for `fbrk.qdev.run` and `new.fbrk.kz` across local repo, GitHub, and both VPS nodes, then prepare a safe base for continued development.

No production files, DB, or services were modified in this pass.

## What Was Checked

1. Local repo and branches in `/Users/belilovsky/Documents/Codex/2026-04-28/codex-6-8-belilovsky-fbrk-clone/fbrk`.
2. GitHub refs (`origin/master`, active audit branches).
3. VPS #1 `62.72.32.112` (legacy host candidate).
4. VPS #2 `148.230.117.131` (current live host candidate).
5. DNS and live HTTP for `fbrk.qdev.run` and `new.fbrk.kz`.

## Current State (Source of Truth Map)

### DNS + Live Traffic

- `fbrk.qdev.run` resolves to `148.230.117.131` and serves live traffic.
- `new.fbrk.kz` resolves to `195.210.46.10` (external host), not to either audited VPS.

### VPS Roles

- `148.230.117.131`:
  - Has active `fbrk-admin.service`.
  - Serves `/var/www/fbrk.qdev.run` via `/etc/nginx/sites-enabled/fbrk.qdev.run`.
  - Contains `/etc/nginx/sites-available/new.fbrk.kz` draft config, but it is **not enabled**.
- `62.72.32.112`:
  - Contains an older FBRK deployment.
  - Still has `fbrk-admin.service`, but DNS no longer points public traffic here.

### Git Divergence

- `origin/master`: `e319218` (`CSS: wider article cover, ad-block styles`).
- `vps148/master`: `7c7d396` (`Track AV DS 2026 redesign assets and new pages`), plus uncommitted edits in:
  - `index.html`
  - `style.css`
  - `js/data.js`
  - `js/data-archive.js`
- `vps62/master`: `a4ae632` (older redesign baseline).

Diff summary:

- `origin/master...vps148/master` = `11` commits only in `origin`, `4` commits only in `vps148`.
- `origin/master...vps62/master` = `11` commits only in `origin`, `0` only in `vps62`.

Interpretation: current production code path is split between GitHub and manual VPS-only history.

## High-Risk Gaps To Close First

1. **Prod is ahead/sideways from GitHub**: VPS #2 has local commits and dirty working tree not preserved in `origin`.
2. **`new.fbrk.kz` cutover is not network-ready**: DNS still points outside audited infra.
3. **Draft `new.fbrk.kz` nginx config used the wrong certificate path**:
   - Existing draft referenced `/etc/letsencrypt/live/fbrk.qdev.run/...`.
   - Correct target must use `/etc/letsencrypt/live/new.fbrk.kz/...` after issuance.

## Artifacts Added In Repo

- `admin/deploy/nginx-new-fbrk.conf`:
  - Cutover-ready template for `new.fbrk.kz`.
  - Uses dedicated LE cert path for `new.fbrk.kz`.
  - Mirrors current FBRK routing (`/admin`, `/api`, `/a/`, `/sitemap.xml`, `/robots.txt`, `/feed.xml`).

## Follow-up Code Prep (same date)

- `admin/app/seo.py` made host-aware:
  - `/a/<slug>`, `/robots.txt`, `/sitemap.xml`, `/feed.xml`, `/feed/ia.xml` now build absolute URLs from current request host/proto.
  - Fallback remains `FBRK_SITE_URL` or `https://fbrk.qdev.run`.
- `js/app.js` made host-aware for client-side article SEO fallback:
  - JSON-LD and canonical image/article URLs now use `location.origin` instead of hardcoded `fbrk.qdev.run`.

## Follow-up Code Prep (split frontend mode)

- Added frontend runtime split config:
  - `js/runtime-config.js` (public-origin/backend-origin overrides).
  - `index.html`, `archive.html`, `about.html`, `article.html` now load runtime config before `app.js`.
- Updated `js/app.js` routing behavior:
  - article links now use configurable backend origin (instead of hardcoded relative `/a/...`).
  - when backend origin differs from public host, article fallback page redirects to backend SSR canonical.
  - fixed wrong fallback behavior where unknown `id`/`slug` could open the first article.
- Updated `admin/app/publish.py`:
  - `SITE_URL` now comes from `FBRK_SITE_URL` (with fallback).
  - sitemap/feed article URLs are now `/a/<slug>` instead of `article.html?id=...`.
- Added KZ-hosting proxy template:
  - `admin/deploy/plesk-new-fbrk-split-proxy.conf`.
  - routes `/a/*`, `/sitemap.xml`, `/robots.txt`, `/feed*` (and optional `/js/data*.js`) to VPS backend.
- Added split runbook:
  - `docs/audit/NEW_FBRK_SPLIT_FRONTEND_RUNBOOK.md`.

## Recommended Continuation Plan

1. Snapshot current VPS #2 web repo state into GitHub branch (including dirty tracked files).
2. Decide merge strategy:
   - Option A: rebase VPS stream onto `origin/master`.
   - Option B: merge `origin/master` into VPS stream and resolve intentionally.
3. Split-hosting prep for `new.fbrk.kz`:
   - Keep frontend static on KZ host.
   - Apply `plesk-new-fbrk-split-proxy.conf` in Plesk for dynamic routes to VPS backend.
   - Configure `js/runtime-config.js` on KZ host (`PUBLIC_ORIGIN=new.fbrk.kz`, `BACKEND_ORIGIN=fbrk.qdev.run`).
   - Run smoke matrix on both hosts (`fbrk.qdev.run` and `new.fbrk.kz`).
4. Only after stable smoke, decide canonical/SEO host policy for the new frontend domain.
5. Execute cutover only by checklist: `docs/audit/NEW_FBRK_CUTOVER_RUNBOOK.md`.

## Evidence (Key Commands)

- `dig +short fbrk.qdev.run A` -> `148.230.117.131`
- `dig +short new.fbrk.kz A` -> `195.210.46.10`
- `git ls-remote root@148.230.117.131:/var/www/fbrk.qdev.run` -> `7c7d396`
- `git ls-remote root@62.72.32.112:/var/www/fbrk.qdev.run` -> `a4ae632`
- `git rev-list --left-right --count origin/master...vps148/master` -> `11 4`
- `ls -l /etc/nginx/sites-enabled | grep new.fbrk.kz` on VPS #2 -> no enabled link

Safety snapshot created (2026-05-14):

- `/opt/fbrk-admin/backups/fbrk-web-dirty-20260514T083849Z.tar.gz` (tracked dirty files from `/var/www/fbrk.qdev.run`: `index.html`, `style.css`, `js/data.js`, `js/data-archive.js`).

## Rollout Update (2026-05-14)

### Production actions performed on `148.230.117.131`

1. Safety gate executed before file updates:
   - DB backup: `/opt/fbrk-admin/backups/fbrk-20260514T091325Z-pre-split-rollout.db` (non-zero, ~70 MB).
   - Web snapshot: `/opt/fbrk-admin/web-snapshots/20260514T091325Z/` (~2.3 GB).
2. Deployed frontend files to `/var/www/fbrk.qdev.run/`:
   - `index.html`, `archive.html`, `about.html`, `article.html`
   - `js/app.js`, `js/runtime-config.js`
3. Deployed backend files to `/opt/fbrk-admin/app/`:
   - `publish.py`, `seo.py`
4. Ownership normalized:
   - `chown www-data:www-data` for all copied frontend/backend files.
5. Backend restarted:
   - `systemctl restart fbrk-admin` (status `active`).

### Incident and fix during rollout

- At ~09:14 UTC, `/a/<slug>` returned `500` due Jinja error:
  - `UndefinedError: 'ad' is undefined` in `article_ssr.html`.
- Immediate recovery:
  - temporary rollback of `seo.py` to server backup (`seo.py.bak_1778658357`).
  - service restart and smoke -> `/a/<slug>` back to `200`.
- Permanent fix applied:
  - restored SSR `ad` helper compatibility in repo `admin/app/seo.py`.
  - redeployed fixed `seo.py`.
  - revalidated `/a/<slug>`, `/`, `/sitemap.xml` as `200`.

### Verified after recovery

- Public smoke:
  - `https://fbrk.qdev.run/` -> `200`
  - `https://fbrk.qdev.run/archive.html` -> `200`
  - `https://fbrk.qdev.run/a/<slug>` -> `200`
  - `https://fbrk.qdev.run/sitemap.xml` -> `200`
- Headless browser smoke (Playwright):
  - home/archive/article load successfully, no page JS errors.
- Host-aware check (direct app test):
  - `curl -H "Host: new.fbrk.kz" -H "X-Forwarded-Proto: https" http://127.0.0.1:8787/sitemap.xml`
  - generated `<loc>` URLs use `https://new.fbrk.kz/...`.

### Remaining blocker for full split cutover

- `new.fbrk.kz` hosting node `195.210.46.10` is reachable over HTTPS but not over SSH from current access path (port 22 timeout), so KZ-host-side config was not directly mutated in this rollout.
- To complete split mode on KZ host, still required:
  - apply `admin/deploy/plesk-new-fbrk-split-proxy.conf` in Plesk Additional nginx directives;
  - set `js/runtime-config.js` on KZ host:
    - `window.FBRK_PUBLIC_ORIGIN = 'https://new.fbrk.kz'`
    - `window.FBRK_BACKEND_ORIGIN = 'https://fbrk.qdev.run'`
