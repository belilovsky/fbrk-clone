// ============================================================
// ФБРК — интерактив (AV DS 2026)
// ============================================================

// ---------- date formatting (used everywhere; defined first) ----------
// Genitive month names («22 апреля» / «22 апр»)
var _RU_MONTHS_FULL = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
var _RU_MONTHS_SHORT = ['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'];
var _CURRENT_YEAR = new Date().getFullYear();

// '2026-04-22' -> '22 апреля' (current year) | '22 апреля 2024' (older)
function fmtDateLong(iso) {
  if (!iso || iso.length < 10) return '';
  var y = +iso.slice(0,4), m = +iso.slice(5,7), d = +iso.slice(8,10);
  if (!y || !m || !d) return '';
  var base = d + ' ' + _RU_MONTHS_FULL[m-1];
  return y === _CURRENT_YEAR ? base : base + ' ' + y;
}

// '2026-04-22' -> '22 апр' (current year) | '22 апр 2024' (older)
function fmtDateShort(iso) {
  if (!iso || iso.length < 10) return '';
  var y = +iso.slice(0,4), m = +iso.slice(5,7), d = +iso.slice(8,10);
  if (!y || !m || !d) return '';
  var base = d + ' ' + _RU_MONTHS_SHORT[m-1];
  return y === _CURRENT_YEAR ? base : base + ' ' + y;
}

// ---------- Theme toggle ----------
(function () {
  const root = document.documentElement;
  const stored = (function () {
    try { return localStorage.getItem('fbrk_theme'); } catch (_) { return null; }
  })();
  // Default to LIGHT (only honour user-chosen preference)
  let current = stored === 'dark' ? 'dark' : 'light';
  root.setAttribute('data-theme', current);

  const sun =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>';
  const moon =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

  function render(btn) {
    btn.innerHTML = current === 'dark' ? sun : moon;
    btn.setAttribute(
      'aria-label',
      current === 'dark' ? 'Переключить на светлую тему' : 'Переключить на тёмную тему'
    );
  }
  document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
    render(btn);
    btn.addEventListener('click', () => {
      current = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', current);
      try { localStorage.setItem('fbrk_theme', current); } catch (_) {}
      document.querySelectorAll('[data-theme-toggle]').forEach(render);
    });
  });
})();

// ---------- Toast helper ----------
function fbrkToast(message, ms = 2400) {
  let el = document.querySelector('.toast');
  if (!el) {
    el = document.createElement('div');
    el.className = 'toast';
    el.setAttribute('role', 'status');
    document.body.appendChild(el);
  }
  el.textContent = message;
  // Force reflow then add class
  // eslint-disable-next-line no-unused-expressions
  el.offsetHeight;
  el.classList.add('is-visible');
  clearTimeout(el._hideTimer);
  el._hideTimer = setTimeout(() => el.classList.remove('is-visible'), ms);
}

// ---------- Language switch (UI stub) ----------
(function () {
  const buttons = document.querySelectorAll('.lang-switch [data-lang]');
  if (!buttons.length) return;
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      if (lang === 'kk') {
        fbrkToast('Қазақша нұсқасы жақын арада қол жетімді болады');
        return;
      }
      // Set RU active
      buttons.forEach((b) => b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'));
    });
  });
})();

