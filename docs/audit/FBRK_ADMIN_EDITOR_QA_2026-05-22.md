# FBRK Admin Editor QA — 2026-05-22

## Scope

Проверка связки `fbrk.qdev.run/admin` -> SQLite -> generated public payloads
после контейнеризации backend/admin и split-фронта `new.fbrk.kz`.

Основной фокус:

- сохранение материала из Editor.js;
- upload обложек и inline images;
- CSRF contract для browser-session API mutations;
- согласованность admin-пароля с production env;
- безопасный Docker rebuild без смены порта nginx upstream.

## Findings

### Fixed: editor save/upload did not send CSRF

`/api/articles`, `/api/upload` и другие browser-session mutations уже требуют
`X-CSRF-Token`, но `admin/templates/editor.html` не передавал этот заголовок:

- `doSave()` отправлял только `Content-Type: application/json`;
- cover upload отправлял `FormData` без CSRF;
- Editor.js image tool не имел `additionalRequestHeaders`.

Это могло проявляться как "новости не сохраняются" и "картинки не
загружаются" при нормальной работе через браузерную сессию.

Исправление:

- добавлен `getAdminCsrfToken()`;
- добавлен `csrfHeaders(extra = {})`;
- JSON save, cover upload и Editor.js image upload используют общий helper.

Regression:

- `tests/test_admin_routes_smoke.py::test_admin_editor_mutation_fetches_include_csrf_header`.

### Fixed: admin password drift

Обычный login по `FBRK_ADMIN_USER` + `FBRK_ADMIN_PASSWORD` из
`/etc/fbrk-admin/fbrk-admin.env` возвращал `/admin/login?error=1`, хотя
JWT-session smoke проходил. Это значит, что DB password hash разошёлся с env.

Исправление:

- production `users.password_hash` для `admin` пересинхронизирован через
  серверный `app.security.hash_password()`;
- секрет не выводился в stdout и не записывался в git;
- audit event записан как `ops / sync_password / user`.

### Fixed: compose default port mismatch

Production nginx проксирует `/admin`, `/api`, `/a` на `127.0.0.1:8787`, а
`admin/deploy/docker-compose.fbrk.yml` имел fallback
`FBRK_ADMIN_HOST_PORT:-8788`. Во время deploy использовался явный
`FBRK_ADMIN_HOST_PORT=8787`, но дефолт в repo мог сломать следующий rebuild.

Исправление:

- fallback compose port изменён на `8787`;
- `README.md` обновлён под текущую Docker-схему.

## Production Gate

Перед prod mutation были сделаны свежие снимки:

- DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260522T043001Z-pre-admin-editor-csrf.db`
  (`76128256` bytes).
- Web snapshot:
  `/opt/fbrk-admin/web-snapshots/20260522T043001Z-pre-admin-editor-csrf`
  (`15444` files).
- Template snapshot:
  `/opt/fbrk-admin/template-snapshots/20260522T043001Z-pre-admin-editor-csrf`
  (`26` files).

Deploy:

- copied `admin/templates/editor.html` to `/opt/fbrk-admin/templates/editor.html`;
- `chown www-data:www-data`;
- rebuilt and recreated Docker service with
  `FBRK_ADMIN_HOST_PORT=8787 docker compose -f docker-compose.fbrk.yml up -d --build admin`;
- container `fbrk-admin` returned `running healthy`;
- `docker port fbrk-admin` stayed `8787/tcp -> 127.0.0.1:8787`;
- `/admin/healthz` returned `200`.

## Verification

Local:

- `.venv/bin/python -m pytest tests/test_admin_routes_smoke.py tests/test_admin_platform_primitives.py tests/test_public_entity_tags.py`
  -> `19 passed`.
- `node --test tests/article_js_filters.test.mjs` -> `1 passed`.

Production:

- `/admin/login` normal password flow:
  `302 /admin/`, session cookie set.
- `/admin/` after login:
  `200`, dashboard rendered.
- `/admin/new` after login:
  `200`, page contains CSRF meta and editor CSRF headers.
- temporary unpublished article smoke:
  create `200`, update `200`, delete `200`;
  temporary row after delete = `0`;
  published count stable: `4715 -> 4715`.
- upload smoke:
  session + CSRF PNG upload `200`;
  generated thumb/full WebP URLs returned HTTP `200`;
  smoke upload DB row and generated files were removed after verification.
- split sync cron exists:
  `/etc/cron.d/fbrk-new-vps-sync`, schedule `6,16,26,36,46,56 * * * *`;
  latest log shows `STATUS=synced`.

## Remaining Notes

- New uploads on `fbrk.qdev.run` become visible on `new.fbrk.kz` after the
  scheduled `sync_new_frontend_to_vps.sh` run, not instantly at upload time.
- The admin still has older inline template styles; no broad visual rewrite was
  done in this pass.
