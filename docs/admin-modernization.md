# FBRK Admin Modernization

Дата старта: 2026-05-17  
Статус: production deployed and live-smoke verified на `fbrk.qdev.run` и
`new.fbrk.kz`.

## Цель

Аккуратно подтянуть админку ФБРК к общему подходу ORTCOM / `qaz-admin-kit`,
не ломая текущие URL, SQLite CRUD, legacy/stub routes, media pipeline и
редакционные процессы.

## Текущее состояние

- Backend: FastAPI standalone service in `admin/app/main.py`.
- DB: SQLite, default production path `/opt/fbrk-admin/fbrk.db`; часть новых
  v0.x routes всё ещё использует hardcoded путь вместо `settings.db_path`.
- Auth/session:
  - cookie session `fbrk_admin` через JWT;
  - password hash: stdlib `scrypt`, with `pbkdf2_sha256` fallback for local
    Python builds where `hashlib.scrypt` is unavailable;
  - API routes принимают session cookie или `X-API-Key`;
  - cookie flags: `HttpOnly`, `SameSite=Lax`, `Secure` через
    `FBRK_COOKIE_SECURE` (`True` по умолчанию).
- Roles/RBAC:
  - отдельной ролевой модели нет;
  - любой валидный пользователь фактически получает admin-доступ.
- CSRF:
  - `/admin/*` form mutation routes теперь получают stateless HMAC token из
    общего admin shell и проверяют его на сервере;
  - `/admin/login` получил отдельный stateless login-CSRF token, потому что на
    странице входа ещё нет authenticated session subject;
  - `/api/*` mutation endpoints теперь разделяют режимы: `X-API-Key`
    automation работает без CSRF, а browser session mutations требуют
    `X-CSRF-Token`.
- Audit:
  - таблица `audit_log` используется частично в ads/categories/settings;
  - upload, article CRUD, publish/feature toggles, public data regenerate,
    bulk article actions, ads, categories and settings теперь пишут
    best-effort audit events через общий helper.
- Uploads:
  - `/api/upload` проверяет declared MIME, размер и открываемость через Pillow;
  - отдельной upload policy-прослойки до этого прохода не было;
  - media/thumb pipeline нельзя менять резко, потому что editor и public cards
    завязаны на `/img/uploads/thumb/*.webp`.
- Templates/layout:
  - public shell и SSR article уже на AV DS 3.7.1;
  - admin shell/login в этом проходе переведены на локальные AV DS fonts и
    Onest stack;
  - часть CRUD-шаблонов ещё содержит inline styles и старые class names
    (`btn`, `card`, `page-header`), но наследует общий admin shell.
- Tests:
  - есть публичные tests для article JS/entity tags;
  - FastAPI/Pillow/pytest отсутствуют в локальном host toolchain, поэтому
    route-level admin tests требуют отдельного test env.

## Риски

1. **CSRF gap**: closed for `/admin/*` form routes and browser-backed
   `/api/*` mutation endpoints; explicit `X-API-Key` automation stays
   compatible by design.
2. **Hardcoded production DB path**: часть legacy routes не уважает
   `FBRK_DB_PATH`, что мешает тестам и staging.
3. **Audit coverage gap**: основные mutation flows теперь идут через общий
   best-effort audit helper; remaining gap — route-level tests на реальном
   FastAPI test client после установки локальных зависимостей.
4. **Upload policy split**: проверка upload живёт в route-коде; нужна
   централизованная policy с magic-byte validation.
5. **Template drift**: admin CRUD pages постепенно росли патчами, есть inline
   styles и разные классы, но это надо чистить малыми шагами.

## Что вынесено в локальный общий слой

Создан project-neutral слой `admin/app/admin_platform/`, совместимый по идее с
будущим `qaz-admin-kit` adapter:

- `access.py` — Principal/roles helpers.
- `audit.py` — best-effort audit writer.
- `csrf.py` — stateless HMAC CSRF tokens.
- `session.py` — session cookie defaults.
- `paths.py` — settings-aware path helpers and safe joins.
- `responses.py` — redirect helpers.
- `templating.py` — shell context metadata.
- `uploads.py` — upload policy + magic-byte image validation.
- `settings.py` — admin platform metadata.

Private `qaz-admin-kit` intentionally not added as dependency: production
build/deploy access to private registry is not guaranteed.

## Safe next layers

1. ~~Wire `uploads.py` into `/api/upload`.~~ Done in this pass: route now uses
   centralized MIME/size/magic-byte validation and records a best-effort audit
   event after successful upload.
