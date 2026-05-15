# Content Audit Notes

## 2026-05-05 Prod DB Integrity Follow-up

### SQLite Metrics

- Articles: `4589`.
- Empty `body_json`: `0`; empty `sections_json`: `0`.
- Published: `4589`; categories: `news=4505`, `investigation=84`.
- Duplicate slugs: `0`.
- Duplicate non-empty source values: `2`, both text-source labels reused by two different news items (`Kaktus.media`, `МИА «Казинформ»), not duplicate canonical URLs.
- Date format invalid: `0`; future dates: `0`; dates before 2010: `0`; range `2023-08-28..2026-05-05`.
- Invalid `tags_json`: `0`.
- Empty `dek`: `0`; `dek == title`: `1`; `dek` containing angle brackets: `1` (`<…>` quote omission, not an HTML tag).
- Images: `4589` present. Local upload files checked on VPS: missing `0`, zero-byte `0`, unsafe paths `0`. External image sample: `120/120` returned `200`.

### Derived Data Checks

- `editorjs_to_sections(body_json) == sections_json` for all `4589` articles: mismatches `0`.
- Body block counts: min `1`, max `75`, average `8.54`; multi-block articles `4254`.
- Dry-run `data.js` hash matched live `/var/www/fbrk.qdev.run/js/data.js`.
- Dry-run `data-archive.js` hash matched live `/var/www/fbrk.qdev.run/js/data-archive.js`.

### Source Normalization

- Source distribution before fix: `4577` canonical `https://fbrk.kz/...` URLs, `12` text sources.
- For the 12 text sources, direct candidate URLs `/news/<slug>` and `/articles/<slug>` were checked against `fbrk.kz`; only 2 had confirmed `200` plus matching `<h1>`.
- Fixed those 2 rows only:
  - `podozrevaemuyu-v-khischenii-230-tysyach-ekstradirovali-iz-grecii` -> `https://fbrk.kz/news/podozrevaemuyu-v-khischenii-230-tysyach-ekstradirovali-iz-grecii`
  - `trekhkratnyi-razryv-potrebleniia-miasa-fiksiruetsia-u-kazakhstantsev-s-raznym-dostatkom` -> `https://fbrk.kz/articles/trekhkratnyy-razryv-potrebleniya-myasa-fiksiruetsya-u-kazakhstancev-s-raznym-dostatkom`
- Backup before DB update: `/opt/fbrk-admin/backups/fbrk-20260505T034616Z-pre-content-source-normalize-two.db`.
- Live SSR verification: both article pages now expose `article__source` links to `https://fbrk.kz/...`.
- Remaining text sources: `10`; left unchanged because checked canonical candidates returned `404` or had no high-confidence sitemap match.

## Public Archive Metrics

- `data-archive.js`: 4547 articles.
- Date range: `2025-05-06` to `2026-04-28`.
- Categories: `news=4545`, `investigation=2`.
- Duplicate slugs: 0.
- Invalid/future/too-old dates: 0.
- Empty `dek`: 0; `dek == title`: 0; `dek` with HTML: 1.
- Images present: 4547; relative images: 543; `fbrk.kz` images: 4004.

## fbrk.kz Comparison

- Deterministic random sample: 50 articles from `import/urls_all.txt` matched against `https://fbrk.qdev.run/a/<slug>`.
- Source HTTP failures: 0.
- Qdev HTTP failures: 0.
- Title mismatches: 0.
- Body ratio min: 0.901; average: 0.997.
- Missing source link on SSR page: 0 in sample.

## Blocked

- Direct SQLite checks for `body_json`, `sections_json`, source distribution, tags JSON and full duplicate/source checks require VPS DB access.
- Mass regeneration of `sections_json` is intentionally not attempted without DB backup and owner approval.
