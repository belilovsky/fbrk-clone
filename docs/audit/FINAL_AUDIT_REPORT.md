# ФБРК — финальный пост-Codex аудит

## Follow-up audit — 5 мая 2026

**Среда:** prod `https://fbrk.qdev.run`, VPS `148.230.117.131`
**Состояние БД:** `4589` статей, `4505 news / 84 investigation`
**Статус:** публичный фронт, admin security, content DB, ingester/cron и infra quick-wins проверены и доведены до прода.

### Executive summary

1. Публичный сайт после AV DS-переделки проверен по sitemap и браузерной матрице: `4594/4594` внутренних URL OK; `60` page/viewport/theme checks OK; поиск, тема, mobile menu и archive filters OK.
2. Исправлены SSR-склейки вокруг inline-тегов (`<b>`, `<a>`, `<i>`) и punctuation-only legacy tags; problematic article sweep теперь чистый.
3. `/article.html` без `id` больше не подставляет мета-заголовок первой статьи; shell теперь `Материал не найден — ФБРК`, `noindex, follow`.
4. Главная получила static raw-HTML `<h1>` fallback для no-JS/первичного HTML; после JS он заменяется актуальной главной новостью.
5. Admin dashboard hardened: inline `onclick` actions заменены на `data-admin-action` + event delegation; authenticated prod smoke показывает `onclick_count=0`.
6. Content DB integrity: `body_json`/`sections_json` пустых нет; `editorjs_to_sections(body_json)` совпадает с `sections_json` у всех `4589`; `data.js` и `data-archive.js` hash-match с dry-run.
7. Нормализованы 2 high-confidence `source` URL; 10 text-source строк оставлены без изменений, потому что canonical candidates на fbrk.kz не подтвердились.
8. Ingester синхронизирован с production source и сделан идемпотентным: double `rss --no-regen` не меняет article count, `updated_at` и `data.js` hash.
9. Infra quick-wins: HSTS `max-age=15552000`, `server_tokens off`, `/etc/logrotate.d/fbrk`; nginx reload OK.
10. На новом VPS диск здоровый: `/` used `31%`; DB backups около `1.00G`, web snapshots `5.6G`.

### PRs / branches

- PR #6 `audit/frontend-home-avds-refresh`: AV DS public pages + SSR/article shell/home fallback fixes. Deployed and smoke-tested.
- PR #7 `audit/security-admin-js`: admin dashboard inline JS hardening. Deployed and smoke-tested.
- PR #8 `audit/content-db-integrity`: content DB evidence + 2 source URL normalizations. DB updated with backup.
- PR #9 `audit/ingester-prod-sync-idempotency`: prod ingester sync + idempotent RSS UPSERT. Deployed and double-run verified.
- PR #10 `audit/infra-hsts-logrotate`: HSTS/server_tokens/logrotate. Deployed and header-verified.

### Fresh backups / snapshots created

- Public/SSR/frontend deploys: `/opt/fbrk-admin/backups/fbrk-20260504T194512Z-pre-public-avds-refresh.db`, `/opt/fbrk-admin/backups/fbrk-20260504T195034Z-pre-public-avds-shell.db`, plus web/template snapshots.
- SSR inline fixes: `/opt/fbrk-admin/backups/fbrk-20260504T200739Z-pre-ssr-inline-spacing.db`, `/opt/fbrk-admin/backups/fbrk-20260504T200906Z-pre-ssr-punctuation-cleanup.db`, `/opt/fbrk-admin/backups/fbrk-20260504T201146Z-pre-ssr-inline-legacy-tags.db`, `/opt/fbrk-admin/backups/fbrk-20260504T201936Z-pre-ssr-nested-inline-spacing.db`.
- Public shell/cache/home fallback: `/opt/fbrk-admin/backups/fbrk-20260504T202453Z-pre-public-shell-meta-cache.db`, `/opt/fbrk-admin/backups/fbrk-20260504T202931Z-pre-home-noscript-h1.db`.
- Admin security: `/opt/fbrk-admin/backups/fbrk-20260505T034222Z-pre-admin-dashboard-inline-js.db`.
- Content source normalization: `/opt/fbrk-admin/backups/fbrk-20260505T034616Z-pre-content-source-normalize-two.db`.
- Ingester: `/opt/fbrk-admin/backups/fbrk-20260505T035028Z-pre-ingester-idempotent-upsert.db`, `/opt/fbrk-admin/backups/fbrk-20260505T035058Z-pre-ingester-rss-idempotency-check.db`.
- Infra: `/opt/fbrk-admin/backups/fbrk-20260505T035422Z-pre-infra-hsts-logrotate.db`, config snapshot `/opt/fbrk-admin/config-snapshots/20260505T035422Z/nginx-fbrk.qdev.run`.

