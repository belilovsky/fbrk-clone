# NEW Frontend Split Progress (2026-05-14)

## Контекст

Цель: `new.fbrk.kz` (KZ-hosting) держит фронтенд, `fbrk.qdev.run` держит backend+DB.

Ограничение: без роли Plesk с правом редактировать **Additional nginx directives** нельзя включить ключевой split-proxy слой на KZ-хосте.

---

## Что уже доведено (без Plesk-role)

1. Проверена связка backend/admin на проде:
   - `https://fbrk.qdev.run/admin/login` -> `200`
   - `https://fbrk.qdev.run/admin/healthz` -> `200`
   - `POST https://fbrk.qdev.run/api/publish` без ключа -> `401` (защита работает)

2. Добавлен и задеплоен smoke-скрипт связки:
   - repo: `admin/scripts/check_split_linkage.sh`
   - prod: `/opt/fbrk-admin/scripts/check_split_linkage.sh`
   - скрипт сверяет:
     - коды `200` для ключевых URL,
     - `totalCount` в `data.js` (`new` vs `backend`),
     - canonical на `new` (home/article).

3. Включен периодический мониторинг (без мутаций контента):
   - cron: `/etc/cron.d/fbrk-split-linkage-check`
   - лог: `/var/log/fbrk/split-linkage.log`
   - периодичность: каждые 30 минут.

4. Собран фронтенд sync-пакет для KZ-хоста (ручная синхронизация файлов, если нужно):
   - VPS: `/opt/fbrk-admin/backups/new-fbrk-sync-20260514T132403Z.tar.gz`
   - VPS checksums: `/opt/fbrk-admin/backups/new-fbrk-sync-20260514T132403Z/SHA256SUMS`
   - local copy: `fbrk_audit/new-fbrk-sync/new-fbrk-sync-20260514T132403Z.tar.gz`

---

## Текущий live-срез (13:23Z)

По `check_split_linkage.sh`:

- `BACKEND_TOTAL=4658`
- `NEW_TOTAL=4625`
- `DELTA_BACKEND_MINUS_NEW=33` (new-фронт отстаёт по публикациям)
- `NEW_CANONICAL_HOME=https://fbrk.qdev.run/`
- `NEW_CANONICAL_ARTICLE=https://fbrk.qdev.run/article.html`

Вывод: статика на `new` живая, но split-прокси не включен, и данные/каноникал на KZ-хосте не догоняют backend автоматически.

---

## Что осталось (единственный блокер)

Нужно дать роль в Plesk, где доступно редактирование **Additional nginx directives** для `new.fbrk.kz`.

После этого применяем:

1. `admin/deploy/plesk-new-fbrk-split-proxy.conf`
2. финальный smoke:
   - `/opt/fbrk-admin/scripts/check_split_linkage.sh https://new.fbrk.kz https://fbrk.qdev.run --strict`

Ожидаемый критерий готовности:
- `DELTA_BACKEND_MINUS_NEW=0`
- canonical на `new` указывает на `https://new.fbrk.kz/...`
- `/a/<slug>`, `/sitemap.xml`, `/feed.xml`, `/robots.txt` на `new` обслуживаются через split-маршруты.

---

## Hotfix (2026-05-14, вечером)

Выполнен аварийный фикс на `new.fbrk.kz` без прав Plesk Admin (через File Manager):

1. Карточки теперь ведут на `https://new.fbrk.kz/a/<slug>`, а не сразу на `fbrk.qdev.run`.
2. `article.html` переведён на абсолютные ассеты (`/css/...`, `/js/...`) и подключает `data-archive.js`,
   чтобы URL вида `/a/<slug>` больше не ломался из-за `404` на `/a/js/*` и `/a/css/*`.
3. `js/app.js` обновлён:
   - поддержка чтения slug из пути `/a/<slug>`;
   - fallback-поиск статьи в `ARTICLES_ARCHIVE`, если нет в `FBRK_DATA`;
   - fallback-рендер текста из `dek`, если `sections` отсутствуют;
   - мягкий fallback на backend только если статьи нет в локальных данных вообще.

Smoke после выкладки:
- главная генерирует ссылки на `new.fbrk.kz/a/...`;
- `https://new.fbrk.kz/a/trekhkratnyi-...` открывается на `new.fbrk.kz` (без редиректа на `fbrk.qdev.run`);
- `https://new.fbrk.kz/a/latifundisty-kazakhstana-glava-7-yug` рендерится полностью из локального архива.

Важно: это рабочий hotfix маршрутизации и UI. Для 100% канонической схемы split-proxy всё ещё нужен доступ Plesk Admin к `Additional nginx directives`.

---

## Static sync (2026-05-14, 14:50Z)

После hotfix-а выполнена дополнительная безопасная синхронизация статики через
Plesk File Manager, без изменения БД/backend/systemd:

1. Обновлены на `new.fbrk.kz`:
   - `index.html`, `archive.html`, `about.html`, `article.html`, `404.html`;
   - `js/app.js`, `js/runtime-config.js`, `js/data.js`, `js/data-archive.js`;
   - `robots.txt`, `sitemap.xml`, `feed.xml`.
2. Данные догнаны до backend:
   - `https://new.fbrk.kz/js/data.js` -> `totalCount=4659`;
   - `https://fbrk.qdev.run/js/data.js` -> `totalCount=4659`;
   - `DELTA_BACKEND_MINUS_NEW=0`.
