# FBRK Admin Modernization

Дата старта: 2026-05-17  
Статус: in progress, без production deploy в этом блоке.

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
  - password hash: stdlib `scrypt`;
  - API routes принимают session cookie или `X-API-Key`;
  - cookie flags: `HttpOnly`, `SameSite=Lax`, `Secure` через
    `FBRK_COOKIE_SECURE` (`True` по умолчанию).
- Roles/RBAC:
  - отдельной ролевой модели нет;
  - любой валидный пользователь фактически получает admin-доступ.
- CSRF:
  - `/admin/*` form mutation routes теперь получают stateless HMAC token из
    общего admin shell и проверяют его на сервере;
  - `/api/*` mutation endpoints пока остаются без обязательного CSRF, потому
    что они совместимы с session cookie и `X-API-Key` automation; для них нужен
    отдельный совместимый план, чтобы не сломать редактор/importer.
- Audit:
  - таблица `audit_log` используется частично в ads/categories/settings;
  - article CRUD и upload flows пока покрыты неполно.
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

1. **CSRF gap**: form/fetch mutation endpoints доступны с session cookie без
   CSRF token. Частично закрыто для `/admin/*` form routes; остаётся совместимый
   план для `/api/*` mutation endpoints.
2. **Hardcoded production DB path**: часть legacy routes не уважает
   `FBRK_DB_PATH`, что мешает тестам и staging.
3. **Audit coverage gap**: не все изменения статей/медиа фиксируются в
   `audit_log`.
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
4. Design a compatible CSRF/API split for `/api/*` mutation fetches:
   browser session mutations should require `X-CSRF-Token`, while explicit
   `X-API-Key` automation must keep working.
5. Add audit helper to article CRUD, uploads, bulk actions.
6. Add FastAPI smoke tests once test deps are available:
   unauth redirect, login render, protected access, CSRF reject, safe mutation,
   upload policy.
7. Only after security primitives are stable: CRUD polish and inline style
   cleanup.

## Production readiness

Current status: **with caveats**.

The admin is operational and now visually aligned with AV DS 3.7.1, but it is
not yet fully production-hardened because `/api/*` mutation endpoints still need
a compatible CSRF/API-key plan and article CRUD audit coverage is incomplete.

## Verification Log

- `python3 -m unittest tests/test_admin_platform_primitives.py` — OK, 6 tests.
- `python3 -m py_compile admin/app/main.py admin/app/seo.py admin/app/admin_platform/*.py tests/test_admin_platform_primitives.py` — OK.
- `git diff --check` — OK.
- FastAPI route-level smoke tests are still blocked locally by missing host
  dependencies (`fastapi`, `starlette`, `PIL`, `jwt`, `slugify`, `pytest`).