// ---------- Mobile menu toggle ----------
(function () {
  const btn = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-site-nav]');
  if (!btn || !nav) return;
  btn.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    btn.setAttribute('aria-expanded', String(open));
  });
  nav.addEventListener('click', (e) => {
    if (e.target.closest('a')) {
      nav.classList.remove('is-open');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
})();

// ---------- Active nav link ----------
(function () {
  const links = document.querySelectorAll('[data-nav-link]');
  if (!links.length) return;
  const path = location.pathname;
  const cat = new URLSearchParams(location.search).get('cat');
  let active = null;
  if (path === '/' || path === '/index.html') active = 'home';
  else if (path.startsWith('/about')) active = 'about';
  else if (path.startsWith('/archive')) {
    if (cat === 'investigation') active = 'investigation';
    else if (cat === 'news') active = 'news';
    else active = 'archive';
  }
  if (active) {
    links.forEach((l) => {
      if (l.dataset.navLink === active) l.setAttribute('aria-current', 'page');
    });
  }
})();

// ---------- Search overlay ----------
(function () {
  const overlay = document.querySelector('.search-overlay');
  if (!overlay) return;
  const input = overlay.querySelector('.search-box__input');
  const results = overlay.querySelector('.search-box__results');
  // Lazy getter: when full archive lands later, search uses it automatically.
  function dataset() {
    if (typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE.articles) return ARTICLES_ARCHIVE.articles;
    if (typeof FBRK_DATA !== 'undefined') return FBRK_DATA.articles;
    return [];
  }

  function open() {
    overlay.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    setTimeout(() => input.focus(), 80);
  }
  function close() {
    overlay.classList.remove('is-open');
    document.body.style.overflow = '';
    input.value = '';
    renderResults('');
  }
  function toResultHtml(a) {
    return `<a class="search-result" href="/a/${a.slug || a.id}">
      <div class="search-result__title">${escapeHtml(a.title)}</div>
      <div class="search-result__meta">${a.categoryLabel} · ${fmtDateLong(a.dateIso) || a.date}</div>
    </a>`;
  }
  function renderResults(q) {
    const data = dataset();
    q = q.trim().toLowerCase();
    if (!q) {
      results.innerHTML = data.slice(0, 5).map(toResultHtml).join('');
      return;
    }
    // Kick off lazy archive load on first non-empty query so search covers everything.
    if (typeof ARTICLES_ARCHIVE === 'undefined' && !window.__archiveLoading) {
      window.__archiveLoading = true;
      const s = document.createElement('script');
      s.src = '/js/data-archive.js?v=' + (window.__FBRK_V || Date.now());
      s.onload = () => { try { renderResults(input.value); } catch(_){} };
      document.head.appendChild(s);
    }
    const matches = data.filter((a) => {
      const hay = (a.title + ' ' + a.dek + ' ' + (a.tags || []).join(' ')).toLowerCase();
      return hay.includes(q);
    }).slice(0, 50);
    if (!matches.length) {
      results.innerHTML =
        '<div style="color:var(--color-text-muted); padding: var(--space-5) 0; font-size: var(--text-sm);">Ничего не найдено. Попробуйте другой запрос.</div>';
      return;
    }
    results.innerHTML = matches.map(toResultHtml).join('');
  }
  document.querySelectorAll('[data-search-open]').forEach((b) => b.addEventListener('click', open));
  overlay.querySelector('.search-close').addEventListener('click', close);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      open();
    }
  });
  input.addEventListener('input', (e) => renderResults(e.target.value));
  renderResults('');
})();