3. Raw SEO-файлы на KZ-хосте переписаны на `new.fbrk.kz`:
   - home canonical / OG / hreflang -> `https://new.fbrk.kz/...`;
   - `sitemap.xml` loc -> `https://new.fbrk.kz/...`;
   - `feed.xml` links/guid -> `https://new.fbrk.kz/...`;
   - `robots.txt` sitemap -> `https://new.fbrk.kz/sitemap.xml`.
4. Cache-busting обновлен до `v=202605141448` для HTML entrypoints.

Пакет сборки зафиксирован как воспроизводимый скрипт:
`admin/scripts/build_new_frontend_static_package.sh`.

Live smoke после синхронизации:

- `/`, `/archive.html`, `/about.html` -> `200`, без горизонтального скролла,
  без ссылок на `fbrk.qdev.run` в rendered DOM;
- `/a/latifundisty-kazakhstana-glava-7-yug` -> остаётся на `new.fbrk.kz`,
  полный текст рендерится из локального архива;
- `/a/kanal-k-30-v-turkestanskoy-oblasti-namereny-rekonstruirovat-v-2026-godu`
  -> остаётся на `new.fbrk.kz`, но показывает только fallback-текст из `dek`.

Следующий вечерний фикс: добавлен отдельный `article-full.js` для полного
статического body на `/a/<slug>`, чтобы новые статьи на `new.fbrk.kz` не
зависели от компактного listing-поля `dek`.

---

## Article body static payload (2026-05-14, 15:40Z)

Закрыт остаточный дефект статических статей на `new.fbrk.kz`:

1. Backend publish теперь генерирует `/js/article-full.js`:
   - `ARTICLE_FULL_ARTICLES=4659`;
   - файл содержит только публичные поля карточки + `sections`;
   - не содержит `body_json`, admin-полей, авторских имён.
2. `article.html` на static-хосте грузит `/js/article-full.js` вместо
   `/js/data-archive.js` для полной article-page отрисовки.
3. `js/app.js` для body сохраняет разрешённое inline-форматирование:
   `<b>`, `<strong>`, `<i>`, `<em>`, `<a>`, `<br>`, `<img>`, но санитайзит
   произвольный HTML перед вставкой в DOM.
4. `admin/scripts/check_split_linkage.sh --strict` теперь проверяет не только
   `data.js`, но и наличие/актуальность `article-full.js`.

Safety gates перед deploy на активный VPS `148.230.117.131`:

- DB backup: `/opt/fbrk-admin/backups/fbrk-20260514T152734Z-pre-article-full.db`
  (`72M`, non-zero).
- Web snapshot: `/opt/fbrk-admin/web-snapshots/20260514T152734Z/` (`2.3G`).
- Plesk HTTP snapshot: `fbrk_audit/plesk-backups/20260514T153809Z/`.

Live verification:

- `https://new.fbrk.kz/js/article-full.js` -> `200`, `ARTICLE_FULL_ARTICLES=4659`;
- strict linkage -> `DELTA_BACKEND_MINUS_NEW=0`;
- headless Chrome на свежей статье
  `/a/kanal-k-30-v-turkestanskoy-oblasti-namereny-rekonstruirovat-v-2026-godu`:
  `p_count=12`, `b_count=32`, `a_count=1`, `img_count=1`.

Long-term: Plesk split-proxy всё ещё предпочтительнее, потому что отдаёт SSR
без тяжёлого static payload, но на конец дня `new.fbrk.kz/a/<slug>` уже не
теряет полный текст свежих статей.

---

## Admin dashboard recovery (2026-05-14, 16:20Z)

После split-работ публичная админка на `https://fbrk.qdev.run/admin/`
редиректила неавторизованного пользователя на `/admin/login`, но после логина
dashboard падал при рендере live-шаблона: `jinja2.exceptions.UndefinedError:
'stats' is undefined`.

Root cause: на VPS уже лежала новая версия admin UI с KPI-блоками, `recent` и
`audit`, но route `/admin/` всё ещё отдавал старый контекст только с
`articles` и `user`. Активные live-файлы админки синхронизированы обратно в
репозиторий, чтобы следующий деплой из GitHub не откатил рабочие разделы.

Safety gates перед deploy на активный VPS `148.230.117.131`:

- DB backup: `/opt/fbrk-admin/backups/fbrk-20260514T161856Z-pre-admin-dashboard.db`
  (`72M`, non-zero).
- Web snapshot: `/opt/fbrk-admin/web-snapshots/20260514T161856Z/` (`2.3G`).
- Admin snapshot:
  `/opt/fbrk-admin/admin-snapshots/20260514T161856Z/` (`752K`).

Deploy:

- обновлены `/opt/fbrk-admin/app/main.py`, активные
  `/opt/fbrk-admin/templates/*.html`, `/opt/fbrk-admin/static/admin.css`;
- применён `chown www-data:www-data`;
- выполнен `python3 -m py_compile /opt/fbrk-admin/app/main.py`;
- выполнен `systemctl restart fbrk-admin`, сервис `active`.

Live verification:

- `https://fbrk.qdev.run/admin/login` -> `200`;
- `https://fbrk.qdev.run/admin/healthz` -> `200`;
- `https://fbrk.qdev.run/admin/` без cookie -> `302` на `/admin/login`;
- `https://fbrk.qdev.run/admin/` с валидной session cookie -> `200`,
  dashboard содержит `Всего материалов`, `Последние материалы`, `Сущности`;
