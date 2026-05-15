# Project Idea Radar — 2026-05-15

Рабочий документ для отбора идей из внешних ссылок в реальные улучшения проектов. Цель — не копировать чужие продукты целиком, а аккуратно забрать применимые паттерны: графы сущностей, evidence-архив, RAG/eval, AEO/SEO, мониторинг инфраструктуры и ревью кода.

## Принципы

- Не добавлять новые внешние зависимости в прод без отдельного proposal/PR.
- Не использовать OSINT-инструменты для сталкинга, доксинга или сбора персональных данных без правового основания.
- Не переносить AGPL-код внутрь закрытых проектов; использовать такие проекты только как standalone-инструменты или источник идей.
- Любые публичные изменения FBRK должны сохранять русский UI, текущий AV DS-направленный стиль и редакционную аккуратность.
- Сначала пилоты в advisory/dry-run режиме, потом точечные production changes.

## Короткий вывод

Самая сильная линия — построить общий слой intelligence поверх существующих проектов:

1. `ФБРК`: сущности, теги, тезисы, related materials, тематические хабы и evidence-архив.
2. `QazPipe/QazInvestigate`: реестр источников, граф событий и сущностей, confidence scoring с прозрачными доказательствами.
3. `PicFinder/QazLake`: provenance для медиа, источник/лицензия/хеш/время сохранения.
4. `QazShield`: приватный eval-layer и локальные модели как fallback для чувствительных задач.
5. `Ortcom/KJ/Туркистан`: геомониторинг, таймлайны, маршруты, объекты и визуальные слои.
6. Все репозитории: AI review, codebase map, ADR и multi-repo context для Codex/Claude.

## Журнал внедрения

### 2026-05-15

- Создан этот радар идей как единая точка принятия решений по внешним ссылкам.
- Проверен первый безопасный кандидат для FBRK: уже существующий слой `summary_short`, `key_points`, `entities_json`, `tags_auto`, public render и тесты дедупликации.
- Прогнаны narrow-тесты:
  - `../.audit-tools/venv/bin/python -m unittest tests/test_public_entity_tags.py` — OK, 4 tests.
  - `node --test tests/article_js_filters.test.mjs` — OK, 1 test.
- Вывод: текущий слой сущностей/тегов не нужно переписывать. Дальше — укреплять его вокруг реестра, evidence и тематических страниц.
- Read-only parity check обнаружил drift: `new.fbrk.kz/js/article-full.js` отставал от backend и держал старые `entities: other` для проблемного материала.
- Сделан точечный Plesk sync только для `/js/article-full.js`:
  - snapshot старого файла: `fbrk_audit/plesk-backups/20260515T100229Z-article-full-drift/`;
  - свежий файл: `fbrk_audit/generated-sync-20260515T100229Z-article-full-resync/`;
  - Plesk upload: `SUCCESS`, файл `article-full.js`;
  - strict linkage после upload: `BACKEND_TOTAL=4664`, `NEW_TOTAL=4664`, `DELTA_BACKEND_MINUS_NEW=0`, SHA256 совпадает для `data.js`, `data-archive.js`, `article-full.js`.
- Root cause следующего drift найден: `article-full.js` включал volatile `updatedAt`,
  а RSS cron обновляет `updated_at` у свежих материалов даже без видимого
  изменения текста. Поле удалено из full-static payload, добавлен регрессионный
  тест. Deploy выполнен после свежих backup/snapshot:
  - DB: `/opt/fbrk-admin/backups/fbrk-20260515T102356Z-pre-stable-article-full.db`;
  - web snapshot: `/opt/fbrk-admin/web-snapshots/20260515T102356Z/`;
  - admin snapshot: `/opt/fbrk-admin/admin-snapshots/20260515T102356Z/`;
  - Plesk snapshot: `fbrk_audit/plesk-backups/20260515T102447Z-stable-article-full/`;
  - fresh sync: `fbrk_audit/generated-sync-20260515T102447Z-stable-article-full/`;
  - stable `article-full.js` SHA256:
    `0e35b4e83ee7150321326404e299558750325a5cd0b69d616361a82516892756`.
  Повторная ручная генерация на backend сохранила тот же SHA, strict linkage
  остался зелёным. Контрольная проверка после cron-окна 10:30Z также зелёная.

## Приоритетные пилоты

### P0. FBRK Entity & Narrative Layer

**Что берем:** паттерны knowledge graph, AEO/SEO, source confidence и evidence archive.

**Что уже есть:** `article_meta`, `summary_short`, `summary_tts`, `key_points`, `entities_json`, `tags_auto`, public rendering blocks, admin list pages for tags/entities.

**Следующие шаги:**

- Убедиться, что `new.fbrk.kz` и `fbrk.qdev.run` одинаково рендерят `Кратко`, `Упоминания`, теги и related materials.
- Доделать dedupe: сущности не должны дублироваться как теги, fallback-теги не должны становиться “упоминаниями”.
- Добавить внутреннюю спецификацию “Реестр”: `entity -> article -> source -> evidence`.
- Подготовить proposal для тематических страниц: `/topics/<slug>`, `/entities/<slug>`, `/registry`.

