# Content Audit Notes

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
