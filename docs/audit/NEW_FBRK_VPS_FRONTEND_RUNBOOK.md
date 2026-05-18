# Runbook: new.fbrk.kz on dedicated KZ VPS

Status date: 2026-05-18

## Purpose

`new.fbrk.kz` is the public static frontend. `fbrk.qdev.run` remains the
backend/admin/SQLite source of truth. The dedicated KZ VPS replaces the
temporary Plesk File Manager static sync path.

## Current topology

- Backend/admin VPS: `148.230.117.131`
- Frontend VPS: `213.155.22.190`
- Frontend IPv6: `2a00:5da0:2005:1::2d1`
- Frontend web-root: `/var/www/new.fbrk.kz`
- Frontend nginx site: `/etc/nginx/sites-available/new.fbrk.kz`
- Public origin: `https://new.fbrk.kz`
- Backend origin: `https://fbrk.qdev.run`

Current DNS still points to the legacy Plesk host until cutover:

- `A`: `195.210.46.10`
- `AAAA`: `2a00:5da0:1000::150`

The currently available Plesk API role can sync files but cannot mutate DNS
records (`dns.get_rec` returns `Permission denied`). DNS cutover must be done in
the ps.kz DNS panel or by an account/role with DNS permissions.

## Sync command

Run on the backend VPS:

```bash
/opt/fbrk-admin/scripts/sync_new_frontend_to_vps.sh
```

What it does:

- builds the same split-frontend package used for Plesk static mode;
- rewrites public runtime/canonical URLs to `https://new.fbrk.kz`;
- fetches fresh `data.js`, `data-archive.js`, and `article-full.js` from the
  backend;
- includes referenced `/img/uploads/...` assets plus small static image assets;
- deploys to the frontend VPS with `rsync` over SSH;
- reloads nginx after `nginx -t`.

No Plesk credentials are required.

## Pre-cutover verification

Before changing DNS:

```bash
curl --resolve new.fbrk.kz:80:213.155.22.190 -fsSI http://new.fbrk.kz/
curl --resolve new.fbrk.kz:80:213.155.22.190 -fsSI http://new.fbrk.kz/archive.html
curl --resolve new.fbrk.kz:80:213.155.22.190 -fsSI http://new.fbrk.kz/a/<valid-slug>
curl --resolve new.fbrk.kz:80:213.155.22.190 -fsSI http://new.fbrk.kz/no-such-page
```

Generated payloads must match backend:

```bash
for f in data.js data-archive.js article-full.js; do
  curl --resolve new.fbrk.kz:80:213.155.22.190 -fsS "http://new.fbrk.kz/js/$f" -o "/tmp/new-$f"
  curl -fsS "https://fbrk.qdev.run/js/$f" -o "/tmp/backend-$f"
  shasum -a 256 "/tmp/new-$f" "/tmp/backend-$f"
done
```

Each pair should have the same SHA256.

## DNS cutover

At ps.kz DNS, change only `new.fbrk.kz`:

- `A` -> `213.155.22.190`
- `AAAA` -> `2a00:5da0:2005:1::2d1`

Do not change `fbrk.qdev.run`.

After DNS resolves to the new VPS, issue the certificate on the frontend VPS:

```bash
certbot --nginx -d new.fbrk.kz --non-interactive --agree-tos -m admin@qdev.run --redirect
systemctl reload nginx
```

## Post-cutover verification

```bash
dig +short new.fbrk.kz A
dig +short new.fbrk.kz AAAA
curl -fsSI https://new.fbrk.kz/ | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/archive.html | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/a/<valid-slug> | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/no-such-page | sed -n '1,20p'
/opt/fbrk-admin/scripts/check_split_linkage.sh https://new.fbrk.kz https://fbrk.qdev.run --strict
```

## Rollback

DNS-only rollback:

- `A` -> previous Plesk IP `195.210.46.10`
- `AAAA` -> previous Plesk IPv6 `2a00:5da0:1000::150`

The backend/admin VPS is not changed by this frontend cutover.
