# Аудит ФБРК — 2026-04-28

> Update (2026-05-14): for current GitHub+VPS split status and `new.fbrk.kz` cutover baseline, see `docs/audit/NEW_FBRK_STATUS_2026-05-14.md`.

## Executive Summary

Проведён repo + public audit проекта `belilovsky/fbrk-clone` и публичного сайта `https://fbrk.qdev.run`.
Prod-only проверки VPS/SQLite/logs/cron/backup/restore заблокированы: SSH к `62.72.32.112` без интерактивного пароля вернул `Permission denied (publickey,password)`.
Gitleaks 8.30.1 просканировал 3 git-коммита, утечек не нашёл.
Публичный архив отдаёт 4547 статей; выборка 50 материалов против `fbrk.kz` показала 0 недоступных исходников, 0 расхождений заголовков, средний body ratio 0.997.
Найдены и локально исправлены три класса безопасных проблем: auth-hardening, frontend layout/a11y/LiveBadge, env compatibility.
Критичный blocker для ingester-аудита: актуальный `ingest_fbrk.py`, описанный в задании и README, отсутствует в `master`; без SSH невозможно сверить его с `/opt/fbrk-admin/ingest_fbrk.py`.

## Findings By Severity

### High

- **Ingester отсутствует в репозитории.** В `master` нет `ingest_fbrk.py`, хотя README и прод-контекст описывают cron `/opt/fbrk-admin/ingest_fbrk.py rss`. Нельзя проверить recent changes, splitter `<br><br>`, UPSERT и SIGTERM/WAL по source-controlled файлу. Статус: blocked/proposed sync PR после VPS-доступа.
- **Публичная классификация почти всех материалов как `news`.** `data-archive.js`: `news=4545`, `investigation=2`. Для издания расследований это ломает архив, навигацию и SEO-разделы. Статус: needs DB audit; массовую правку категорий не делать без approval.
- **Security headers неполные.** Публичные ответы имеют `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, но нет `Strict-Transport-Security` и `Content-Security-Policy`. Статус: proposed; CSP требует аккуратного плана из-за inline JSON-LD/скриптов и CDN Editor.js.

### Medium

- **Admin auth timing/cookie defaults.** В `admin/app/security.py` API key сравнивался через `==`, cookie в `admin/app/main.py` ставилась с `secure=False`. Исправлено в локальной ветке `audit/security/auth-hardening` (`3b6d9ec`): `hmac.compare_digest`, `FBRK_COOKIE_SECURE=true` по умолчанию.
- **LiveBadge зависел от timezone пользователя.** При локальной дате браузера `2026-04-29 GMT+0500` статьи `2026-04-28` уже теряли badge; логика сравнивала с browser-local date. Исправлено в `audit/frontend/badges-layout-a11y` (`885b389`): сравнение через `Intl.DateTimeFormat(... timeZone: "Asia/Almaty")`.
- **Горизонтальный скролл и a11y regressions.** Playwright: overflow на 375/1024, axe: contrast/heading/landmark violations, все динамические `<img>` без `width/height`. Исправлено в `audit/frontend/badges-layout-a11y` (`885b389`).
- **ENV mismatch для SQLite.** README/операционный контекст используют `FBRK_DB`, код принимал только `FBRK_DB_PATH`. Исправлено в `audit/backend/env-compat` (`b7f5b75`): оба имени поддержаны, `FBRK_DB_PATH` имеет приоритет.

### Low / Info

- `ruff` по Python: 16 замечаний, в основном unused imports и style в `publish.py`.
- `mypy` по `admin`: 3 ошибки типов в `editorjs.py` и `enrich.py`.
- Выборка 60 image HEAD: 0 broken images, но frontend smoke видел lazy/external image failures в headless до полной загрузки.
- TLS сертификат Let's Encrypt: `notAfter=Jul 22 17:04:56 2026 GMT`.
- `/api/articles/list` без ключа возвращает `401`, `/admin/` перенаправляет на login.

## Evidence

- `git ls-remote origin master`: `525684f6710185f93cad270c440d05c6b81bf451`.
- `gitleaks git --redact`: 3 commits scanned, 0 findings.
- Public headers `/`: `HTTP/2 200`, `server: nginx`, `x-content-type-options: nosniff`, `x-frame-options: SAMEORIGIN`, `referrer-policy: strict-origin-when-cross-origin`.
- Public archive parse: 4547 articles, date range `2025-05-06..2026-04-28`, duplicate slugs `0`, invalid dates `0`, empty dek `0`.
- Content sample 50: source failures `0`, qdev failures `0`, title mismatch `0`, body ratio min `0.901`, avg `0.997`.
- Axe before frontend fix: `/` had `color-contrast` and `landmark-complementary-is-top-level`; `/archive.html` and `/about.html` had `heading-order`.
- Local verification after frontend fix: axe violations `0` on `/`, `/archive.html`, `/about.html`; overflow false on 375 `/`, 1024 `/`, 1024 `/archive.html`.

## Status

- Draft PRs opened:
  - [#1](https://github.com/belilovsky/fbrk-clone/pull/1) `audit/security/auth-hardening` — auth defaults.
  - [#2](https://github.com/belilovsky/fbrk-clone/pull/2) `audit/frontend/badges-layout-a11y` — LiveBadge/layout/a11y/image dimensions.
  - [#3](https://github.com/belilovsky/fbrk-clone/pull/3) `audit/backend/env-compat` — `FBRK_DB` compatibility.
  - [#4](https://github.com/belilovsky/fbrk-clone/pull/4) `audit/report/full-audit` — audit report.
- Deferred:
  - DB integrity SQL, `sections_json` regeneration diff, cron logs, backup/restore dry-run, live nginx/systemd diff: blocked by SSH.
  - Category normalization and source normalization: requires DB evidence and owner approval before mass writes.
  - CSP/HSTS deploy: should be a separate infra PR with live nginx validation.

## Next Audit Recommendations

- First unlock VPS access, then sync `/opt/fbrk-admin/ingest_fbrk.py` into repo before deeper ingester work.
- Add a non-mutating DB audit script that emits JSON metrics for `body_json`, `sections_json`, categories, source URLs, duplicates and date validity.
- Add smoke Playwright + axe checks to CI for `/`, `/archive.html`, representative `/a/<slug>`, and `/404`.
- Add a written restore runbook and quarterly restore drill for `/opt/fbrk-admin/fbrk.db`.
