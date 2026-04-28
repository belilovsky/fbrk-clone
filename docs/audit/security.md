# Security Audit Notes

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