// ---------- Current date in topstrip ----------
(function () {
  const el = document.querySelector('[data-today]');
  if (!el) return;
  const months = [
    'января','февраля','марта','апреля','мая','июня',
    'июля','августа','сентября','октября','ноября','декабря',
  ];
  const weekdays = ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'];
  const d = new Date();
  el.textContent = `${weekdays[d.getDay()]} · ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
})();

// ---------- Helper: prefer full cover for hero ----------
function fullCover(a) {
  // swap /covers/thumb/ -> /covers/web/ for larger rendering
  if (a.image && a.image.includes('/covers/thumb/')) {
    return a.image.replace('/covers/thumb/', '/covers/web/');
  }
  return a.image;
}

// Importance badge — shown only for AI-rated articles with importance >= 4 (out of 5)
function importanceBadgeHtml(a) {
  const imp = Number(a && a.importance);
  if (!imp || imp < 4) return '';
  const label = imp >= 5 ? 'Важно' : 'Резонанс';
  const cls = imp >= 5 ? 'importance-badge importance-badge--top' : 'importance-badge';
  return `<span class="${cls}" aria-label="${label}">${label}</span>`;
}

function todayAlmatyString() {
  try {
    const parts = new Intl.DateTimeFormat('en', {
      timeZone: 'Asia/Almaty',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(new Date());
    const byType = {};
    parts.forEach((p) => { byType[p.type] = p.value; });
    return `${byType.year}-${byType.month}-${byType.day}`;
  } catch (_) {
    const today = new Date();
    return today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');
  }
}

// Live badge — pulse dot for articles published today in editorial time.
// Inspired by AV DS LiveBadge.
function liveBadgeHtml(a) {
  if (!a || !a.dateIso) return '';
  // dateIso is published in Kazakhstan editorial time; compare in Asia/Almaty,
  // not in the reader browser timezone.
  if (a.dateIso !== todayAlmatyString()) return '';
  return '<span class="live-badge" aria-label="Свежая публикация сегодня по времени Алматы"><span class="live-badge__dot" aria-hidden="true"></span>СЕГОДНЯ</span>';
}

// ---------- Home page renderer ----------
(function () {
  const leadRoot = document.querySelector('[data-lead]');
  if (!leadRoot || typeof FBRK_DATA === 'undefined') return;
  const all = FBRK_DATA.articles;
  const featured = all.find((a) => a.featured) || all[0];

  leadRoot.innerHTML = `
    <a class="lead__media" href="/a/${featured.slug || featured.id}" aria-label="${escapeHtml(featured.title)}">
      <img src="${fullCover(featured)}" alt="${escapeHtml(featured.title)}" width="1200" height="800" loading="eager"/>
    </a>
    <div class="lead__body">
      <div class="kicker">${featured.categoryLabel}</div>
      <h1 class="lead__title">
        <a href="/a/${featured.slug || featured.id}">${escapeHtml(featured.title)}</a>
      </h1>
      <p class="lead__dek">${escapeHtml(featured.dek)}</p>
      <div class="lead__meta">
        <span>${fmtDateLong(featured.dateIso) || featured.date}</span>
      </div>
    </div>
  `;

  // Investigations grid — top 6 non-featured "investigation" articles,
  // fallback to latest news if there aren't enough tagged investigations
  const invRoot = document.querySelector('[data-investigations]');
  const shownIds = new Set([featured.id]);
  if (invRoot) {
    let invs = all
      .filter((a) => a.category === 'investigation' && !shownIds.has(a.id))
      .slice(0, 6);
    if (invs.length < 6) {
      const need = 6 - invs.length;
      const usedIds = new Set([...shownIds, ...invs.map((x) => x.id)]);
      const extras = all.filter((a) => !usedIds.has(a.id)).slice(0, need);
      invs = invs.concat(extras);
    }
    invs.forEach((a) => shownIds.add(a.id));
    invRoot.innerHTML = invs
      .map((a) => {
        const hasImg = !!(a.image && String(a.image).trim());
        const cardCls = hasImg ? 'card' : 'card card--no-image';
        const mediaInner = hasImg
          ? `<img src="${a.image}" alt="${escapeHtml(a.title)}" width="600" height="400" loading="lazy"/>`
          : '';
        return `
      <article class="${cardCls}">
        <a href="/a/${a.slug || a.id}">
          <div class="card__media">
            ${mediaInner}
            <span class="card__date-badge">${fmtDateShort(a.dateIso) || a.date}</span>
            ${importanceBadgeHtml(a)}${liveBadgeHtml(a)}
          </div>
          <h3 class="card__title">${escapeHtml(a.title)}</h3>
        </a>
        <p class="card__dek">${escapeHtml(a.dek)}</p>
      </article>`;
      })
      .join('');
  }

  // Latest list — excludes featured + investigation cards, paginated by "Ещё" button
  const latestRoot = document.querySelector('[data-latest]');
  if (latestRoot) {
    const pool = all.filter((a) => !shownIds.has(a.id));
    const PAGE = 12;
    let rendered = 0;
    const renderItem = (a) => {
      const hasImg = !!(a.image && String(a.image).trim());
      const thumbCls = hasImg ? 'latest__thumb' : 'latest__thumb latest__thumb--no-image';
      const thumbInner = hasImg
        ? `<img src="${a.image}" alt="${escapeHtml(a.title)}" width="320" height="200" loading="lazy"/>`
        : `<span class="latest__thumb-mark">FBRK</span>`;
      return `
      <li class="latest__item">
        <a class="${thumbCls}" href="/a/${a.slug || a.id}">
          ${thumbInner}
          ${importanceBadgeHtml(a)}${liveBadgeHtml(a)}
        </a>
        <div>
          <h3 class="latest__title">
            <a href="/a/${a.slug || a.id}">${escapeHtml(a.title)}</a>
          </h3>
          <div class="latest__meta">${fmtDateShort(a.dateIso) || a.date}</div>
        </div>
      </li>`;
    };
    function renderMore() {
      const next = pool.slice(rendered, rendered + PAGE);
      latestRoot.insertAdjacentHTML('beforeend', next.map(renderItem).join(''));
      rendered += next.length;
      if (!moreBtn) return;
      if (rendered >= pool.length) {
        // Пул свежих новостей кончился — показываем CTA в архив,
        // чтобы пользователь не упирался в пустоту.
        moreBtn.classList.add('latest__more--archive');
        moreBtn.textContent = 'Открыть весь архив →';
        moreBtn.onclick = () => { window.location.href = '/archive.html'; };
      } else {
        moreBtn.textContent = `Показать ещё (осталось ${pool.length - rendered})`;
      }
    }
    latestRoot.innerHTML = '';
    // Insert "Ещё" button after the .latest grid container
    let moreBtn = document.querySelector('[data-latest-more]');
    if (!moreBtn) {
      moreBtn = document.createElement('button');
      moreBtn.type = 'button';
      moreBtn.className = 'latest__more';
      moreBtn.setAttribute('data-latest-more', '');
      const latestGrid = latestRoot.closest('.latest');
      if (latestGrid) latestGrid.parentNode.insertBefore(moreBtn, latestGrid.nextSibling);
    }
    moreBtn.addEventListener('click', renderMore);
    renderMore();
  }

  // Tag cloud — dedupe (case-insensitive) and sort
  const tagRoot = document.querySelector('[data-tags]');
  if (tagRoot && FBRK_DATA.tags) {
    const seen = new Map();
    FBRK_DATA.tags.forEach((t) => {
      const k = String(t).trim().toLowerCase();
      if (k && !seen.has(k)) seen.set(k, String(t).trim());
    });
    const uniqueTags = Array.from(seen.values()).sort((a, b) => a.localeCompare(b, 'ru'));
    tagRoot.innerHTML = uniqueTags
      .map((t) => `<a href="#" onclick="event.preventDefault()">${escapeHtml(t)}</a>`)
      .join('');
  }
})();

// ---------- YouTube video showcase ----------
(function () {
  const root = document.querySelector('[data-videos]');
  if (!root) return;

  const playSvg =
    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
  const closeSvg =
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>';

  function formatDate(iso) {
    // "2026-04-23" → "23 апреля"
    const months = ['января','февраля','марта','апреля','мая','июня',
      'июля','августа','сентября','октября','ноября','декабря'];
    if (!iso || typeof iso !== 'string') return '';
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return iso;
    return `${+m[3]} ${months[+m[2]-1]}`;
  }
  function formatViews(n) {
    n = parseInt(n || 0, 10);
    if (!n) return '';
    if (n >= 1000000) return (n/1e6).toFixed(1).replace('.0','') + ' млн просмотров';
    if (n >= 10000) return Math.round(n/1000) + ' тыс просмотров';
    if (n >= 1000) return (n/1000).toFixed(1).replace('.0','') + ' тыс просмотров';
    return n + ' просмотров';
  }

  function render(videos) {
    root.innerHTML = videos.slice(0, 9).map((v) => `
      <a class="video-card" href="https://www.youtube.com/watch?v=${v.id}" target="_blank" rel="noopener" data-video-id="${v.id}">
        <div class="video-card__media">
          <img src="${v.thumb}"
               onerror="this.onerror=null;this.src='${v.thumb_fallback || 'https://i.ytimg.com/vi/'+v.id+'/hqdefault.jpg'}'"
               alt="${escapeHtml(v.title)}" width="480" height="270" loading="lazy"/>
          <div class="video-card__play">
            <div class="video-card__play-btn" aria-hidden="true">${playSvg}</div>
          </div>
        </div>
        <div class="video-card__body">
          <h3 class="video-card__title">${escapeHtml(v.title)}</h3>
          <div class="video-card__meta">
            ${v.published ? `<time>${formatDate(v.published)}</time>` : ''}
            ${v.views ? `<span>${formatViews(v.views)}</span>` : ''}
          </div>
        </div>
      </a>
    `).join('');

    // Modal handler
    const modal = document.createElement('div');
    modal.className = 'video-modal';
    modal.innerHTML = `
      <div class="video-modal__inner">
        <button class="video-modal__close" aria-label="Закрыть">${closeSvg}</button>
        <div class="video-modal__frame"></div>
      </div>`;
    document.body.appendChild(modal);
    const frame = modal.querySelector('.video-modal__frame');

    function closeModal() {
      modal.classList.remove('is-open');
      frame.innerHTML = '';
      document.body.style.overflow = '';
    }
    modal.addEventListener('click', (e) => {
      if (e.target === modal || e.target.closest('.video-modal__close')) closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.classList.contains('is-open')) closeModal();
    });

    root.querySelectorAll('.video-card').forEach((card) => {
      card.addEventListener('click', (e) => {
        e.preventDefault();
        const id = card.getAttribute('data-video-id');
        frame.innerHTML = `<iframe src="https://www.youtube.com/embed/${id}?autoplay=1&rel=0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
        modal.classList.add('is-open');
        document.body.style.overflow = 'hidden';
      });
    });

    // ---- Carousel arrows: wrap root once, attach nav ----
    if (!root.parentElement.classList.contains('video-shelf')) {
      const shelf = document.createElement('div');
      shelf.className = 'video-shelf';
      root.parentNode.insertBefore(shelf, root);
      shelf.appendChild(root);
      const arrowSvg = (dir) => dir === 'prev'
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>';
      const prev = document.createElement('button');
      prev.type = 'button';
      prev.className = 'video-shelf__nav video-shelf__nav--prev';
      prev.setAttribute('aria-label', 'Прокрутить назад');
      prev.innerHTML = arrowSvg('prev');
      const next = document.createElement('button');
      next.type = 'button';
      next.className = 'video-shelf__nav video-shelf__nav--next';
      next.setAttribute('aria-label', 'Прокрутить вперёд');
      next.innerHTML = arrowSvg('next');
      shelf.appendChild(prev);
      shelf.appendChild(next);
      const step = () => Math.max(220, Math.round(root.clientWidth * 0.85));
      prev.addEventListener('click', () => root.scrollBy({ left: -step(), behavior: 'smooth' }));
      next.addEventListener('click', () => root.scrollBy({ left: step(), behavior: 'smooth' }));
      const updateArrows = () => {
        const max = root.scrollWidth - root.clientWidth - 2;
        prev.hidden = root.scrollLeft <= 2;
        next.hidden = root.scrollLeft >= max;
      };
      root.addEventListener('scroll', updateArrows, { passive: true });
      window.addEventListener('resize', updateArrows);
      updateArrows();
    }
  }

  fetch('data/videos.json')
    .then((r) => (r.ok ? r.json() : []))
    .then((videos) => {
      console.log('[videos] fetched', videos.length);
      if (!videos.length) { root.closest('.section').style.display = 'none'; return; }
      render(videos);
    })
    .catch((e) => { console.error('[videos] fetch failed', e); root.closest('.section').style.display = 'none'; });
})();

