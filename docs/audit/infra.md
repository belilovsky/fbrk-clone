# Infra And DR Audit Notes

## 2026-05-05 Prod Infra Follow-up

### Checked

- VPS: `Linux srv1626458`, Ubuntu kernel `6.8.0-110-generic`.
- Disk `/`: `193G` total, `59G` used, `135G` available, `31%` used.
- Largest FBRK-related paths: `/opt/fbrk-admin/web-snapshots` `5.6G`, `/opt/fbrk-admin/backups` `1.0G`, `/var/www/fbrk.qdev.run/img` `779M`, `/opt/fbrk-admin/fbrk.db` `69M`.
- DB backups: 15 files, total about `1.00G`, latest backup created before this audit block.
- Live nginx config for `fbrk.qdev.run` matched repo `admin/deploy/nginx-fbrk.conf` before this change.
- `nginx -t`: syntax OK, with unrelated warnings about duplicate/conflicting server names on other qdev sites.
- `fbrk-admin.service`: `User=www-data`, `Restart=on-failure`, `NoNewPrivileges=true`, `ProtectSystem=full`, `ReadWritePaths=/var/www/fbrk.qdev.run`.
- Certbot timer active; next run scheduled by `certbot.timer`.
- `/etc/logrotate.d/nginx` exists; no `/etc/logrotate.d/fbrk` was present.

### Findings Fixed

- **Medium / infra / security headers:** live FBRK responses lacked HSTS. Added `Strict-Transport-Security: max-age=15552000` for the HTTPS server block. Did not add `includeSubDomains` to avoid affecting unrelated qdev subdomains.
- **Low / infra / information exposure:** added `server_tokens off` inside the FBRK server block. This reduces nginx version disclosure where the directive applies.
- **Low / infra / logs:** added `/etc/logrotate.d/fbrk` coverage for `/var/log/fbrk/*.log`, `/opt/fbrk-admin/*cron.log`, and `/opt/fbrk-admin/enrich.log`.

### Prod Safety

- DB backup before deploy: `/opt/fbrk-admin/backups/fbrk-20260505T035422Z-pre-infra-hsts-logrotate.db`.
- Nginx backup before deploy: `/opt/fbrk-admin/config-snapshots/20260505T035422Z/nginx-fbrk.qdev.run`.
- Logrotate config deployed as `/etc/logrotate.d/fbrk`.
- Validation before reload: `nginx -t` OK; `logrotate -d /etc/logrotate.d/fbrk` parsed the new config.
- Reload used `systemctl reload nginx`; no webroot/DB changes required for this infra step.
- Header verification after reload: `server: nginx`, `strict-transport-security: max-age=15552000` on `/` and `/admin/login`.

### Still Deferred

- CSP: deferred because public pages and admin templates still use inline JSON-LD/scripts and external Editor.js/CDN assets. Needs staged `Content-Security-Policy-Report-Only` first.
- Backup/web-snapshot rotation: disk is currently healthy, but `/opt/fbrk-admin/web-snapshots` is already `5.6G`; add a retention policy before it grows again.
- Nginx warnings from unrelated qdev sites should be cleaned separately; not touched in the FBRK audit branch.

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