2. ~~Replace hardcoded DB paths in legacy routes with `settings.db_path`.~~
   Done in this pass for admin v0.x routes, ads API helpers and SSR ad lookup.
   Media browser now uses `settings.uploads_dir` for thumb discovery.
3. ~~Add CSRF token emission to admin shell and enforce it first on one low-risk
   mutation route.~~ Done as a wider safe pilot for `/admin/*` form routes:
   upload delete, ads toggle/update, categories add/delete, settings set and
   articles bulk now require the generated token.
4. ~~Design a compatible CSRF/API split for `/api/*` mutation fetches:~~
   browser session mutations should require `X-CSRF-Token`, while explicit
   `X-API-Key` automation must keep working. Done and covered by smoke tests.
5. ~~Add audit helper to article CRUD, uploads, bulk actions.~~ Done for API
   create/update/delete, publish/feature toggles, data regenerate, upload and
   `/admin/articles/bulk`.
6. Add FastAPI smoke tests once test deps are available:
   unauth redirect, login render, protected access, CSRF reject, safe mutation,
   upload policy. Done in local `.venv`.
7. Only after security primitives are stable: CRUD polish and inline style
   cleanup.

## Production readiness

Current status: **yes**.

The admin is operational, deployed, visually aligned with AV DS 3.7.1, and the
main security primitives are covered locally and smoke-verified on production.
The previous maintenance caveat is also closed in this branch: FastAPI startup
now uses lifespan, and legacy admin/SSR template calls are normalized by the
shared `AdminJinja2Templates` adapter.

## Editorial Policy Carrier Pass 2026-05-27

ФБРК теперь не только публичный носитель Editorial Hub, но и админ-носитель:

- добавлен защищённый раздел `/admin/editorial-policy`;
- публичные формулировки, статус, контакты и ссылка на Editorial Hub хранятся в
  `settings` с префиксом `editorial_policy.*`;
- сохранение и ручная публикация требуют session + CSRF;
- каждое изменение пишет best-effort audit event `editorial_policy`;
- публичный URL `/editorial-policy.html` остаётся статическим HTML для SEO,
  отказоустойчивости и синхронизации на split-фронтенд;
- генератор берёт актуальные header/footer из `index.html`, чтобы не было
  рассинхронизации shell.

Практическое правило: редактор меняет политику в админке, админка
перегенерирует статическую страницу, а public/split хосты получают готовый HTML
при обычном deploy/sync.

## Follow-up Pass 2026-05-22

Additional container-era admin/editor check after backend Dockerization:

- fixed `admin/templates/editor.html` so Editor.js save, cover upload and image
  tool upload all send the session CSRF token expected by `/api/*` mutation
  routes;
- synced the production `admin` DB password hash with
  `FBRK_ADMIN_PASSWORD` from `/etc/fbrk-admin/fbrk-admin.env` without exposing
  the secret in logs or git;
- corrected `admin/deploy/docker-compose.fbrk.yml` fallback host port to
  `8787`, matching live nginx upstreams;
- updated `README.md` to document the current Docker deployment instead of the
  legacy systemd restart path;
- detailed evidence is in
  `docs/audit/FBRK_ADMIN_EDITOR_QA_2026-05-22.md`.

Verification highlights:

- local `.venv/bin/python -m pytest tests/test_admin_routes_smoke.py tests/test_admin_platform_primitives.py tests/test_public_entity_tags.py`
  -> `19 passed`;
- `node --test tests/article_js_filters.test.mjs` -> `1 passed`;
- production `/admin/login` with env credential -> `302 /admin/`;
- production temporary unpublished create/update/delete through session + CSRF
  -> OK, no row residue, published count stable `4715 -> 4715`;
- production image upload through session + CSRF -> OK, generated WebP URLs
  returned `200`, smoke files/DB row removed after verification.

## Night Pass 2026-05-17

Дополнительный спокойный проход по связке `new.fbrk.kz` + `fbrk.qdev.run`
зафиксировал несколько безопасных хвостов старого публичного SSR-слоя:

- article SSR ещё ссылался на старый cache-token
  `/css/av-ds/tokens.css?v=202605050020`;
- в шапке SSR-статьи оставалась кнопка `EN`, хотя публичный сайт ФБРК ведётся
  на русском с переключателем `RU` / `ҚАЗ`;
- внизу статьи был клиентский fetch `/data/articles.json`, который на
  split-фронте `new.fbrk.kz` отдаёт 404 и не нужен для SSR;
- шаблон принудительно снимал жирное начертание с `<strong>/<b>` в тексте
  статьи, из-за чего терялось оригинальное форматирование;
- related-карточки могли тянуть описание материала, хотя на главной и в новых
  AV DS карточках оставлен только заголовок.