**Риск:** низкий для dry-run и docs, средний для публичного рендера.

### P0. Multi-Repo Code Intelligence

**Что берем:** идеи из Repowise, AI Review, Google CodeWiki-подобных инструментов и Memoir.

**Следующие шаги:**

- Для каждого активного repo завести короткий `CODEBASE_MAP.md` или секцию в существующем audit-документе.
- Добавить advisory AI-review workflow только вручную, без blocking gate.
- Зафиксировать ADR: какие runtime, deploy, secrets, smoke checks являются “истиной” для каждого проекта.
- Проверить совместимость приватных repo с внешними LLM-провайдерами; для чувствительных repo использовать local/self-hosted provider.

**Риск:** низкий, если workflow manual и не блокирует CI.

### P1. OSINT/Event Registry

**Что берем:** идеи из геополитического агрегатора, OSIRIS, VoidAccess, WhoCord.

**Следующие шаги:**

- Начать не с “автоматических выводов”, а с объектной модели: источник, событие, сущность, утверждение, доказательство, confidence.
- Для QazPipe/QazInvestigate собрать прототип offline-import из RSS/Telegram/HTML.
- В UI показывать не “AI считает”, а почему событие попало в кластер: источники, даты, совпадения, противоречия.
- Экспорт: CSV/JSON, позже STIX/MISP только если реально нужно.

**Риск:** высокий без правовой рамки; запускать только как внутренний research tool.

### P1. Evidence & Media Provenance

**Что берем:** идею media capture/save, но не публичную downloader-функцию.

**Следующие шаги:**

- Внутренний evidence object: URL, canonical URL, timestamp, screenshot/video snapshot, hash, source type, rights note.
- Для FBRK использовать как редакционный архив к расследованиям.
- Для PicFinder/QazLake добавить provenance-поля рядом с медиа-объектами.

**Риск:** средний: нужны ограничения по авторскому праву и персональным данным.

### P1. RAG/Eval Harness

**Что берем:** методологию EnterpriseRAG-Bench.

**Следующие шаги:**

- Создать небольшой локальный eval-набор на русском/казахском: вопросы, источники, ожидаемые ссылки, недопустимые hallucinations.
- Применить к FBRK search/summaries, Constitution-RAG, QazShield и QazPipe.
- Порог качества фиксировать как advisory metric, не как production blocker на первом этапе.

**Риск:** низкий.

### P2. Infra/Container Control Plane

**Что берем:** идеи ContainerFlow: карта сервисов, health, logs, restart policy warnings.

**Следующие шаги:**

- Не копировать AGPL-код в закрытые repo.
- Сначала сделать read-only inventory: VPS, systemd/docker services, URLs, health endpoints, disk, cert expiry.
- Потом alerts через Telegram/email/SentDM-like adapter, если будет approval.

**Риск:** низкий для read-only, высокий для кнопок управления контейнерами.

## Карта по проектам

| Проект | Быстрый win | Большой выигрыш | Ограничитель |
| --- | --- | --- | --- |
| FBRK/new.fbrk.kz | Довести `Кратко`, `Упоминания`, теги, related | Реестр сущностей и тематические хабы | Не ломать публичный стиль и SEO |
| QazPipe | Source confidence + graph model | Event intelligence pipeline | Не смешивать факты и AI-оценки |
| QazInvestigate | Evidence model | Graph investigations | Правовая рамка OSINT |
| PicFinder/QazLake | Media provenance | Evidence archive/search | Лицензии и источник медиа |
| QazShield | Local eval + private review | Quality gates для чувствительных документов | Не отправлять приватные данные наружу |
| Ortcom/KJ/Туркистан | Geo timeline | 3D/map monitoring | Карта должна объяснять, а не украшать |
| Все repo | Manual AI review | Multi-repo code intelligence | Не делать blocking gate сразу |

## Deferred

- Financial datasets MCP: полезно для экономических материалов и KJ, но только как optional enrichment после проверки лицензий и источников.
- Cobalt-style capture: только для разрешенных/редакционных evidence use cases, не как публичная функция.
- Dark web tooling: только отдельный proposal, отдельная инфраструктура, отдельная правовая политика.
- Local Qwen/Ollama: R&D для стоимости и приватности, не production replacement.

## Источники

- https://github.com/Nikita-Filonov/ai-review
- https://github.com/repowise-dev/repowise
- https://github.com/RGJorge/containerflow
- https://github.com/Siv-nick/WhoCord
- https://github.com/simplifaisoul/osiris
- https://github.com/KatrielMoses/voidaccess
- https://github.com/imputnet/cobalt
- https://github.com/onyx-dot-app/EnterpriseRAG-Bench
- https://github.com/zhangfengcdt/memoir
- https://www.reddit.com/r/osinttools/comments/1t9ez8i/i_built_a_geopolitical_intelligence_aggregator/
- https://www.reddit.com/r/Agentic_SEO/comments/1t6557k/0_to_15k_active_users_in_8_weeks_0_on_ads_heres/
- https://www.reddit.com/r/vibecoding/comments/1tbqti3/open_source_palantir/
