# ФБРК — Фонд-бюро расследования коррупции

Независимое казахстанское издание: журналистские расследования, новости, досье,
госзакупки и борьба с коррупцией в Казахстане.

Продакшен: https://fbrk.qdev.run

## Стек

- **Frontend**: статический сайт (HTML/CSS/Vanilla JS) с client-side роутингом
  через nginx try_files. Шрифт — Onest, бренд-цвет `#0C115F`. Тёмная тема.
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

VPS: `62.72.32.112`. Web-root: `/var/www/fbrk.qdev.run/`.
Backend: systemd-юнит `fbrk-admin.service`, порт 8787 (uvicorn, www-data).
DB: `/opt/fbrk-admin/fbrk.db`.

После rsync/scp всегда:
```
chown -R www-data:www-data /var/www/fbrk.qdev.run/...
systemctl restart fbrk-admin
```

Для split-схемы (`new.fbrk.kz` = статика, `fbrk.qdev.run` = backend/DB):
- `docs/audit/NEW_FBRK_SPLIT_FRONTEND_RUNBOOK.md`
- `admin/deploy/plesk-new-fbrk-split-proxy.conf`
- `admin/scripts/build_new_frontend_static_package.sh` — delta-пакет для ручной
  синхронизации Plesk-статики, пока split-proxy недоступен по правам роли.

## ENV (через `/etc/fbrk-admin/fbrk-admin.env`)

- `FBRK_API_KEY` — admin API-ключ (заголовок `X-API-Key`)
- `FBRK_DB_PATH` / `FBRK_DB` — путь к SQLite (по умолчанию `/opt/fbrk-admin/fbrk.db`)
- `FBRK_SITE_URL` — fallback base URL для SEO/publish ссылок (`/sitemap.xml`, `/feed.xml`, `/robots.txt`, RSS item links) когда `Host` недоступен
- LLM-ключи для AI-обогащения

## Cron

```
*/10 * * * * cd /opt/fbrk-admin && set -a && . /etc/fbrk-admin/fbrk-admin.env \
  && set +a && /usr/bin/python3 /opt/fbrk-admin/ingest_fbrk.py rss \
  >> /var/log/fbrk/rss-poll.log 2>&1
```

## Лицензия

Внутренний проект. Все права защищены.
