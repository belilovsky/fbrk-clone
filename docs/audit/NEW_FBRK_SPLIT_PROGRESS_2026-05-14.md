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

