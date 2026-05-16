# Runbook: Split Frontend Hosting (KZ + VPS Backend)

## Цель

- `new.fbrk.kz` (KZ-hosting) хранит и отдает frontend-статику.
- backend + DB продолжают жить на `fbrk.qdev.run` (VPS).
- Публичный пользователь работает через `new.fbrk.kz`, а динамические маршруты проксируются на VPS.

---

## 0) Что уже подготовлено в репо

1. `js/runtime-config.js`
   - поддерживает override:
     - `window.FBRK_PUBLIC_ORIGIN`
     - `window.FBRK_BACKEND_ORIGIN`
2. `js/app.js`
   - больше не привязан жёстко к `fbrk.qdev.run` для article-ссылок.
   - умеет отправлять `/a/<slug>` на backend-origin (если он отличается от public-origin).
   - не показывает "первую попавшуюся" статью при отсутствии id/slug в локальном `data.js`.
3. `admin/app/publish.py`
   - `SITE_URL` берётся из `FBRK_SITE_URL` (fallback: `https://fbrk.qdev.run`).
   - sitemap/feed ссылки на статьи формируются как `/a/<slug>`.
4. `admin/deploy/plesk-new-fbrk-split-proxy.conf`
   - готовый шаблон `Additional nginx directives` для Plesk.
5. `admin/scripts/build_new_frontend_static_package.sh`
   - собирает delta-пакет для ручной загрузки через Plesk File Manager:
     HTML, `.htaccess`, AV DS fonts, `style.css`, `app.js`,
     `runtime-config.js`, свежие `data.js`/`data-archive.js`,
     `article-full.js`, `robots.txt`, `sitemap.xml`, `feed.xml`;
   - переписывает публичные SEO-ссылки с `fbrk.qdev.run` на `new.fbrk.kz`
     внутри пакета, не меняя основной qdev-compatible source;
   - переписывает `?v=<timestamp>` на свежий `ASSET_VERSION`, чтобы браузеры
     не держали старые generated payloads после ручного sync.

---

## 1) Preflight (без мутаций)

```bash
dig +short new.fbrk.kz A
dig +short fbrk.qdev.run A
curl -fsSI https://new.fbrk.kz/ | sed -n '1,20p'
curl -fsSI https://fbrk.qdev.run/ | sed -n '1,20p'
```

Проверить:
- `new.fbrk.kz` открывается.
- `fbrk.qdev.run` стабилен.

---

## 2) Backend safety gates (VPS)

Перед любыми backend-изменениями:

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
sqlite3 /opt/fbrk-admin/fbrk.db ".backup '/opt/fbrk-admin/backups/fbrk-${TS}-pre-split.db'"
test -s "/opt/fbrk-admin/backups/fbrk-${TS}-pre-split.db"
mkdir -p "/opt/fbrk-admin/web-snapshots/${TS}"
rsync -a /var/www/fbrk.qdev.run/ "/opt/fbrk-admin/web-snapshots/${TS}/"
```

---

## 3) KZ-hosting (Plesk): включение split-прокси

1. В панели Plesk для `new.fbrk.kz` открыть:
   - `Apache & nginx Settings` -> `Additional nginx directives`.
2. Вставить содержимое:
   - `admin/deploy/plesk-new-fbrk-split-proxy.conf`.
3. Применить конфиг и проверить, что nginx прошёл валидацию.

Если роли для `Additional nginx directives` ещё нет, можно обновить только
статику через File Manager:

```bash
ASSET_VERSION="$(date -u +%Y%m%d%H%M)" \
  admin/scripts/build_new_frontend_static_package.sh
```

После этого загрузить файлы из выведенного `OUT_DIR` в корень `new.fbrk.kz`
и соответствующие подпапки `css/`, `js/`, `fonts/avds/`. Это держит главную,
архив, поиск, SEO-файлы, AV DS-оформление и статический fallback `/a/<slug>`
в актуальном состоянии. В этом режиме `article-full.js` даёт статическим
страницам полный публичный body. Это тяжелее, чем SSR через split-прокси,
поэтому после получения Plesk-роли лучше включить nginx proxy и вернуться к
backend SSR как каноническому источнику.

Не используйте старый sync-пакет повторно. Plesk может отдавать
`/js/data.js`, `/js/data-archive.js` и `/js/article-full.js` с очень длинным
cache-control, поэтому каждый ручной sync должен выпускать новый
`ASSET_VERSION`.

В корне `new.fbrk.kz` должен лежать `.htaccess` из пакета. Он отвечает за:
- internal rewrite `/a/<slug>` -> `/article.html?id=<slug>&spa=1`;
- `ErrorDocument 404 /404.html`, чтобы не показывать дефолтную Plesk-404;
- короткий cache-control для static assets, если запрос проходит через Apache.
  Если Plesk nginx отдаёт static напрямую, примените Additional nginx
  directives из `admin/deploy/plesk-new-fbrk-split-proxy.conf`, чтобы generated
  payloads не замораживались в браузере.

---

## 4) Runtime config на `new.fbrk.kz`

В файле `js/runtime-config.js` на KZ-hosting указать:

```js
window.FBRK_PUBLIC_ORIGIN = 'https://new.fbrk.kz';
window.FBRK_BACKEND_ORIGIN = 'https://fbrk.qdev.run';
window.__FBRK_V = '<asset-version>';
```

Это нужно, чтобы:
- карточки/поиск/листинги вели на public article URLs `new.fbrk.kz/a/<slug>`;
- backend использовался как API/админ-источник и fallback для отсутствующей статьи;
- не было привязки к старому домену в runtime.

---

## 5) Smoke checks после включения

```bash
curl -fsSI https://new.fbrk.kz/ | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/archive.html | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/a/<любой-валидный-slug> | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/sitemap.xml | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/robots.txt | sed -n '1,20p'
curl -fsSI https://new.fbrk.kz/feed.xml | sed -n '1,20p'
```

Проверить вручную в браузере:
- главная, архив, статья, 404;
- поиск `⌘K/Ctrl+K`;
- theme toggle;
- мобильная ширина (375px) без горизонтального скролла.

---

## 6) Rollback

1. Удалить proxy-блоки в Plesk `Additional nginx directives`.
2. В `js/runtime-config.js` очистить overrides.
3. Проверить `https://new.fbrk.kz/` и `/a/...` заново.

---

## Примечание по каноническому хосту

Если целевой canonical должен быть `new.fbrk.kz`, после cutover установите на backend:

```bash
FBRK_SITE_URL=https://new.fbrk.kz
```

и перегенерируйте публикационные артефакты (`/api/publish`), чтобы sitemap/feed consistently указывали на `new.fbrk.kz`.
