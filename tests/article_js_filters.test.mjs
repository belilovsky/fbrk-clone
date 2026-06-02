import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../js/app.js', import.meta.url), 'utf8');

function makeElement() {
  return {
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    content: { childNodes: [] },
    dataset: {},
    getAttribute() { return ''; },
    insertAdjacentHTML() {},
    setAttribute() {},
    addEventListener() {},
    appendChild() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    textContent: '',
  };
}

const context = {
  console,
  Date,
  URL,
  URLSearchParams,
  requestAnimationFrame(callback) { return setTimeout(callback, 0); },
  setTimeout,
  clearTimeout,
  location: { href: 'https://fbrk.qdev.run/a/sample', origin: 'https://fbrk.qdev.run', pathname: '/a/sample', search: '' },
  localStorage: { getItem() { return null; }, setItem() {} },
  navigator: { clipboard: { writeText() { return Promise.resolve(); } } },
  window: null,
  document: {
    documentElement: makeElement(),
    body: makeElement(),
    createElement() { return makeElement(); },
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener() {},
  },
  FBRK_DATA: { articles: [] },
  ARTICLE_FULL: { articles: [] },
  ARTICLES_ARCHIVE: { articles: [] },
};
context.window = context;
vm.createContext(context);
vm.runInContext(source, context, { filename: 'js/app.js' });

test('article entities hide fallback other tags and duplicates with tags', () => {
  const tags = context.articleTags({
    tags: ['БНР', 'мясопотребление', 'Казахстан', 'статистика'],
  });
  const entities = context.articleEntities([
    { name: 'БНР', type: 'other' },
    { name: 'мясопотребление', type: 'other' },
    { name: 'Казахстан', type: 'place' },
    { name: 'Министерство финансов', type: 'gov' },
  ], tags);

  assert.equal(JSON.stringify(entities), JSON.stringify([{ name: 'Министерство финансов', type: 'gov' }]));
  assert.equal(
    JSON.stringify(context.articleTags({ tags: ['БНР', 'Казахстан', 'статистика'] }, entities.map((e) => e.name))),
    JSON.stringify(['БНР', 'Казахстан', 'статистика']),
  );
});

test('article hero dek hides long imported investigation body duplicates', () => {
  const longDek = [
    'Редакция ФБРК с конца прошлого года анализирует динамику изменения площадей крупнейших землепользователей Казахстана.',
    'Напомним, в редакцию ФБРК массово поступают жалобы из регионов на некорректное изъятие.',
    'После нашей публикации, шымкентский филиал Правительства для граждан все же выслал запрашиваемую информацию.',
  ].join('\n\n');

  assert.equal(
    context.articleHeroDek({ dek: longDek }, [{ h: '', p: longDek }]),
    '',
  );
});

test('article hero dek keeps concise editorial lead', () => {
  assert.equal(
    context.articleHeroDek(
      { dek: 'Короткий редакционный лид для статьи.' },
      [{ h: '', p: 'Основной текст начинается другим предложением.' }],
    ),
    'Короткий редакционный лид для статьи.',
  );
});

test('article hero dek prefers editorial dek over ai summary when available', () => {
  assert.equal(
    context.articleHeroDek(
      {
        dek: 'Исходный редакционный лид для статьи.',
        summaryShort: 'Сжатое AI-описание для шапки материала.',
      },
      [{ h: '', p: 'Основной текст статьи.' }],
    ),
    'Исходный редакционный лид для статьи.',
  );
});

test('ai image caption uses neutral wording without illustration label', () => {
  assert.equal(
    context.imageCaptionHtml({
      imageKind: 'ai',
      imageHasRealPerson: true,
    }),
    '<span class="image-caption image-caption--ai">ИИ-изображение. Не является фотоматериалом</span>',
  );
});

