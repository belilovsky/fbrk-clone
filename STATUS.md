# Pre-prod audit status

Branch: `release/pre-prod-audit`

## P0

- [x] `/contacts.html` created with editorial/legal contact blocks and no public placeholder tokens.
- [x] `/sitemap.html`, `/sitemap.xml`, `/robots.txt` added/updated.
- [x] `/search.html?q=...&cat=...` added with client-side deep-link search.
- [x] 404 copy, primary CTA color and CTA sizing fixed.
- [x] KK language pill disabled with tooltip; bottom toast no longer appears.
- [x] Theme toggle uses `currentColor`, stores `localStorage['theme']`, and respects `prefers-color-scheme`.
- [x] Today badge limited to same-day publications.
- [x] AI watermark restricted to `image.kind === "ai"` or inferred AI images.
- [x] Baseline a11y focus/tap-target improvements started.
- [x] Footer public AV DS version is visible in the public shell (`AV DS 3.7.1`).
- [x] `/privacy.html` and functional cookie banner added.
- [x] `about.html` legal/contact section expanded.
- [x] FBRK enrichment supports DeepSeek primary (`DEEPSEEK_API_KEY`) with OpenAI fallback (`OPENAI_API_KEY`); live env is installed only on the active FBRK VPS, values are not committed.
- [x] Plesk sync/package scripts include new pre-prod pages and `js/search-index.js`.

## P1/P2 carried forward

- [ ] Full Lighthouse/LHCI run for staging pages.
- [x] Mobile menu parity: navigation overlay includes theme, language, social links and close control.
- [x] Full card/video/archive/detail visual polish pass.
- [x] Investigation lead fallback now recovers for long or multi-paragraph `dek` using `summaryShort`.
- [x] Legacy investigation URLs with timestamp suffix now resolve to canonical slug on the split frontend.
- [x] Reduced excessive horizontal separators in latest-list and search overlay blocks.
- [x] RSS validation smoke passes as XML/RSS 2.0.
- [x] `image.kind`, `image.source`, `image.hasRealPerson` now generated on publish pipeline and serialized into public payload.
- [x] Local pre-prod verifier script added: `./scripts/verify_preprod.sh` runs JS checks, repo `.venv` tests, compile checks, and strict split linkage.
- [x] Public static shell drift is now guarded by `admin/scripts/sync_public_shell.py --check` and `tests/test_frontend_shell.py`.

## Production smoke 2026-05-23

- [x] Published frontend cache version `202605230105` to `new.fbrk.kz` and `fbrk.qdev.run`.
- [x] Updated 4,727 static article shells on `new.fbrk.kz`.
- [x] Live routes return expected status codes: `/`, `/archive.html`, `/archive.html?cat=investigation`, `/search.html`, `/about.html`, `/contacts.html`, `/privacy.html`, `/sitemap.html`, sample `/a/<slug>`, `/feed.xml`, `/sitemap.xml`; nonexistent URL returns HTTP 404.
- [x] Split-host strict smoke passes: backend/new article counts match, generated data hashes match, canonical URLs point to `https://new.fbrk.kz`.
- [x] Chrome mobile smoke at 390px passes: mobile menu opens, body scroll locks, close/theme/language/social controls render, and no horizontal overflow is detected.
- [x] Local checks pass: Python test suite, article JS tests, `node --check js/app.js`, Python compile checks, RSS/XML parse checks.
- [ ] LHCI desktop metrics are still pending because this workstation has no usable `npm`/`npx` toolchain in the current shell.
- [x] `npx` отсутствует в рабочем окружении этой машины; LHCI планируется выполнить после восстановления CLI toolchain.
- [x] Локальная визуальная проверка Playwright (375/768/1024/1440/1920, key pages) пройдена после правки стилей; горизонтального overflow на `127.0.0.1:8888` не обнаружено.

## Final frontend polish 2026-05-24

