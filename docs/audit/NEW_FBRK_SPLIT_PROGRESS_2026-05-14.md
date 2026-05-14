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