- authenticated smoke for `/admin/home`, `/admin/articles`,
  `/admin/categories/list`, `/admin/tags/list`, `/admin/entities/list`,
  `/admin/ads/list`, `/admin/uploads/list`, `/admin/audit/list`,
  `/admin/settings/list` -> `200`;
- в `journalctl -u fbrk-admin --since "2026-05-14 16:20:00 UTC"` нет
  `UndefinedError`, `Traceback` или `ERROR`.

---

## Admin save + image preview recovery (2026-05-14, 16:45Z)

После восстановления dashboard обнаружены два связанных дефекта в админке:

1. Сохранение материала возвращало `500 Internal Server Error`.
   Root cause: `regenerate_data_js()` не мог создать
   `/var/www/fbrk.qdev.run/js/data.js.lock`, потому что директория `js/` и
   сгенерированные файлы были под чужим владельцем (`501:staff`/`root`), а
   backend работает как `www-data`.
2. Обложки с абсолютными URL `https://fbrk.kz/...` в admin templates
   превращались в `/<https-url>` и не грузились в preview/listing.

Safety gates перед deploy:

- DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260514T163915Z-pre-admin-save-images.db`
  (`72M`, non-zero).
- Web snapshot: `/opt/fbrk-admin/web-snapshots/20260514T163915Z/` (`2.3G`).
- Admin snapshot:
  `/opt/fbrk-admin/admin-snapshots/20260514T163915Z/` (`756K`).

Fix:

- `chown -R www-data:www-data /var/www/fbrk.qdev.run/js` и нормальные
  read/write permissions для generated JS.
- `admin_asset_url()` добавлен в Jinja globals для обеих admin template envs.
- `editor.html`, `articles.html`, `articles_list.html`, `ad_edit.html`
  больше не добавляют `/` перед absolute/external image URL.
- В editor JS preview добавлен такой же URL normalizer.
- Исправлен typo `<scritt>` -> `<script>` для tag chips.

Live verification:

- реальный `PUT /api/articles/smi-soobschayut-o-zaderzhanii-zamnachalnika-rop-po-podozreniyu-vo-vzyatke-v-sko`
  с валидной session cookie -> `200 OK`;
- после PUT перегенерированы:
  `/var/www/fbrk.qdev.run/js/data.js`,
  `/var/www/fbrk.qdev.run/js/data-archive.js`,
  `/var/www/fbrk.qdev.run/js/article-full.js`;
- `/admin/articles`, `/admin/edit/<slug>`, `/admin/ads/list`,
  `/admin/uploads/list` -> `200`;
- на проверенных admin pages `bad_prefixed_external=0` для `src="/https://..."`;
- `https://fbrk.qdev.run/admin/healthz` -> `200`;
- `https://fbrk.qdev.run/js/data.js` -> `200`;
- `https://new.fbrk.kz/` -> `200`;
- в свежем `journalctl` после финального restart нет `PermissionError`,
  `UndefinedError`, `Traceback`, `ERROR`.

---

## Publish lock hardening (2026-05-15, 04:35Z)

После восстановления сохранения найден более глубокий root cause: RSS cron
запускается от `root` и при появлении новых материалов тоже вызывает
`regenerate_data_js()`. Из-за этого `/var/www/fbrk.qdev.run/js/*.js` и старый
web-root lock могли снова становиться root-owned, а следующий save из FastAPI
под `www-data` падал на lock-файле.

Fix:

- publish lock перенесён из web-root в `/tmp/fbrk-publish-<hash>.lock`;
- lock-файл выставляется в `0666`, чтобы root-cron и backend `www-data`
  могли безопасно сериализовать одну и ту же публикацию;
- `check_split_linkage.sh --strict` дополнительно сравнивает SHA256 для
  `/js/data.js`, `/js/data-archive.js`, `/js/article-full.js`, а не только
  количество статей.

Safety gates перед deploy на активный VPS `148.230.117.131`:

- DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260515T043307Z-pre-publish-lock.db`
  (`72M`, non-zero).
- Web snapshot: `/opt/fbrk-admin/web-snapshots/20260515T043307Z/` (`2.3G`).
- Admin snapshot:
  `/opt/fbrk-admin/admin-snapshots/20260515T043307Z/` (`488K`).

Live verification:

- `python3 -m py_compile /opt/fbrk-admin/app/publish.py` -> OK;
- `systemctl restart fbrk-admin` -> сервис `active`;
- root-run `regenerate_data_js()` -> OK, generated JS root-owned, lock
  `/tmp/fbrk-publish-aefcfb66460cc07e.lock` имеет mode `0666`;
- после root-run реальный authenticated `PUT /api/articles/...` из админки
  -> `200 OK`, generated JS снова успешно перезаписаны backend-процессом;
- `journalctl -u fbrk-admin` после проверки не содержит `PermissionError`,
  `Traceback` или `ERROR`.

Plesk static sync:

- перед синхронизацией `check_split_linkage.sh --strict` поймал stale-статику:
  `DELTA_BACKEND_MINUS_NEW=0`, но SHA256 отличались для всех трёх generated
  payload-файлов;
- во время первого sync RSS cron добавил ещё один материал, backend стал
  `4660`, поэтому payload был переснят и выгружен повторно;
- HTTP snapshot старой Plesk-статики:
  `fbrk_audit/plesk-backups/20260515T045254Z/`;
- свежий sync-пакет:
  `fbrk_audit/generated-sync-20260515T045254Z/`;
- через Plesk File Manager API обновлены:
  `/new.fbrk.kz/js/data.js`,
  `/new.fbrk.kz/js/data-archive.js`,
  `/new.fbrk.kz/js/article-full.js`;
- финальный strict smoke на VPS:
  `BACKEND_TOTAL=4660`, `NEW_TOTAL=4660`,
  `BACKEND_ARTICLE_FULL_TOTAL=4660`, `NEW_ARTICLE_FULL_TOTAL=4660`,
  SHA256 всех трёх generated files совпадают, ключевые страницы `200`.

Maintenance note:

- ошибочно широкий admin snapshot `20260515T044346Z` был остановлен и удалён
  только внутри `/opt/fbrk-admin/admin-snapshots/`;
- вместо него создан узкий code snapshot тех же timestamp/path с размером
  `684K`, без рекурсивного копирования `backups/`, `web-snapshots/` и
  `admin-snapshots/`.

---

## Article enrichment UI recovery (2026-05-15, 08:20Z)

После split-static выноса на `new.fbrk.kz` пропал старый публичный слой
обогащения на страницах материалов: summary/тезисы, сущности и видимые теги.

Root cause:

- `article_meta` в БД был заполнен (`4654` meta rows, `4651` материалов с
  сущностями, `4654` с key points), но `article-full.js` сериализовал только
  карточные поля и `sections`;
- static article renderer на `new.fbrk.kz` не рендерил tag chips/entities под
  текстом;
- SSR на `fbrk.qdev.run/a/...` рендерил сущности, но видимые теги и
  `summary_short` в блоке «Кратко» не выводились.

Fix:

- `article-full.js` теперь получает публичные поля:
  `summaryShort`, `keyPoints`, `entities`, объединённые manual/auto tags;
- `js/app.js` рендерит блок «Кратко», «Упоминания» и tag chips на static
  `/a/<slug>`;
- SSR template `article_ssr.html` тоже выводит `summary_short` и tag chips;
- cache-busting для `style.css`, `app.js`, `article-full.js` обновлён до
  `202605151005`;
- Plesk package builder теперь включает `css/style.css`, чтобы CSS не
  отставал от HTML/JS.

Safety gates перед deploy на активный VPS `148.230.117.131`:

- DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260515T081328Z-pre-article-enrichment-ui.db`
  (`73M`, non-zero).
- Web snapshot: `/opt/fbrk-admin/web-snapshots/20260515T081328Z/` (`2.3G`).
- Admin snapshot:
  `/opt/fbrk-admin/admin-snapshots/20260515T081328Z/` (`684K`).
- Plesk HTTP snapshot:
  `fbrk_audit/plesk-backups/20260515T0814-enrichment/`.

Deploy:

- backend: `/opt/fbrk-admin/app/publish.py`, `/opt/fbrk-admin/app/seo.py`,
  `/opt/fbrk-admin/templates/article_ssr.html`;
- web-root: HTML entrypoints, `/css/style.css`, `/js/app.js`;
- generated payload regenerated as `www-data`;
- Plesk `new.fbrk.kz` updated via File Manager API:
  HTML, CSS, JS, `robots.txt`, `sitemap.xml`, `feed.xml`.
- после очередного cron/update без изменения количества статей был повторно
  досинхронизирован только `/js/article-full.js`:
  `fbrk_audit/generated-sync-20260515T0824-article-full-resync/`.

Live verification:

- strict linkage:
  `BACKEND_TOTAL=4664`, `NEW_TOTAL=4664`,
  `BACKEND_ARTICLE_FULL_TOTAL=4664`, `NEW_ARTICLE_FULL_TOTAL=4664`,
  SHA256 совпадает для `data.js`, `data-archive.js`, `article-full.js`;
- Playwright on
  `/a/policeyskiy-nasmert-sbil-polutoragodovalogo-rebenka-v-aktau`:
  - `new.fbrk.kz`: lead summary `true`, key points `5`, entities `8`,
    tags `5`, horizontal overflow `false`, rendered links to qdev `0`;
  - `fbrk.qdev.run`: lead summary `true`, key points `5`, entities `8`,
    tags `5`, horizontal overflow `false`;
- `https://fbrk.qdev.run/admin/healthz` -> `200`;
- `journalctl -u fbrk-admin --since "2026-05-15 08:13:00 UTC"` без
  `PermissionError`, `UndefinedError`, `Traceback`, `ERROR`.

## Article-full parity resync (2026-05-15, 10:05Z)

Follow-up check found `new.fbrk.kz/js/article-full.js` drifting from backend
again while `data.js` and `data-archive.js` still matched. The visible symptom
on the sample slug was stale static payload on `new.fbrk.kz`: old `other`
entities could reappear as `Упоминания`, while backend SSR already filtered
them.

Action:

- saved Plesk HTTP snapshot:
  `fbrk_audit/plesk-backups/20260515T100229Z-article-full-drift/`;
- copied fresh backend payload into:
  `fbrk_audit/generated-sync-20260515T100229Z-article-full-resync/`;
- uploaded only `/new.fbrk.kz/js/article-full.js` via Plesk File Manager API.

Verification:

- `BACKEND_TOTAL=4664`, `NEW_TOTAL=4664`;
- `DELTA_BACKEND_MINUS_NEW=0`;
- `BACKEND_ARTICLE_FULL_TOTAL=4664`, `NEW_ARTICLE_FULL_TOTAL=4664`;
- SHA256 matches for `data.js`, `data-archive.js`, `article-full.js`;
- sample slug
  `trekhkratnyi-razryv-potrebleniia-miasa-fiksiruetsia-u-kazakhstantsev-s-raznym-dostatkom`
  now has identical `tags` and no `entities` in both backend and `new`
  `article-full.js` payloads.

## Stable article-full payload (2026-05-15, 10:27Z)

Follow-up strict linkage still drifted after the 10-minute RSS cycle. This was
not a content mismatch: JSON diff showed only `updatedAt` changing for 10 fresh
articles, while `sections`, `tags`, `entities`, summaries and counts stayed the
same.

Root cause:

- `article-full.js` included `updatedAt`;
- `ingest_fbrk.py rss` can touch `updated_at` for recent unchanged materials;
- `new.fbrk.kz` is static on Plesk, so every volatile backend rebuild caused a
  SHA mismatch until the next manual Plesk sync.

Fix:

- removed `updatedAt` from `_article_full_shape()` in `admin/app/publish.py`;
- added regression test
  `test_article_full_payload_omits_volatile_updated_at`;
- `js/app.js` already falls back from `updatedAt` to `dateIso` for JSON-LD
  `dateModified`, so public rendering remains stable.

Safety gates on active VPS `148.230.117.131`:

- DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260515T102356Z-pre-stable-article-full.db`
  (`73M`, non-zero);
- web snapshot: `/opt/fbrk-admin/web-snapshots/20260515T102356Z/` (`2.3G`);
- admin snapshot: `/opt/fbrk-admin/admin-snapshots/20260515T102356Z/` (`24K`);
- Plesk HTTP snapshot:
  `fbrk_audit/plesk-backups/20260515T102447Z-stable-article-full/`;
- fresh Plesk sync source:
  `fbrk_audit/generated-sync-20260515T102447Z-stable-article-full/`.

Deploy:

- copied `/opt/fbrk-admin/app/publish.py`;
- `chown www-data:www-data /opt/fbrk-admin/app/publish.py`;
- `/opt/fbrk-admin/.venv/bin/python3 -m py_compile app/publish.py`;
- `systemctl restart fbrk-admin`;
- regenerated `data.js`, `data-archive.js`, `article-full.js` as `www-data`;
- uploaded only `/new.fbrk.kz/js/article-full.js` via Plesk File Manager API.

Verification:

- local:
  `../.audit-tools/venv/bin/python -m unittest tests/test_public_entity_tags.py`
  -> `OK`, 4 tests;
- local: `node --test tests/article_js_filters.test.mjs` -> `pass`;
- backend triple fetch of `article-full.js` stable at
  `0e35b4e83ee7150321326404e299558750325a5cd0b69d616361a82516892756`;
- after forced backend `regenerate_data_js()`, SHA stayed
  `0e35b4e83ee7150321326404e299558750325a5cd0b69d616361a82516892756`;
- strict linkage:
  `BACKEND_TOTAL=4664`, `NEW_TOTAL=4664`,
  `DELTA_BACKEND_MINUS_NEW=0`,
  `BACKEND_ARTICLE_FULL_TOTAL=4664`,
  `NEW_ARTICLE_FULL_TOTAL=4664`,
  SHA256 matches for `data.js`, `data-archive.js`, `article-full.js`;
- strict linkage after the next cron window at `2026-05-15T10:30:16Z`
  stayed green with the same `article-full.js` SHA256;
- `journalctl -u fbrk-admin --since "2026-05-15 10:23:00 UTC"` without
  `error`, `traceback`, `permission`, `undefined`.

## AV DS static resync (2026-05-16, 13:30Z)

Follow-up visual audit found `new.fbrk.kz` drifting back to the old public
shell while `fbrk.qdev.run` already had the current AV DS static layer.

Symptoms:

- `new.fbrk.kz` still loaded Google Fonts and old cache-busts
  `v=202605151005` / `v=202605141448`;
- `new.fbrk.kz/fonts/avds/avds-fonts.css` returned `404`;
- `new.fbrk.kz/js/app.js`, `data.js`, `data-archive.js`, `article-full.js`
  were stale:
  `BACKEND_TOTAL=4670`, `NEW_TOTAL=4664`, delta `6`;
- direct missing URLs showed the default Plesk 404 page instead of the AV DS
  FBRK 404 page.

Fix:

- public static entrypoints and `admin/templates/article_ssr.html` now load
  `/fonts/avds/avds-fonts.css?v=202605161250`;
- removed Google Fonts references from public shells;
- bumped public static cache-busts to `v=202605161250`;
- `admin/scripts/build_new_frontend_static_package.sh` now includes:
  `.htaccess`, `/fonts/avds/avds-fonts.css`, all referenced AV DS `.woff2`
  files, CSS, JS and generated public payloads;
- added repo-tracked `.htaccess` for Plesk with:
  `/a/<slug>` internal rewrite and `ErrorDocument 404 /404.html`.

Safety gates:

- active VPS DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260516T1250Z-pre-avds-resync.db`
  (`73M`, non-zero);
- active VPS web snapshot:
  `/opt/fbrk-admin/web-snapshots/20260516T1250Z-avds-resync/` (`2.3G`);
