# FBRK Admin Modernization

Дата старта: 2026-05-17  
Статус: local/GitHub branch ready, без production deploy в этом блоке.

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

Current status: **with caveats**.

The admin is operational, visually aligned with AV DS 3.7.1, and the main
security primitives are now covered locally. Remaining caveats are mostly
operational: production deployment needs the usual backup/snapshot gate, and
the older FastAPI lifespan/template deprecation warnings can be cleaned in a
separate low-risk refactor.

## Verification Log

- `.venv/bin/python -m pytest tests/test_admin_platform_primitives.py tests/test_admin_routes_smoke.py tests/test_public_entity_tags.py` — OK, 15 tests.
- `python3 -m py_compile admin/app/main.py admin/app/security.py admin/app/seo.py admin/app/publish.py admin/app/admin_platform/*.py tests/test_admin_platform_primitives.py tests/test_admin_routes_smoke.py tests/test_public_entity_tags.py` — OK.
- `node --check js/app.js` — OK.
- `node tests/article_js_filters.test.mjs` — OK.
- `git diff --check` — OK.
- Active public/admin grep: no `v0.3`, `AV DS 2026`, `Fontshare`,
  `General Sans`, `Satoshi`, or `--color-accent` markers in active public/admin
  shell files.
- Route smoke covers admin login render, unauth redirect, protected dashboard,
  CSRF reject/accept for `/admin/articles/bulk`, bad image upload rejection,
  session API mutation CSRF reject/accept, `X-API-Key` mutation compatibility,
  and admin-save -> `data.js`/`article-full.js` frontend contract.
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
