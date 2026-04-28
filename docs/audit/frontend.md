# Frontend Audit Notes

## Before Fix

- Playwright matrix on public site found horizontal overflow on 375 and 1024 widths.
- `.site-header__actions` overflowed around 1024 because mobile header breakpoint was too low.
- Video carousel negative margins contributed to mobile overflow.
- Dynamic images rendered without `width`/`height` attributes.
- LiveBadge compared `dateIso` with browser-local date; after midnight in `Asia/Almaty`, April 28 articles no longer appeared as today.
- Axe found contrast issues for date metadata, heading-order issues and a nested complementary landmark.

## Fixed Locally

Branch `audit/frontend/badges-layout-a11y`:

- LiveBadge now compares against `Asia/Almaty`.
- `--color-accent` fallbacks replaced with `--color-brand`.
- Header collapses earlier to avoid 1024 overflow.
- Video carousel no longer creates document-level overflow.
- Dynamic article/card/video images include dimensions.
- Metadata contrast improved.
- Archive/about heading order and home sidebar landmark issue fixed.

## Verification

- `node --check js/app.js`: pass.
- Local Playwright overflow: false for 375 `/`, 1024 `/`, 1024 `/archive.html`.
- Local axe: 0 violations on `/`, `/archive.html`, `/about.html`.