Исправление сделано без изменения схемы БД и без массовой правки статей:

- related materials теперь собираются серверно в `admin/app/seo.py` по
  категории/тегам и рендерятся в SSR без браузерного запроса;
- SSR-статья использует актуальный AV DS asset version, русский shell и
  безопасный escaping для `dek`;
- public design tokens/logo/favicon очищены от старых чужих font fallback и
  приведены к Onest/system stack;
- Plesk full-sync script теперь включает не только `style.css`/`app.js`, но и
  `css/av-ds/tokens.css`, `img/brand/logo.svg`, `img/favicon.svg`, чтобы
  `new.fbrk.kz` не оставался на старых asset-хвостах после split-sync;
- regression smoke расширен проверками SSR: нет `data-lang="en"`, нет
  `/data/articles.json`, нет старого cache-token, related-блок содержит
  заголовок связанного материала и не выводит его описание.

## Verification Log

- `.venv/bin/python -m pytest` — OK, 16 tests.
- `.venv/bin/python -m pytest tests/test_admin_platform_primitives.py tests/test_admin_routes_smoke.py tests/test_public_entity_tags.py` — OK, 16 tests.
- `python3 -m py_compile admin/app/main.py admin/app/security.py admin/app/seo.py admin/app/publish.py admin/app/admin_platform/*.py tests/test_admin_platform_primitives.py tests/test_admin_routes_smoke.py tests/test_public_entity_tags.py` — OK.
- `node --check js/app.js` — OK.
- `node tests/article_js_filters.test.mjs` — OK.
- `git diff --check` — OK.
- `.venv/bin/python -W error::DeprecationWarning -m pytest tests/test_admin_platform_primitives.py tests/test_admin_routes_smoke.py tests/test_public_entity_tags.py` — OK, 15 tests, no deprecation warnings.
- Active public/admin grep: no `v0.3`, `AV DS 2026`, `Fontshare`,
  `General Sans`, `Satoshi`, or `--color-accent` markers in active public/admin
  shell files.
- Route smoke covers admin login render, unauth redirect, protected dashboard,
  login CSRF reject/accept, CSRF reject/accept for `/admin/articles/bulk`,
  bad image upload rejection, session API mutation CSRF reject/accept,
  `X-API-Key` mutation compatibility, and admin-save ->
  `data.js`/`article-full.js` frontend contract.
- Live read-only smoke:
  - `https://new.fbrk.kz/` — 200, AV DS 3.7.1 footer, rendered article links
    point to `new.fbrk.kz/a/...`, no `fbrk.qdev.run/a/...` leak in rendered DOM.
  - `https://new.fbrk.kz/archive.html` — 200, AV DS 3.7.1, no console errors in
    browser check.
  - `https://new.fbrk.kz/no-such-page-codex-readonly-20260517` — 404 with AV DS
    shell.
  - `https://fbrk.qdev.run/admin/login` — 200, local AV DS fonts,
    `/admin/static/admin.css?v=8`, `AV DS 3.7.1`.
  - `https://new.fbrk.kz/js/data.js` and `https://fbrk.qdev.run/js/data.js` —
    both expose `totalCount=4671`, `embedded=200`, same current first article.
  - `article-full.js` on both hosts exposes 4671 full article records with
    rendered `sections`.
- Production deploy gate:
  - DB backup before first deploy:
    `/opt/fbrk-admin/backups/fbrk-20260517T111850Z-pre-admin-final.db` — 73M.
  - Web snapshot before first deploy:
    `/opt/fbrk-admin/web-snapshots/20260517T111850Z-admin-final` — 2.3G.
  - Admin snapshot before first deploy:
    `/opt/fbrk-admin/admin-snapshots/20260517T111850Z-admin-final` — 868K.
  - DB backup before login-CSRF deploy:
    `/opt/fbrk-admin/backups/fbrk-20260517T114006Z-pre-admin-login-csrf.db` — 73M.
  - Web snapshot before login-CSRF deploy:
    `/opt/fbrk-admin/web-snapshots/20260517T114006Z-admin-login-csrf` — 2.3G.
  - Admin snapshot before login-CSRF deploy:
    `/opt/fbrk-admin/admin-snapshots/20260517T114006Z-admin-login-csrf` — 880K.
  - DB backup before deprecation-cleanup deploy:
    `/opt/fbrk-admin/backups/fbrk-20260517T123357Z-pre-admin-deprecation-cleanup.db` — 73M.
  - Admin snapshot before deprecation-cleanup deploy:
    `/opt/fbrk-admin/admin-snapshots/20260517T123357Z-admin-deprecation-cleanup` — 608K.
  - Deploy scope: `admin/app/`, `admin/templates/`, `admin/static/`,
    `admin/scripts/` in first pass; `admin/app/`, `admin/templates/` in
    login-CSRF pass; `admin/app/` in deprecation-cleanup pass.
  - Ownership after deploy: `chown -R www-data:www-data` applied to deployed
    admin paths.
  - Service: `systemctl restart fbrk-admin`, `systemctl is-active` -> `active`,
    `/admin/healthz` -> 200.
  - Journal after restart: no `traceback`, `error`, or `exception` lines in
    checked window.