test('article hero dek falls back to summary for duplicated long investigation import', () => {
  const importedDek = [
    'Редакция ФБРК с конца прошлого года анализирует динамику изменения площадей крупнейших землепользователей Казахстана.',
    'Нашей целью было выяснить, сколько земель было изъято у крупнейших собственников.',
    'После нашей публикации шымкентский филиал все же выслал запрашиваемую информацию.',
  ].join('\n\n');

  assert.equal(
    context.articleHeroDek(
      {
        dek: importedDek,
        summaryShort: 'Шымкент впервые раскрыл данные по крупнейшим землепользователям после серии запросов ФБРК.',
      },
      [{ h: '', p: importedDek }],
    ),
    'Шымкент впервые раскрыл данные по крупнейшим землепользователям после серии запросов ФБРК.',
  );
});

test('article tldr renders only key points and hides duplicated summary lead', () => {
  const html = context.renderArticleTldr({
    summaryShort: 'AI lead that should move into article dek.',
    keyPoints: ['Первый пункт.', 'Второй пункт.'],
  });

  assert.ok(html.includes('article__tldr-list'));
  assert.ok(html.includes('Первый пункт.'));
  assert.ok(!html.includes('article__lead'));
});

test('article tldr stays hidden when there are no key points', () => {
  assert.equal(
    context.renderArticleTldr({ summaryShort: 'Есть только summary.' }),
    '',
  );
});

test('article tldr keeps full key points and only drops dangling helper words', () => {
  const html = context.renderArticleTldr({
    keyPoints: [
      'Лидеры: Туркестанская область и Жамбылская область об',
      'Совместные обследования с Узбекистаном и Кыргызстаном не выявили',
      'Короткий пункт',
    ],
  });

  assert.ok(html.includes('Жамбылская область'));
  assert.ok(!html.includes('Жамбылская область об'));
  assert.ok(html.includes('Кыргызстаном не выявили'));
  assert.ok(html.includes('Короткий пункт'));
});

test('article tldr falls back to section sentences when backend key points are clipped', () => {
  const html = context.renderArticleTldr({
    keyPoints: [
      'Горнолыжники из Казахстана тренируются за рубежом из-за нехватки',
      'Тренер Роман Григоров поддержал развитие Алматинского горного кл',
      'Кластер должен стать крупнейшим всесезонным турпроектом в Центра',
    ],
    sections: [
      { h: '', p: 'Отсутствие современной горной инфраструктуры в Алматы лишает казахстанских спортсменов возможности готовиться дома - часть из них проходит сборы в соседних странах.' },
      { h: 'ЧТО ГОВОРЯТ СПОРТСМЕНЫ', p: 'Представители спортивного сообщества публично выступили в поддержку развития проекта, указав на дефицит качественных трасс и объектов для подготовки.' },
      { h: 'ЧТО ТАКОЕ АЛМАТИНСКИЙ ГОРНЫЙ КЛАСТЕР', p: 'Проект предполагает объединение горных курортов Шымбулак, Бутаковка, Кимасар, Пионер и Ой-Карагай в единую туристическую систему с общей инфраструктурой и управлением.' },
    ],
  });

  assert.ok(html.includes('Отсутствие современной горной инфраструктуры в Алматы лишает казахстанских спортсменов возможности готовиться дома - часть из них проходит сборы в соседних странах.'));
  assert.ok(html.includes('Представители спортивного сообщества публично выступили в поддержку развития проекта, указав на дефицит качественных трасс и объектов для подготовки.'));
  assert.ok(!html.includes('Алматинского горного кл'));
});

test('article renderer keeps summary, mentions, and share below the body', () => {
  const bodyIdx = source.indexOf('<div class="article__body">');
  const tldrIdx = source.indexOf('${tldrHtml}');
  const entitiesIdx = source.indexOf('${entitiesHtml}');
  const shareIdx = source.indexOf('${shareHtml}');

  assert.ok(bodyIdx > -1);
  assert.ok(tldrIdx > bodyIdx);
  assert.ok(entitiesIdx > tldrIdx);
  assert.ok(shareIdx > entitiesIdx);
});

test('image meta normalizes local upload paths on article routes', () => {
  assert.equal(
    context.imageMeta({ image: 'img/uploads/thumb/example.webp' }).url,
    '/img/uploads/thumb/example.webp',
  );
  assert.equal(
    context.imageMeta({ image: '/img/uploads/thumb/example.webp' }).url,
    '/img/uploads/thumb/example.webp',
  );
});