// ---------- Article page renderer ----------
(function () {
  const root = document.querySelector('[data-article]');
  if (!root) return;
  const params = new URLSearchParams(location.search);
  const id = params.get('id');

  // ALWAYS redirect to canonical SSR /a/<slug>. The SSR page has TL;DR,
  // entity-chips, Schema.org NewsArticle. data.js no longer carries full
  // article bodies (only listing metadata for the latest 80 articles), so
  // SPA rendering is not viable for older articles. Trust the id as slug.
  if (id && params.get('spa') !== '1') {
    location.replace('/a/' + id + (location.hash || ''));
    return;
  }
  if (typeof FBRK_DATA === 'undefined') return;
  const a = FBRK_DATA.articles.find((x) => x.id === id) || FBRK_DATA.articles[0];
  if (!a) return;

  document.title = `${a.title} — ФБРК`;

  // Reading time estimate
  const plainText = (a.dek || '') + ' ' + (a.sections || []).map((s) => (s.h || '') + ' ' + (s.p || '')).join(' ');
  const wordCount = plainText.trim().split(/\s+/).filter(Boolean).length;
  const readMin = Math.max(1, Math.round(wordCount / 180));

  // Share URL & targets
  const shareUrl = encodeURIComponent(location.href);
  const shareTitle = encodeURIComponent(a.title);
  const shareTargets = [
    { label: 'Telegram', href: `https://t.me/share/url?url=${shareUrl}&text=${shareTitle}`, icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>' },
    { label: 'X', href: `https://twitter.com/intent/tweet?url=${shareUrl}&text=${shareTitle}`, icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>' },
    { label: 'ВКонтакте', href: `https://vk.com/share.php?url=${shareUrl}&title=${shareTitle}`, icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12.785 16.241s.288-.032.435-.194c.136-.148.132-.427.132-.427s-.02-1.304.576-1.496c.588-.19 1.342 1.26 2.141 1.818.605.422 1.064.33 1.064.33l2.137-.03s1.117-.071.588-.964c-.043-.073-.308-.66-1.588-1.87-1.337-1.266-1.158-1.06.453-3.27.98-1.345 1.374-2.164 1.251-2.515-.118-.334-.848-.245-.848-.245l-2.434.016s-.18-.025-.314.056c-.13.08-.215.264-.215.264s-.377 1.022-.882 1.89c-1.064 1.832-1.49 1.929-1.664 1.814-.403-.267-.302-1.08-.302-1.658 0-1.806.27-2.558-.528-2.756-.264-.066-.459-.11-1.135-.116-.867-.009-1.6.003-2.016.209-.277.137-.49.443-.36.46.162.022.528.1.722.368.25.345.241 1.122.241 1.122s.144 2.135-.336 2.4c-.33.181-.782-.189-1.731-1.852-.486-.852-.853-1.794-.853-1.794s-.07-.175-.2-.269c-.156-.114-.374-.15-.374-.15l-2.313.015s-.348.01-.476.163c-.113.136-.009.418-.009.418s1.812 4.288 3.864 6.449c1.882 1.982 4.019 1.852 4.019 1.852z"/></svg>' },
    { label: 'Copy', href: '#', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>', copy: true },
  ];
  const shareHtml = `<div class="article__share" role="group" aria-label="Поделиться">
    <span class="article__share__label">Поделиться:</span>
    ${shareTargets.map((t) => `<a class="article__share__btn" href="${t.href}" ${t.copy ? 'data-copy' : 'target="_blank" rel="noopener"'} aria-label="${t.label}">${t.icon}</a>`).join('')}
  </div>`;

  root.innerHTML = `
    <article class="article container">
      <header class="article__head">
        <div class="kicker article__kicker">${a.categoryLabel}</div>
        <h1 class="article__title">${escapeHtml(a.title)}</h1>
        <p class="article__dek">${escapeHtml(a.dek)}</p>
        <div class="article__meta">
          <span>${fmtDateLong(a.dateIso) || a.date}</span>
          <span class="article__meta__dot">${readMin} мин чтения</span>
        </div>
        ${shareHtml}
      </header>
      <div class="article__cover">
        <img src="${fullCover(a)}" alt="${escapeHtml(a.title)}" width="1440" height="810" loading="eager"/>
      </div>
      <div class="article__body">
        ${a.sections.map((s) => `<h2>${escapeHtml(s.h).replace(/^(.)(.*)/,(_,f,r)=>f+r.toLowerCase())}</h2><p>${escapeHtml(s.p)}</p>`).join('')}
      </div>
                ${a.source && !a.source.includes('fbrk.kz') ? `<div class="article_source">Источник: <a href="${a.source}" target="_blank" rel="noopener">${new URL(a.source).hostname}</a></div>` : ''}

          <div class="ad-block ad-block--article" data-ad-slot="article-bottom"></div>
      <section class="related">
                    <h2 class="related__title">Материалы по теме</h2>
        <div class="card-grid">
          ${FBRK_DATA.articles
            .filter((x) => x.id !== a.id)
            .slice(0, 3)
            .map(
              (x) => {
                const hasImg = !!(x.image && String(x.image).trim());
                const cardCls = hasImg ? 'card' : 'card card--no-image';
                const mediaInner = hasImg
                  ? `<img src="${x.image}" alt="${escapeHtml(x.title)}" width="600" height="400" loading="lazy"/>`
                  : '';
                return `
            <article class="${cardCls}">
              <a href="/a/${x.slug || x.id}">
                <div class="card__media">
                  ${mediaInner}
                  <span class="card__date-badge">${fmtDateShort(x.dateIso) || x.date}</span>
                  ${importanceBadgeHtml(x)}${liveBadgeHtml(x)}
                </div>
                <h3 class="card__title">${escapeHtml(x.title)}</h3>
              </a>
              <p class="card__dek">${escapeHtml(x.dek)}</p>
            </article>`;
              }
            )
            .join('')}
        </div>
      </section>
                <div class="ad-block ad-block--footer" data-ad-slot="article-footer"></div>
    </article>
  `;

  // Copy-link handler
  root.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-copy]');
    if (!btn) return;
    e.preventDefault();
    navigator.clipboard?.writeText(location.href).then(() => {
      const prev = btn.innerHTML;
      btn.innerHTML = '<span style="font-size:.85em">Скопировано</span>';
      setTimeout(() => { btn.innerHTML = prev; }, 1600);
    });
  });
})();

// ---------- util ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ---------- Article page SEO (meta tags from article data) ----------
(function () {
  const titleEl = document.querySelector('[data-article-title]');
  if (!titleEl || typeof FBRK_DATA === 'undefined') return;
  const id = new URLSearchParams(location.search).get('id');
  const a = FBRK_DATA.articles.find((x) => x.id === id) || FBRK_DATA.articles[0];
  if (!a) return;
  const title = `${a.title} — ФБРК`;
  const desc = (a.dek || '').slice(0, 200);
  const url = `https://fbrk.qdev.run/a/${a.slug || a.id}`;
  const img = (a.image || '').startsWith('http') ? a.image : `https://fbrk.qdev.run${a.image || '/img/og-default.jpg'}`;
  titleEl.textContent = title;
  const descEl = document.querySelector('[data-article-desc]');
  if (descEl) descEl.setAttribute('content', desc);
  const canon = document.querySelector('[data-article-canonical]');
  if (canon) canon.setAttribute('href', url);
  const ogt = document.querySelector('[data-article-og-title]');
  if (ogt) ogt.setAttribute('content', title);
  const ogd = document.querySelector('[data-article-og-desc]');
  if (ogd) ogd.setAttribute('content', desc);
  const ogi = document.querySelector('[data-article-og-image]');
  if (ogi) ogi.setAttribute('content', img);
  const ogu = document.querySelector('[data-article-og-url]');
  if (ogu) ogu.setAttribute('content', url);
  const twt = document.querySelector('[data-article-tw-title]');
  if (twt) twt.setAttribute('content', title);
  const twd = document.querySelector('[data-article-tw-desc]');
  if (twd) twd.setAttribute('content', desc);
  const twi = document.querySelector('[data-article-tw-image]');
  if (twi) twi.setAttribute('content', img);

  // JSON-LD NewsArticle
  const ld = document.createElement('script');
  ld.type = 'application/ld+json';
  ld.textContent = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'NewsArticle',
    mainEntityOfPage: { '@type': 'WebPage', '@id': url },
    headline: (a.title || '').slice(0, 110),
    description: desc,
    image: [img],
    datePublished: a.dateIso || a.date,
    dateModified: a.updatedAt || a.dateIso || a.date,
    author: { '@type': 'Organization', name: 'ФБРК', url: 'https://fbrk.qdev.run/' },
    publisher: {
      '@type': 'NewsMediaOrganization',
      name: 'ФБРК',
      legalName: 'Фонд-бюро расследования коррупции',
      logo: { '@type': 'ImageObject', url: 'https://fbrk.qdev.run/img/brand/logo-brand-256.png', width: 256, height: 256 },
    },
    articleSection: a.categoryLabel || 'Новости',
    inLanguage: 'ru',
    isAccessibleForFree: true,
    keywords: Array.isArray(a.tags) && a.tags.length ? a.tags.join(', ') : undefined,
    speakable: { '@type': 'SpeakableSpecification', cssSelector: ['.article__title', '.article__dek', '.article__lead'] },
  });
  document.head.appendChild(ld);

  // BreadcrumbList
  const crumb = document.createElement('script');
  crumb.type = 'application/ld+json';
  crumb.textContent = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Главная', item: 'https://fbrk.qdev.run/' },
      { '@type': 'ListItem', position: 2, name: a.categoryLabel || 'Новости', item: 'https://fbrk.qdev.run/archive.html?cat=' + (a.category || 'news') },
      { '@type': 'ListItem', position: 3, name: a.title, item: url },
    ],
  });
  document.head.appendChild(crumb);
})();

