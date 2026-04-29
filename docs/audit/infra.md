# Infra And DR Audit Notes

## Public Evidence

- TLS certificate: Let's Encrypt E8, valid from `Apr 23 17:04:57 2026 GMT` to `Jul 22 17:04:56 2026 GMT`.
- Public nginx identifies as `server: nginx`.
- Public headers lack observed HSTS and CSP.
- `/admin/` returns `302` to `/admin/login`.
- `/api/articles/list` returns `401` without API key.

## Repo Evidence

- `admin/deploy/fbrk-admin.service`: `User=www-data`, `Restart=on-failure`, `NoNewPrivileges=true`, `ProtectSystem=full`.
- No `LimitNOFILE` in systemd unit.
- `admin/deploy/fbrk-enrich.service` uses `EnvironmentFile=/opt/fbrk-admin/.env`, different from admin service `/etc/fbrk-admin/fbrk-admin.env`.
- `admin/deploy/nginx-fbrk.conf` includes basic headers but no HSTS/CSP.

## Blocked

- Live nginx config diff, systemd status, backups inventory, restore dry-run, disk usage, logrotate and cron logs require SSH access.
- No prod mutations were attempted because backup/snapshot gate could not be satisfied without SSH.