test('homepage focus cards keep investigations honest and fallback to latest when needed', () => {
  const shownIds = new Set(['featured']);
  const investigationFocus = context.homeFocusCards([
    { id: 'featured', category: 'news' },
    { id: 'i1', category: 'investigation' },
    { id: 'n1', category: 'news' },
  ], shownIds, 6);

  assert.equal(investigationFocus.mode, 'investigation');
  assert.equal(JSON.stringify(investigationFocus.items.map((item) => item.id)), JSON.stringify(['i1']));

  const latestFocus = context.homeFocusCards([
    { id: 'featured', category: 'news' },
    { id: 'n1', category: 'news' },
    { id: 'n2', category: 'news' },
  ], shownIds, 6);

  assert.equal(latestFocus.mode, 'latest');
  assert.equal(JSON.stringify(latestFocus.items.map((item) => item.id)), JSON.stringify(['n1', 'n2']));
});

test('article hero dek uses summary when compact cards do not have sections yet', () => {
  assert.equal(
    context.articleHeroDek(
      {
        dek: 'Очень длинный импортированный лид.\n\nВторой абзац повторяет структуру старого материала.',
        summaryShort: 'Короткий lead для компактной карточки.',
      },
      [],
    ),
    'Короткий lead для компактной карточки.',
  );
});

test('article hero dek drops metadata-only lead in compact cards', () => {
  assert.equal(
    context.articleHeroDek(
      {
        dek: '(2 февраля 2026 | Источники: Tengrinews.kz, Kursiv.kz, Nege.kz)',
      },
      [],
    ),
    '',
  );
});

test('article section headings drop all-caps while preserving acronyms and title nouns', () => {
  assert.equal(
    context.formatArticleSectionHeading(
      'ЧТО ЗАЯВИЛИ В МВД',
      'Ребенок погиб под колесами бетономешалки в Астане',
    ),
    'Что заявили в МВД',
  );
  assert.equal(
    context.formatArticleSectionHeading(
      'КАКИЕ ДОГОВОРЕННОСТИ ДОСТИГЛИ КАЗАХСТАН И РОССИЯ',
      'Казахстан и Россия протестировали беспилотный маршрут Астана - Москва',
    ),
    'Какие договоренности достигли Казахстан и Россия',
  );
});

test('article date label keeps legacy date short format', () => {
  assert.equal(context.articleDateLabelFromData({ date: '15 мая 2026', dateIso: '' }), '15 мая');
  assert.equal(context.articleDateLabelFromData({ date: '1 апреля 2025', dateIso: '' }), '1 апреля');
  assert.equal(context.articleDateLabelFromData({ date: 'old style', dateIso: '' }), 'old style');
});

test('article lookup keys keep legacy timestamp slug compatible', () => {
  assert.equal(
    JSON.stringify(context.articleLookupKeys('latifundisty-kazakhstana-glava-9-shymkent-2026-05-23-00_30_44')),
    JSON.stringify([
      'latifundisty-kazakhstana-glava-9-shymkent-2026-05-23-00_30_44',
      'latifundisty-kazakhstana-glava-9-shymkent',
    ]),
  );
});

test('article lookup finds canonical article by legacy timestamp slug', () => {
  assert.deepEqual(
    context.findArticleByKeys(
      [{ slug: 'latifundisty-kazakhstana-glava-9-shymkent', title: 'Шымкент' }],
      'latifundisty-kazakhstana-glava-9-shymkent-2026-05-23-00_30_44',
    ),
    { slug: 'latifundisty-kazakhstana-glava-9-shymkent', title: 'Шымкент' },
  );
});

test('editorial fallback classifies topics, series, and resonance', () => {
  const article = context.ensureEditorialFields({
    slug: 'latifundisty-kazakhstana-glava-9-shymkent',
    title: 'Латифундисты Казахстана. Глава 9: Шымкент',
    dek: 'Редакция ФБРК разбирает крупнейшие земельные массивы, пастбища и агробизнес региона.',
    category: 'investigation',
    importance: 4,
    tags: ['земля'],
  });

  assert.equal(article.series.slug, 'latifundisty-kazakhstana');
  assert.ok(article.topics.some((item) => item.slug === 'land-and-agro'));
  assert.equal(article.resonance, true);
});

