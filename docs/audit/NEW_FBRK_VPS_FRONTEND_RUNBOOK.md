# Runbook: new.fbrk.kz on dedicated KZ VPS

Status date: 2026-05-21

Production status: cutover complete; static frontend is served by Docker.

## Purpose

`new.fbrk.kz` is the public static frontend. `fbrk.qdev.run` remains the
backend/admin/SQLite source of truth. A separate KZ VPS in the same ps.kz
account replaces the temporary Plesk File Manager static sync path.

## Current topology

- Backend/admin VPS: `148.230.117.131`
- Frontend VPS: `213.155.22.190` (same ps.kz account, separate VPS)
- Frontend IPv6: `2a00:5da0:2005:1::2d1`
- Frontend web-root: `/var/www/new.fbrk.kz`
- Frontend nginx site: `/etc/nginx/sites-available/new.fbrk.kz`
- Frontend Docker compose: `/opt/new-fbrk-frontend/deploy/docker-compose.new-fbrk.yml`
- Frontend container: `new-fbrk-frontend`
- Public origin: `https://new.fbrk.kz`
- Backend origin: `https://fbrk.qdev.run`

Host nginx terminates TLS and proxies HTTPS traffic to the local Docker nginx
container on `127.0.0.1:8088`. The container mounts
`/var/www/new.fbrk.kz` read-only, so the existing backend-to-frontend sync keeps
working without storing the canonical DB or admin secrets on the frontend VPS.

Current authoritative DNS for `new.fbrk.kz` points to the separate frontend
VPS in the same ps.kz account:

- `A`: `213.155.22.190`
- `AAAA`: `2a00:5da0:2005:1::2d1`

Legacy Plesk values were:

- `A`: `195.210.46.10`
- `AAAA`: `2a00:5da0:1000::150`

Plesk File Manager sync remains a rollback/fallback path only. The active
frontend is now the separate ps.kz VPS.

## Docker frontend status

Applied on 2026-05-21:

- Docker installed from Ubuntu packages on the frontend VPS.
- `new-fbrk-frontend` runs image `nginx:1.27-alpine`.
- Published port: `127.0.0.1:8088 -> 8080/tcp`.
- Restart policy: `unless-stopped`.
- Container health: `/healthz` inside the container.
- Host nginx config keeps ACME challenge handling on port `80` and proxies all
  HTTPS page/static traffic to `127.0.0.1:8088`.

Safety snapshot before Docker cutover:

- `/opt/new-fbrk-frontend/snapshots/20260521T173643Z-pre-dockerize/web-root`
- `/opt/new-fbrk-frontend/snapshots/20260521T173643Z-pre-dockerize/nginx-new.fbrk.kz.conf`

Runtime files:

- `/opt/new-fbrk-frontend/deploy/docker-compose.new-fbrk.yml`
- `/opt/new-fbrk-frontend/deploy/nginx-new-fbrk-container.conf`
- `/etc/nginx/sites-available/new.fbrk.kz`

Operational commands on the frontend VPS:

```bash
cd /opt/new-fbrk-frontend/deploy
docker compose -f docker-compose.new-fbrk.yml ps
docker compose -f docker-compose.new-fbrk.yml logs --tail=80 frontend
curl -fsS http://127.0.0.1:8088/healthz
nginx -t
```

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

Applied on 2026-05-18 in the `new.fbrk.kz` DNS zone:

- `A` record id `101864` -> `213.155.22.190`
- `AAAA` record id `101863` -> `2a00:5da0:2005:1::2d1`

Authoritative verification:

```bash
dig @ns1.ps.kz +short new.fbrk.kz A
dig @ns2.ps.kz +short new.fbrk.kz A
dig @ns3.ps.kz +short new.fbrk.kz A
dig @ns1.ps.kz +short new.fbrk.kz AAAA
dig @ns2.ps.kz +short new.fbrk.kz AAAA
dig @ns3.ps.kz +short new.fbrk.kz AAAA
```

Expected: all A answers are `213.155.22.190`; all AAAA answers are
`2a00:5da0:2005:1::2d1`.

After DNS resolves to the new VPS, issue the certificate on the frontend VPS:

```bash
certbot --nginx -d new.fbrk.kz --non-interactive --agree-tos -m admin@qdev.run --redirect
systemctl reload nginx
```

Certificate issued on 2026-05-18. Current expiry: 2026-08-16.

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

Docker verification:

```bash
ssh root@213.155.22.190 \
  'docker inspect --format "status={{.State.Status}} health={{.State.Health.Status}}" new-fbrk-frontend'
```

## Rollback

Docker frontend rollback on the frontend VPS:

```bash
cp /opt/new-fbrk-frontend/snapshots/20260521T173643Z-pre-dockerize/nginx-new.fbrk.kz.conf \
  /etc/nginx/sites-available/new.fbrk.kz
nginx -t
systemctl reload nginx
cd /opt/new-fbrk-frontend/deploy
docker compose -f docker-compose.new-fbrk.yml down
```

This returns `new.fbrk.kz` to direct host-nginx static serving from
`/var/www/new.fbrk.kz`.

DNS-only rollback:

- `A` -> previous Plesk IP `195.210.46.10`
- `AAAA` -> previous Plesk IPv6 `2a00:5da0:1000::150`

The backend/admin VPS is not changed by this frontend cutover.
