# FBRK Dockerization Runbook

Last updated: 2026-05-21

## Production Status (2026-05-21)

Backend/admin on `fbrk.qdev.run` has been cut over from the legacy systemd
`fbrk-admin` process to Docker:

- container: `fbrk-admin`
- image: `fbrk-admin:local`
- compose file on VPS: `/opt/fbrk-admin/deploy/docker-compose.fbrk.yml`
- published port: `127.0.0.1:8787 -> 8787/tcp`
- restart policy: `unless-stopped`
- Docker daemon: enabled
- legacy systemd unit: `fbrk-admin` is stopped and disabled

No nginx production config change was required: nginx still proxies backend,
admin, API and SSR article requests to `127.0.0.1:8787`.

Safety snapshots taken before cutover:

- DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260521T171715Z-pre-dockerize.db`
  (`73M`)
- web-root snapshot:
  `/opt/fbrk-admin/web-snapshots/20260521T171715Z-pre-dockerize`
- admin/deploy snapshot:
  `/opt/fbrk-admin/admin-snapshots/20260521T171715Z-pre-dockerize`

Verified after cutover:

- `https://fbrk.qdev.run/` -> `200`
- `https://fbrk.qdev.run/admin/healthz` -> `200`
- `https://fbrk.qdev.run/admin/login` -> `200`
- representative SSR article `/a/<slug>` -> `200`
- `https://fbrk.qdev.run/sitemap.xml` -> `200`
- `https://fbrk.qdev.run/feed.xml` -> `200`
- container health: `healthy`
- compose syntax check: `docker compose -f deploy/docker-compose.fbrk.yml
  config --quiet`
- job image smoke: `docker compose -f deploy/docker-compose.fbrk.yml run --rm
  --no-deps rss python -m py_compile ingest_fbrk.py enrich.py app/main.py`
- split linkage to `new.fbrk.kz` strict check:
  `BACKEND_TOTAL=4715`, `NEW_TOTAL=4715`, delta `0`, matching SHA256 for
  `data.js`, `data-archive.js`, `article-full.js`, and `data/videos.json`.

Operational note: do not paste raw `docker compose config` output into tickets
or PRs because Compose expands `/etc/fbrk-admin/fbrk-admin.env`.

## Target Architecture

`fbrk.qdev.run` remains the full canonical installation:

- FastAPI admin/backend
- SQLite database
- RSS ingest
- enrichment jobs
- public static web-root generation
- source for `new.fbrk.kz` split frontend sync

`new.fbrk.kz` remains public frontend only. It must not hold the canonical DB or
admin backend.

## Why Dockerize `fbrk.qdev.run` First

The split frontend depends on generated files from the full backend:

- `/js/data.js`
- `/js/data-archive.js`
- `/js/article-full.js`
- `/data/videos.json`
- `/img/uploads/...`
- `/sitemap.xml`, `/robots.txt`, `/feed.xml`

Dockerizing the backend first gives us a stable source for later ps.kz frontend
containerization.

## Files

- `admin/deploy/Dockerfile`
- `admin/deploy/docker-compose.fbrk.yml`
- `admin/.dockerignore`

The image intentionally uses `/opt/fbrk-admin` as its internal working directory
because legacy scripts expect that layout.

## Volume Contract

The container image contains app code. Runtime state stays on the host:

- `/opt/fbrk-admin:/host/fbrk-admin`
- `/var/www/fbrk.qdev.run:/var/www/fbrk.qdev.run`
- `/var/log/fbrk:/var/log/fbrk`

The container uses:

- `FBRK_DB_PATH=/host/fbrk-admin/fbrk.db`
- `FBRK_PUBLIC_ROOT=/var/www/fbrk.qdev.run`
- `FBRK_UPLOADS_DIR=/var/www/fbrk.qdev.run/img/uploads`
- `FBRK_DATA_JS=/var/www/fbrk.qdev.run/js/data.js`

This keeps SQLite WAL/shm sidecar files on the host and avoids baking secrets or
the DB into the image.

## Canary Deploy

Run these commands on the `fbrk.qdev.run` VPS.

```bash
cd /opt/fbrk-admin

docker compose -f deploy/docker-compose.fbrk.yml build admin
FBRK_ADMIN_HOST_PORT=8788 docker compose -f deploy/docker-compose.fbrk.yml up -d admin

curl -fsS http://127.0.0.1:8788/admin/healthz
curl -fsS -H "Host: fbrk.qdev.run" http://127.0.0.1:8788/admin/healthz
docker compose -f deploy/docker-compose.fbrk.yml ps
docker logs --tail=80 fbrk-admin
```