// ---------- About page: live article counter ----------
(function () {
  const el = document.querySelector('[data-stat-articles]');
  if (!el || typeof FBRK_DATA === 'undefined') return;
  // Prefer totalCount published by data.js (full archive size), fall back to slice length.
  const n = (typeof FBRK_DATA.totalCount === 'number' ? FBRK_DATA.totalCount : FBRK_DATA.articles.length);
  el.textContent = n >= 1000 ? (n/1000).toFixed(1).replace('.0','') + 'k+' : String(n);
})();

// ---------- Search overlay: live counter ----------
(function () {
  const counter = document.querySelector('[data-search-count]');
  const input = document.querySelector('.search-overlay .search-box__input');
  const results = document.querySelector('.search-overlay .search-box__results');
  if (!counter || !input || !results || typeof FBRK_DATA === 'undefined') return;
  function dataset() {
    if (typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE.articles) return ARTICLES_ARCHIVE.articles;
    return FBRK_DATA.articles;
  }
  const totalCount = (typeof FBRK_DATA.totalCount === 'number' ? FBRK_DATA.totalCount : FBRK_DATA.articles.length);
  function update() {
    const data = dataset();
    const q = input.value.trim().toLowerCase();
    if (!q) { counter.textContent = `Всего материалов: ${totalCount}`; return; }
    const n = data.filter((a) => (a.title + ' ' + a.dek + ' ' + (a.tags||[]).join(' ')).toLowerCase().includes(q)).length;
    counter.textContent = n ? `Найдено: ${n}` : 'Ничего не найдено';
  }
  input.addEventListener('input', update);
  // initial + when overlay opens (click is handled in first block, we mirror via MutationObserver)
  update();
  new MutationObserver(update).observe(document.querySelector('.search-overlay'), { attributes: true, attributeFilter: ['class'] });
})();

