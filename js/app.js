// ============================================================
// ФБРК — интерактив
// ============================================================

// ---------- Theme toggle ----------
(function () {
  const root = document.documentElement;
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  let current = systemDark ? 'dark' : 'light';
  root.setAttribute('data-theme', current);

  const sun =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>';
  const moon =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

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
      document.querySelectorAll('[data-theme-toggle]').forEach(render);
    });
  });
})();

// ---------- Shrink nav on scroll ----------
(function () {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  const onScroll = () => {
    nav.classList.toggle('is-shrunk', window.scrollY > 140);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();

// ---------- Search overlay ----------
(function () {
  const overlay = document.querySelector('.search-overlay');
  if (!overlay) return;
  const input = overlay.querySelector('.search-box__input');
  const results = overlay.querySelector('.search-box__results');
  const data = typeof FBRK_DATA !== 'undefined' ? FBRK_DATA.articles : [];

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

  function renderResults(q) {
    q = q.trim().toLowerCase();
    if (!q) {
      results.innerHTML = data
        .slice(0, 5)
        .map(toResultHtml)
        .join('');
      return;
    }
    const matches = data.filter((a) => {
      const hay = (a.title + ' ' + a.dek + ' ' + (a.tags || []).join(' ')).toLowerCase();
      return hay.includes(q);
    });
    if (!matches.length) {
      results.innerHTML =
        '<div style="color:var(--color-text-muted); padding: var(--space-4) 0;">Ничего не найдено. Попробуйте другой запрос.</div>';
      return;
    }
    results.innerHTML = matches.map(toResultHtml).join('');
  }

  function toResultHtml(a) {
    return `<a class="search-result" href="article.html?id=${a.id}">
      <div class="search-result__title">${a.title}</div>
      <div class="search-result__meta">${a.categoryLabel} · ${a.date} · ${a.author}</div>
    </a>`;
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
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
  ];
  const weekdays = [
    'Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота',
  ];
  const d = new Date();
  el.textContent = `${weekdays[d.getDay()]} · ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
})();

// ---------- Home page renderer ----------
(function () {
  const leadRoot = document.querySelector('[data-lead]');
  if (!leadRoot || typeof FBRK_DATA === 'undefined') return;
  const all = FBRK_DATA.articles;
  const featured = all.find((a) => a.featured) || all[0];
  const sideArticles = all.filter((a) => a.id !== featured.id).slice(0, 3);

  leadRoot.innerHTML = `
    <div class="lead__main">
      <a class="lead__image-wrap" href="article.html?id=${featured.id}">
        <img src="${featured.image}" alt="${escapeHtml(featured.title)}" loading="eager"/>
      </a>
      <div>
        <div class="kicker ${featured.category === 'investigation' ? 'kicker--investigation' : ''}">
          ${featured.categoryLabel}
        </div>
        <h1 class="lead__title" style="margin-top: var(--space-3)">
          <a href="article.html?id=${featured.id}">${escapeHtml(featured.title)}</a>
        </h1>
        <p class="lead__dek" style="margin-top: var(--space-4)">${escapeHtml(featured.dek)}</p>
        <div class="lead__meta" style="margin-top: var(--space-4)">
          <span class="lead__author">${featured.author}</span>
          <span class="dot">·</span>
          <span>${featured.date}</span>
        </div>
      </div>
    </div>
    <aside class="lead__side">
      ${sideArticles
        .map(
          (a) => `
        <div class="lead__side-item">
          <a class="lead__side-thumb" href="article.html?id=${a.id}">
            <img src="${a.image}" alt="${escapeHtml(a.title)}" loading="lazy"/>
          </a>
          <div>
            <div class="kicker ${a.category === 'investigation' ? 'kicker--investigation' : ''}" style="margin-bottom: var(--space-2); font-size: 0.625rem;">
              ${a.categoryLabel}
            </div>
            <h3 class="lead__side-title">
              <a href="article.html?id=${a.id}">${escapeHtml(a.title)}</a>
            </h3>
            <div class="lead__side-meta">${a.author} · ${a.date}</div>
          </div>
        </div>`
        )
        .join('')}
    </aside>
  `;

  // Investigations grid
  const invRoot = document.querySelector('[data-investigations]');
  if (invRoot) {
    const invs = all.filter((a) => a.category === 'investigation').slice(0, 3);
    invRoot.innerHTML = invs
      .map(
        (a) => `
      <article class="card">
        <a class="card__image" href="article.html?id=${a.id}">
          <img src="${a.image}" alt="${escapeHtml(a.title)}" loading="lazy"/>
        </a>
        <div class="kicker kicker--investigation">${a.categoryLabel}</div>
        <h3 class="card__title"><a href="article.html?id=${a.id}">${escapeHtml(a.title)}</a></h3>
        <p class="card__dek">${escapeHtml(a.dek)}</p>
        <div class="card__meta">
          <span>${a.author}</span>
          <span>·</span>
          <span>${a.date}</span>
        </div>
      </article>`
      )
      .join('');
  }

  // Latest list
  const latestRoot = document.querySelector('[data-latest]');
  if (latestRoot) {
    const featuredIds = new Set([featured.id, ...sideArticles.map((a) => a.id)]);
    const latest = all.filter((a) => !featuredIds.has(a.id)).slice(0, 8);
    latestRoot.innerHTML = latest
      .map(
        (a) => `
      <li class="latest__item">
        <a class="latest__thumb" href="article.html?id=${a.id}">
          <img src="${a.image}" alt="${escapeHtml(a.title)}" loading="lazy"/>
        </a>
        <div>
          <div class="kicker ${a.category === 'investigation' ? 'kicker--investigation' : ''}" style="margin-bottom: var(--space-2); font-size: 0.625rem;">
            ${a.categoryLabel}
          </div>
          <h3 class="latest__title">
            <a href="article.html?id=${a.id}">${escapeHtml(a.title)}</a>
          </h3>
          <div class="latest__meta">${a.author} · ${a.date}</div>
        </div>
      </li>`
      )
      .join('');
  }

  // Tag cloud
  const tagRoot = document.querySelector('[data-tags]');
  if (tagRoot && FBRK_DATA.tags) {
    tagRoot.innerHTML = FBRK_DATA.tags
      .map((t) => `<a class="tag" href="#" onclick="event.preventDefault()">${t}</a>`)
      .join('');
  }
})();

// ---------- Article page renderer ----------
(function () {
  const root = document.querySelector('[data-article]');
  if (!root || typeof FBRK_DATA === 'undefined') return;
  const id = new URLSearchParams(location.search).get('id');
  const a = FBRK_DATA.articles.find((x) => x.id === id) || FBRK_DATA.articles[0];
  if (!a) return;

  document.title = `${a.title} — ФБРК`;

  const isInvestigation = a.category === 'investigation';
  root.innerHTML = `
    <section class="article-hero">
      <div class="container container--default">
        <nav class="crumbs">
          <a href="index.html">Главная</a>
          <span class="crumbs__sep">›</span>
          <a href="index.html#${a.category === 'investigation' ? 'investigations' : 'latest'}">${a.categoryLabel}</a>
        </nav>
        <div class="kicker ${isInvestigation ? 'kicker--investigation' : ''} article-hero__kicker">
          ${a.categoryLabel}
        </div>
        <h1 class="article-hero__title">${escapeHtml(a.title)}</h1>
        <p class="article-hero__dek">${escapeHtml(a.dek)}</p>
        <div class="article-hero__meta">
          <span class="article-hero__author">${a.author}</span>
          <span class="dot">·</span>
          <span>${a.date}</span>
          ${a.source ? `<span class="dot">·</span><span>Источник: ${escapeHtml(a.source)}</span>` : ''}
        </div>
        <div class="article-hero__image">
          <img src="${a.image}" alt="${escapeHtml(a.title)}" loading="eager"/>
        </div>
      </div>
    </section>
    <section class="article-body">
      <div class="container">
        <div class="article-prose">
          ${a.sections
            .map(
              (s) => `
            <h2>${escapeHtml(s.h)}</h2>
            <p>${escapeHtml(s.p)}</p>`
            )
            .join('')}
          ${
            a.source
              ? `<div class="article-source">Источник: ${escapeHtml(a.source)}</div>`
              : ''
          }
          ${
            a.tags && a.tags.length
              ? `<div class="article-tags">
              <div class="article-tags__label">Теги</div>
              <div class="tag-cloud" style="margin-top: 0;">
                ${a.tags.map((t) => `<span class="tag">${t}</span>`).join('')}
              </div>
            </div>`
              : ''
          }
        </div>
      </div>
    </section>
    <section class="section">
      <div class="container">
        <header class="section__header">
          <h2 class="section__title">Читайте также</h2>
          <a class="section__link" href="index.html">Все материалы →</a>
        </header>
        <div class="card-grid">
          ${FBRK_DATA.articles
            .filter((x) => x.id !== a.id)
            .slice(0, 3)
            .map(
              (x) => `
            <article class="card">
              <a class="card__image" href="article.html?id=${x.id}">
                <img src="${x.image}" alt="${escapeHtml(x.title)}" loading="lazy"/>
              </a>
              <div class="kicker ${x.category === 'investigation' ? 'kicker--investigation' : ''}">${x.categoryLabel}</div>
              <h3 class="card__title"><a href="article.html?id=${x.id}">${escapeHtml(x.title)}</a></h3>
              <p class="card__dek">${escapeHtml(x.dek)}</p>
              <div class="card__meta"><span>${x.author}</span><span>·</span><span>${x.date}</span></div>
            </article>`
            )
            .join('')}
        </div>
      </div>
    </section>
  `;
})();

// ---------- util ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
