// ============================================================
// ФБРК — интерактив (AV DS 3.7.1)
// ============================================================

function _cfgOrigin(key) {
  try {
    const value = (window && window[key]) ? String(window[key]).trim() : '';
    if (!value) return '';
    return value.replace(/\/+$/, '');
  } catch (_) {
    return '';
  }
}

function siteOrigin() {
  const configured = _cfgOrigin('FBRK_PUBLIC_ORIGIN');
  if (configured) return configured;
  try {
    if (window.location && window.location.origin) {
      return window.location.origin.replace(/\/+$/, '');
    }
  } catch (_) {}
  return 'https://fbrk.qdev.run';
}

function backendOrigin() {
  const configured = _cfgOrigin('FBRK_BACKEND_ORIGIN');
  return configured || siteOrigin();
}

function absSiteUrl(pathOrUrl) {
  if (!pathOrUrl) return siteOrigin();
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  const base = siteOrigin();
  if (String(pathOrUrl).startsWith('/')) return base + pathOrUrl;
  return base + '/' + pathOrUrl;
}

function absBackendUrl(pathOrUrl) {
  if (!pathOrUrl) return backendOrigin();
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  const base = backendOrigin();
  if (String(pathOrUrl).startsWith('/')) return base + pathOrUrl;
  return base + '/' + pathOrUrl;
}

function articleUrl(slugOrId) {
  const id = encodeURIComponent(String(slugOrId || ''));
  return absSiteUrl(`/a/${id}`);
}

function articleHref(a) {
  if (!a) return articleUrl('');
  return articleUrl(a.slug || a.id);
}

function articleLookupKeys(rawId) {
  const value = String(rawId || '').trim();
  if (!value) return [];
  const keys = [value];
  const legacySlug = value.replace(/-\d{4}-\d{2}-\d{2}-\d{2}_\d{2}_\d{2}$/, '');
  if (legacySlug && legacySlug !== value) keys.push(legacySlug);
  return keys;
}

function findArticleByKeys(list, rawId) {
  if (!Array.isArray(list) || !list.length) return null;
  const keys = articleLookupKeys(rawId);
  if (!keys.length) return null;
  return list.find((item) => item && keys.some((key) => item.id === key || item.slug === key)) || null;
}

// Align static SEO tags with runtime public origin in split-hosting mode.
(function normalizeStaticSeoHost() {
  const base = siteOrigin();
  const isDefault = base === 'https://fbrk.qdev.run';
  if (isDefault) return;
  const path = (location && location.pathname) ? location.pathname : '/';
  const href = (path === '/' || path === '/index.html') ? '/' : path;
  const canonical = document.querySelector('link[rel="canonical"]');
  if (canonical) canonical.setAttribute('href', absSiteUrl(href));
  const ogUrl = document.querySelector('meta[property="og:url"]');
  if (ogUrl) ogUrl.setAttribute('content', absSiteUrl(href));
  const hreflangs = document.querySelectorAll('link[rel="alternate"][hreflang]');
  hreflangs.forEach((el) => el.setAttribute('href', absSiteUrl('/')));
  const imgMeta = document.querySelectorAll('meta[property="og:image"],meta[name="twitter:image"]');
  imgMeta.forEach((el) => {
    const content = (el.getAttribute('content') || '').trim();
    if (!content) return;
    if (content.startsWith('/')) {
      el.setAttribute('content', absSiteUrl(content));
      return;
    }
    if (content.includes('fbrk.qdev.run')) {
      el.setAttribute('content', content.replace('https://fbrk.qdev.run', base));
    }
  });
  const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
  ldScripts.forEach((script) => {
    const raw = script.textContent || '';
    if (!raw.includes('fbrk.qdev.run')) return;
    script.textContent = raw.replace(/https:\/\/fbrk\.qdev\.run/g, base);
  });
})();