- Production auth/API smoke:
  - `/admin/` unauthenticated -> 302 `/admin/login`.
  - `/admin/login` -> 200, AV DS 3.7.1, `admin.css?v=8`, login CSRF hidden
    input present.
  - `/admin/login` POST without CSRF -> 403; with valid login CSRF reaches the
    normal login flow (302).
  - `/api/upload` with session but without CSRF -> 403.
  - `/api/upload` with session + CSRF and a corrupt image -> 400 image-policy
    rejection.
  - `/api/upload` with `X-API-Key` and a corrupt image -> 400 image-policy
    rejection.
  - `/api/articles/list` with `X-API-Key` -> 200.
  - Temporary unpublished article create/delete smoke through session + CSRF:
    create 200, delete 200, remaining matching records in SQLite = 0.
- Production frontend/backend linkage after admin save smoke:
  - `BACKEND_TOTAL=4671`, `NEW_TOTAL=4671`, delta `0`.
  - `data.js`, `data-archive.js`, `article-full.js` SHA-256 hashes match
    between `fbrk.qdev.run` and `new.fbrk.kz`.
- Browser smoke after deploy: home, archive, 404, admin login all have
    `consoleErrors=0`; home has 37 `https://new.fbrk.kz/a/...` links and 0
    `https://fbrk.qdev.run/a/...` article-link leaks.
- Maintenance cleanup after production pass:
  - `@app.on_event("startup")` replaced with FastAPI lifespan.
  - Admin and SSR templates now use `AdminJinja2Templates`, which normalizes
    legacy `TemplateResponse(name, context)` calls to Starlette's current
    request-first API.
  - Verified with deprecation warnings treated as errors.
  - Production deprecation-cleanup deploy: `fbrk-admin` restarted and active,
    `/admin/healthz` -> 200, checked journal window has no
    `traceback/error/exception/deprecat` lines.
  - Post-cleanup linkage: totals still `4671/4671`, delta `0`; hashes still
    match across `data.js`, `data-archive.js`, `article-full.js`.
  - Post-cleanup browser smoke: `new.fbrk.kz/` and `/admin/login` both have
    `consoleErrors=0`; login keeps CSRF input and AV DS 3.7.1 badge.
- Night pass local verification:
  - `python3 -m py_compile admin/app/main.py admin/app/security.py admin/app/seo.py admin/app/publish.py admin/app/admin_platform/*.py regen_covers.py tests/test_admin_kit_manifest.py tests/test_admin_platform_primitives.py tests/test_admin_routes_smoke.py tests/test_public_entity_tags.py` — OK.
  - `.venv/bin/python -m pytest` — OK, 16 tests.
  - `node --check js/app.js && node tests/article_js_filters.test.mjs` — OK.
  - `git diff --check` — OK.
  - Active grep: no `data-lang="en"`, `/data/articles.json`,
    `202605050020`, forced `font-weight: normal`, `a.dek|safe`,
    `AV Design System 2026`, `General Sans`, `Satoshi`, `Playfair`,
    `Georgia`, or `--color-accent` in active SSR/public assets.
- Night pass production gate:
  - DB backup:
    `/opt/fbrk-admin/backups/fbrk-20260517T172910Z-pre-public-ssr-nightpass.db`
    — 73M.
  - Web snapshot:
    `/opt/fbrk-admin/web-snapshots/20260517T172910Z-public-ssr-nightpass`
    — 2.3G.
  - Admin snapshot:
    `/opt/fbrk-admin/admin-snapshots/20260517T172910Z-public-ssr-nightpass`
    — 844K.
  - Deploy scope: `admin/app/seo.py`, `admin/templates/article_ssr.html`,
    public `style.css`, `css/av-ds/tokens.css`, logo/favicon assets, and
    `admin/scripts/sync_new_frontend_to_plesk.py`.
  - Ownership: deployed backend/template/static/script files installed with
    `www-data:www-data`.
  - Service: `systemctl restart fbrk-admin`, then `active`; local
    `/admin/healthz` -> 200.
  - Plesk split sync: `--full --force`, asset version `20260517173924`,
    `UPLOAD_FILES=76`, includes `css/av-ds/tokens.css`,
    `img/brand/logo.svg`, `img/favicon.svg`; final `STATUS=synced`.
