# ФБРК — итоговый prod handoff

Дата: 2026-05-05  
Прод: https://fbrk.qdev.run  
Ветка: `audit/frontend-visual-polish`  
GitHub PR: https://github.com/belilovsky/fbrk-clone/pull/12  
Статус: prod обновлён, PR открыт как draft, merge не выполнялся.

## Executive Summary

Публичный сайт после AV DS refresh, контентного reingest и финальной визуальной полировки доведён до проверенного prod-состояния. На проде развернуты текущие HTML/CSS/JS, SSR template, `admin/app/seo.py` и обновлённый ingester из ветки `audit/frontend-visual-polish`. Последняя проверка покрыла весь sitemap и ключевые браузерные сценарии.

Финальный результат:

- Sitemap regression: `4606/4606` URL вернули `200`, `failure_count=0`.
- Browser regression: `62/62` checks без failures.
- Главная, архив, новости, расследования, about, статья и 404 проверены на `375/768/1024/1440/1920`, light/dark.
- Глобальный поиск работает с клавиатуры: `Ctrl/Cmd+K`, `ArrowDown`, `Enter`.
- Архивные первые изображения грузятся eager/high-priority, без пустых первых плиток.
- Проверены `lang="ru"`, `theme-color=#03052D`, финальные asset versions, отсутствие пустых `alt`, horizontal overflow и запрещённого `--color-accent`.

## GitHub State

- Repo: `belilovsky/fbrk-clone`.
- Current branch: `audit/frontend-visual-polish`.
- Prod-deployed code SHA: `eaaf4bd6fe67b078c539a2d93257583532152b00`.
- Current branch head: see PR #12 / `origin/audit/frontend-visual-polish`; docs-only handoff commits may move this after prod deploy.
- Branch pushed to origin: yes.
- Current open PR: #12 `fix(frontend): финальная AV DS полировка и prod handoff`.
- PR #12 is stacked on PR #6 (`audit/frontend-home-avds-refresh`). This is intentional for review history. If the owner wants one direct merge into `master`, retarget/review the stack before merge.
- `master` at verification time: `5264caa3b8bf6ec1c9b265b8a7279be51bfb89f7`.

Merge policy:

- Do not merge #12 without explicit owner approval.
- If prod hotfix parity must be preserved, merge PR #6 before PR #12 or retarget #12 to `master` and review the combined diff.

## What Changed

### Content / Ingester

- Synced and improved ingester behavior for nested formatting and inline images.
- Preserved article body formatting from original `fbrk.kz`.
- Updated legacy slug rows in place rather than creating broken duplicates.
- Reingested affected articles after content-formatting checks.

Evidence from content pass:

- Original `fbrk.kz` URLs checked from sitemap/RSS: 4534 unique.
- Missing originals: `0`.
- Text mismatches after repair: `0`.
- Format gaps after repair: `0`.
- Prod DB article count during final pass: `4601` articles.

### Frontend / Design

- Main site color moved to a darker FBRK-specific blue gradient while preserving `--color-brand: #0C115F`.
- `theme-color` updated to `#03052D`.
- Home card descriptions hidden to avoid cramped lower text.
- Archive/news cards use open text, without card-like text plates.
- Article pages use open text surfaces instead of heavy panels.
- Negative `letter-spacing` removed from public CSS.
- First archive images load eagerly to avoid blank first viewport tiles.
- Search result list now supports keyboard selection and navigation.

Current public asset versions:

- `/css/style.css?v=202605051535`
- `/js/app.js?v=202605051545`

### Backend / SSR

- SSR body rendering wraps inline-only body chunks in semantic paragraphs.
- Inline article images with empty or missing `alt` get safe fallback alt text from the article title.
- Dek truncation avoids cutting in the middle of a word/sentence.

## Prod Deploy Gates

All prod mutations were preceded by backup/snapshot gates. Important latest artifacts:

- Content formatting reingest DB backup: `/opt/fbrk-admin/backups/fbrk-20260505T141957Z-pre-content-formatting-reingest.db`
- Content formatting web snapshot: `/opt/fbrk-admin/web-snapshots/20260505T141957Z`
- Brand gradient DB backup: `/opt/fbrk-admin/backups/fbrk-20260505T145707Z-pre-brand-gradient-polish.db`
- Brand gradient web snapshot: `/opt/fbrk-admin/web-snapshots/20260505T145707Z`
- SEO inline image alt DB backup: `/opt/fbrk-admin/backups/fbrk-20260505T150942Z-pre-seo-inline-image-alt.db`
- SEO code snapshot: `/opt/fbrk-admin/code-snapshots/20260505T150942Z/seo.py`
- Search regression DB backup: `/opt/fbrk-admin/backups/fbrk-20260505T152718Z-pre-frontend-full-regression-search.db`
- Search regression web snapshot: `/opt/fbrk-admin/web-snapshots/20260505T152718Z`
- Search regression template snapshot: `/opt/fbrk-admin/template-snapshots/20260505T152718Z/article_ssr.html`
- Archive eager images DB backup: `/opt/fbrk-admin/backups/fbrk-20260505T154006Z-pre-frontend-archive-eager-images.db`
- Archive eager images web snapshot: `/opt/fbrk-admin/web-snapshots/20260505T154006Z`
- Archive eager images template snapshot: `/opt/fbrk-admin/template-snapshots/20260505T154006Z/article_ssr.html`

Post-copy steps were completed:

- `chown www-data:www-data` for copied public/backend/template files.
- `systemctl restart fbrk-admin` after backend/template changes.
- `fbrk-admin=active`, `nginx=active`.

## Final Verification

Final sitemap regression:

- Artifact: `/tmp/fbrk-final-sitemap-regression-20260505/summary.json`
- URL count: `4606`
- Status counts: `{"200": 4606}`
- Failure count: `0`
- Max elapsed: `1185ms`
- Failure CSV: `/tmp/fbrk-final-sitemap-regression-20260505/failures.csv` (header only)

Final browser regression:

- Artifact: `/tmp/fbrk-live-regression-after-search-20260505/results.json`
- Checks: `62`
- Failures: `0`
- Screenshots:
  - `/tmp/fbrk-live-regression-after-search-20260505/home-1440.png`
  - `/tmp/fbrk-live-regression-after-search-20260505/home-375.png`
  - `/tmp/fbrk-live-regression-after-search-20260505/archive-news-1440.png`
  - `/tmp/fbrk-live-regression-after-search-20260505/article-1440.png`

Validation covered:

- Expected HTTP status for core pages and 404.
- `lang="ru"`.
- Final CSS/JS cache-bust versions.
- Dark FBRK gradient on header/footer.
- Light/dark theme persistence.
- No horizontal overflow.
- No empty image `alt` on checked pages and sitemap HTML.
- Article body SSR paragraphs and JSON-LD presence.
- Search overlay keyboard behavior.
- First archive images eager/high-priority.

Tool limitations:

- Host `npm`, `gh`, Lighthouse CLI, Node Playwright and axe packages were unavailable.
- Browser regression used Python Playwright with local Google Chrome.
- Sitemap/HTML regression used Python standard library.

## Rollback

For public static files:

1. Restore files from the relevant `/opt/fbrk-admin/web-snapshots/<timestamp>/`.
2. Keep `/data/`, `/img/uploads/`, `/js/data.js` protected if using rsync.
3. `chown www-data:www-data` restored files.

For SSR/backend files:

1. Restore `article_ssr.html` from `/opt/fbrk-admin/template-snapshots/<timestamp>/`.
2. Restore `seo.py` from `/opt/fbrk-admin/code-snapshots/<timestamp>/` if needed.
3. `chown www-data:www-data`.
4. `systemctl restart fbrk-admin`.
5. Verify `systemctl is-active fbrk-admin nginx`.

For DB:

1. Do not overwrite `/opt/fbrk-admin/fbrk.db` without owner approval.
2. Use the latest relevant `/opt/fbrk-admin/backups/fbrk-<timestamp>-pre-<area>.db`.
3. Run SQLite integrity check on a temp copy first.

## Remaining Notes

- PR #12 remains draft/open by design.
- Lighthouse and axe should be added as CI or run from an environment with the packages installed.
- Full sitemap regression can be repeated with the scripts embedded in this session, or converted into a repo script in a separate PR.
- No mass DB/content edits should be made from this branch without explicit approval.
