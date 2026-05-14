# Runbook: new.fbrk.kz Cutover

Date: 2026-05-14  
Target host: `148.230.117.131`  
Current public host: `fbrk.qdev.run`  

## Purpose

Safely move frontend entrypoint to `new.fbrk.kz` while preserving backend routes and rollback path.

## Non-negotiable safety rules

1. Do not mutate DB schema.
2. Before any nginx/prod file change: create fresh DB backup and web snapshot.
3. Do not remove `/opt/fbrk-admin/fbrk.db`.
4. After backend/template copies: `chown www-data:www-data` and restart `fbrk-admin`.
5. Validate with smoke checks before declaring done.

## Preflight

Run locally:

```bash
dig +short new.fbrk.kz A
dig +short fbrk.qdev.run A
curl -fsSI https://fbrk.qdev.run/ | sed -n '1,20p'
```

Expected before cutover:

- `fbrk.qdev.run -> 148.230.117.131`
- `new.fbrk.kz` must be changed to `148.230.117.131` before LE issuance.

## 1) Create safety snapshots on VPS

```bash
ssh root@148.230.117.131 '
set -e
TS=$(date -u +%Y%m%dT%H%M%SZ)
sqlite3 /opt/fbrk-admin/fbrk.db ".backup '\''/opt/fbrk-admin/backups/fbrk-${TS}-pre-new-fbrk-cutover.db'\''"
test -s /opt/fbrk-admin/backups/fbrk-${TS}-pre-new-fbrk-cutover.db
mkdir -p /opt/fbrk-admin/web-snapshots/${TS}
rsync -a /var/www/fbrk.qdev.run/ /opt/fbrk-admin/web-snapshots/${TS}/
echo "backup_ts=${TS}"
ls -lh /opt/fbrk-admin/backups/fbrk-${TS}-pre-new-fbrk-cutover.db
'
```

## 2) Deploy nginx config for new.fbrk.kz

Source of truth in repo: `admin/deploy/nginx-new-fbrk.conf`.

```bash
scp /path/to/repo/admin/deploy/nginx-new-fbrk.conf root@148.230.117.131:/etc/nginx/sites-available/new.fbrk.kz
ssh root@148.230.117.131 '
set -e
ln -sfn /etc/nginx/sites-available/new.fbrk.kz /etc/nginx/sites-enabled/new.fbrk.kz
nginx -t
'
```

Note: config references LE paths for `new.fbrk.kz`; cert must exist before reload.

## 3) DNS switch in PS panel

In `ps.kz` DNS panel:

1. Update `A` record for `new.fbrk.kz` to `148.230.117.131`.
2. Wait for propagation (`dig +short new.fbrk.kz A`).

## 4) Issue certificate

After DNS points correctly:

```bash
ssh root@148.230.117.131 '
set -e
certbot certonly --nginx -d new.fbrk.kz --non-interactive --agree-tos -m admin@qdev.run
test -s /etc/letsencrypt/live/new.fbrk.kz/fullchain.pem
test -s /etc/letsencrypt/live/new.fbrk.kz/privkey.pem
nginx -t
systemctl reload nginx
'
```

## 5) Smoke checks

```bash
curl -fsSI https://new.fbrk.kz/ | sed -n '1,25p'
curl -fsSI https://new.fbrk.kz/archive.html | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/about.html | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/sitemap.xml | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/robots.txt | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/no-such-page | sed -n '1,20p'
```

Expected:

- main/archive/about/sitemap/robots -> `200`
- unknown page -> `404`
- no TLS warning

Optional browser matrix:

- widths: `375, 768, 1024, 1440`
- pages: `/`, `/archive.html`, `/about.html`, sample `/a/<slug>`
- themes: light/dark

## 6) Rollback

If new host fails:

1. Remove nginx symlink and reload:

```bash
ssh root@148.230.117.131 '
set -e
rm -f /etc/nginx/sites-enabled/new.fbrk.kz
nginx -t
systemctl reload nginx
'
```

2. Revert DNS `new.fbrk.kz` to previous record in `ps.kz`.
3. If web files were changed, restore from `/opt/fbrk-admin/web-snapshots/<TS>/`.

## 7) Post-cutover follow-up

1. Decide canonical host policy (`fbrk.qdev.run` vs `new.fbrk.kz`).
2. Align static page canonical/OG URLs once policy is approved.
3. Preserve migration notes in `docs/audit/NEW_FBRK_STATUS_2026-05-14.md`.