// Static utility pages can opt into the common shell by omitting duplicated
// header/footer markup. Keep this before global controls initialize.
(function ensureSiteShell() {
  if (!document.querySelector('.site-header')) {
    document.body.insertAdjacentHTML('afterbegin', `
      <header class="site-header" role="banner">
        <div class="container site-header__inner">
          <a class="site-header__logo" href="/" aria-label="ФБРК — на главную"><span class="site-header__logo-mark">ФБРК</span><span class="site-header__logo-text">Фонд-бюро расследования коррупции</span></a>
          <nav class="site-header__nav" aria-label="Основная навигация" data-site-nav>
            <ul role="list"><li><a href="/" data-nav-link="home">Главная</a></li><li><a href="/archive.html?cat=investigation" data-nav-link="investigation">Расследования</a></li><li><a href="/archive.html?cat=news" data-nav-link="news">Новости</a></li><li><a href="/archive.html" data-nav-link="archive">Архив</a></li><li><a href="/about.html" data-nav-link="about">О нас</a></li></ul>
          </nav>
          <div class="site-header__actions">
            <div class="lang-switch" role="group" aria-label="Язык сайта"><button type="button" data-lang="ru" aria-pressed="true">RU</button><button type="button" data-lang="kk" aria-pressed="false" aria-disabled="true">ҚАЗ</button></div>
            <span class="site-header__divider" aria-hidden="true"></span>
            <a class="site-header__btn" href="/search.html" data-search-open aria-label="Открыть поиск"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.35-4.35"/></svg></a>
            <button class="site-header__btn" type="button" data-theme-toggle aria-label="Переключить тему"></button>
            <a class="site-header__btn site-header__btn--social" href="https://t.me/fund_kz_bot" target="_blank" rel="noopener" aria-label="Telegram-бот"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg></a>
            <button class="site-header__btn site-header__menu-btn" type="button" data-menu-toggle aria-label="Меню" aria-expanded="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg></button>
          </div>
        </div>
      </header>
    `);
  }
  if (!document.querySelector('.site-footer')) {
    document.body.insertAdjacentHTML('beforeend', `
      <footer class="site-footer" role="contentinfo">
        <div class="container">
          <div class="site-footer__top">
            <div class="site-footer__brand-block"><div class="site-footer__brand"><span class="site-footer__brand-name">ФБРК</span></div><p class="site-footer__about">Фонд-бюро расследования коррупции — независимое сетевое издание. Свидетельство СМИ № KZ83VPY00075165 от 21.08.2023.</p></div>
            <div><div class="site-footer__heading">Разделы</div><ul class="site-footer__list" role="list"><li><a href="/">Главная</a></li><li><a href="/archive.html?cat=investigation">Расследования</a></li><li><a href="/archive.html?cat=news">Новости</a></li><li><a href="/archive.html">Архив</a></li></ul></div>
            <div><div class="site-footer__heading">Редакция</div><ul class="site-footer__list" role="list"><li><a href="/about.html">О нас</a></li><li><a href="/contacts.html">Контакты</a></li><li><a href="/editorial-policy.html">Редакционная политика</a></li><li><a href="/privacy.html">Политика конфиденциальности</a></li><li><a href="/feed.xml">RSS-лента</a></li><li><a href="/sitemap.html">Карта сайта</a></li></ul></div>
          </div>
          <div class="site-footer__bottom"><div class="site-footer__legal"><span>© 2023–2026 ФБРК</span><span aria-hidden="true">·</span><span class="site-footer__version">AV DS 3.7.1</span><span aria-hidden="true">·</span><span>Астана, Казахстан</span></div></div>
        </div>
      </footer>
    `);
  }
})();

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
    try { return localStorage.getItem('theme') || localStorage.getItem('fbrk_theme'); } catch (_) { return null; }
  })();
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  let current = stored === 'dark' || stored === 'light' ? stored : (prefersDark ? 'dark' : 'light');
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
      try {
        localStorage.setItem('theme', current);
        localStorage.setItem('fbrk_theme', current);
      } catch (_) {}
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
    if (btn.dataset.lang === 'kk') {
      btn.setAttribute('aria-disabled', 'true');
      btn.setAttribute('title', 'Қазақша нұсқасы жақын арада');
    }
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      if (lang === 'kk') {
        btn.setAttribute('aria-pressed', 'false');
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
  if (!nav.querySelector('[data-mobile-menu-panel]')) {
    nav.insertAdjacentHTML('beforeend', `
      <div class="site-header__mobile-panel" data-mobile-menu-panel>
        <div class="site-header__mobile-controls">
          <button class="site-header__btn site-header__mobile-theme" type="button" data-mobile-theme aria-label="Переключить тему">Тема</button>
          <div class="lang-switch site-header__mobile-lang" role="group" aria-label="Язык сайта">
            <button type="button" data-mobile-lang="ru" aria-pressed="true">RU</button>
            <button type="button" data-mobile-lang="kk" aria-pressed="false" aria-disabled="true" title="Қазақша нұсқасы жақын арада">ҚАЗ</button>
          </div>
        </div>
        <div class="site-header__mobile-socials" aria-label="Социальные сети">
          <a href="https://t.me/fund_kz_bot" target="_blank" rel="noopener" aria-label="Telegram-бот">Telegram</a>
          <a href="https://www.youtube.com/@fbrk_news" target="_blank" rel="noopener" aria-label="YouTube">YouTube</a>
        </div>
        <button class="site-header__mobile-close" type="button" data-menu-close aria-label="Закрыть меню">Закрыть</button>
      </div>
    `);
  }
  let lastFocus = null;
  function setOpen(open) {
    nav.classList.toggle('is-open', open);
    btn.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
    if (open) {
      lastFocus = document.activeElement;
      const first = nav.querySelector('a, button, [tabindex]:not([tabindex="-1"])');
      setTimeout(() => first?.focus(), 20);
    } else if (lastFocus && typeof lastFocus.focus === 'function') {
      lastFocus.focus();
    }
  }
  btn.addEventListener('click', () => {
    setOpen(!nav.classList.contains('is-open'));
  });
  nav.querySelector('[data-menu-close]')?.addEventListener('click', () => setOpen(false));
  nav.querySelector('[data-mobile-theme]')?.addEventListener('click', () => {
    document.querySelector('.site-header__actions [data-theme-toggle]')?.click();
  });
  nav.querySelectorAll('[data-mobile-lang]').forEach((langBtn) => {
    langBtn.addEventListener('click', () => {
      if (langBtn.dataset.mobileLang === 'kk') {
        langBtn.setAttribute('aria-pressed', 'false');
        return;
      }
      nav.querySelectorAll('[data-mobile-lang]').forEach((item) => {
        item.setAttribute('aria-pressed', item === langBtn ? 'true' : 'false');
      });
    });
  });
  nav.addEventListener('click', (e) => {
    if (e.target.closest('a')) {
      setOpen(false);
    }
    if (e.target === nav) {
      setOpen(false);
    }
  });
  document.addEventListener('keydown', (e) => {
    if (!nav.classList.contains('is-open')) return;
    if (e.key === 'Escape') {
      setOpen(false);
      return;
    }
    if (e.key !== 'Tab') return;
    const focusables = Array.from(nav.querySelectorAll('a, button, [tabindex]:not([tabindex="-1"])'))
      .filter((el) => !el.disabled && el.offsetParent !== null);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
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
  else if (path.startsWith('/contacts')) active = 'about';
  else if (path.startsWith('/editorial-policy')) active = 'about';
  else if (path.startsWith('/archive')) {
    if (cat === 'investigation') active = 'investigation';
    else if (cat === 'news') active = 'news';
    else active = 'archive';
  } else if (path.startsWith('/a/')) {
    const slug = decodeURIComponent(path.split('/').filter(Boolean).pop() || '');
    const items = []
      .concat((typeof FBRK_DATA !== 'undefined' && FBRK_DATA.articles) ? FBRK_DATA.articles : [])
      .concat((typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE.articles) ? ARTICLES_ARCHIVE.articles : []);
    const article = items.find((a) => a && (a.slug === slug || a.id === slug));
    active = article && article.category === 'investigation' ? 'investigation' : 'news';
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
  let activeIndex = -1;
  // Lazy getter: when full archive lands later, search uses it automatically.
  function dataset() {
    if (typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE.articles) return ARTICLES_ARCHIVE.articles;
    if (typeof FBRK_DATA !== 'undefined') return FBRK_DATA.articles;
    return [];
  }
  function resultLinks() {
    return Array.from(results.querySelectorAll('.search-result'));
  }
  function setActiveResult(index) {
    const links = resultLinks();
    if (!links.length) {
      activeIndex = -1;
      return;
    }
    activeIndex = Math.max(0, Math.min(index, links.length - 1));
    links.forEach((link, i) => {
      link.classList.toggle('is-active', i === activeIndex);
      if (i === activeIndex) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
    links[activeIndex].scrollIntoView({ block: 'nearest' });
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
    return `<a class="search-result" href="${articleHref(a)}">
      <div class="search-result__title">${escapeHtml(a.title)}</div>
      <div class="search-result__meta">${a.categoryLabel} · ${fmtDateLong(a.dateIso) || a.date}</div>
    </a>`;
  }
  function renderResults(q) {
    const data = dataset();
    q = q.trim().toLowerCase();
    if (!q) {
      results.innerHTML = data.slice(0, 5).map(toResultHtml).join('');
      activeIndex = -1;
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
      activeIndex = -1;
      return;
    }
    results.innerHTML = matches.map(toResultHtml).join('');
    setActiveResult(0);
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
  input.addEventListener('keydown', (e) => {
    const links = resultLinks();
    if (!links.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveResult(activeIndex < 0 ? 0 : activeIndex + 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveResult(activeIndex < 0 ? links.length - 1 : activeIndex - 1);
    } else if (e.key === 'Enter') {
      const target = links[activeIndex >= 0 ? activeIndex : 0];
      if (target) {
        e.preventDefault();
        window.location.href = target.href;
      }
    }
  });
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
  const meta = imageMeta(a);
  const image = meta.url;
  // swap /covers/thumb/ -> /covers/web/ for larger rendering
  if (image && image.includes('/covers/thumb/')) {
    return image.replace('/covers/thumb/', '/covers/web/');
  }
  return image;
}

function imageMeta(a) {
  const image = a && a.image;
  const meta = image && typeof image === 'object' ? image : {};
  const rawUrl = typeof image === 'string' ? image : (meta.url || meta.src || '');
  const url = String(rawUrl || '');
  let kind = String(a?.imageKind || meta.kind || '').toLowerCase();
  if (!kind) {
    if (/chatgpt|dall|midjourney|ai[-_%20]?image/i.test(url)) kind = 'ai';
    else if (/infographic|info[-_%20]?graphic|chart|diagram/i.test(url)) kind = 'infographic';
    else kind = 'photo';
  }
  const source = String(a?.imageSource || meta.source || '').trim();
  const hasRealPerson = Boolean(a?.imageHasRealPerson || meta.hasRealPerson);
  return { url, kind, source, hasRealPerson };
}

function imageKindClass(a) {
  return `image-kind-${imageMeta(a).kind}`;
}

function imageCaptionHtml(a) {
  const meta = imageMeta(a);
  if (meta.kind === 'ai' && meta.hasRealPerson) {
    return '<span class="image-caption image-caption--ai">Иллюстрация ИИ. Не является фотоматериалом</span>';
  }
  if (meta.kind === 'photo' && meta.source) {
    return `<span class="image-caption">Фото: ${escapeHtml(meta.source)}</span>`;
  }
  return '';
}

function truncateText(text, maxLength) {
  const clean = String(text || '').trim();
  if (!clean) return '';
  if (clean.length <= maxLength) return clean;
  return `${clean.slice(0, maxLength).trim()}…`;
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

// Live badge — pulse dot for fresh articles (published within last 6 hours).
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
    <a class="lead__media ${imageKindClass(featured)}" href="${articleHref(featured)}" aria-label="${escapeHtml(featured.title)}">
      <img src="${fullCover(featured)}" alt="${escapeHtml(featured.title)}" width="1200" height="800" loading="eager"/>
    </a>
    <div class="lead__body">
      <div class="kicker">${featured.categoryLabel}</div>
      <h1 class="lead__title">
        <a href="${articleHref(featured)}">${escapeHtml(featured.title)}</a>
      </h1>
      <p class="lead__dek">${escapeHtml(articleHeroDek(featured, []))}</p>
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
        <a href="${articleHref(a)}">
          <div class="card__media ${imageKindClass(a)}">
            ${mediaInner}
            <span class="card__date-badge">${fmtDateShort(a.dateIso) || a.date}</span>
            ${importanceBadgeHtml(a)}${liveBadgeHtml(a)}
          </div>
          <h3 class="card__title">${escapeHtml(a.title)}</h3>
        </a>
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
        : `<span class="latest__thumb-mark">ФБРК</span>`;
      return `
      <li class="latest__item">
        <a class="${thumbCls} ${imageKindClass(a)}" href="${articleHref(a)}" aria-label="${escapeHtml(a.title)}">
          ${thumbInner}
          ${importanceBadgeHtml(a)}${liveBadgeHtml(a)}
        </a>
        <div>
          <h3 class="latest__title">
            <a href="${articleHref(a)}">${escapeHtml(a.title)}</a>
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
  const pathMatch = (location.pathname || '').match(/^\/a\/([^/?#]+)/);
  const id = params.get('id') || (pathMatch ? decodeURIComponent(pathMatch[1]) : '');
  if (!id) return;

  const primary = (typeof FBRK_DATA !== 'undefined' && Array.isArray(FBRK_DATA.articles))
    ? FBRK_DATA.articles
    : [];
  const fullArticles = (typeof ARTICLE_FULL !== 'undefined' && Array.isArray(ARTICLE_FULL.articles))
    ? ARTICLE_FULL.articles
    : [];
  const archive = (typeof ARTICLES_ARCHIVE !== 'undefined' && Array.isArray(ARTICLES_ARCHIVE.articles))
    ? ARTICLES_ARCHIVE.articles
    : [];
  const compactArticle = findArticleByKeys(primary, id) || findArticleByKeys(archive, id);
  const fullArticle = findArticleByKeys(fullArticles, id);
  const a = fullArticle
    ? { ...(compactArticle || {}), ...fullArticle }
    : compactArticle;

  // If article is not present in local static data, fallback to backend canonical.
  const redirectToBackend = backendOrigin() !== siteOrigin();
  if (!a) {
    if (redirectToBackend) {
      location.replace(absBackendUrl(`/a/${encodeURIComponent(id)}`) + (location.hash || ''));
    }
    return;
  }

  const canonicalSlug = String(a.slug || a.id || '').trim();
  if (pathMatch && canonicalSlug && canonicalSlug !== id) {
    history.replaceState(null, '', `${articleUrl(canonicalSlug)}${location.hash || ''}`);
  }

  const sectionItems = Array.isArray(a.sections)
    ? a.sections.filter((s) => s && ((s.h && String(s.h).trim()) || (s.p && String(s.p).trim())))
    : [];
  const fallbackParagraphs = String(a.dek || '')
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}/)
    .map((x) => x.trim())
    .filter(Boolean)
    .map((p) => ({ h: '', p }));
  const bodySections = sectionItems.length ? sectionItems : fallbackParagraphs;
  const heroDek = articleHeroDek(a, sectionItems);
  const articleDateLabel = fmtDateLong(a.dateIso) || a.date || '';

  document.title = `${a.title} — ФБРК`;

  // Reading time estimate
  const plainText = (heroDek || '') + ' ' + bodySections.map((s) => (s.h || '') + ' ' + (s.p || '')).join(' ');
  const wordCount = plainText.trim().split(/\s+/).filter(Boolean).length;
  const readMin = Math.max(1, Math.round(wordCount / 180));

  // Share URL & targets
  const shareUrl = encodeURIComponent(location.href);
  const shareTitle = encodeURIComponent(a.title);
  const shareTargets = [
    { label: 'Telegram', href: `https://t.me/share/url?url=${shareUrl}&text=${shareTitle}`, icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>' },
    { label: 'X', href: `https://twitter.com/intent/tweet?url=${shareUrl}&text=${shareTitle}`, icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>' },
    { label: 'ВКонтакте', href: `https://vk.com/share.php?url=${shareUrl}&title=${shareTitle}`, icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12.785 16.241s.288-.032.435-.194c.136-.148.132-.427.132-.427s-.02-1.304.576-1.496c.588-.19 1.342 1.26 2.141 1.818.605.422 1.064.33 1.064.33l2.137-.03s1.117-.071.588-.964c-.043-.073-.308-.66-1.588-1.87-1.337-1.266-1.158-1.06.453-3.27.98-1.345 1.374-2.164 1.251-2.515-.118-.334-.848-.245-.848-.245l-2.434.016s-.18-.025-.314.056c-.13.08-.215.264-.215.264s-.377 1.022-.882 1.89c-1.064 1.832-1.49 1.929-1.664 1.814-.403-.267-.302-1.08-.302-1.658 0-1.806.27-2.558-.528-2.756-.264-.066-.459-.11-1.135-.116-.867-.009-1.6.003-2.016.209-.277.137-.49.443-.36.46.162.022.528.1.722.368.25.345.241 1.122.241 1.122s.144 2.135-.336 2.4c-.33.181-.782-.189-1.731-1.852-.486-.852-.853-1.794-.853-1.794s-.07-.175-.2-.269c-.156-.114-.374-.15-.374-.15l-2.313.015s-.348.01-.476.163c-.113.136-.009.418-.009.418s1.812 4.288 3.864 6.449c1.882 1.982 4.019 1.852 4.019 1.852z"/></svg>' },
    { label: 'Скопировать ссылку', href: '#', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>', copy: true },
  ];
  const shareHtml = `<div class="article__share" role="group" aria-label="Поделиться">
    <span class="article__share__label">Поделиться:</span>
    ${shareTargets.map((t) => `<a class="article__share__btn" href="${t.href}" ${t.copy ? 'data-copy' : 'target="_blank" rel="noopener"'} aria-label="${t.label}">${t.icon}</a>`).join('')}
  </div>`;
  const rawTags = articleTags(a);
  const visibleEntities = articleEntities(a.entities, rawTags);
  const tldrHtml = renderArticleTldr(a);
  const entitiesHtml = renderArticleEntities(visibleEntities);
  const tagsHtml = renderArticleTags(articleTags(a, visibleEntities.map((e) => e.name)));

  root.innerHTML = `
    <article class="article container">
      <header class="article__head">
        <div class="kicker article__kicker">
          <span>${escapeHtml(a.categoryLabel || 'Материал')}</span>
          ${articleDateLabel ? `<span class="article__kicker-sep" aria-hidden="true">·</span><time datetime="${escapeHtml(a.dateIso || '')}">${escapeHtml(articleDateLabel)}</time>` : ''}
          <span class="article__kicker-sep" aria-hidden="true">·</span>
          <span class="article__kicker-meta">${readMin} мин чтения</span>
        </div>
        <h1 class="article__title">${escapeHtml(a.title)}</h1>
        ${heroDek ? `<p class="article__dek">${escapeHtml(heroDek)}</p>` : ''}
      </header>
      <div class="article__cover ${imageKindClass(a)}">
        <img src="${fullCover(a)}" alt="${escapeHtml(a.title)}" width="1440" height="810" loading="eager"/>
        ${imageCaptionHtml(a)}
      </div>
      <div class="article__body">
        ${bodySections.map((s) => {
          const h = String((s && s.h) || '').trim();
          const p = String((s && s.p) || '').trim();
          const hHtml = h ? `<h2>${escapeHtml(h)}</h2>` : '';
          const pHtml = p ? renderArticleParagraphs(p) : '';
          return hHtml + pHtml;
        }).join('')}
      </div>
      ${tldrHtml}
      ${entitiesHtml}
      ${shareHtml}
      ${tagsHtml}
      ${a.source && !a.source.includes('fbrk.kz') ? `<div class="article__source">Источник: <a href="${a.source}" target="_blank" rel="noopener">${new URL(a.source).hostname}</a></div>` : ''}

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
              <a href="${articleHref(x)}">
                <div class="card__media ${imageKindClass(x)}">
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
})();

// ---------- util ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function safeArticleUrl(raw) {
  const value = String(raw || '').trim();
  if (!value) return '';
  try {
    const url = new URL(value, location.origin);
    if (url.protocol === 'http:' || url.protocol === 'https:' || url.protocol === 'mailto:') {
      return url.href;
    }
  } catch (_) {}
  return '';
}

function sanitizeArticleInlineHtml(raw) {
  const template = document.createElement('template');
  template.innerHTML = String(raw || '');
  const allowedTextTags = new Set(['b', 'strong', 'i', 'em', 'u', 's', 'sub', 'sup', 'code']);

  function clean(node) {
    if (node.nodeType === Node.TEXT_NODE) return escapeHtml(node.textContent || '');
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    const tag = node.tagName.toLowerCase();
    const children = Array.from(node.childNodes).map(clean).join('');
    if (allowedTextTags.has(tag)) return `<${tag}>${children}</${tag}>`;
    if (tag === 'br') return '<br>';
    if (tag === 'a') {
      const href = safeArticleUrl(node.getAttribute('href'));
      if (!href) return children;
      return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">${children}</a>`;
    }
    if (tag === 'img') {
      const src = safeArticleUrl(node.getAttribute('src'));
      if (!src) return '';
      const alt = escapeHtml(node.getAttribute('alt') || '');
      return `<img src="${escapeHtml(src)}" alt="${alt}" loading="lazy" decoding="async">`;
    }
    return children;
  }

  return Array.from(template.content.childNodes).map(clean).join('');
}

function renderArticleParagraphs(raw) {
  return String(raw || '')
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => `<p>${sanitizeArticleInlineHtml(part).replace(/\n/g, '<br>')}</p>`)
    .join('');
}

function normalizedArticleText(value) {
  return String(value || '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function articleHeroDek(a, sectionItems = []) {
  const dek = String((a && a.dek) || '').trim();
  const summaryShort = String((a && a.summaryShort) || '').trim();
  const normalizedSections = Array.isArray(sectionItems) ? sectionItems : [];
  const firstParagraph = dek.split(/\n{2,}/)[0]?.trim() || '';

  if (summaryShort) {
    return truncateText(summaryShort, 240);
  }

  if (!dek) return '';

  if (!normalizedSections.length) {
    return truncateText(summaryShort || firstParagraph || dek, 420);
  }

  const firstSectionText = normalizedArticleText(`${sectionItems[0]?.h || ''} ${sectionItems[0]?.p || ''}`);
  const candidates = [
    dek,
    firstParagraph,
    summaryShort,
  ];

  for (const candidate of candidates) {
    const text = String(candidate || '').trim();
    if (!text || text.length > 420) continue;
    if (/\n\s*\n/.test(text)) continue;
    const normalizedDek = normalizedArticleText(text);
    if (normalizedDek && firstSectionText.startsWith(normalizedDek)) continue;
    return text;
  }

  return '';
}

function articleTags(a, excludedNames = []) {
  const excluded = new Set((excludedNames || []).map(normalizeEntityName).filter(Boolean));
  const seen = new Set();
  const tags = [];
  ((a && a.tags) || []).forEach((item) => {
    const value = String(item || '').trim();
    const key = normalizeEntityName(value);
    if (!value || !key || excluded.has(key) || seen.has(key)) return;
    tags.push(value);
    seen.add(key);
  });
  return tags.slice(0, 16);
}

function normalizeEntityName(value) {
  return String(value || '').trim().toLocaleLowerCase('ru-RU');
}

function articleEntities(entities, excludedNames = []) {
  if (!Array.isArray(entities) || !entities.length) return [];
  const publicTypes = new Set(['person', 'org', 'gov', 'place', 'law', 'case', 'money']);
  const excluded = new Set((excludedNames || []).map(normalizeEntityName).filter(Boolean));
  const seen = new Set();
  const items = [];
  entities.forEach((entity) => {
    if (!entity || typeof entity !== 'object') return;
    const name = String(entity.name || '').trim();
    const normalizedName = normalizeEntityName(name);
    const type = String(entity.type || 'other').toLowerCase().replace(/[^a-z0-9_-]/g, '') || 'other';
    if (!name || !normalizedName || !publicTypes.has(type) || excluded.has(normalizedName)) return;
    const key = `${type}:${normalizedName}`;
    if (seen.has(key)) return;
    seen.add(key);
    items.push({ name, type });
  });
  return items.slice(0, 12);
}

function renderArticleTldr(a) {
  const points = Array.isArray(a && a.keyPoints)
    ? a.keyPoints.map((x) => String(x || '').trim()).filter(Boolean).slice(0, 5)
    : [];
  if (!points.length) return '';
  return `
    <aside class="article__tldr" aria-label="Кратко">
      ${points.length ? `<ul class="article__tldr-list">${points.map((p) => `<li>${escapeHtml(p)}</li>`).join('')}</ul>` : ''}
    </aside>
  `;
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-copy]');
  if (!btn) return;
  e.preventDefault();
  navigator.clipboard?.writeText(location.href).then(() => {
    const prev = btn.innerHTML;
    btn.innerHTML = '<span style="font-size:.85em">Скопировано</span>';
    setTimeout(() => { btn.innerHTML = prev; }, 1600);
  });
});

function renderArticleEntities(entities) {
  if (!Array.isArray(entities) || !entities.length) return '';
  return `
    <div class="entity-chips" aria-label="Упомянуты в тексте">
      <h3 class="entity-chips__title">Упоминания</h3>
      <div class="entity-chips__row">
        ${entities.slice(0, 12).map((e) => `<span class="entity-chip entity-chip--${escapeHtml(e.type)}">${escapeHtml(e.name)}</span>`).join('')}
      </div>
    </div>
  `;
}

function renderArticleTags(tags) {
  if (!Array.isArray(tags) || !tags.length) return '';
  return `
    <div class="article__tags" aria-label="Теги">
      ${tags.map((tag) => `<a class="tag-chip" href="/archive.html?q=${encodeURIComponent(tag)}">${escapeHtml(tag)}</a>`).join('')}
    </div>
  `;
}

// ---------- Article page SEO (meta tags from article data) ----------
(function () {
  const titleEl = document.querySelector('[data-article-title]');
  if (!titleEl || typeof FBRK_DATA === 'undefined') return;
  const params = new URLSearchParams(location.search);
  const pathMatch = (location.pathname || '').match(/^\/a\/([^/?#]+)/);
  const id = params.get('id') || (pathMatch ? decodeURIComponent(pathMatch[1]) : '');
  const primary = Array.isArray(FBRK_DATA.articles) ? FBRK_DATA.articles : [];
  const fullArticles = (typeof ARTICLE_FULL !== 'undefined' && Array.isArray(ARTICLE_FULL.articles))
    ? ARTICLE_FULL.articles
    : [];
  const archive = (typeof ARTICLES_ARCHIVE !== 'undefined' && Array.isArray(ARTICLES_ARCHIVE.articles))
    ? ARTICLES_ARCHIVE.articles
    : [];
  const compactArticle = findArticleByKeys(primary, id)
    || findArticleByKeys(archive, id);
  const fullArticle = findArticleByKeys(fullArticles, id);
  const a = fullArticle
    ? { ...(compactArticle || {}), ...fullArticle }
    : compactArticle;
  if (!a) return;
  const base = siteOrigin();
  const title = `${a.title} — ФБРК`;
  const desc = (a.summaryShort || a.dek || '').slice(0, 200);
  const url = articleUrl(a.slug || a.id);
  const imageUrl = imageMeta(a).url || '/img/og-default.jpg';
  const img = imageUrl.startsWith('http') ? imageUrl : absSiteUrl(imageUrl);
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
    author: { '@type': 'Organization', name: 'ФБРК', url: base + '/' },
    publisher: {
      '@type': 'NewsMediaOrganization',
      name: 'ФБРК',
      legalName: 'Фонд-бюро расследования коррупции',
      logo: { '@type': 'ImageObject', url: absSiteUrl('/img/brand/logo-brand-256.png'), width: 256, height: 256 },
    },
    articleSection: a.categoryLabel || 'Новости',
    inLanguage: 'ru',
    isAccessibleForFree: true,
    keywords: Array.isArray(a.tags) && a.tags.length ? a.tags.join(', ') : undefined,
    speakable: { '@type': 'SpeakableSpecification', cssSelector: ['.article__title', '.article__dek', '.article__tldr-list'] },
  });
  document.head.appendChild(ld);

  // BreadcrumbList
  const crumb = document.createElement('script');
  crumb.type = 'application/ld+json';
  crumb.textContent = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Главная', item: base + '/' },
      { '@type': 'ListItem', position: 2, name: a.categoryLabel || 'Новости', item: base + '/archive.html?cat=' + (a.category || 'news') },
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
  el.textContent = n >= 1000 ? `${new Intl.NumberFormat('ru-KZ').format(Math.floor(n / 100) * 100)}+` : String(n);
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
    if (cat === 'investigation') { titleEl.textContent = 'Расследования'; if (kickerEl) kickerEl.textContent = 'Расследования'; document.title = 'Расследования — ФБРК'; }
    else if (cat === 'news') { titleEl.textContent = 'Новости'; if (kickerEl) kickerEl.textContent = 'Новости'; document.title = 'Новости — ФБРК'; }
    else { titleEl.textContent = 'Архив материалов'; if (kickerEl) kickerEl.textContent = 'Архив'; document.title = 'Архив материалов — ФБРК'; }
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
    if (countEl) countEl.textContent = `Найдено материалов: ${new Intl.NumberFormat('ru-KZ').format(filtered.length)}`;
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
    history.pushState(null, '', qs ? `?${qs}` : location.pathname);
  }

  function itemHtml(a) {
    const hasImg = !!imageMeta(a).url;
    const cardCls = hasImg ? 'card' : 'card card--no-image';
    const mediaInner = hasImg
      ? `<img src="${imageMeta(a).url}" alt="${escapeHtml(a.title)}" width="600" height="400" loading="lazy" decoding="async"/>`
      : '';
    return `
      <article class="${cardCls}">
        <a href="${articleHref(a)}">
          <div class="card__media ${imageKindClass(a)}">
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
  if (moreBtn) moreBtn.addEventListener('click', () => {
    moreBtn.disabled = true;
    moreBtn.textContent = 'Загрузка...';
    requestAnimationFrame(() => {
      renderMore();
      moreBtn.disabled = false;
    });
  });
  if (resetBtn) resetBtn.addEventListener('click', () => {
    if (catSel) catSel.value = '';
    if (yearSel) yearSel.value = '';
    if (monthSel) monthSel.value = '';
    if (qInput) qInput.value = '';
    filter();
  });

  filter();
})();

// ---------- Search page ----------
(function () {
  const root = document.querySelector('[data-search-page]');
  if (!root) return;
  const input = document.querySelector('[data-search-page-q]');
  const catSel = document.querySelector('[data-search-page-cat]');
  const results = document.querySelector('[data-search-page-results]');
  const empty = document.querySelector('[data-search-page-empty]');
  const reset = document.querySelector('[data-search-page-reset]');
  const count = document.querySelector('[data-search-page-count]');
  const data = (typeof FBRK_SEARCH_INDEX !== 'undefined' && Array.isArray(FBRK_SEARCH_INDEX.items))
    ? FBRK_SEARCH_INDEX.items
    : ((typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE.articles) ? ARTICLES_ARCHIVE.articles : FBRK_DATA.articles);

  const params = new URLSearchParams(location.search);
  if (input) input.value = params.get('q') || '';
  if (catSel) catSel.value = params.get('cat') || '';

  function highlight(text, q) {
    const value = escapeHtml(text || '');
    const term = String(q || '').trim();
    if (!term) return value;
    const safe = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return value.replace(new RegExp(`(${safe})`, 'ig'), '<mark>$1</mark>');
  }

  function searchable(a) {
    return String([a.title, a.dek, a.description, a.body, (a.tags || []).join(' ')].join(' ')).toLowerCase();
  }

  function render() {
    const q = (input?.value || '').trim();
    const cat = catSel?.value || '';
    const qLower = q.toLowerCase();
    const matches = data.filter((a) => {
      if (cat && a.category !== cat) return false;
      if (!qLower) return true;
      return searchable(a).includes(qLower);
    }).slice(0, 80);
    if (count) {
      const formatted = new Intl.NumberFormat('ru-KZ').format(matches.length);
      count.textContent = q ? `Найдено: ${formatted}` : `Материалов в индексе: ${new Intl.NumberFormat('ru-KZ').format(data.length)}`;
    }
    if (!matches.length) {
      if (results) results.innerHTML = '';
      if (empty) {
        empty.hidden = false;
        const text = empty.querySelector('[data-empty-query]');
        if (text) text.textContent = q;
      }
    } else {
      if (empty) empty.hidden = true;
      if (results) {
        results.innerHTML = matches.map((a) => `
          <article class="search-page-result">
            <a href="${articleHref(a)}">
              <div class="search-page-result__meta">${escapeHtml(a.categoryLabel || '')} · ${fmtDateLong(a.dateIso) || a.date || ''}</div>
              <h2>${highlight(a.title, q)}</h2>
              <p>${highlight(a.dek || a.description || '', q)}</p>
            </a>
          </article>
        `).join('');
      }
    }
    const next = new URLSearchParams();
    if (q) next.set('q', q);
    if (cat) next.set('cat', cat);
    history.replaceState(null, '', next.toString() ? `?${next}` : location.pathname);
  }
  input?.addEventListener('input', render);
  catSel?.addEventListener('change', render);
  reset?.addEventListener('click', () => {
    if (input) input.value = '';
    if (catSel) catSel.value = '';
    render();
    input?.focus();
  });
  render();
})();

// ---------- Functional cookie notice ----------
(function () {
  if (document.querySelector('[data-cookie-banner]')) return;
  let accepted = false;
  try { accepted = localStorage.getItem('cookie-consent') === 'ok'; } catch (_) {}
  if (accepted) return;
  const banner = document.createElement('div');
  banner.className = 'cookie-banner';
  banner.setAttribute('data-cookie-banner', '');
  banner.setAttribute('role', 'status');
  banner.innerHTML = `
    <p>Сайт использует функциональные cookie.</p>
    <div class="cookie-banner__actions">
      <a class="btn--secondary" href="/privacy.html">Подробнее</a>
      <button class="btn--primary" type="button" data-cookie-ok>OK</button>
    </div>
  `;
  document.body.appendChild(banner);
  requestAnimationFrame(() => banner.classList.add('is-visible'));
  banner.querySelector('[data-cookie-ok]')?.addEventListener('click', () => {
    try { localStorage.setItem('cookie-consent', 'ok'); } catch (_) {}
    banner.classList.remove('is-visible');
  });
})();