Use `docker compose -f deploy/docker-compose.fbrk.yml config --quiet` for
syntax validation. Avoid storing full rendered config output because it expands
secrets from `env_file`.

During canary mode the current systemd service keeps serving production on
`127.0.0.1:8787`.

## Read-only Canary Smoke

```bash
curl -fsS http://127.0.0.1:8788/admin/healthz
curl -fsS http://127.0.0.1:8788/sitemap.xml | head
curl -fsS http://127.0.0.1:8788/robots.txt | head
```

For article SSR, use a known published slug:

```bash
SLUG="$(python3 - <<'PY'
import json, urllib.request
text = urllib.request.urlopen('https://fbrk.qdev.run/js/data.js').read().decode()
payload = text[text.find('{'):].rstrip(';')
print(json.loads(payload)['articles'][0]['slug'])
PY
)"
curl -fsS "http://127.0.0.1:8788/a/${SLUG}" | grep -m1 '<title'
```

## Optional Job Smoke

Do not run these while the host cron is running unless you intentionally want a
manual job run.

```bash
cd /opt/fbrk-admin
docker compose -f deploy/docker-compose.fbrk.yml run --rm rss python ingest_fbrk.py rss --no-regen
docker compose -f deploy/docker-compose.fbrk.yml run --rm enrich python enrich.py --limit 1
```

## Cutover To Container Backend

Only after canary smoke is green:

```bash
TS="$(date -u +%Y%m%dT%H%M%SZ)"
sqlite3 /opt/fbrk-admin/fbrk.db ".backup '/opt/fbrk-admin/backups/fbrk-${TS}-pre-docker-cutover.db'"
test -s "/opt/fbrk-admin/backups/fbrk-${TS}-pre-docker-cutover.db"
mkdir -p "/opt/fbrk-admin/web-snapshots/${TS}-pre-docker-cutover"
rsync -a /var/www/fbrk.qdev.run/ "/opt/fbrk-admin/web-snapshots/${TS}-pre-docker-cutover/"

systemctl stop fbrk-admin
cd /opt/fbrk-admin
FBRK_ADMIN_HOST_PORT=8787 docker compose -f deploy/docker-compose.fbrk.yml up -d admin

curl -fsS http://127.0.0.1:8787/admin/healthz
curl -fsS https://fbrk.qdev.run/admin/healthz
```

Nginx can keep proxying to `127.0.0.1:8787`, so no nginx config change is
required for the backend cutover.

## Rollback

```bash
cd /opt/fbrk-admin
docker compose -f deploy/docker-compose.fbrk.yml down
systemctl enable --now fbrk-admin
curl -fsS https://fbrk.qdev.run/admin/healthz
```

If static output changed during a failed deploy, restore from the web snapshot
captured before cutover.

## Later Step: ps.kz Frontend

Completed on 2026-05-21.

`new.fbrk.kz` now runs as a static nginx container on the ps.kz frontend VPS:

- container: `new-fbrk-frontend`
- image: `nginx:1.27-alpine`
- compose file on VPS: `/opt/new-fbrk-frontend/deploy/docker-compose.new-fbrk.yml`
- published port: `127.0.0.1:8088 -> 8080/tcp`
- restart policy: `unless-stopped`
- host nginx: TLS terminator and reverse proxy to `127.0.0.1:8088`
- mounted frontend package: `/var/www/new.fbrk.kz:/usr/share/nginx/html:ro`

It receives only the split frontend package and never the canonical SQLite DB
or admin secrets.

Frontend safety snapshot before cutover:

- `/opt/new-fbrk-frontend/snapshots/20260521T173643Z-pre-dockerize/web-root`
- `/opt/new-fbrk-frontend/snapshots/20260521T173643Z-pre-dockerize/nginx-new.fbrk.kz.conf`

Verified after frontend cutover:

- `https://new.fbrk.kz/` -> `200`
- representative static article `/a/<slug>` -> `200`
- missing page -> `404`
- `/js/data.js` keeps `no-cache, no-store, must-revalidate`
- `/css/style.css` keeps `public, max-age=86400`
- container health: `healthy`
- nginx syntax check: `nginx -t`