### Remaining deferred items

- CSP: add staged `Content-Security-Policy-Report-Only` first; direct enforcing CSP can break inline JSON-LD/admin scripts.
- Backup/web-snapshot retention: disk is fine now, but `/opt/fbrk-admin/web-snapshots` should get retention before it grows unchecked.
- Full external image crawl: local upload files are all present and external sample `120/120` is OK; a complete 4036-URL external crawl should be a slow scheduled check, not an ad-hoc burst.
- Nginx warnings from unrelated qdev sites: `nginx -t` succeeds but reports duplicate/conflicting server names outside FBRK scope.
- CSRF/rate limiting: admin uses `SameSite=Lax` and auth is working; explicit CSRF/origin enforcement plus login/API throttling should be a separate tested PR.

---

**Дата:** 29 апреля 2026
**Среда:** prod (`https://fbrk.qdev.run`, VPS 62.72.32.112)
**Состояние БД:** 4547 статей, 4464 news / 83 investigation

---

## Краткое резюме

После того как Codex прошёлся по проекту и сдал 4 PR (security, frontend, backend, audit-docs — все помержены), оставались задачи, требующие SSH-доступа на прод. Они закрыты в этой сессии:

1. ✅ Полный DB-аудит — целостность, индексы, дубликаты, источники
2. ✅ Нормализация категорий: 81 материал переклассифицирован в `investigation`
3. ✅ Регенерация `sections_json` для всех 4547 статей (идемпотентно)
4. ✅ Нормализация `source` URL: 531 запись `fbrk.kz` → `https://fbrk.kz/articles/<slug>`
5. ✅ Удалён 1 dup (Drupal `-0` суффикс)
6. ✅ **Восстановлена хронология**: 3968 статей с искусственной датой ингеста (2026-04-28) → настоящие даты публикации (через sitemap.xml fbrk.kz)
7. ✅ Исправлены 32 случая слитых слов в `dek` ("Алматыпресечена", "Борейкозаблокировали", "Скляррассказал", и т.п.)
8. ✅ Cron работает стабильно — 6 запусков/час, 1 новая статья за последний час
9. ✅ Все 4 бекапа БД проверены — integrity ok
10. ✅ nginx/systemd diff между prod и репо: 6 строк синхронизированы (404 page handling)
11. ✅ Disk usage 80% (стабильно, FBRK занимает ~1.2 ГБ из 387 ГБ)
12. ✅ Сверка с fbrk.kz по выборке: title/category/date/source совпадают

---

## Подробности

### 1. DB-аудит (4547 статей, после нормализации)

| Метрика | Значение |
|---|---|
| Всего статей | 4547 |
| Категории | 4464 news, 83 investigation |
| Диапазон дат | 2023-08-28 → 2026-04-29 |
| Уникальных дат | 542 |
| Пустые `body_json` | 0 |
| Пустые `image` | 0 |
| Пустые `source` | 0 |
| `source` в виде http URL | 4545 (2 — пресс-служба и telegram-канал) |
| Дубликатов по title | 0 |
| Integrity | ok (WAL on) |

### 2. Нормализация категорий

Реализован скрипт `/home/user/workspace/fbrk_audit/normalize_db.py` с двумя списками паттернов:

- **STRICT** (повышаются всегда): `latifundist`, `dosie-`, `otmyvani`, `vivod-aktivov`, `raskhody-regionov`, `finansovye-pokazateli-regionov`, `skhemy-raboty`
- **WEAK** (только в сочетании с ≥25 блоками тела): `dezinsekci`, `khishchen`, `epshtey`, `rakhat-alie`, `-skhem`, `-masimov`, `-dubae|-vena|-londone|-monako`, `prokuratur.*vskryla`, `presledovan`

Дополнительно: blocks≥25 + age≥7 дней → investigation.

**Итог: 2 → 83 investigation.**

### 3. Восстановление хронологии

**Проблема:** 3969 статей имели `date_iso=2026-04-28` (день массового ингеста), вместо настоящих дат публикации.

**Решение:** парсинг `https://fbrk.kz/sitemap.xml` (4519 записей с `lastmod`) → массовое обновление дат.

**До:** 1 дата охватывала 87% контента (визуально вся история сжата в 1 день).
**После:** 542 уникальных дат с реалистичным распределением:

| Год | Статей |
|---|---|
| 2023 | 12 |
| 2024 | 1838 |
| 2025 | 2193 |
| 2026 | 504 |

Для 25 главных серий-расследований (latifundisty главы 1-9, raskhody-regionov, finansovye-pokazateli-spk, skhemy-raboty) даты взяты прямо со страницы fbrk.kz через HTML парсинг.

### 4. Бекапы (все integrity=ok)

```
fbrk-20260428T165331Z.db                49M  4008 articles  (initial)
fbrk-20260428T182938Z-after-resync.db   67M  4547 articles
fbrk-20260429T053617Z-pre-codex-fixes.db 68M 4548 articles  (перед Codex deploy)
fbrk-20260429T055242Z-pre-normalize.db   65M 4548 articles
fbrk-20260429T060126Z-pre-date-fix.db    65M 4547 articles
fbrk-20260429T060315Z-pre-sitemap-dates.db 65M 4547 articles  (последний)
```

### 5. Cron — 24ч обзор

`*/10 * * * *` пуллит RSS fbrk.kz. За последний час сделано 6 ингестов, 1 новая статья (`oshibki-v-uchete-skota`). Все запуски завершались `regenerate_data_js` без ошибок.

### 6. Infra diff (prod vs репо)

- **systemd** (`fbrk-admin.service`, `fbrk-enrich.service`, `fbrk-enrich.timer`): идентичны
- **nginx** (`/etc/nginx/sites-enabled/fbrk.qdev.run`): на проде было 6 дополнительных строк (custom 404 page) — синхронизированы в репо commit `3d45001`

### 7. Очистка слитых слов

В 32 статьях найдены "слипания" — типичный артефакт парсинга HTML `<br>` без пробела (или конкатенации в Drupal):

- 29 числовых: `4млнзвонков`, `15млнтенге` → `4 млн звонков`, `15 млн тенге`
- 3 именных: `Борейкозаблокировали`, `Скляррассказал`, `Светлана Оксютарассказала` → разделены пробелом

После каждого фикса делалась перегенерация `sections_json` и `data.js`.

---

## GitHub state

Репо: `belilovsky/fbrk-clone` (private)
Master: содержит все 4 Codex PR (#1-4) + commit `fbb540f` (`ingest_fbrk.py`) + commit `3d45001` (nginx sync)

---

## Что ещё можно сделать (выходит за рамки этой сессии)

1. **CSP/HSTS** — Codex предложил в `infra-5.md`, требует отдельного PR
2. **Более точные даты для свежих статей** — sitemap отстаёт; через RSS можно получить более актуальные `pubDate`
3. **Enrichment pipeline** (`fbrk-enrich.service`) — не использовалось активно, можно подключить для авто-категоризации новых статей вместо паттернов

---

## Деплой статус

- БД: `/opt/fbrk-admin/fbrk.db` (66 MB) — актуальная
- `data.js`: 4547 articles, 5:53 mtime, 80 свежих в hot zone
- `data-archive.js`: 4547 articles, регенерирован
- nginx: reload не требовался (config не менялся в проде)
- systemd: не перезапускался (БД пишется через app, не требует рестарта)

Сайт работает, все 9 LiveBadge светятся, скриншоты в `/home/user/workspace/fbrk_final_*.png`.