- Night pass live verification:
  - `https://new.fbrk.kz/css/av-ds/tokens.css`, logo and favicon no longer
    contain `General Sans`, `Satoshi`, `Playfair`, `Georgia`, `sgeo-ui-kit` or
    Total-oriented comments; Onest/system stack is present.
  - Backend SSR article:
    no `data-lang="en"`, no `/data/articles.json`, no `202605050020`,
    no forced `font-weight: normal`, brand `theme-color=#0C115F`, related
    block present, related cards contain no `.card__dek`.
  - Browser DOM smoke:
    `new.fbrk.kz` home, archive, article, 404 and `fbrk.qdev.run/admin/login`
    render with AV DS 3.7.1, no EN button, no old cache token, no
    `/data/articles.json`; article page renders `Материалы по теме`; admin
    login has login-CSRF input.
  - API save/delete smoke with `X-API-Key`: temporary unpublished article
    created and deleted; DB residue `0`; published total stays `4671`.
  - Split linkage after smoke: `BACKEND_TOTAL=4671`, `NEW_TOTAL=4671`,
    delta `0`; `data.js`, `data-archive.js`, `article-full.js` hashes match.
  - Journal after deploy: `journalctl -u fbrk-admin -p warning..alert` for
    the checked window has no entries.
- Caveat:
  - scripted session-login smoke could not authenticate with the credentials
    available in `/etc/fbrk-admin/fbrk-admin.env` / `/opt/fbrk-admin/.admin_creds`;
    the login page itself is healthy and returns the normal `error=1` path for
    bad credentials. This looks like secret/password drift, not a runtime
    regression, and should be resolved by rotating or resyncing the admin
    password separately.

## Commits In This Pass

- `0619aff feat(admin): добавить локальный слой admin platform`
- `768dce0 fix(admin): централизовать проверку загрузок`
- `a592cbe refactor(admin): убрать жесткие пути к данным`
- `90a2ce0 fix(admin): добавить csrf для admin form routes`
- `45ce1ce fix(admin): расширить audit trail материалов`
- `26f2b0f refactor(admin): унифицировать audit helper`
- `4d54c04 test(admin): добавить smoke проверки админки`
- `b09a036 chore(admin): убрать старые av ds маркеры`
- `1d176a1 fix(admin): требовать csrf для session api mutations`
- `90b0a7f docs(admin): обновить hash финального csrf шага`
- `3bac58a fix(admin): добавить csrf для входа`
- `867e194 docs(admin): зафиксировать prod deploy финального прохода`
- `e129919 refactor(admin): убрать deprecated startup и template api`
- `7e64843 fix(public): убрать старые хвосты av ds и ssr статьи`
- `ca1d419 fix(deploy): синхронизировать все av ds assets на new fbrk`

## Night Follow-up 2026-05-17/18

Additional pass after the admin password drift report and image-loading
complaints.

Fixes:

- Rotated/recovered the production `admin` password without exposing it in git
  or logs. The current credential is stored only in root-owned
  `/opt/fbrk-admin/.admin_creds` (`0600`).
- Fixed `admin/templates/articles_list.html`: inline publish/featured scripts
  no longer render inside the `<title>` block, and the bulk action form now has
  an explicit CSRF hidden field in addition to the shell auto-injection.
- Fixed `admin/app/main.py`: `/admin/edit/{id}` now loads `article_meta`
  summary/entities/AI tags for normal Editor.js articles, not only legacy
  section-only articles.
- Updated `admin/scripts/sync_new_frontend_to_plesk.py`: split sync now uploads
  only the `/img/uploads/...` assets that are referenced by generated
  `data.js`, `data-archive.js`, or `article-full.js`. This repaired missing
  local upload images on `new.fbrk.kz` without uploading the whole 745 MB
  uploads tree or deleting anything.
- Maintenance cleanup: old web-root snapshots were trimmed to free disk space;
  `/` moved from 95% used to 73% used, with recent snapshots retained.

Safety gates:

- DB backup before password reset:
  `/opt/fbrk-admin/backups/fbrk-20260517T193542Z-pre-admin-password-reset-2.db`
  (`73M`).
- DB backup + web/admin snapshots before articles-list template deploy:
  `/opt/fbrk-admin/backups/fbrk-20260517T195512Z-pre-admin-list-template.db`
  (`73M`),
  `/opt/fbrk-admin/web-snapshots/20260517T195512Z-admin-list-template`
  (`2.3G`),
  `/opt/fbrk-admin/admin-snapshots/20260517T195512Z-admin-list-template`
  (`240K`).
