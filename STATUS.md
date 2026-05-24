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
- [x] Footer public AV DS version removed from new footer surfaces and kept as HTML comment where added.
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
