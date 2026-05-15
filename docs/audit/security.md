# Security Audit Notes

## 2026-05-05 Follow-up: Admin Dashboard JS Surface

### Checked

- Heuristic secret scan over working tree: only code variable names / env lookups; no literal secrets.
- Heuristic secret scan over full reachable git history: 26 revisions scanned, 0 unique findings after excluding generated public data files.
- Public headers on `/` and `/admin/login`: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`; still no HSTS/CSP in live response.
- TLS certificate: Let's Encrypt `E8`, valid from `2026-04-23 17:04:57 GMT` to `2026-07-22 17:04:56 GMT`.
- Admin dashboard template reviewed for JS-string injection around article IDs.

### Finding Fixed

- **Medium / security / admin:** `admin/templates/dashboard.html` placed DB-backed article IDs inside inline `onclick` JavaScript strings. IDs are normally slug-like, but this is still a brittle JS-context pattern and blocks a stricter CSP later.
- **Fix:** replaced inline handlers with `data-admin-action` / `data-article-id` controls and event delegation; API paths now use `encodeURIComponent(id)`, edit links use `urlencode`.
- **Prod safety:** before deploy, created `/opt/fbrk-admin/backups/fbrk-20260505T034222Z-pre-admin-dashboard-inline-js.db`, `/opt/fbrk-admin/web-snapshots/20260505T034222Z/`, and `/opt/fbrk-admin/template-snapshots/20260505T034222Z/dashboard.html`.
- **Verification:** Jinja render on VPS with a hostile synthetic ID passed; authenticated dashboard smoke returned `dashboard_http=200`, `onclick_count=0`, `data_action_count=9179`, `fbrk-admin active`.

### Still Deferred

- Add HSTS and a staged CSP policy after checking live nginx includes and inline script requirements.
- Add login/API rate limiting after confirming expected admin workflows and reverse-proxy limits.
- Add explicit CSRF tokens or same-origin enforcement for session-auth write endpoints; `SameSite=Lax` helps, but a token/origin gate would be clearer.

## Checked

- Gitleaks 8.30.1 over full local git history: 0 findings.
- `admin/app/security.py`: password hashing uses `hashlib.scrypt` and `hmac.compare_digest` for password hash verification.
- API routes require session cookie or `X-API-Key`; unauthenticated `/api/articles/list` returned `401`.
- Public nginx headers include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.
- SQL grep did not find unsafe f-string user-input SQL; reviewed dynamic `LIMIT int(limit)` usages.

## Findings

- `X-API-Key` used direct equality in `master`; fixed in `audit/security/auth-hardening`.
- Admin cookie used `secure=False` in `master`; fixed in `audit/security/auth-hardening` with `FBRK_COOKIE_SECURE`.
- No CSP/HSTS in observed public headers; propose separate infra PR after live nginx validation.
- No CSRF token was observed on admin POST forms; session-auth write endpoints should be reviewed before adding token enforcement.
- No rate limiting was observed on login/API; propose nginx or app-level throttling after confirming expected admin workflows.