- [x] Desktop header no longer clips right-side actions around 1280px; grid sizing now shrinks safely before the mobile breakpoint.
- [x] Public asset version bumped to `20260524115400` for public shells and SSR article template so the header fix is not hidden behind stale CSS cache.
- [x] `./scripts/verify_preprod.sh` passes after the final CSS pass (`29 passed`, compile checks OK, strict split linkage `STATUS=ok`).
- [x] Live browser smoke on `https://new.fbrk.kz/`, representative `/a/<slug>`, and `https://fbrk.qdev.run/admin/login` passes on desktop (`1280px`) with `overflow=false`; both public social buttons remain visible.
- [x] Local browser smoke on home/article/admin at `390px` passes with no horizontal overflow.

## AI enrichment quality pass 2026-05-24

- [x] Live `article_meta` coverage checked for all `4,727` published articles; rows without meta: `0`.
- [x] DeepSeek primary path verified live on backend VPS (`FBRK_ENRICH_MODEL=deepseek-chat`); OpenAI fallback remains available but is no longer present in current article output tail.
- [x] Added `--quality-rerun` mode to `admin/enrich.py` so reruns target only rows with `fallback-local`, overlong `summary_short`, or title-copy short summaries.
- [x] Re-ran the full live quality queue with DeepSeek: `918/918` rows completed successfully, `err=0`.
- [x] Post-rerun quality tail reduced to zero for the tracked failure modes: `fallback_local=0`, `long_summary=0`, `all_other=0`, `empty_summary=0`, `empty_entities=0`, `quality_queue_remaining=0`.
- [x] Static split article shells now prefer `summaryShort` over `dek` for meta description, Open Graph, Twitter, and JSON-LD fields.
- [x] Live curl smoke on representative `https://new.fbrk.kz/a/<slug>/` pages confirms corrected AI summaries in HTML head metadata; browser-visible article leads also render correctly.
- [x] Second live DeepSeek pass reprocessed the remaining entity-quality queue (`516/516 ok`, `err=0`) and removed entity-count outliers from `article_meta`: `entities_lt_2=0`, `entities_gt_12=0`.
- [x] Public article payload now caps visible entity chips at `12` and supplements obvious missing public entities from title/dek/summary context when that can be done cleanly.
- [x] After the public payload refresh and split sync, `new.fbrk.kz/js/article-full.js` dropped from `18` public single-entity articles to `4`; the remaining four are intentionally left as-is because a second public entity is not extractable without introducing awkward fragments.
- [ ] `region` remains empty on `1,193` rows; this is tracked as normal mixed coverage rather than a current blocker because national or non-local materials may legitimately have no single region.

## Visual QA pass 2026-05-27

- [x] Empty article ad placeholders now collapse instead of adding blank cards/extra vertical gaps.
- [x] Negative heading letter-spacing removed from the public CSS for more stable Cyrillic readability.
- [x] Article order is guarded in tests: body -> AI key points -> mentions -> share.
- [x] Public asset version bumped to `20260527053943` to force browsers off the stale article renderer/CSS.

## Editorial policy carrier 2026-05-27

- [x] `/editorial-policy.html` added as the first FBRK-specific carrier page for Editorial Hub v1.2.
- [x] Footer, sitemap page, static sitemap generation and split-frontend package scripts include the editorial policy page.
- [x] Public shell drift tests now require the editorial policy link in every public shell and SSR article template.
- [x] Public asset version bumped to `20260527101809` for the carrier page rollout.
- [x] Follow-up live QA found the policy route still served 404 before redeploy; fixed by syncing the current static package to `new.fbrk.kz`.
- [x] About page inline styles, frontend debug logging, and a stale missing `mobile-menu-fix.js` SSR reference were removed.
- [x] Mobile header compacted on narrow screens so search and menu remain visible without horizontal clipping.
- [x] Desktop header container widened and the compact header breakpoint raised for 1440px QA so navigation no longer crowds the language switcher.
- [x] Article AI key points now soften visibly truncated backend fragments instead of rendering dangling words.