test('editorial fallback classifies canonical region refs from raw region labels', () => {
  const article = context.ensureEditorialFields({
    slug: 'kanal-k-30',
    title: 'Канал К-30 в Туркестанской области намерены реконструировать',
    dek: 'Материал о местной инфраструктуре и воде.',
    category: 'news',
    region: 'Туркестан',
  });

  assert.equal(article.regionRef.slug, 'turkestanskaya-oblast');
  assert.equal(article.regionRef.title, 'Туркестанская область');
  assert.equal(article.region, 'Туркестан');
});

test('manual editorial status and labels render as normalized badges', () => {
  const article = context.ensureEditorialFields({
    slug: 'manual-editorial',
    title: 'Материал с ручной редакционной разметкой',
    editorialStatus: { slug: 'state-response' },
    editorialLabels: [{ slug: 'documents' }, { slug: 'monitoring' }],
  });

  assert.equal(context.articleEditorialStatusSlug(article), 'state-response');
  assert.equal(
    JSON.stringify(context.articleEditorialLabelSlugs(article)),
    JSON.stringify(['documents', 'monitoring']),
  );
  assert.equal(context.editorialStatusMeta('court-stage').title, 'Судебный процесс');
  assert.equal(context.editorialLabelMeta('documents').url, '/archive.html?label=documents');
  const html = context.cardEditorialBadgesHtml(article);
  assert.ok(html.includes('Ответ госоргана'));
  assert.ok(html.includes('Документы'));
  assert.ok(html.includes('Мониторинг'));
});

test('editorial catalog derives region hubs from article payload', () => {
  const catalog = context.editorialCatalogFromArticles([
    {
      slug: 'astana-case',
      title: 'Кейс из Астаны',
      dek: 'Столичный материал',
      category: 'news',
      dateIso: '2026-05-20',
      region: 'Астана',
    },
    {
      slug: 'karaganda-case',
      title: 'Кейс из Караганды',
      dek: 'Областной материал',
      category: 'news',
      dateIso: '2026-05-18',
      region: 'Караганда',
    },
  ]);

  assert.ok(Array.isArray(catalog.regions));
  assert.equal(catalog.regions[0].slug, 'astana');
  assert.equal(catalog.regions[0].url, '/archive.html?region=astana');
  assert.equal(catalog.regions[1].slug, 'karagandinskaya-oblast');
});

test('editorial hub page meta prefers published data and keeps defaults as fallback', () => {
  assert.equal(context.editorialHubPageMeta('topics').title, 'Темы');

  context.FBRK_DATA.editorialHubPages = {
    topics: {
      eyebrow: 'Редакционная карта',
      title: 'Досье и темы',
      description: 'Ключевые редакционные линии и быстрый вход в архив.',
      seo_title: 'Досье и темы',
      seo_description: 'Обновлённая страница тем ФБРК.',
    },
  };

  assert.equal(context.editorialHubPageMeta('topics').title, 'Досье и темы');
  assert.equal(context.editorialHubPageMeta('topics').eyebrow, 'Редакционная карта');
  assert.equal(context.editorialHubPageMeta('series').title, 'Серии');
});

test('homepage block meta prefers published data and keeps defaults as fallback', () => {
  assert.equal(context.homepageBlockMeta('resonance').title, 'Резонанс');

  context.FBRK_DATA.homepageBlocks = {
    resonance: {
      eyebrow: 'На старте',
      title: 'Главный резонанс',
      description: 'Подборка для первого экрана.',
      link_label: 'Смотреть всё',
    },
  };

  assert.equal(context.homepageBlockMeta('resonance').title, 'Главный резонанс');
  assert.equal(context.homepageBlockMeta('resonance').eyebrow, 'На старте');
  assert.equal(context.homepageBlockMeta('resonance').link_label, 'Смотреть всё');
  assert.equal(context.homepageBlockMeta('regions').title, 'По регионам');
});