- active VPS template snapshot:
  `/opt/fbrk-admin/template-snapshots/20260516T1250Z-avds-resync/article_ssr.html`;
- Plesk HTTP snapshot:
  `fbrk_audit/plesk-http-snapshots/20260516T1322-avds-resync/`;
- reproducible Plesk packages:
  `fbrk_audit/new-fbrk-deploy-20260516T1250-avds-resync/` and
  `fbrk_audit/new-fbrk-deploy-20260516T1335-avds-resync-htaccess/`.

Deploy:

- updated on `fbrk.qdev.run`:
  `index.html`, `archive.html`, `article.html`, `about.html`, `404.html`,
  `admin/templates/article_ssr.html`;
- applied `chown www-data:www-data` to changed prod files;
- restarted `fbrk-admin`; health check returned `{"ok":true,...}`;
- uploaded to Plesk `new.fbrk.kz` via File Manager API:
  `.htaccess`, HTML entrypoints, `css/style.css`, all `js/*`, `robots.txt`,
  `sitemap.xml`, `feed.xml`, `fonts/avds/*`.

Verification:

- strict linkage:
  `BACKEND_TOTAL=4670`, `NEW_TOTAL=4670`,
  `DELTA_BACKEND_MINUS_NEW=0`,
  `BACKEND_ARTICLE_FULL_TOTAL=4670`,
  `NEW_ARTICLE_FULL_TOTAL=4670`;
- SHA256 matches for `data.js`, `data-archive.js`, `article-full.js`;
- `https://new.fbrk.kz/fonts/avds/avds-fonts.css` -> `200`;
- `https://new.fbrk.kz/fonts/avds/onest-057.woff2` -> `200`;
- public HTML pages no longer contain `fonts.googleapis.com`,
  `fonts.gstatic.com` or `fbrk.qdev.run` host references;
- Browser smoke on `new.fbrk.kz`:
  home, archive, article, article body scroll, about, 404 all render with
  current AV DS shell and no page console errors;
- `https://new.fbrk.kz/no-such-page-20260516` now returns HTTP `404` with the
  FBRK AV DS 404 page, not the default Plesk page.

## AV DS polish follow-up (2026-05-16, 17:50Z)

Follow-up AV DS check after the static resync found several small but visible
drifts:

- dark theme temporarily overrode `--color-brand` with white instead of the
  FBRK brand blue `#0C115F`;
- AI illustration watermark used Latin `AI`;
- no-image fallback text could still render Latin `FBRK`;
- homepage investigation cards again showed `dek` text, which visually
  crowded the card bottom on mobile.

Fix:

- restored original `--color-brand: #0C115F` in dark theme and
  `prefers-color-scheme: dark`;
- changed public watermark text to `ИЛЛЮСТРАЦИЯ ФБРК · ИИ`;
- changed JS no-image fallback mark to `ФБРК`;
- removed `card__dek` only from homepage investigation cards; archive cards,
  search cards and related-material cards keep descriptions;
- bumped static cache-busts to `v=202605161750`;
- rebuilt Plesk package with
  `PUBLIC_ORIGIN=https://new.fbrk.kz` and
  `BACKEND_ORIGIN=https://fbrk.qdev.run`.

Safety gates:

- active VPS DB backups:
  `/opt/fbrk-admin/backups/fbrk-20260516T1720Z-pre-avds-polish.db`,
  `/opt/fbrk-admin/backups/fbrk-20260516T1735Z-pre-avds-card-polish.db`,
  `/opt/fbrk-admin/backups/fbrk-20260516T1750Z-pre-avds-final-polish.db`
  (`73M`, non-zero);
- active VPS web snapshots:
  `/opt/fbrk-admin/web-snapshots/20260516T1720Z-avds-polish`,
  `/opt/fbrk-admin/web-snapshots/20260516T1735Z-avds-card-polish`,
  `/opt/fbrk-admin/web-snapshots/20260516T1750Z-avds-final-polish`;
- active VPS template snapshots:
  `/opt/fbrk-admin/template-snapshots/20260516T1720Z-avds-polish/article_ssr.html`,
  `/opt/fbrk-admin/template-snapshots/20260516T1735Z-avds-card-polish/article_ssr.html`,
  `/opt/fbrk-admin/template-snapshots/20260516T1750Z-avds-final-polish/article_ssr.html`;
- Plesk HTTP snapshots:
  `fbrk_audit/plesk-http-snapshots/20260516T1725-avds-polish/`,
  `fbrk_audit/plesk-http-snapshots/20260516T1738-avds-card-polish/`,
  `fbrk_audit/plesk-http-snapshots/20260516T1758-avds-final-polish/`;
- reproducible final Plesk package:
  `fbrk_audit/new-fbrk-deploy-20260516T1750-avds-final-polish/`.

Deploy:

- updated on `fbrk.qdev.run`:
  `index.html`, `archive.html`, `article.html`, `about.html`, `404.html`,
  `css/style.css`, `js/app.js`, `admin/templates/article_ssr.html`;
- applied `chown www-data:www-data` to changed prod files;
- restarted `fbrk-admin`; health check returned `{"ok":true,...}`;
- uploaded to Plesk via File Manager API from the generated static package:
  `.htaccess`, HTML entrypoints, `css/style.css`,
  `js/runtime-config.js`, `js/app.js`.

Important operational note:

- Plesk `new.fbrk.kz` must be synced from the generated package, not directly
  from repo HTML files. Repo HTML is correct for `fbrk.qdev.run` canonical,
  while package HTML is rewritten to `https://new.fbrk.kz/...`. Verification
  caught one source/package mix-up during this pass; final upload re-applied
  the package HTML and strict linkage turned green.

Verification:

- local syntax checks:
  `node --check js/app.js` and
  `bash -n admin/scripts/build_new_frontend_static_package.sh`;
- final package:
  `AVDS_FONT_FILES=57`, `DATA_JS_TOTAL=4670`,
  `ARCHIVE_ARTICLES=4670`, `ARTICLE_FULL_ARTICLES=4670`;
- strict linkage:
  `BACKEND_TOTAL=4670`, `NEW_TOTAL=4670`,
  `DELTA_BACKEND_MINUS_NEW=0`,
  `BACKEND_ARTICLE_FULL_TOTAL=4670`,
  `NEW_ARTICLE_FULL_TOTAL=4670`;
- SHA256 matches for `data.js`, `data-archive.js`, `article-full.js`;
- `NEW_CANONICAL_HOME=https://new.fbrk.kz/`;
- `NEW_CANONICAL_ARTICLE=https://new.fbrk.kz/article.html`;
- `new.fbrk.kz` public HTML contains AV DS fonts, no Google Fonts and no
  `fbrk.qdev.run` references in SEO head;
- `fbrk.qdev.run` public HTML keeps qdev canonical and AV DS fonts;
- live CSS/JS checks:
  no `--color-accent`, watermark is `ИЛЛЮСТРАЦИЯ ФБРК · ИИ`,
  homepage investigations have `0` `.card__dek`,
  latest no-image fallback uses `ФБРК`;
- Browser smoke on `new.fbrk.kz`:
  home renders, investigation cards are title-only, mobile menu opens and
  contains `Архив` / `О нас`, article page has one `h1` and 14 body
  paragraphs, 404 page renders AV DS shell, page console has no app errors.

## Cache freshness follow-up (2026-05-16, 19:25Z)

Follow-up live audit found a real freshness risk in the split frontend:

- `new.fbrk.kz` serves static JS from Plesk with
  `Cache-Control: max-age=315360000`;
- public HTML still pointed at `?v=202605161750`;
- after backend RSS/admin regeneration, a browser that had already cached
  `/js/data.js?v=202605161750` could keep stale public data even though
  backend and Plesk files had matching SHA256.

Fix:

- bumped public static cache-busts to `v=202605161904`;
- `admin/scripts/build_new_frontend_static_package.sh` now rewrites
  `?v=<timestamp>` to a fresh `ASSET_VERSION` for every generated Plesk
  package;
- generated `js/runtime-config.js` now sets `window.__FBRK_V`, so lazy-loaded
  archive payloads use the same package version;
- repo `.htaccess` now marks `data.js`, `data-archive.js` and
  `article-full.js` as `no-cache/no-store` for Apache-served static mode;
- `admin/deploy/nginx-fbrk.conf` and `admin/deploy/nginx-new-fbrk.conf` now
  keep generated public data files out of the long immutable cache while
  leaving stable CSS/JS/images cacheable;
- `admin/deploy/plesk-new-fbrk-split-proxy.conf` now includes `article-full.js`
  and no-cache headers for all generated data proxy routes.

Safety gates:

- active VPS DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260516T191202Z-pre-cache-fresh.db`
  (`73M`, non-zero);
- active VPS web snapshot:
  `/opt/fbrk-admin/web-snapshots/20260516T191202Z-cache-fresh`;
- active VPS template snapshot:
  `/opt/fbrk-admin/template-snapshots/20260516T191202Z-cache-fresh/article_ssr.html`;
- Plesk HTTP snapshot:
  `fbrk_audit/plesk-http-snapshots/20260516T1904-cache-fresh/`;
- reproducible Plesk package:
  `fbrk_audit/new-fbrk-deploy-20260516T1904-cache-fresh/`.

Deploy:

- updated on `fbrk.qdev.run`:
  `index.html`, `archive.html`, `article.html`, `about.html`, `404.html`,
  `admin/templates/article_ssr.html`, live nginx config for
  `fbrk.qdev.run`;
- applied `chown www-data:www-data` to changed public/template files;
- `nginx -t` passed, nginx reloaded, `fbrk-admin` restarted and health check
  returned `{"ok":true,...}`;
- uploaded to Plesk via File Manager API from the generated static package:
  `.htaccess`, HTML entrypoints, `robots.txt`, `sitemap.xml`, `feed.xml`,
  `js/runtime-config.js`, `js/data.js`, `js/data-archive.js`,
  `js/article-full.js`.

Verification:

- local checks passed:
  `node --check js/app.js`,
  `bash -n admin/scripts/build_new_frontend_static_package.sh`,
  `bash -n admin/scripts/check_split_linkage.sh`,
  `python3 -m unittest tests/test_public_entity_tags.py`,
  `node --test tests/article_js_filters.test.mjs`;
- final package:
  `DATA_JS_TOTAL=4670`, `ARCHIVE_ARTICLES=4670`,
  `ARTICLE_FULL_ARTICLES=4670`;
- strict linkage:
  `BACKEND_TOTAL=4670`, `NEW_TOTAL=4670`,
  `DELTA_BACKEND_MINUS_NEW=0`,
  SHA256 matches for `data.js`, `data-archive.js`, `article-full.js`;
- `fbrk.qdev.run/js/data.js`, `data-archive.js`, `article-full.js` now return
  `Cache-Control: no-cache, no-store, must-revalidate`;
- `new.fbrk.kz` HTML now contains `v=202605161904` and no
  `v=202605161750`;
- `new.fbrk.kz/js/data.js?v=202605161904` has first slug
  `tokaev-vydvinul-sem-iniciativ-na-neformalnom-sammite-otg-v-turkestane`;
- Browser smoke on `new.fbrk.kz`:
  home, archive, enriched article, and 404 render with `data.js?v=202605161904`
  and no console errors; sample enriched article renders `7` entity chips.

Remaining Plesk note:

- Plesk still adds long cache headers to static JS when files are served
  directly by its nginx layer. The fresh package version fixes current browser
  staleness. The stronger long-term fix is still to apply the documented
  Plesk Additional nginx directives so generated data files are proxied or
  served with `no-cache` at the Plesk nginx layer.

## Automated Plesk sync (2026-05-17, 07:24Z)

Follow-up after the cache-freshness fix showed the same root class one more
time: Plesk static payloads can drift after RSS/admin regeneration because
`new.fbrk.kz` is not yet using the nginx split-proxy. Instead of relying on
manual uploads, a guarded automatic File Manager sync is now installed.

Repo changes:

- added `admin/scripts/sync_new_frontend_to_plesk.py`;
- `admin/scripts/build_new_frontend_static_package.sh` now supports
  `REPO_ROOT=...` override for the deployed script;
- updated split runbook with cron/env/manual recovery procedure.

Production install:

- script deployed to `/opt/fbrk-admin/scripts/sync_new_frontend_to_plesk.py`;
- root-only env file: `/etc/fbrk-admin/plesk-sync.env`;
- cron installed at `/etc/cron.d/fbrk-plesk-sync`;
- log file: `/var/log/fbrk/plesk-sync.log`;
- schedule: `4,14,24,34,44,54 * * * *`, intentionally shortly after the
  10-minute RSS poll.

Safety gates before mutation:

- active VPS DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260517T071818Z-pre-plesk-auto-sync.db`
  (`73M`, non-zero);
- active VPS web snapshot:
  `/opt/fbrk-admin/web-snapshots/20260517T071818Z-plesk-auto-sync`
  (`2.3G`);
- local Plesk HTTP snapshot:
  `fbrk_audit/plesk-http-snapshots/20260517T071816Z-pre-auto-sync/`.

Deploy:

- verified Plesk File Manager upload/delete with a temporary smoke file before
  touching production assets;
- ran the sync once in normal mode and once with `--force` after fixing the
  package version regex;
- final forced package version: `20260517072436`;
- uploaded 13 files in the normal sync path:
  `.htaccess`, HTML entrypoints, `robots.txt`, `sitemap.xml`, `feed.xml`,
  `js/runtime-config.js`, `js/data.js`, `js/data-archive.js`,
  `js/article-full.js`.

Verification:

- local syntax checks:
  `python3 -m py_compile admin/scripts/sync_new_frontend_to_plesk.py`,
  `bash -n admin/scripts/build_new_frontend_static_package.sh`,
  `bash -n admin/scripts/check_split_linkage.sh`;
- remote syntax check:
  `python3 -m py_compile /opt/fbrk-admin/scripts/sync_new_frontend_to_plesk.py`;
- `check_split_linkage.sh --strict` after upload:
  `BACKEND_TOTAL=4670`, `NEW_TOTAL=4670`,
  `DELTA_BACKEND_MINUS_NEW=0`,
  `BACKEND_ARTICLE_FULL_TOTAL=4670`,
  `NEW_ARTICLE_FULL_TOTAL=4670`;
- SHA256 matches for `data.js`, `data-archive.js`, `article-full.js`;
- follow-up strict check at `2026-05-17T07:36:07Z` still matched all three
  generated SHA256 values and kept `DELTA_BACKEND_MINUS_NEW=0`;
- `https://new.fbrk.kz/` HTML contains `?v=20260517072436`;
- `https://new.fbrk.kz/js/runtime-config.js` sets
  `window.FBRK_PUBLIC_ORIGIN = 'https://new.fbrk.kz'`,
  `window.FBRK_BACKEND_ORIGIN = 'https://fbrk.qdev.run'`,
  `window.__FBRK_V = '20260517072436'`;
- public HTML on `new.fbrk.kz` contains no `fbrk.qdev.run` references and no
  Google Fonts;
- cron service is active; manual no-drift run prints `STATUS=already-synced`;
- cron ran at `07:24Z` and logged a strict green check.

Browser smoke on `new.fbrk.kz`:

- home: title correct, `6` cards, `1` h1, `0` console errors;
- archive: title correct, `24` cards, `1` h1, `0` console errors;
- latest article sample:
  `/a/tokaev-vydvinul-sem-iniciativ-na-neformalnom-sammite-otg-v-turkestane`
  renders `14` paragraphs, `1` h1, `0` console errors;
- arbitrary missing page renders AV DS 404 with `0` console errors.

Remaining Plesk note:

- current role still cannot edit Additional nginx directives:
  `features.additionalNginxSettings=false`;
- the installed cron keeps the static split frontend current and usable, but
  the cleaner long-term architecture remains the documented Plesk nginx
  split-proxy.
