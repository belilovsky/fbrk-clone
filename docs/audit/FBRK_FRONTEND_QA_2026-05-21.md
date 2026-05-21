# FBRK frontend QA — 2026-05-21

## Scope

Post-containerization frontend pass for:

- `https://new.fbrk.kz`
- `https://fbrk.qdev.run`

The goal was to verify AV DS public pages after Docker cutover and fix small
visible/interaction regressions without changing data, routes, branding, or DB
schema.

## Safety

Snapshots taken before production frontend changes:

- Backend DB backup:
  `/opt/fbrk-admin/backups/fbrk-20260521T175213Z-pre-frontend-polish.db`
- Backend web-root snapshot:
  `/opt/fbrk-admin/web-snapshots/20260521T175213Z-pre-frontend-polish`
- Frontend web-root/nginx snapshot:
  `/opt/new-fbrk-frontend/snapshots/20260521T175226Z-pre-frontend-polish`

## Findings fixed

### Desktop header nav wrap

On a 1440px viewport the header item `О нас` could wrap to two visual lines in
the article header.

Fix:

- reduced `.site-header__inner` gap from `--space-6` to `--space-4`;
- reduced nav link horizontal padding from `14px` to `12px`;
- added `white-space: nowrap` for `.site-header__nav a`.

### Mobile LiveBadge clipping in latest thumbnails

On a 375px viewport, `СЕГОДНЯ` badges inside narrow `.latest__thumb` previews
could be wider than the thumbnail content box.

Fix:

- added a compact `max-width: 420px` rule for `.latest__thumb .live-badge`;
- reduced small-thumb padding, font size, letter spacing and dot size.

### Search keyboard flow

Search opened and rendered results, but pressing `Enter` in the search input did
not open the selected result.

Fix:

- search results now maintain an active item;
- `ArrowDown` and `ArrowUp` move selection;
- `Enter` opens the active result;
- active result gets a subtle AV DS-compatible highlight.

## Verification

Local tests:

```bash
.venv/bin/python -m pytest \
  tests/test_frontend_shell.py \
  tests/test_static_article_meta.py \
  tests/test_public_entity_tags.py \
  tests/test_admin_platform_primitives.py
```

Result: `14 passed`.

Browser matrix:

- pages: home, archive, about, article, 404;
- viewports: 1440x1000, 768x1000, 375x900;
- checks: page title/H1, `html lang="ru"`, horizontal overflow, clipped text,
  broken images, empty image `alt`, console warnings/errors.

Final browser checks after deploy:

- no horizontal overflow on desktop/mobile;
- no broken images in checked views;
- no empty image `alt` in checked views;
- no console warnings/errors in checked views;
- `О нас` renders as one line on desktop;
- mobile LiveBadge no longer reports clipped content;
- search query `саранчи` shows one active result and `Enter` opens the article;
- mobile menu opens and sets `aria-expanded="true"`;
- theme toggle switches document theme from `light` to `dark`.

Live HTTP smoke:

- `https://fbrk.qdev.run/` -> `200`;
- `https://fbrk.qdev.run/admin/healthz` -> `200`;
- `https://new.fbrk.kz/` -> `200`;
- `https://new.fbrk.kz/archive.html` -> `200`;
- representative `new.fbrk.kz/a/<slug>` -> `200`;
- missing `new.fbrk.kz` page -> `404`.

Split linkage:

- `BACKEND_TOTAL=4715`;
- `NEW_TOTAL=4715`;
- `DELTA_BACKEND_MINUS_NEW=0`;
- `data.js`, `data-archive.js`, `article-full.js`, and `data/videos.json`
  SHA256 hashes match between backend and frontend.

Runtime:

- backend container `fbrk-admin`: `running`, `healthy`;
- frontend container `new-fbrk-frontend`: `running`, `healthy`;
- frontend VPS `nginx -t`: ok.

## Notes

`/videos.html` is not a current split-frontend route. Video content is rendered
as the homepage section and loaded from `/data/videos.json`, which is included
in strict split-linkage checks.