- DB backup + admin snapshot before metadata editor deploy:
  `/opt/fbrk-admin/backups/fbrk-20260517T200600Z-pre-admin-meta-editor.db`
  (`73M`),
  `/opt/fbrk-admin/admin-snapshots/20260517T200600Z-admin-meta-editor`
  (`852K`).
- DB backup + scripts snapshot before Plesk upload-asset sync deploy:
  `/opt/fbrk-admin/backups/fbrk-20260517T203332Z-pre-plesk-upload-assets-sync.db`
  (`73M`),
  `/opt/fbrk-admin/admin-snapshots/20260517T203332Z-plesk-upload-assets-sync`
  (`96K`).

Verification:

- Local:
  - `python3 -m py_compile admin/app/main.py admin/app/security.py admin/app/seo.py admin/app/publish.py admin/app/admin_platform/*.py admin/scripts/sync_new_frontend_to_plesk.py regen_covers.py tests/test_admin_kit_manifest.py tests/test_admin_platform_primitives.py tests/test_admin_routes_smoke.py tests/test_public_entity_tags.py` — OK.
  - `.venv/bin/python -m pytest` — OK, 19 tests.
  - `node --check js/app.js` and `node tests/article_js_filters.test.mjs` — OK.
  - `git diff --check` — OK.
  - `ruff` and `mypy` are not installed in the local venv/host.
- Production admin:
  - `fbrk-admin` restarted and stayed `active`; `/admin/healthz` -> 200.
  - HTTPS login with the recovered credential works; dashboard and
    `/admin/articles` return 200.
  - `/admin/articles` title is clean, bulk form has CSRF, and inline toggle
    script is present.
  - Existing enriched article `neftegaz-avarii` shows `Метаданные NLP`.
  - Temporary unpublished article create/update/delete through session + CSRF
    succeeded; DB residue `0`, published total unchanged.
- Split frontend:
  - strict linkage after admin smoke and after Plesk upload sync:
    `BACKEND_TOTAL=4671`, `NEW_TOTAL=4671`, delta `0`, generated SHA256 values
    match for `data.js`, `data-archive.js`, and `article-full.js`.
  - `sync_new_frontend_to_plesk.py --force --dry-run` planned 336 files,
    including 323 referenced upload assets; live sync finished with
    `STATUS=synced`.
  - Previously broken upload URLs now return 200:
    `/img/uploads/thumb/20260430-104625-8a0468.webp`,
    `/img/uploads/thumb/20260423-193532-5fc0f1.webp`,
    `/img/uploads/thumb/20260424-191456-ec47b6.webp`,
    `/img/uploads/thumb/20260424-165748-9e72ed.webp`.
  - Random image sample after sync: 30 checked, 0 bad.
- Browser DOM smoke:
  - `new.fbrk.kz` home/archive/article/404 and `fbrk.qdev.run/admin/login`
    have `consoleErrors=0`, `lang="ru"`, `AV DS 3.7.1`, no old font markers,
    no `fbrk.qdev.run/a/` article-link leaks, and no images without `alt`.
  - Article page renders both `Упоминания` and `Материалы по теме`.

## 2026-05-18 new.fbrk.kz VPS cutover

The split frontend was moved from temporary Plesk static hosting to a separate
KZ frontend VPS in the same ps.kz account.

Changes:

- `new.fbrk.kz` DNS in the ps.kz/Plesk zone now points to the frontend VPS:
  `A 213.155.22.190`, `AAAA 2a00:5da0:2005:1::2d1`.
- Let's Encrypt certificate was issued on the frontend VPS with `certbot
  --nginx`; HTTPS redirect is active and certificate renewal is scheduled by
  certbot.
- Backend/admin remains on `https://fbrk.qdev.run`; no DB/backend migration was
  made during this cutover.
- Backend -> frontend VPS sync remains the primary publication path via
  `/opt/fbrk-admin/scripts/sync_new_frontend_to_vps.sh`.
- Plesk File Manager sync remains only as rollback/fallback while DNS
  propagation finishes and for emergency static rollback.

Verification:

- Authoritative DNS:
  `ns1.ps.kz`, `ns2.ps.kz`, and `ns3.ps.kz` all return
  `213.155.22.190` for A and `2a00:5da0:2005:1::2d1` for AAAA.
- Frontend VPS:
  `nginx -t` OK, `systemctl is-active nginx` -> `active`, cert expires
  `2026-08-16`.
- Live HTTPS:
  `https://new.fbrk.kz/` -> 200,
  `https://new.fbrk.kz/archive.html` -> 200,
  representative `/a/...` article -> 200,
  unknown page -> 404.
