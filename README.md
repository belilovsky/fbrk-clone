# ФБРК — Фонд-бюро расследования коррупции

Независимое казахстанское издание: журналистские расследования, новости, досье,
госзакупки и борьба с коррупцией в Казахстане.

Продакшен: https://fbrk.qdev.run

## Стек

- **Frontend**: статический сайт (HTML/CSS/Vanilla JS) с client-side роутингом
  через nginx try_files. AV DS `3.7.1`, шрифт — Onest, бренд-цвет
  `#0C115F`. Тёмная тема.
- **Backend** (`/admin`): FastAPI + Uvicorn, SQLite, Editor.js для тел статей,
  AI-обогащение (importance, TL;DR, сущности).
- **Контент-синхронизация**: ingester `ingest_fbrk.py` тянет статьи с fbrk.kz
  по RSS (раз в 10 мин через cron) и по sitemap (по запросу) → пишет в `articles`
  таблицу, нормализует `<br><br>` в отдельные параграфы, регенерит `data.js`.

## Структура

```
fbrk/
├── index.html            — главная (lead + расследования + видео + последнее)
├── archive.html          — архивный листинг (фильтры по дате/категории)
├── article.html          — fallback-шаблон для CSR
├── about.html            — о проекте
├── contacts.html         — контакты редакции и каналы обращений
├── editorial-policy.html — редакционная политика ФБРК как проекта-носителя
├── privacy.html          — политика конфиденциальности
├── videos.html           — YouTube-канал
├── 404.html
├── css/
│   ├── style.css         — основной стайл (~2700 строк)
│   └── av-ds/tokens.css  — AV Design System токены (опционально подключаются)
├── js/
│   ├── app.js            — рендереры + ⌘K-поиск + listing
│   ├── runtime-config.js — runtime overrides (split-hosting mode)
│   ├── data.js           — 80 свежих статей (генерируется)
│   ├── data-archive.js   — полный архив карточек (генерируется)
│   └── article-full.js   — полные публичные тела статей для static `/a/*` (генерируется)
├── img/                  — обложки, бренд
├── admin/                — mirror backend-кода (FastAPI; на VPS `/opt/fbrk-admin`)
└── data/                 — DB-снепшоты (gitignored)
```

## Деплой

Backend VPS: `148.230.117.131`. Web-root: `/var/www/fbrk.qdev.run/`.
Backend/admin работает в Docker-контейнере `fbrk-admin` из
`admin/deploy/docker-compose.fbrk.yml`, порт `127.0.0.1:8787 -> 8787`.
Legacy systemd-юнит `fbrk-admin.service` должен оставаться inactive/disabled.
DB: `/opt/fbrk-admin/fbrk.db` монтируется в контейнер как
`/host/fbrk-admin/fbrk.db`.

Перед любым прод-изменением:
```
TS=$(date -u +%Y%m%dT%H%M%SZ)
sqlite3 /opt/fbrk-admin/fbrk.db ".backup '/opt/fbrk-admin/backups/fbrk-$TS-pre-<area>.db'"
test -s /opt/fbrk-admin/backups/fbrk-$TS-pre-<area>.db
rsync -a /var/www/fbrk.qdev.run/ /opt/fbrk-admin/web-snapshots/$TS-pre-<area>/
```

После копирования backend/admin файлов:
```
chown -R www-data:www-data /opt/fbrk-admin/...
cd /opt/fbrk-admin/deploy
docker compose -f docker-compose.fbrk.yml up -d --build admin
docker inspect -f '{{.State.Health.Status}}' fbrk-admin
```

Локальная pre-prod проверка из репозитория:
```
./scripts/verify_preprod.sh
```

Примечание: полный Python smoke-набор нужно запускать через repo `.venv`
(`.venv/bin/python`). Системный `python3` на этой машине может не содержать
зависимости админки, включая `PyJWT`.

Для split-схемы (`new.fbrk.kz` = статика, `fbrk.qdev.run` = backend/DB):
- `docs/audit/NEW_FBRK_VPS_FRONTEND_RUNBOOK.md` — текущая целевая схема:
  отдельный KZ VPS в том же ps.kz-аккаунте (`213.155.22.190`) отдаёт
  `new.fbrk.kz`, backend остаётся на `fbrk.qdev.run`.
- `docs/audit/NEW_FBRK_SPLIT_FRONTEND_RUNBOOK.md`
- `admin/deploy/plesk-new-fbrk-split-proxy.conf`
- `admin/scripts/sync_new_frontend_to_vps.sh` — штатный backend → frontend VPS
  sync через SSH/rsync; на backend VPS установлен cron
  `/etc/cron.d/fbrk-new-vps-sync`. Скрипт автоматически использует
  `~/.ssh/fbrk_new_frontend_sync`, если этот deploy-key присутствует на host.
- `admin/scripts/build_new_frontend_static_package.sh` — delta-пакет для ручной
  синхронизации Plesk-статики; после cutover 2026-05-18 это fallback/rollback
  путь, а не основной production-hosting. Пакет включает
  `/editorial-policy.html`, чтобы FBRK оставался первым проектом-носителем
  Editorial Hub v1.2 после любой статической пересборки.
- `admin/scripts/sync_new_frontend_to_plesk.py` — автоматический guarded sync
  через Plesk File Manager; используется как fallback, на проде запущен cron
  `/etc/cron.d/fbrk-plesk-sync`, env-секреты лежат вне репо в
  `/etc/fbrk-admin/plesk-sync.env`.

## ENV (через `/etc/fbrk-admin/fbrk-admin.env`)

- `FBRK_API_KEY` — admin API-ключ (заголовок `X-API-Key`)
- `FBRK_DB_PATH` / `FBRK_DB` — путь к SQLite (по умолчанию `/opt/fbrk-admin/fbrk.db`)
- `FBRK_SITE_URL` — fallback base URL для SEO/publish ссылок (`/sitemap.xml`, `/feed.xml`, `/robots.txt`, RSS item links) когда `Host` недоступен
- LLM-ключи для AI-обогащения

## AI-обогащение

Основной воркер: `admin/enrich.py`.

Типовые операционные режимы:

```
cd /opt/fbrk-admin
set -a && . /etc/fbrk-admin/fbrk-admin.env && . ./.env && set +a

# обычный догон новых материалов
./.venv/bin/python3 enrich.py --limit 20

# точечный повтор проблемных/ошибочных строк
./.venv/bin/python3 enrich.py --retry-errors

# quality pass только по слабому хвосту summary/entities
./.venv/bin/python3 enrich.py --quality-rerun --model deepseek-chat --sleep 0.1
```

`--quality-rerun` не трогает весь архив подряд: он выбирает только строки с
`fallback-local`, слишком длинным `summary_short`, плохим short-summary
контрактом или аномальным количеством сущностей. После AI-перезапуска нужно
заново сгенерировать публичные payload'ы и прогнать штатную синхронизацию
split-фронта.

## Cron

```
*/10 * * * * cd /opt/fbrk-admin && set -a && . /etc/fbrk-admin/fbrk-admin.env \
  && set +a && /usr/bin/python3 /opt/fbrk-admin/ingest_fbrk.py rss \
  >> /var/log/fbrk/rss-poll.log 2>&1
```

Синхронизация split-фронта `new.fbrk.kz`:

```
6,16,26,36,46,56 * * * * root /opt/fbrk-admin/scripts/sync_new_frontend_to_vps.sh \
  >> /var/log/fbrk/new-vps-sync.log 2>&1
```

## Лицензия

Внутренний проект. Все права защищены.
