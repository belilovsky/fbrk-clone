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

## Recommended Continuation Plan

1. Snapshot current VPS #2 web repo state into GitHub branch (including dirty tracked files).
2. Decide merge strategy:
   - Option A: rebase VPS stream onto `origin/master`.
   - Option B: merge `origin/master` into VPS stream and resolve intentionally.
3. Cutover prep for `new.fbrk.kz`:
   - Point DNS to `148.230.117.131`.
   - Issue LE cert for `new.fbrk.kz`.
   - Enable `nginx-new-fbrk.conf`.
   - Run smoke matrix on both hosts (`fbrk.qdev.run` and `new.fbrk.kz`).
4. Only after stable smoke, decide canonical/SEO host policy for the new frontend domain.

## Evidence (Key Commands)

- `dig +short fbrk.qdev.run A` -> `148.230.117.131`
- `dig +short new.fbrk.kz A` -> `195.210.46.10`
- `git ls-remote root@148.230.117.131:/var/www/fbrk.qdev.run` -> `7c7d396`
- `git ls-remote root@62.72.32.112:/var/www/fbrk.qdev.run` -> `a4ae632`
- `git rev-list --left-right --count origin/master...vps148/master` -> `11 4`
- `ls -l /etc/nginx/sites-enabled | grep new.fbrk.kz` on VPS #2 -> no enabled link