- Payload consistency:
  `data.js`, `data-archive.js`, and `article-full.js` SHA256 values match
  `https://fbrk.qdev.run/js/...`.
- Browser smoke:
  home, archive, and article render through `https://new.fbrk.kz`; article
  title, share URLs, `Упоминания`/`Материалы по теме`, and `AV DS 3.7.1` footer
  are present.

## 2026-05-24 final frontend polish

The final pre-prod/front-facing pass found one real desktop regression that was
worth closing before calling the split frontend finished: around `1280px` wide,
the public header grid was slightly wider than the viewport, so the right-side
action group could clip one of the social buttons even though mobile and full
desktop widths looked acceptable.

Changes:

- added a safer `minmax(0, 1fr)` middle track for `.site-header__inner`;
- allowed the nav cluster to shrink cleanly instead of pushing the action group
  off-canvas;
- added an intermediate desktop breakpoint (`max-width: 1320px`) that hides the
  long logo text, tightens nav pill padding, and reduces action spacing before
  the dedicated mobile breakpoint;
- bumped public asset references to `20260524115400` across public shells and
  `admin/templates/article_ssr.html` so the CSS fix is not lost behind browser
  cache.

Verification:

- Local verifier: `./scripts/verify_preprod.sh` -> OK, including `29 passed`,
  Python compile checks, and strict split linkage `STATUS=ok`.
- Local browser smoke:
  - `http://127.0.0.1:5057/` at `1280px`: `scrollWidth == clientWidth`,
    both social buttons visible, no header clipping.
  - `390px` home/article/admin: no horizontal overflow.
- Live browser smoke:
  - `https://new.fbrk.kz/` at `1280px`: `overflow=false`,
    `socialCount=2`, `/css/style.css?v=20260524115400`.
  - representative article on `new.fbrk.kz`: `overflow=false`,
    header action group fully visible.
  - `https://fbrk.qdev.run/admin/login`: renders cleanly with no overflow.

## 2026-05-24 Entity chips harmonization pass

После доработки AI-контента осталось техническое рассогласование: на карточках и
в SEO-инфо блоке сущности по-разному отрезались (32 в некоторых местах,
12 в других), плюс отсутствовала защита по количеству сущностей при
критических краях (0 / >12). Пробежались все публичные и SSR-пути и выровняли
лимиты.

Изменения:

- `admin/app/publish.py`
  - публичный лимит сущностей в `_public_entities` и сборке `_article_full_shape`
    поставлен в `12`.
- `admin/app/seo.py`
  - `_visible_entities` теперь лимитирует выдачу до `12`.
- `admin/enrich.py`
  - `_sanitize_result` жёстко режет AI-выход по `12` сущностям;
  - `--quality-rerun` теперь пересобирает записи с менее чем `2` или более чем
    `12` сущностями;
  - дата времени теперь в UTC-формате через `datetime.now(timezone.utc)`.
- `admin/templates/article_ssr.html` и `js/app.js`
  - отрисовка чипов сущностей унифицирована до `12`.

Проверка:

- `python3 -m pytest` -> `37 passed`.
- `article_full_shape` и `_visible_entities` теперь возвращают максимум `12` элементов
  в тестах.

## 2026-05-24 Split sync stabilization

Во время финального прохода обнаружилось, что актуальный live backend уже
смотрит не на старый VPS `62.72.32.112`, а на `148.230.117.131`, тогда как
`new.fbrk.kz` живёт на `213.155.22.190`. Из-за этого ручные проверки на старом
хосте могли давать ложное чувство, что правка уже в проде.

Что закрыто:

- live operational mapping перепроверен по DNS и HTTP;
- `sync_new_frontend_to_vps.sh` теперь:
  - принимает новый host key через `StrictHostKeyChecking=accept-new`;
  - автоматически использует `~/.ssh/fbrk_new_frontend_sync`, если ключ
    присутствует на backend host;
  - вычищает `.DS_Store` и `._*` из package и target tree;
- на live backend VPS `148.230.117.131` создан выделенный SSH key для sync на
  `213.155.22.190` и добавлен в `authorized_keys` frontend VPS;
- после этого штатный backend -> new frontend sync завершился `STATUS=synced`;
- финальный `scripts/verify_preprod.sh` прошёл зелёно (`STATUS=ok`).

## 2026-05-24 AI summary and entity quality pass

The next production-facing gap was not layout but content quality inside the AI
layer that powers article summary metadata, TTS copy, and public entity chips.
A live DB audit on the active backend host showed that all `4,727` published
articles already had `article_meta` rows, but a historical fallback wave from
`2026-05-14` had left a long tail of weak outputs:

- `589` rows still marked `model=fallback-local`;
- `621` short summaries were longer than the intended `180` characters;
- `508` short summaries simply echoed `dek`;
- `586` rows exposed entity lists typed entirely as `other`;
- a small tail of broken endings, title copies, or empty entities remained.

That was enough drift to justify a targeted rerun instead of pretending the AI
surface was "good enough".

Changes:

- added short-summary normalization helpers in `admin/enrich.py`:
  stripping source/date boilerplate, sentence-aware trimming, punctuation
  repair, and a hard `180`-character target for `summary_short`;
- added heuristic entity typing for fallback output so obvious `gov`, `org`,
  `place`, and `person` names no longer collapse into `other`;
- added `--quality-rerun`, which reselects only rows with
  `fallback-local`, overlong summaries, or title-copy short summaries;
- updated split static article rendering so `summaryShort` is now the first
  source for `<meta name="description">`, Open Graph, Twitter, and JSON-LD
  article descriptions instead of stale or overly long `dek`.

Verification:

- local tests:
  - `./.venv/bin/python -m pytest tests/test_public_entity_tags.py tests/test_static_article_meta.py -q`
    -> `14 passed`;
  - `python3 -m py_compile admin/enrich.py admin/scripts/sync_new_frontend_to_plesk.py`
    -> OK;
  - `./scripts/verify_preprod.sh` -> OK, including strict split linkage.
- live safety prep:
  - DB backup:
    `/opt/fbrk-admin/backups/fbrk-20260524T120742Z-pre-enrich-quality.db`;
  - code snapshot:
    `/opt/fbrk-admin/code-snapshots/20260524T120742Z-enrich-quality/enrich.py`.
- live rerun:
  - smoke batch:
    `python3 /opt/fbrk-admin/enrich.py --quality-rerun --limit 5 --model deepseek-chat --sleep 0.4`
    -> `ok=5 err=0`;
  - full batch:
    `python3 /opt/fbrk-admin/enrich.py --quality-rerun --model deepseek-chat --sleep 0.1`
    -> `DONE ok=918 err=0 total=918`.
- live end state after rerun and final normalization of the last two edge rows:
  - `fallback_local=0`
  - `long_summary=0`
  - `all_other=0`
  - `empty_summary=0`
  - `empty_entities=0`
  - `quality_queue_remaining=0`
- split publication:
  - regenerated `data.js` on backend and re-ran
    `/opt/fbrk-admin/scripts/sync_new_frontend_to_vps.sh`;
  - backend/new hashes matched for `data.js`, `data-archive.js`,
    `article-full.js`, and `search-index.js`;
  - curl-confirmed article HTML on `https://new.fbrk.kz/a/<slug>/` now exposes
    the cleaned AI summary in meta description, Open Graph, Twitter, and
    JSON-LD output.

Residual note:

- `region` is still empty on `1,193` rows. This is intentionally not treated as
  a blocker here because many national, broad, or non-local materials do not
  have a single defensible region label. The current pass focused on summary and
  entity quality, not forcing synthetic geography.

Follow-up entity pass:

The first rerun fixed summary quality and raw entity typing, but a second audit
showed two narrower tails still worth closing:

- `516` rows still matched the stricter quality selector because they had
  entity counts outside the desired `2..12` range;
- public `article-full.js` still contained `18` articles with fewer than two
  visible entity chips after public-type filtering.

Changes:

- expanded `--quality-rerun` selection in `admin/enrich.py` so it also requeues
  rows with `<2` or `>12` stored entities;
- capped sanitized model output to `12` stored entities;
- added small deterministic entity backfill from article context when the model
  still returns only one entity;
- capped public chip rendering to `12` across SSR and split static article
  pages;
- added a publication-layer supplement in `admin/app/publish.py` so obvious
  public entities such as money figures or clear org/place names can still
  appear when the raw stored entity list is too thin after public filtering,
  while explicitly avoiding awkward partial place fragments.

Verification:

- second live rerun:
  `python3 /opt/fbrk-admin/enrich.py --quality-rerun --model deepseek-chat --sleep 0.1`
  -> `DONE ok=516 err=0 total=516`;
- final DB state:
  - `entities_lt_2=0`
  - `entities_gt_12=0`
  - `summary_equals_dek=0`
  - `summary_ends_badly=0`
  - `region_empty=1111`
- final public state after regenerate + VPS sync:
  - `public_entities_lt_2=4`
  - `public_entities_gt_12=0`
  - split linkage strict smoke still passes with matching backend/new hashes and
    `STATUS=ok`.