test('archive active filters expose readable labels for current state', () => {
  context.ARTICLES_ARCHIVE.topics = [{ slug: 'corruption', title: 'Коррупция и Антикор' }];
  context.ARTICLES_ARCHIVE.regions = [{ slug: 'astana', title: 'Астана' }];
  context.ARTICLES_ARCHIVE.series = [{ slug: 'dezinsekciya-2025', title: 'Дезинсекция-2025' }];
  const filters = context.archiveActiveFilters({
    cat: 'news',
    year: '2026',
    month: '05',
    topic: 'corruption',
    region: 'astana',
    series: 'dezinsekciya-2025',
    status: 'state-response',
    label: 'documents',
    resonance: true,
    q: 'АФМ',
  }).map((item) => item.label);

  assert.ok(filters.includes('Новости'));
  assert.ok(filters.includes('2026'));
  assert.ok(filters.includes('Коррупция и Антикор'));
  assert.ok(filters.includes('Астана'));
  assert.ok(filters.includes('Дезинсекция-2025'));
  assert.ok(filters.includes('Ответ госоргана'));
  assert.ok(filters.includes('Документы'));
  assert.ok(filters.includes('Резонанс'));
  assert.ok(filters.includes('Запрос: АФМ'));
});

test('searchable article text includes editorial taxonomy fields', () => {
  const text = context.searchableArticleText({
    slug: 'search-smoke',
    title: 'Материал про реагирование госоргана',
    dek: 'Астана и документы по делу',
    category: 'news',
    categoryLabel: 'Новости',
    tags: ['АФМ'],
    region: 'Астана',
    series: { slug: 'dezinsekciya-2025', title: 'Дезинсекция-2025' },
    editorialStatus: { slug: 'state-response', title: 'Ответ госоргана' },
    editorialLabels: [{ slug: 'documents', title: 'Документы' }],
    topics: [{ slug: 'corruption', title: 'Коррупция и Антикор' }],
  });

  assert.ok(text.includes('астана'));
  assert.ok(text.includes('ответ госоргана'));
  assert.ok(text.includes('документы'));
  assert.ok(text.includes('дезинсекция-2025'));
  assert.ok(text.includes('коррупция и антикор'));
});

