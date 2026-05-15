# FBRK Entity & Narrative Pilot — 2026-05-15

Пилот для аккуратного возврата и усиления “умного” слоя статей: тезисы, краткое summary, теги, сущности, связанные материалы и будущий реестр.

## Цель

Сделать так, чтобы каждая статья на `new.fbrk.kz` и `fbrk.qdev.run` имела понятный, недублирующийся и редакционно полезный слой:

- `Кратко` — короткое summary и до 5 тезисов.
- `Упоминания` — только реальные сущности: люди, организации, госорганы, места, законы, дела, деньги.
- `Теги` — тематические chips без дублей с сущностями.
- `Материалы по теме` — объяснимые related links.
- `Evidence` — внутренний будущий слой доказательств и источников.

## Что уже есть в коде

- `admin/app/meta_schema.py` — схема `article_meta`.
- `admin/enrich.py` — AI/fallback enrichment.
- `admin/app/publish.py` — public payload для split static frontend.
- `admin/app/seo.py` и `admin/templates/article_ssr.html` — SSR article rendering.
- `js/app.js` — static article rendering.
- `tests/test_public_entity_tags.py` и `tests/article_js_filters.test.mjs` — регрессии на шумные сущности и дубли.

## Текущий verified status

Проверено 2026-05-15:

```text
../.audit-tools/venv/bin/python -m unittest tests/test_public_entity_tags.py
OK, 4 tests

node --test tests/article_js_filters.test.mjs
OK, 1 test
```

Это означает, что базовая дедупликация сущностей/тегов в текущем checkout работает на уровне unit-тестов. Live/static parity нужно проверять отдельно перед деплоем.

## Live parity update

Проверено 2026-05-15 после stable payload deploy и Plesk resync:

```text
admin/scripts/check_split_linkage.sh https://new.fbrk.kz https://fbrk.qdev.run --strict

BACKEND_TOTAL=4664
NEW_TOTAL=4664
DELTA_BACKEND_MINUS_NEW=0
BACKEND_ARTICLE_FULL_TOTAL=4664
NEW_ARTICLE_FULL_TOTAL=4664
BACKEND_DATA_SHA256=00ea9e85cec2726a9a9c6327abe4edb4110c98444e8a25bd54ecc90260938ba0
NEW_DATA_SHA256=00ea9e85cec2726a9a9c6327abe4edb4110c98444e8a25bd54ecc90260938ba0
BACKEND_ARCHIVE_SHA256=be5ac4c7536ac6e98f25bb51aca5a20026f08966eb2dd4c6ec7d893d425faee2
NEW_ARCHIVE_SHA256=be5ac4c7536ac6e98f25bb51aca5a20026f08966eb2dd4c6ec7d893d425faee2
BACKEND_ARTICLE_FULL_SHA256=0e35b4e83ee7150321326404e299558750325a5cd0b69d616361a82516892756
NEW_ARTICLE_FULL_SHA256=0e35b4e83ee7150321326404e299558750325a5cd0b69d616361a82516892756
```

Проблемный slug `trekhkratnyi-razryv-potrebleniia-miasa-fiksiruetsia-u-kazakhstantsev-s-raznym-dostatkom` теперь одинаков в `new` и backend payload: `updatedAt` отсутствует в full-static payload, `entities` отсутствуют, auto/fallback tags не выводятся как публичные chips и не дублируют «Упоминания».

Причина прежнего drift: `updatedAt` менялся при cron/RSS-проверке свежих
материалов, хотя видимый текст не менялся. Для split-static `article-full.js`
это поле не используется фронтом как обязательное: JSON-LD `dateModified`
падает обратно на `dateIso`. Поэтому поле удалено из `article-full.js`, а
повторная генерация backend payload теперь сохраняет тот же SHA256.

## Минимальный backlog

### 1. Static/SSR parity check

Проверить на одном и том же slug:

- `new.fbrk.kz/a/<slug>`
- `fbrk.qdev.run/a/<slug>`

Критерии:

- `Кратко` отображается один раз.
- `Упоминания` отображаются один раз.
- Теги не повторяют имена сущностей.
- Нет горизонтального overflow.
- Ссылки внутри article body не ведут случайно на `fbrk.qdev.run`, если страница открыта на `new.fbrk.kz`.

### 2. Public registry proposal

Подготовить proposal без миграции БД:

- `/entities/<slug>` — публичная страница сущности.
- `/topics/<slug>` — тематическая страница.
- `/registry` — внутренняя/публичная витрина реестра, если владелец подтвердит.

На первом этапе данные можно собирать из существующих `articles.tags_json` и `article_meta.entities_json`.

### 3. Evidence model proposal

Не внедрять в прод без отдельного согласования. Сначала описать модель:

- article id / slug;
- source URL;
- captured URL;
- timestamp UTC;
- hash;
- media type;
- rights note;
- operator note.

### 4. AEO/narrative layer

Сделать редакционные хабы:

- “Коррупция”;
- “Госзакупки”;
- “Суды и следствие”;
- “Назарбаев/семья/связанные лица”;
- “Регионы”.

Каждый хаб должен быть полезной страницей, а не SEO-мусором: intro, последние материалы, ключевые фигуранты, источники, связанные темы.

## Guardrails

- Не добавлять имена авторов в публичные карточки.
- Не вводить английский UI.
- Не превращать fallback-теги в “Упоминания”.
- Не показывать AI-confidence как факт без объяснения источников.
- Не подключать внешние OSINT/media инструменты к production без отдельного proposal.