// ---------- Archive page ----------
(function () {
  const grid = document.querySelector('[data-archive-grid]');
  if (!grid || typeof FBRK_DATA === 'undefined') return;

  const catSel = document.querySelector('[data-archive-cat]');
  const yearSel = document.querySelector('[data-archive-year]');
  const monthSel = document.querySelector('[data-archive-month]');
  const qInput = document.querySelector('[data-archive-q]');
  const moreBtn = document.querySelector('[data-archive-more]');
  const emptyEl = document.querySelector('[data-archive-empty]');
  const resetBtn = document.querySelector('[data-archive-reset]');
  const countEl = document.querySelector('[data-archive-count]');
  const kickerEl = document.querySelector('[data-archive-kicker]');
  const titleEl = document.querySelector('[data-archive-title]');

  const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  const PAGE = 24;
  // Prefer full archive (data-archive.js) when available, fall back to data.js
  const all = (typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE.articles)
    ? ARTICLES_ARCHIVE.articles.slice()
    : FBRK_DATA.articles.slice();

  // Populate year select from data
  if (yearSel) {
    const years = Array.from(new Set(all.map((a) => (a.dateIso || '').slice(0, 4)).filter(Boolean))).sort().reverse();
    years.forEach((y) => {
      const o = document.createElement('option'); o.value = y; o.textContent = y;
      yearSel.appendChild(o);
    });
  }
  if (monthSel) {
    MONTHS.forEach((name, i) => {
      const o = document.createElement('option'); o.value = String(i + 1).padStart(2, '0'); o.textContent = name;
      monthSel.appendChild(o);
    });
  }

  // URL state
  const params = new URLSearchParams(location.search);
  if (catSel && params.get('cat')) catSel.value = params.get('cat');
  if (yearSel && params.get('year')) yearSel.value = params.get('year');
  if (monthSel && params.get('month')) monthSel.value = params.get('month');
  if (qInput && params.get('q')) qInput.value = params.get('q');

  // Update page title based on filter
  function updateHeader(cat) {
    if (!titleEl) return;
    if (cat === 'investigation') { titleEl.textContent = 'Расследования'; if (kickerEl) kickerEl.textContent = 'Архив'; }
    else if (cat === 'news') { titleEl.textContent = 'Новости'; if (kickerEl) kickerEl.textContent = 'Архив'; }
    else { titleEl.textContent = 'Архив материалов'; if (kickerEl) kickerEl.textContent = 'Архив'; }
  }

  let rendered = 0;
  let filtered = [];

  function filter() {
    const cat = catSel ? catSel.value : '';
    const year = yearSel ? yearSel.value : '';
    const month = monthSel ? monthSel.value : '';
    const q = qInput ? qInput.value.trim().toLowerCase() : '';
    updateHeader(cat);
    filtered = all.filter((a) => {
      if (cat && a.category !== cat) return false;
      const iso = a.dateIso || '';
      if (year && iso.slice(0, 4) !== year) return false;
      if (month && iso.slice(5, 7) !== month) return false;
      if (q) {
        const hay = (a.title + ' ' + a.dek + ' ' + (a.tags||[]).join(' ')).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    rendered = 0;
    grid.innerHTML = '';
    if (countEl) countEl.textContent = `Найдено материалов: ${filtered.length}`;
    if (!filtered.length) {
      if (emptyEl) emptyEl.hidden = false;
      if (moreBtn) moreBtn.style.display = 'none';
      return;
    }
    if (emptyEl) emptyEl.hidden = true;
    renderMore();
    // sync URL
    const next = new URLSearchParams();
    if (cat) next.set('cat', cat);
    if (year) next.set('year', year);
    if (month) next.set('month', month);
    if (q) next.set('q', q);
    const qs = next.toString();
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
  }

  function itemHtml(a) {
    const hasImg = !!(a.image && String(a.image).trim());
    const cardCls = hasImg ? 'card' : 'card card--no-image';
    const mediaInner = hasImg
      ? `<img src="${a.image}" alt="${escapeHtml(a.title)}" width="600" height="400" loading="lazy"/>`
      : '';
    return `
      <article class="${cardCls}">
        <a href="/a/${a.slug || a.id}">
          <div class="card__media">
            ${mediaInner}
            <span class="card__date-badge">${fmtDateShort(a.dateIso) || a.date}</span>
            ${importanceBadgeHtml(a)}${liveBadgeHtml(a)}
          </div>
          <h2 class="card__title">${escapeHtml(a.title)}</h2>
        </a>
        <p class="card__dek">${escapeHtml(a.dek)}</p>
      </article>`;
  }

  function renderMore() {
    const next = filtered.slice(rendered, rendered + PAGE);
    grid.insertAdjacentHTML('beforeend', next.map(itemHtml).join(''));
    rendered += next.length;
    if (moreBtn) {
      if (rendered >= filtered.length) {
        moreBtn.style.display = 'none';
      } else {
        moreBtn.style.display = '';
        moreBtn.textContent = `Показать ещё (осталось ${filtered.length - rendered})`;
      }
    }
  }

  [catSel, yearSel, monthSel].forEach((el) => el && el.addEventListener('change', filter));
  if (qInput) {
    let t;
    qInput.addEventListener('input', () => { clearTimeout(t); t = setTimeout(filter, 120); });
  }
  if (moreBtn) moreBtn.addEventListener('click', renderMore);
  if (resetBtn) resetBtn.addEventListener('click', () => {
    if (catSel) catSel.value = '';
    if (yearSel) yearSel.value = '';
    if (monthSel) monthSel.value = '';
    if (qInput) qInput.value = '';
    filter();
  });

  filter();
})();