test('site profile hydrates footer and social links from published data', () => {
  const footerAbout = { textContent: '' };
  const footerCity = { textContent: '' };
  const logoText = { textContent: '' };
  const telegramBtn = { setAttribute(name, value) { this[name] = value; } };
  const footerTelegram = { setAttribute(name, value) { this[name] = value; } };
  const footerTelegramSocial = { setAttribute(name, value) { this[name] = value; } };
  const mobileTelegram = { setAttribute(name, value) { this[name] = value; } };
  const homepageTelegram = { textContent: '', setAttribute(name, value) { this[name] = value; } };
  const youtubeBtn = { setAttribute(name, value) { this[name] = value; } };
  const footerYoutube = { setAttribute(name, value) { this[name] = value; } };
  const footerYoutubeSocial = { setAttribute(name, value) { this[name] = value; } };
  const mobileYoutube = { setAttribute(name, value) { this[name] = value; } };
  const homepageYoutube = { setAttribute(name, value) { this[name] = value; } };

  context.document = {
    ...context.document,
    querySelector(selector) {
      return null;
    },
    querySelectorAll(selector) {
      if (selector === '.site-footer__about') return [footerAbout];
      if (selector === '.site-footer__legal span:last-child') return [footerCity];
      if (selector === '.site-header__logo-text') return [logoText];
      if (selector === '.site-header__btn--social[aria-label="Telegram-бот"]') return [telegramBtn];
      if (selector === '.site-footer__list a[href="https://t.me/fund_kz_bot"]') return [footerTelegram];
      if (selector === '.site-footer__socials a[aria-label="Telegram"]') return [footerTelegramSocial];
      if (selector === '.site-header__mobile-socials a[aria-label="Telegram-бот"]') return [mobileTelegram];
      if (selector === '[data-site-telegram-cta]') return [homepageTelegram];
      if (selector === '.site-header__btn--social[aria-label="YouTube"]') return [youtubeBtn];
      if (selector === '.site-footer__list a[href="https://www.youtube.com/@fbrk_news"]') return [footerYoutube];
      if (selector === '.site-footer__socials a[aria-label="YouTube"]') return [footerYoutubeSocial];
      if (selector === '.site-header__mobile-socials a[aria-label="YouTube"]') return [mobileYoutube];
      if (selector === '[data-site-youtube-link]') return [homepageYoutube];
      return [];
    },
  };
  context.FBRK_DATA = {
    ...context.FBRK_DATA,
    site: {
      fullName: 'Фонд-бюро расследования коррупции',
      footerAbout: 'Обновлённый footer текст',
      city: 'Алматы, Казахстан',
      telegram: 'https://t.me/fbrk_secure',
      telegramName: '@fbrk_secure',
      youtube: 'https://www.youtube.com/@fbrk_custom',
    },
  };

  context.applySiteProfile();

  assert.equal(logoText.textContent, 'Фонд-бюро расследования коррупции');
  assert.equal(footerAbout.textContent, 'Обновлённый footer текст');
  assert.equal(footerCity.textContent, 'Алматы, Казахстан');
  assert.equal(telegramBtn.href, 'https://t.me/fbrk_secure');
  assert.equal(footerTelegram.href, 'https://t.me/fbrk_secure');
  assert.equal(footerTelegramSocial.href, 'https://t.me/fbrk_secure');
  assert.equal(mobileTelegram.href, 'https://t.me/fbrk_secure');
  assert.equal(homepageTelegram.href, 'https://t.me/fbrk_secure');
  assert.equal(homepageTelegram.textContent, 'Открыть @fbrk_secure →');
  assert.equal(youtubeBtn.href, 'https://www.youtube.com/@fbrk_custom');
  assert.equal(footerYoutube.href, 'https://www.youtube.com/@fbrk_custom');
  assert.equal(footerYoutubeSocial.href, 'https://www.youtube.com/@fbrk_custom');
  assert.equal(mobileYoutube.href, 'https://www.youtube.com/@fbrk_custom');
  assert.equal(homepageYoutube.href, 'https://www.youtube.com/@fbrk_custom');
});

test('related picker prefers same series over generic latest items', () => {
  const current = {
    slug: 'latifundisty-kazakhstana-glava-9-shymkent',
    title: 'Латифундисты Казахстана. Глава 9: Шымкент',
    dek: 'Пастбища и земельные массивы.',
    category: 'investigation',
    importance: 4,
    tags: ['земля'],
  };
  const picks = context.pickRelatedArticlesClient(current, [
    {
      slug: 'latifundisty-kazakhstana-glava-8-almatinskaya-oblast',
      title: 'Латифундисты Казахстана. Глава 8: Алматинская область',
      dek: 'Земля и пастбища.',
      category: 'investigation',
      dateIso: '2026-05-05',
      tags: ['земля'],
    },
    {
      slug: 'obychnaya-svezhaya-novost',
      title: 'Обычная свежая новость',
      dek: 'Без связи с серией.',
      category: 'news',
      dateIso: '2026-05-20',
      tags: [],
    },
  ], 1);

  assert.equal(picks[0].slug, 'latifundisty-kazakhstana-glava-8-almatinskaya-oblast');
});

test('related picker matches regions by canonical slug, not raw label text', () => {
  const picks = context.pickRelatedArticlesClient(
    {
      slug: 'turkestan-current',
      title: 'Материал из Туркестана',
      dek: 'Текущий кейс.',
      category: 'news',
      dateIso: '2026-05-21',
      region: 'Туркестан',
    },
    [
      {
        slug: 'turk-region-nearby',
        title: 'Материал по Туркестанской области',
        dek: 'Связанный кейс.',
        category: 'news',
        dateIso: '2026-05-20',
        region: 'Туркестанская область',
      },
      {
        slug: 'other-region',
        title: 'Материал из Астаны',
        dek: 'Не тот регион.',
        category: 'news',
        dateIso: '2026-05-19',
        region: 'Астана',
      },
    ],
    1,
  );

  assert.equal(picks[0].slug, 'turk-region-nearby');
});
