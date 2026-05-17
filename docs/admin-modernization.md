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
