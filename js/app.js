// ============================================================
// ФБРК — интерактив (AV DS 4)
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

const EDITORIAL_TOPICS = [
  {
    slug: 'corruption',
    title: 'Коррупция и Антикор',
    description: 'Взятки, хищения, служебные злоупотребления, расследования и проверки вокруг публичных денег.',
    strongTerms: ['коррупц', 'антикор', 'взятк', 'растра', 'хищен', 'отмыв'],
    supportTerms: ['ущерб', 'аффилиир', 'злоупотреб', 'подкуп', 'легализ'],
  },
  {
    slug: 'budget-and-procurement',
    title: 'Бюджет и госзакупки',
    description: 'Госрасходы, аудит, тендеры, субсидии и цена управленческих решений в цифрах.',
    strongTerms: ['госзакуп', 'тендер', 'бюджет', 'аудит', 'вап', 'расходы ведомств', 'расходы регионов'],
    supportTerms: ['субсид', 'контракт', 'закуп', 'финанс', 'вознагражден', 'нацкомпан'],
  },
  {
    slug: 'land-and-agro',
    title: 'Земля и агробизнес',
    description: 'Земельные ресурсы, латифундисты, пастбища, фермеры и аграрная политика по регионам.',
    strongTerms: ['земл', 'латифунд', 'пастбищ', 'фермер', 'сельхоз', 'агро'],
    supportTerms: ['орошен', 'саранч', 'выпас', 'урож', 'мсх', 'скот'],
  },
  {
    slug: 'courts-and-siloviki',
    title: 'Суды и силовики',
    description: 'Судебные процессы, прокурорский надзор, МВД, КНБ и громкие уголовные дела.',
    strongTerms: ['прокуратур', 'суд', 'мвд', 'кнб', 'полиц', 'приговор'],
    supportTerms: ['задерж', 'экстрад', 'террор', 'арест', 'следств', 'подозрев'],
  },
  {
    slug: 'ecology-and-resources',
    title: 'Экология и ресурсы',
    description: 'Вода, воздух, отходы, природные ресурсы и экологические последствия решений государства и бизнеса.',
    strongTerms: ['эколог', 'загряз', 'воздух', 'вода', 'полигон', 'отход'],
    supportTerms: ['нефть', 'рудник', 'уран', 'сайгак', 'река', 'канал'],
  },
  {
    slug: 'assets-and-elites',
    title: 'Активы и элиты',
    description: 'Недвижимость, корпоративные активы, семьи элит и крупные интересы вокруг государства.',
    strongTerms: ['актив', 'недвижим', 'олигарх', 'самрук', 'казатомпром', 'назарбаев'],
    supportTerms: ['кулибаев', 'масимов', 'особняк', 'пентхаус', 'владел', 'бизнес-центр'],
  },
];

const EDITORIAL_SERIES = [
  {
    slug: 'latifundisty-kazakhstana',
    title: 'Латифундисты Казахстана',
    description: 'Длинная серия ФБРК о крупнейших землевладельцах, изъятиях и реальном балансе сельхозземель по регионам.',
    matchTerms: ['латифундисты казахстана'],
  },
  {
    slug: 'rashody-vedomstv-2024',
    title: 'Расходы ведомств - 2024',
    description: 'Разбор бюджетов министерств и ведомств: на что уходили деньги в 2024 году.',
    matchTerms: ['расходы ведомств - 2024', 'расходы ведомств – 2024'],
  },
  {
    slug: 'rashody-regionov-2024',
    title: 'Расходы регионов - 2024',
    description: 'Серия о тратах региональных бюджетов и приоритетах областных администраций.',
    matchTerms: ['расходы регионов - 2024', 'расходы регионов – 2024'],
  },
  {
    slug: 'top-menedzhery-nackompaniy',
    title: 'Вознаграждения топ-менеджеров нацкомпаний',
    description: 'Цикл о зарплатах, бонусах и управленческих вознаграждениях в крупнейших компаниях с госучастием.',
    matchTerms: ['впечатляющие вознаграждения топ-менеджеров нацкомпаний'],
  },
  {
    slug: 'dezinsekciya-2025',
    title: 'Дезинсекция-2025',
    description: 'Региональная серия ФБРК о химических и биологических обработках, их подрядчиках и последствиях.',
    matchTerms: ['дезинсекция-2025'],
  },
];

const EDITORIAL_REGIONS = [
  { slug: 'astana', title: 'Астана', description: 'Материалы о столице, республиканских органах и событиях в Астане.', aliases: ['астана'] },
  { slug: 'almaty', title: 'Алматы', description: 'Городские и республиканские сюжеты, связанные с Алматы.', aliases: ['алматы'] },
  { slug: 'shymkent', title: 'Шымкент', description: 'Материалы о Шымкенте и локальных кейсах юга страны.', aliases: ['шымкент'] },
  { slug: 'akmolinskaya-oblast', title: 'Акмолинская область', description: 'Региональные публикации по Акмолинской области и близлежащим городам.', aliases: ['акмолинская область', 'кокшетау', 'степногорск'] },
  { slug: 'almatinskaya-oblast', title: 'Алматинская область', description: 'Материалы о районах и инфраструктуре Алматинской области.', aliases: ['алматинская область'] },
  { slug: 'aktyubinskaya-oblast', title: 'Актюбинская область', description: 'Публикации по Актюбинской области и Актобе.', aliases: ['актюбинская область', 'актобе'] },
  { slug: 'atyrauskaya-oblast', title: 'Атырауская область', description: 'Материалы по Атырауской области и нефтегазовым кейсам региона.', aliases: ['атырауская область', 'атырау'] },
  { slug: 'vostochno-kazakhstanskaya-oblast', title: 'Восточно-Казахстанская область', description: 'Сюжеты по Восточному Казахстану и окрестностям Усть-Каменогорска.', aliases: ['восточно-казахстанская область', 'вко', 'восточный казахстан', 'усть-каменогорск'] },
  { slug: 'zhambylskaya-oblast', title: 'Жамбылская область', description: 'Публикации по Жамбылской области и Таразу.', aliases: ['жамбылская область', 'тараз'] },
  { slug: 'zapadno-kazakhstanskaya-oblast', title: 'Западно-Казахстанская область', description: 'Материалы по Западно-Казахстанской области и Уральску.', aliases: ['западно-казахстанская область', 'уральск'] },
  { slug: 'karagandinskaya-oblast', title: 'Карагандинская область', description: 'Публикации о Карагандинской области, Караганде, Темиртау и Балхаше.', aliases: ['карагандинская область', 'караганда', 'темиртау', 'балхаш'] },
  { slug: 'kostanayskaya-oblast', title: 'Костанайская область', description: 'Сюжеты по Костанайской области и Костанаю.', aliases: ['костанайская область', 'костанай'] },
  { slug: 'kyzylordinskaya-oblast', title: 'Кызылординская область', description: 'Материалы по Кызылординской области и Кызылорде.', aliases: ['кызылординская область', 'кызылорда'] },
  { slug: 'mangistauskaya-oblast', title: 'Мангистауская область', description: 'Публикации по Мангистауской области и Актау.', aliases: ['мангистауская область', 'актау'] },
  { slug: 'oblast-abay', title: 'Область Абай', description: 'Материалы по области Абай и Семею.', aliases: ['область абай', 'абайская область', 'семей', 'абай'] },
  { slug: 'pavlodarskaya-oblast', title: 'Павлодарская область', description: 'Публикации по Павлодарской области и Павлодару.', aliases: ['павлодарская область', 'павлодар'] },
  { slug: 'severo-kazakhstanskaya-oblast', title: 'Северо-Казахстанская область', description: 'Сюжеты по Северо-Казахстанской области и Петропавловску.', aliases: ['северо-казахстанская область', 'петропавловск'] },
  { slug: 'turkestanskaya-oblast', title: 'Туркестанская область', description: 'Материалы по Туркестанской области и Туркестану.', aliases: ['туркестанская область', 'туркестан', 'арысь'] },
  { slug: 'ulytauskaya-oblast', title: 'Улытауская область', description: 'Публикации по Улытауской области и Жезказгану.', aliases: ['улытауская область', 'область улытау', 'улытау', 'ұлытау', 'жезказган'] },
  { slug: 'zhetysu-oblast', title: 'Жетысуская область', description: 'Материалы по области Жетысу и Талдыкоргану.', aliases: ['жетысу', 'жетысуская область', 'область жетысу', 'жетісу область', 'жетісуская область', 'жетiсу область', 'талдыкорган'] },
];

const EDITORIAL_STATUSES = [
  {
    slug: 'follow-up',
    title: 'Продолжение темы',
    description: 'Материал развивает уже идущую редакционную линию и добавляет новое звено в историю.',
  },
  {
    slug: 'state-response',
    title: 'Ответ госоргана',
    description: 'Публикация с официальной реакцией ведомства, акимата или другого публичного органа.',
  },
  {
    slug: 'court-stage',
    title: 'Судебный процесс',
    description: 'Материал о судебном этапе: заседании, ходатайстве, решении или приговоре.',
  },
  {
    slug: 'archive-context',
    title: 'Контекст',
    description: 'Фоновый или архивный материал, который помогает удержать длинную тему в одном контуре.',
  },
];

const EDITORIAL_LABELS = [
  {
    slug: 'documents',
    title: 'Документы',
    description: 'Опора на письма, договоры, ответы ведомств и другие первичные документы.',
  },
  {
    slug: 'data',
    title: 'Данные',
    description: 'Материал строится на цифрах, таблицах, выборках или статистике.',
  },
  {
    slug: 'monitoring',
    title: 'Мониторинг',
    description: 'Редакция наблюдает за развитием кейса и собирает новые эпизоды в одну линию.',
  },
  {
    slug: 'explain',
    title: 'Разбор',
    description: 'Материал помогает объяснить механику сюжета, участников и последствия.',
  },
];

const RESONANCE_META = {
  slug: 'resonance',
  title: 'Резонанс',
  description: 'Важные материалы редакции.',
  url: '/resonance.html',
};

const EDITORIAL_HUB_PAGE_DEFAULTS = {
  topics: {
    eyebrow: 'Навигация',
    title: 'Темы',
    description: 'Самые важные редакционные линии ФБРК, через которые удобнее заходить в архив и разбирать большие сюжеты по слоям.',
    seo_title: 'Темы',
    seo_description: 'Ключевые темы ФБРК: коррупция, бюджет, земля, суды, экология и активы элит.',
  },
  regions: {
    eyebrow: 'География',
    title: 'Регионы',
    description: 'Материалы по городам и областям.',
    seo_title: 'Регионы',
    seo_description: 'Региональные хабы ФБРК: Астана, Алматы, Шымкент и ключевые области Казахстана.',
  },
  series: {
    eyebrow: 'Редакционный формат',
    title: 'Серии',
    description: 'Редакционные сюжеты в развитии.',
    seo_title: 'Серии',
    seo_description: 'Редакционные серии ФБРК: длительные расследовательские и дата-циклы, собранные в понятные линии.',
  },
  resonance: {
    eyebrow: 'Подборка',
    title: 'Резонанс',
    description: 'Важные материалы редакции.',
    seo_title: 'Резонанс',
    seo_description: 'Подборка материалов ФБРК с повышенной редакционной значимостью.',
  },
};

const HOMEPAGE_BLOCK_DEFAULTS = {
  resonance: {
    eyebrow: 'Выбор редакции',
    title: 'Резонанс',
    description: 'Что открыть в первую очередь.',
    link_label: 'Вся подборка',
    url: '/resonance.html',
  },
  regions: {
    eyebrow: 'География',
    title: 'По регионам',
    description: 'Материалы по городам и областям.',
    link_label: 'Все регионы',
    url: '/regions.html',
  },
};

const EDITORIAL_REGION_BY_SLUG = Object.fromEntries(
  EDITORIAL_REGIONS.map((region) => [region.slug, region]),
);
const EDITORIAL_STATUS_BY_SLUG = Object.fromEntries(
  EDITORIAL_STATUSES.map((item) => [item.slug, item]),
);
const EDITORIAL_LABEL_BY_SLUG = Object.fromEntries(
  EDITORIAL_LABELS.map((item) => [item.slug, item]),
);

const EDITORIAL_REGION_ALIAS_TO_SLUG = EDITORIAL_REGIONS.reduce((acc, region) => {
  (region.aliases || []).forEach((alias) => {
    const key = normalizeSearchText(alias);
    if (key) acc[key] = region.slug;
  });
  return acc;
}, {});

function normalizeSearchText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('ru-RU');
}

function articleSlugOrId(article) {
  return String((article && (article.slug || article.id)) || '').trim();
}

function editorialStatus(article) {
  const slug = String(article && article.editorialStatus && article.editorialStatus.slug || '').trim();
  if (!slug) return null;
  const status = EDITORIAL_STATUS_BY_SLUG[slug];
  if (!status) return null;
  return {
    slug: status.slug,
    title: status.title,
    description: status.description,
    url: `/archive.html?status=${encodeURIComponent(status.slug)}`,
  };
}

function editorialStatusMeta(slug) {
  const item = EDITORIAL_STATUS_BY_SLUG[String(slug || '').trim()];
  if (!item) return null;
  return {
    slug: item.slug,
    title: item.title,
    description: item.description,
    url: `/archive.html?status=${encodeURIComponent(item.slug)}`,
  };
}

function editorialLabels(article) {
  const raw = Array.isArray(article && article.editorialLabels) ? article.editorialLabels : [];
  const seen = new Set();
  return raw
    .map((item) => {
      const slug = String(item && item.slug || '').trim();
      if (!slug || seen.has(slug)) return null;
      const label = EDITORIAL_LABEL_BY_SLUG[slug];
      if (!label) return null;
      seen.add(slug);
      return {
        slug: label.slug,
        title: label.title,
        description: label.description,
        url: `/archive.html?label=${encodeURIComponent(label.slug)}`,
      };
    })
    .filter(Boolean);
}

function editorialLabelMeta(slug) {
  const item = EDITORIAL_LABEL_BY_SLUG[String(slug || '').trim()];
  if (!item) return null;
  return {
    slug: item.slug,
    title: item.title,
    description: item.description,
    url: `/archive.html?label=${encodeURIComponent(item.slug)}`,
  };
}

function articleEditorialStatusSlug(article) {
  const status = editorialStatus(article);
  return status ? status.slug : '';
}

function articleEditorialLabelSlugs(article) {
  return editorialLabels(article).map((item) => item.slug);
}

function articleTextBlob(article) {
  if (!article || typeof article !== 'object') return '';
  const status = editorialStatus(article);
  const labels = editorialLabels(article);
  const parts = [
    article.title,
    article.dek,
    article.slug,
    article.category,
    article.categoryLabel,
    article.region,
    status && status.title,
    ...((article.tags || []).filter(Boolean)),
    ...(((article.topics || []).map((item) => item && item.title).filter(Boolean))),
    ...labels.map((item) => item.title),
  ];
  return normalizeSearchText(parts.join(' '));
}

function fallbackTopicScore(topic, text) {
  const strongHits = topic.strongTerms.filter((term) => text.includes(term)).length;
  const supportHits = topic.supportTerms.filter((term) => text.includes(term)).length;
  if (!strongHits && strongHits + supportHits < 2) return 0;
  return strongHits * 4 + supportHits;
}

function fallbackTopicsForArticle(article) {
  const text = articleTextBlob(article);
  if (!text) return [];
  return EDITORIAL_TOPICS
    .map((topic, index) => ({ topic, score: fallbackTopicScore(topic, text), index }))
    .filter((item) => item.score > 0)
    .sort((a, b) => (b.score - a.score) || (a.index - b.index))
    .slice(0, 3)
    .map(({ topic }) => ({
      slug: topic.slug,
      title: topic.title,
      description: topic.description,
      url: `/archive.html?topic=${encodeURIComponent(topic.slug)}`,
    }));
}

function fallbackSeriesForArticle(article) {
  const text = articleTextBlob(article);
  if (!text) return null;
  const found = EDITORIAL_SERIES.find((series) => series.matchTerms.some((term) => text.includes(term)));
  return found ? {
    slug: found.slug,
    title: found.title,
    description: found.description,
    url: `/archive.html?series=${encodeURIComponent(found.slug)}`,
  } : null;
}

function fallbackRegionForArticle(article) {
  const raw = normalizeSearchText(article && (article.region || article._meta_region));
  if (!raw) return null;
  const slug = EDITORIAL_REGION_ALIAS_TO_SLUG[raw];
  if (!slug) return null;
  const region = EDITORIAL_REGION_BY_SLUG[slug];
  if (!region) return null;
  return {
    slug: region.slug,
    title: region.title,
    description: region.description,
    url: `/archive.html?region=${encodeURIComponent(region.slug)}`,
  };
}

function isResonanceArticle(article) {
  if (article && typeof article.resonance === 'boolean') return article.resonance;
  return Number(article && article.importance) >= 4;
}

function ensureEditorialFields(article) {
  if (!article || typeof article !== 'object') return article;
  const status = editorialStatus(article);
  if (status) article.editorialStatus = status;
  const labels = editorialLabels(article);
  if (labels.length) article.editorialLabels = labels;
  if (!Array.isArray(article.topics) || !article.topics.length) {
    article.topics = fallbackTopicsForArticle(article);
  }
  if (!article.regionRef || typeof article.regionRef !== 'object') {
    const fallbackRegion = fallbackRegionForArticle(article);
    if (fallbackRegion) {
      article.regionRef = fallbackRegion;
      if (!String(article.region || '').trim()) article.region = fallbackRegion.title;
    }
  } else if (!String(article.region || '').trim() && article.regionRef.title) {
    article.region = article.regionRef.title;
  }
  if (!article.series || typeof article.series !== 'object') {
    const fallbackSeries = fallbackSeriesForArticle(article);
    if (fallbackSeries) article.series = fallbackSeries;
  }
  if (typeof article.resonance !== 'boolean') {
    article.resonance = isResonanceArticle(article);
  }
  return article;
}

function editorialCatalogFromArticles(articles) {
  const normalized = Array.isArray(articles) ? articles.map((article) => ensureEditorialFields(article)).filter(Boolean) : [];
  const topics = EDITORIAL_TOPICS
    .map((topic) => {
      const matches = normalized.filter((article) => (article.topics || []).some((item) => item.slug === topic.slug));
      if (!matches.length) return null;
      return {
        slug: topic.slug,
        title: topic.title,
        description: topic.description,
        count: matches.length,
        url: `/archive.html?topic=${encodeURIComponent(topic.slug)}`,
        latest: matches.slice(0, 3).map((article) => ({
          slug: articleSlugOrId(article),
          title: article.title,
          date: article.date,
          dateIso: article.dateIso,
          image: article.image,
          category: article.category,
          categoryLabel: article.categoryLabel,
        })),
      };
    })
    .filter(Boolean);

  const regions = EDITORIAL_REGIONS
    .map((region) => {
      const matches = normalized.filter((article) => articleRegionSlug(article) === region.slug);
      if (!matches.length) return null;
      return {
        slug: region.slug,
        title: region.title,
        description: region.description,
        count: matches.length,
        url: `/archive.html?region=${encodeURIComponent(region.slug)}`,
        latest: matches.slice(0, 3).map((article) => ({
          slug: articleSlugOrId(article),
          title: article.title,
          date: article.date,
          dateIso: article.dateIso,
          image: article.image,
          category: article.category,
          categoryLabel: article.categoryLabel,
        })),
      };
    })
    .filter(Boolean);

  const series = EDITORIAL_SERIES
    .map((item) => {
      const matches = normalized.filter((article) => article.series && article.series.slug === item.slug);
      if (!matches.length) return null;
      return {
        slug: item.slug,
        title: item.title,
        description: item.description,
        count: matches.length,
        url: `/archive.html?series=${encodeURIComponent(item.slug)}`,
        latest: matches.slice(0, 3).map((article) => ({
          slug: articleSlugOrId(article),
          title: article.title,
          date: article.date,
          dateIso: article.dateIso,
          image: article.image,
          category: article.category,
          categoryLabel: article.categoryLabel,
        })),
      };
    })
    .filter(Boolean);

  return {
    topics,
    regions,
    series,
    resonance: {
      ...RESONANCE_META,
      count: normalized.filter((article) => article.resonance).length,
    },
  };
}

function editorialCatalogValue(kind) {
  const dataset = (typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE)
    || (typeof FBRK_DATA !== 'undefined' && FBRK_DATA)
    || null;
  if (dataset && Array.isArray(dataset[kind]) && dataset[kind].length) {
    return dataset[kind];
  }
  const articles = (dataset && Array.isArray(dataset.articles)) ? dataset.articles : [];
  const derived = editorialCatalogFromArticles(articles);
  return kind === 'resonance' ? derived.resonance : derived[kind];
}

function editorialCatalogEntry(kind, slug) {
  const collection = editorialCatalogValue(kind);
  if (!Array.isArray(collection)) return null;
  return collection.find((item) => item && item.slug === slug) || null;
}

function editorialHubPageMeta(kind) {
  const defaults = EDITORIAL_HUB_PAGE_DEFAULTS[kind] || {
    eyebrow: '',
    title: '',
    description: '',
    seo_title: '',
    seo_description: '',
  };
  const archiveValue = (typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE && ARTICLES_ARCHIVE.editorialHubPages)
    ? ARTICLES_ARCHIVE.editorialHubPages[kind]
    : null;
  const dataValue = (typeof FBRK_DATA !== 'undefined' && FBRK_DATA && FBRK_DATA.editorialHubPages)
    ? FBRK_DATA.editorialHubPages[kind]
    : null;
  const value = archiveValue || dataValue;
  if (!value || typeof value !== 'object') return { ...defaults };
  return {
    eyebrow: value.eyebrow || defaults.eyebrow,
    title: value.title || defaults.title,
    description: value.description || defaults.description,
    seo_title: value.seo_title || defaults.seo_title,
    seo_description: value.seo_description || defaults.seo_description,
  };
}

function homepageBlockMeta(kind) {
  const defaults = HOMEPAGE_BLOCK_DEFAULTS[kind] || {
    eyebrow: '',
    title: '',
    description: '',
    link_label: '',
    url: '/',
  };
  const archiveValue = (typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE && ARTICLES_ARCHIVE.homepageBlocks)
    ? ARTICLES_ARCHIVE.homepageBlocks[kind]
    : null;
  const dataValue = (typeof FBRK_DATA !== 'undefined' && FBRK_DATA && FBRK_DATA.homepageBlocks)
    ? FBRK_DATA.homepageBlocks[kind]
    : null;
  const value = archiveValue || dataValue;
  if (!value || typeof value !== 'object') return { ...defaults };
  return {
    eyebrow: value.eyebrow || defaults.eyebrow,
    title: value.title || defaults.title,
    description: value.description || defaults.description,
    link_label: value.link_label || defaults.link_label,
    url: defaults.url,
  };
}

function archiveActiveFilters(state) {
  const items = [];
  if (state.cat) {
    items.push({ key: 'cat', label: state.cat === 'investigation' ? 'Расследования' : state.cat === 'news' ? 'Новости' : state.cat });
  }
  if (state.year) items.push({ key: 'year', label: state.year });
  if (state.month) items.push({ key: 'month', label: `Месяц: ${state.month}` });
  if (state.topic) {
    const meta = editorialCatalogEntry('topics', state.topic);
    items.push({ key: 'topic', label: meta ? meta.title : state.topic });
  }
  if (state.region) {
    const meta = editorialCatalogEntry('regions', state.region);
    items.push({ key: 'region', label: meta ? meta.title : state.region });
  }
  if (state.series) {
    const meta = editorialCatalogEntry('series', state.series);
    items.push({ key: 'series', label: meta ? meta.title : state.series });
  }
  if (state.status) {
    const meta = editorialStatusMeta(state.status);
    items.push({ key: 'status', label: meta ? meta.title : state.status });
  }
  if (state.label) {
    const meta = editorialLabelMeta(state.label);
    items.push({ key: 'label', label: meta ? meta.title : state.label });
  }
  if (state.resonance) items.push({ key: 'resonance', label: 'Резонанс' });
  if (state.q) items.push({ key: 'q', label: `Запрос: ${state.q}` });
  return items;
}

function searchableArticleText(article) {
  const current = ensureEditorialFields(article);
  return normalizeSearchText([
    current.title,
    current.dek,
    current.description,
    current.body,
    current.region,
    ((current.regionRef || {}).title || ''),
    ((current.series || {}).title || ''),
    ((current.editorialStatus || {}).title || ''),
    (current.tags || []).join(' '),
    (current.topics || []).map((item) => item.title).join(' '),
    (editorialLabels(current) || []).map((item) => item.title).join(' '),
    current.categoryLabel,
  ].join(' '));
}

function articleTopicSlugs(article) {
  return (ensureEditorialFields(article).topics || []).map((item) => item.slug).filter(Boolean);
}

function articleSeriesSlug(article) {
  const series = ensureEditorialFields(article).series;
  return series && series.slug ? series.slug : '';
}

function articleRegionSlug(article) {
  const current = ensureEditorialFields(article);
  const regionRef = current.regionRef && typeof current.regionRef === 'object' ? current.regionRef : null;
  if (regionRef && regionRef.slug) return String(regionRef.slug);
  const raw = normalizeSearchText(current.region || current._meta_region);
  return raw ? (EDITORIAL_REGION_ALIAS_TO_SLUG[raw] || '') : '';
}

function pickRelatedArticlesClient(target, articles, limit = 3) {
  const current = ensureEditorialFields(target);
  const currentSlug = articleSlugOrId(current);
  const currentTopics = new Set(articleTopicSlugs(current));
  const currentTags = new Set(((current.tags || []).map((tag) => normalizeSearchText(tag)).filter(Boolean)));
  const currentSeries = articleSeriesSlug(current);
  const currentRegion = articleRegionSlug(current);

  const scored = [];
  const fallback = [];
  (articles || []).forEach((article) => {
    const candidate = ensureEditorialFields(article);
    const slug = articleSlugOrId(candidate);
    if (!slug || slug === currentSlug) return;

    let score = 0;
    const candidateTopics = new Set(articleTopicSlugs(candidate));
    const candidateTags = new Set(((candidate.tags || []).map((tag) => normalizeSearchText(tag)).filter(Boolean)));
    if (currentSeries && articleSeriesSlug(candidate) === currentSeries) score += 10;
    if (currentTopics.size) {
      let overlap = 0;
      currentTopics.forEach((topicSlug) => { if (candidateTopics.has(topicSlug)) overlap += 1; });
      score += overlap * 4;
    }
    if (currentTags.size) {
      let overlap = 0;
      currentTags.forEach((tag) => { if (candidateTags.has(tag)) overlap += 1; });
      score += overlap * 2;
    }
    if (current.category && candidate.category === current.category) score += 1.5;
    if (currentRegion && articleRegionSlug(candidate) === currentRegion) score += 1;
    if (candidate.image) score += 0.25;

    if (score > 0) {
      scored.push({ score, dateIso: String(candidate.dateIso || ''), article: candidate });
    } else if (current.category && candidate.category === current.category) {
      fallback.push(candidate);
    }
  });

  scored.sort((a, b) => (b.score - a.score) || b.dateIso.localeCompare(a.dateIso));
  const picked = scored.slice(0, limit).map((item) => item.article);
  if (picked.length >= limit) return picked;

  const seen = new Set(picked.map((item) => articleSlugOrId(item)));
  fallback
    .sort((a, b) => String(b.dateIso || '').localeCompare(String(a.dateIso || '')))
    .forEach((article) => {
      if (picked.length >= limit) return;
      const slug = articleSlugOrId(article);
      if (!slug || seen.has(slug)) return;
      seen.add(slug);
      picked.push(article);
    });
  return picked.slice(0, limit);
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
            <div><div class="site-footer__heading">Разделы</div><ul class="site-footer__list" role="list"><li><a href="/">Главная</a></li><li><a href="/archive.html?cat=investigation">Расследования</a></li><li><a href="/archive.html?cat=news">Новости</a></li><li><a href="/archive.html">Архив</a></li><li><a href="/topics.html">Темы</a></li><li><a href="/regions.html">Регионы</a></li><li><a href="/series.html">Серии</a></li><li><a href="/resonance.html">Резонанс</a></li><li><a href="/feed.xml">RSS</a></li><li><a href="/sitemap.html">Карта сайта</a></li></ul></div>
            <div><div class="site-footer__heading">Редакция</div><ul class="site-footer__list" role="list"><li><a href="/about.html">О нас</a></li><li><a href="/contacts.html">Контакты</a></li><li><a href="/editorial-policy.html">Редакционная политика</a></li><li><a href="/privacy.html">Конфиденциальность</a></li></ul></div>
            <div><div class="site-footer__heading">Соцмедиа</div><ul class="site-footer__list" role="list"><li><a href="https://t.me/fund_anticorr" target="_blank" rel="noopener" data-footer-telegram>Telegram</a></li><li><a href="https://www.youtube.com/@fbrk_news" target="_blank" rel="noopener">YouTube</a></li><li><span class="site-footer__text">TikTok</span></li></ul></div>
          </div>
          <div class="site-footer__bottom"><div class="site-footer__legal"><span>© 2023–2026 ФБРК</span><span aria-hidden="true">·</span><span class="site-footer__version">AV DS 4</span><span aria-hidden="true">·</span><span>Астана, Казахстан</span></div></div>
        </div>
      </footer>
    `);
  }
})();

function currentSiteMeta() {
  const site = (window.FBRK_DATA && window.FBRK_DATA.site) || {};
  return site && typeof site === 'object' ? site : {};
}

function applySiteProfile() {
  const site = currentSiteMeta();
  if (!site || !Object.keys(site).length) return;

  const setText = (selector, value) => {
    if (!value) return;
    document.querySelectorAll(selector).forEach((node) => {
      if (node) node.textContent = value;
    });
  };

  const setHref = (selector, value) => {
    if (!value || value === '#') return;
    document.querySelectorAll(selector).forEach((node) => {
      if (node && typeof node.setAttribute === 'function') {
        node.setAttribute('href', value);
      }
    });
  };

  setText('.site-header__logo-text', site.fullName);
  setText('.site-footer__about', site.footerAbout);
  setText('.site-footer__legal span:last-child', site.city);

  setHref('.site-header__btn--social[aria-label="Telegram-бот"]', site.telegram);
  setHref('[data-footer-telegram]', site.telegramChannel || 'https://t.me/fund_anticorr');
  setHref('.site-header__mobile-socials a[aria-label="Telegram-бот"]', site.telegram);
  setHref('[data-site-telegram-cta]', site.telegram);

  setHref('.site-header__btn--social[aria-label="YouTube"]', site.youtube);
  setHref('.site-footer__list a[href="https://www.youtube.com/@fbrk_news"]', site.youtube);
  setHref('.site-header__mobile-socials a[aria-label="YouTube"]', site.youtube);
  setHref('[data-site-youtube-link]', site.youtube);

  if (site.telegramName) {
    setText('[data-site-telegram-cta]', `Открыть ${site.telegramName} →`);
  }
}

applySiteProfile();

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
  applySiteProfile();
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
        '<div class="search-empty">Ничего не найдено. Попробуйте другой запрос.</div>';
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
const IMAGE_FALLBACK_URL = '/img/og-default.jpg';

if (!window.__fbrkImageFallback) {
  window.__fbrkImageFallback = function fbrkImageFallback(imageEl) {
    if (!imageEl || imageEl.tagName !== 'IMG') return;
    if (imageEl.dataset.fbrkFallbackApplied === '1') return;
    imageEl.dataset.fbrkFallbackApplied = '1';
    const fallback = imageEl.getAttribute('data-fbrk-fallback') || IMAGE_FALLBACK_URL;
    imageEl.src = fallback;
    imageEl.removeAttribute('onerror');
  };
}

function fullCover(a) {
  const meta = imageMeta(a);
  const image = meta.url;
  // swap /covers/thumb/ -> /covers/web/ for larger rendering
  if (image && image.includes('/covers/thumb/')) {
    return image.replace('/covers/thumb/', '/covers/web/');
  }
  return image || IMAGE_FALLBACK_URL;
}

function ensureImageUrl(rawUrl) {
  const normalized = normalizeImageUrl(rawUrl);
  return normalized || IMAGE_FALLBACK_URL;
}

function articleImageHtml(src, options = {}) {
  const value = String(src || '').trim();
  const alt = escapeHtml(String(options.alt || '').trim() || 'Изображение');
  const loading = options.loading || 'lazy';
  const decoding = options.decoding || 'async';
  const fallback = String(options.fallback || IMAGE_FALLBACK_URL).trim() || IMAGE_FALLBACK_URL;
  const width = Number.isFinite(options.width) ? ` width="${parseInt(options.width, 10)}"` : '';
  const height = Number.isFinite(options.height) ? ` height="${parseInt(options.height, 10)}"` : '';
  const safeSrc = escapeHtml(ensureImageUrl(value));
  const safeFallback = escapeHtml(fallback);
  const safeLoading = escapeHtml(loading);
  const safeDecoding = escapeHtml(decoding);
  return `<img src="${safeSrc}" alt="${alt}"${width}${height} loading="${safeLoading}" decoding="${safeDecoding}" data-fbrk-fallback="${safeFallback}" onerror="window.__fbrkImageFallback(this)"/>`;
}

function normalizeImageUrl(rawUrl) {
  const url = String(rawUrl || '').trim();
  if (!url) return '';
  if (
    url.startsWith('/') ||
    url.startsWith('http://') ||
    url.startsWith('https://') ||
    url.startsWith('//') ||
    url.startsWith('data:')
  ) {
    return url;
  }
  if (url.startsWith('img/')) return `/${url}`;
  return url;
}

function imageMeta(a) {
  const image = a && a.image;
  const meta = image && typeof image === 'object' ? image : {};
  const rawUrl = typeof image === 'string' ? image : (meta.url || meta.src || '');
  const url = normalizeImageUrl(rawUrl);
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

function imageSourceLabel(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const normalized = raw.toLowerCase();
  if (['external', 'internal', 'upload', 'cover', 'inline'].includes(normalized)) {
    return '';
  }
  return raw;
}

function imageCaptionHtml(a) {
  const meta = imageMeta(a);
  if (meta.kind === 'ai' && meta.hasRealPerson) {
    return '<span class="image-caption image-caption--ai">ИИ-изображение. Не является фотоматериалом</span>';
  }
  const sourceLabel = imageSourceLabel(meta.source);
  if (meta.kind === 'photo' && sourceLabel) {
    return `<span class="image-caption">Фото: ${escapeHtml(sourceLabel)}</span>`;
  }
  return '';
}

function truncateText(text, maxLength) {
  const clean = String(text || '').trim();
  if (!clean) return '';
  if (clean.length <= maxLength) return clean;
  return `${clean.slice(0, maxLength).trim()}…`;
}

function isMetadataOnlyLead(text) {
  const clean = normalizedArticleText(text).replace(/\u00a0/g, ' ').trim();
  if (!clean) return true;
  if (clean.length > 220) return false;
  if (!/источник(?:и)?/i.test(clean)) return false;
  return (
    /^\(.+\)$/.test(clean) ||
    /^\d{1,2}\s+[а-яё]+\s+\d{4}\s*(?:г\.)?\s*[|·-]/i.test(clean) ||
    /^\d{1,2}\s+[а-яё]+\s+\d{4}\s*(?:г\.)?\s+источник/i.test(clean)
  );
}

function cardPreviewDek(a) {
  return truncateText(articleHeroDek(a, []), 220);
}

function cardImageHtml(a, width = 640, height = 360) {
  const url = imageMeta(a).url;
  if (!url) return '';
  return articleImageHtml(url, {
    alt: a && a.title,
    width,
    height,
    loading: 'lazy',
    decoding: 'async',
  });
}

const HEADING_ACRONYMS = new Set([
  'АПК', 'АЭС', 'АФМ', 'БАД', 'ВВП', 'ВИЧ', 'ВКО', 'ВОЗ', 'ГЭС', 'ДТП',
  'ЕНПФ', 'ЕС', 'ЖКХ', 'ИИ', 'КГД', 'КНБ', 'КТЖ', 'МВД', 'МЧС', 'НДС',
  'ООН', 'ПДД', 'РК', 'РФ', 'СМИ', 'США', 'ТЭЦ', 'ФБРК',
]);
const HEADING_PROPER_NOUNS = new Map([
  ['алматы', 'Алматы'],
  ['астана', 'Астана'],
  ['казахстан', 'Казахстан'],
  ['китай', 'Китай'],
  ['кыргызстан', 'Кыргызстан'],
  ['москва', 'Москва'],
  ['россия', 'Россия'],
  ['туркестан', 'Туркестан'],
  ['узбекистан', 'Узбекистан'],
  ['шымкент', 'Шымкент'],
]);

function headingContextMap(context) {
  const restore = new Map();
  const tokens = String(context || '').match(/[A-Za-zА-Яа-яЁё0-9-]+/g) || [];
  tokens.forEach((token) => {
    const lower = token.toLocaleLowerCase('ru');
    const upper = token.toUpperCase();
    if (HEADING_ACRONYMS.has(upper)) {
      restore.set(lower, upper);
      return;
    }
    if (token[0] && token[0] === token[0].toUpperCase()) {
      restore.set(lower, token);
    }
  });
  return restore;
}

function formatArticleSectionHeading(text, context = '') {
  const raw = String(text || '').trim();
  if (!raw) return '';
  const letters = raw.match(/[A-Za-zА-Яа-яЁё]/g) || [];
  if (letters.length < 4) return raw;
  const lowerCount = (raw.match(/[a-zа-яё]/g) || []).length;
  const upperCount = (raw.match(/[A-ZА-ЯЁ]/g) || []).length;
  if (lowerCount > 0 || upperCount / Math.max(letters.length, 1) < 0.72) return raw;

  const restore = headingContextMap(context);
  const normalized = raw.replace(/[A-Za-zА-Яа-яЁё0-9-]+/g, (token) => {
    const lower = token.toLocaleLowerCase('ru');
    const upper = token.toUpperCase();
    if (/\d/.test(token)) return upper;
    if (HEADING_ACRONYMS.has(upper)) return upper;
    if (restore.has(lower)) return restore.get(lower);
    if (HEADING_PROPER_NOUNS.has(lower)) return HEADING_PROPER_NOUNS.get(lower);
    return token.toLocaleLowerCase('ru');
  });

  return normalized.replace(/[A-Za-zА-Яа-яЁё]/, (char) => char.toUpperCase());
}

function editorialBadgeLinkHtml(item, kind = 'label') {
  if (!item) return '';
  const cls = kind === 'status'
    ? 'editorial-badge editorial-badge--status'
    : 'editorial-badge editorial-badge--label';
  return `<a class="${cls}" href="${escapeHtml(item.url || '#')}" title="${escapeHtml(item.description || item.title)}">${escapeHtml(item.title)}</a>`;
}

function cardEditorialBadgesHtml(article, { limitLabels = 2 } = {}) {
  const status = editorialStatus(article);
  const labels = editorialLabels(article).slice(0, Math.max(0, limitLabels));
  if (!status && !labels.length) return '';
  return `<div class="editorial-badges editorial-badges--card">
    ${status ? editorialBadgeLinkHtml(status, 'status') : ''}
    ${labels.map((item) => editorialBadgeLinkHtml(item)).join('')}
  </div>`;
}

function articleEditorialBadgesHtml(article) {
  const status = editorialStatus(article);
  const labels = editorialLabels(article);
  if (!status && !labels.length) return '';
  return `<div class="editorial-badges editorial-badges--article" aria-label="Редакционные метки">
    ${status ? editorialBadgeLinkHtml(status, 'status') : ''}
    ${labels.map((item) => editorialBadgeLinkHtml(item)).join('')}
  </div>`;
}

// Importance badge — shown only for AI-rated articles with importance >= 4 (out of 5)
function importanceBadgeHtml(a) {
  const imp = Number(a && a.importance);
  if (!imp || imp < 4) return '';
  const label = imp >= 5 ? 'Важно' : 'Резонанс';
  const cls = imp >= 5 ? 'importance-badge importance-badge--top' : 'importance-badge';
  return `<span class="${cls}" aria-label="${label}">${label}</span>`;
}

function homeFocusCards(all, shownIds, limit = 6) {
  const hidden = shownIds instanceof Set ? shownIds : new Set(shownIds || []);
  const investigations = all
    .filter((a) => a.category === 'investigation' && !hidden.has(a.id))
    .slice(0, limit);
  if (investigations.length) {
    return {
      mode: 'investigation',
      items: investigations,
    };
  }
  return {
    mode: 'latest',
    items: all.filter((a) => !hidden.has(a.id)).slice(0, limit),
  };
}

// ---------- Home page renderer ----------
(function () {
  const leadRoot = document.querySelector('[data-lead]');
  if (!leadRoot || typeof FBRK_DATA === 'undefined') return;
  const all = Array.isArray(FBRK_DATA.articles) ? FBRK_DATA.articles : [];
  if (!all.length) return;
  const featured = all.find((a) => a.featured) || all[0];
  if (!featured) return;
  const shownIds = new Set([featured.id]);

  function renderHomepageBlockCopy(kind) {
    const meta = homepageBlockMeta(kind);
    document.querySelectorAll(`[data-home-block-eyebrow="${kind}"]`).forEach((node) => {
      node.textContent = meta.eyebrow;
    });
    document.querySelectorAll(`[data-home-block-title="${kind}"]`).forEach((node) => {
      node.textContent = meta.title;
    });
    document.querySelectorAll(`[data-home-block-description="${kind}"]`).forEach((node) => {
      node.textContent = meta.description;
    });
    document.querySelectorAll(`[data-home-block-link="${kind}"]`).forEach((node) => {
      node.setAttribute('href', meta.url);
      node.textContent = `${meta.link_label} →`;
    });
    return meta;
  }

  function renderHomeStoryCard(a) {
    const hasImg = !!imageMeta(a).url;
    const cardCls = hasImg ? 'card' : 'card card--no-image';
    const mediaInner = hasImg ? cardImageHtml(a) : '';
    return `
      <article class="${cardCls}">
        <a href="${articleHref(a)}">
          <div class="card__media ${imageKindClass(a)}">
            ${mediaInner}
            <span class="card__date-badge">${fmtDateShort(a.dateIso) || a.date}</span>
            ${importanceBadgeHtml(a)}
          </div>
          <h3 class="card__title">${escapeHtml(a.title)}</h3>
        </a>
        ${cardEditorialBadgesHtml(a)}
      </article>
    `;
  }

  leadRoot.innerHTML = `
    <a class="lead__media ${imageKindClass(featured)}" href="${articleHref(featured)}" aria-label="${escapeHtml(featured.title)}">
      ${articleImageHtml(fullCover(featured), {alt: featured && featured.title, width: 1200, height: 800, loading: "eager"})}
    </a>
    <div class="lead__body">
      <h1 class="lead__title">
        <a href="${articleHref(featured)}">${escapeHtml(featured.title)}</a>
      </h1>
      <p class="lead__dek">${escapeHtml(articleHeroDek(featured, []))}</p>
      <div class="lead__meta">
        <span class="lead__meta-label">${escapeHtml(featured.categoryLabel || 'Материал')}</span>
        <span class="lead__meta__dot" aria-hidden="true"></span>
        <span>${fmtDateLong(featured.dateIso) || featured.date}</span>
      </div>
    </div>
  `;

  // Investigations grid — keep this block editorially honest:
  // only investigation-tagged materials should appear here.
  const invRoot = document.querySelector('[data-investigations]');
  if (invRoot) {
    const invSection = document.querySelector('#investigations');
    const focusTitle = document.querySelector('[data-home-focus-title]');
    const focusLink = document.querySelector('[data-home-focus-link]');
    const focus = homeFocusCards(all, shownIds, 6);
    if (focus.mode !== 'investigation') {
      if (focusTitle) focusTitle.textContent = 'Главное сейчас';
      if (focusLink) {
        focusLink.setAttribute('href', '/archive.html');
        focusLink.textContent = 'Весь архив →';
      }
      if (invSection) invSection.hidden = !focus.items.length;
      invRoot.innerHTML = focus.items.map((a) => renderHomeStoryCard(a)).join('');
      focus.items.forEach((a) => shownIds.add(a.id));
    } else {
      if (focusTitle) focusTitle.textContent = 'Расследования';
      if (focusLink) {
        focusLink.setAttribute('href', '/archive.html?cat=investigation');
        focusLink.textContent = 'Все расследования →';
      }
      if (invSection) invSection.hidden = false;
      invRoot.innerHTML = focus.items
        .map((a) => renderHomeStoryCard(a))
        .join('');
      focus.items.forEach((a) => shownIds.add(a.id));
    }
  }

  const resonanceSection = document.querySelector('[data-home-resonance-section]');
  const resonanceRoot = document.querySelector('[data-home-resonance]');
  if (resonanceSection && resonanceRoot) {
    renderHomepageBlockCopy('resonance');
    let resonanceItems = all
      .filter((a) => a.resonance && !shownIds.has(a.id))
      .slice(0, 3);
    if (resonanceItems.length < 3) {
      const usedIds = new Set([...shownIds, ...resonanceItems.map((item) => item.id)]);
      const extras = all
        .filter((a) => !usedIds.has(a.id))
        .slice(0, 3 - resonanceItems.length);
      resonanceItems = resonanceItems.concat(extras);
    }
    if (resonanceItems.length) {
      resonanceRoot.innerHTML = resonanceItems.map((a) => renderHomeStoryCard(a)).join('');
      resonanceItems.forEach((a) => shownIds.add(a.id));
      resonanceSection.hidden = false;
    } else {
      resonanceSection.hidden = true;
    }
  }

  // Latest list — excludes featured + investigation cards, paginated by "Ещё" button
  const latestRoot = document.querySelector('[data-latest]');
  if (latestRoot) {
    const pool = all.filter((a) => !shownIds.has(a.id));
    const PAGE = 12;
    let rendered = 0;
    const renderItem = (a) => {
      const hasImg = !!imageMeta(a).url;
      const thumbCls = hasImg ? 'latest__thumb' : 'latest__thumb latest__thumb--no-image';
      const thumbInner = hasImg
        ? articleImageHtml(imageMeta(a).url, {alt: a && a.title, width: 320, height: 180})
        : `<span class="latest__thumb-mark">ФБРК</span>`;
      return `
      <li class="latest__item">
        <a class="${thumbCls} ${imageKindClass(a)}" href="${articleHref(a)}" aria-label="${escapeHtml(a.title)}">
          ${thumbInner}
          ${importanceBadgeHtml(a)}
        </a>
        <div>
          <h3 class="latest__title">
            <a href="${articleHref(a)}">${escapeHtml(a.title)}</a>
          </h3>
          ${cardEditorialBadgesHtml(a, { limitLabels: 1 })}
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
  if (tagRoot) {
    const topics = editorialCatalogValue('topics');
    if (Array.isArray(topics) && topics.length) {
      tagRoot.innerHTML = topics
        .slice(0, 8)
        .map((topic) => `<a href="${topic.url || `/archive.html?topic=${encodeURIComponent(topic.slug)}`}">${escapeHtml(topic.title)}</a>`)
        .join('');
    } else if (FBRK_DATA.tags) {
      const seen = new Map();
      FBRK_DATA.tags.forEach((t) => {
        const k = String(t).trim().toLowerCase();
        if (k && !seen.has(k)) seen.set(k, String(t).trim());
      });
      const uniqueTags = Array.from(seen.values()).sort((a, b) => a.localeCompare(b, 'ru'));
      tagRoot.innerHTML = uniqueTags
        .map((t) => `<a href="/archive.html?q=${encodeURIComponent(t)}">${escapeHtml(t)}</a>`)
        .join('');
    }
  }

  const seriesRoot = document.querySelector('[data-series-links]');
  if (seriesRoot) {
    const seriesWidget = document.querySelector('[data-series-widget]');
    const seriesItems = editorialCatalogValue('series');
    if (Array.isArray(seriesItems) && seriesItems.length) {
      seriesRoot.innerHTML = seriesItems
        .slice(0, 5)
        .map((series) => `<li><a href="${series.url || `/archive.html?series=${encodeURIComponent(series.slug)}`}">${escapeHtml(series.title)}</a></li>`)
        .join('');
      if (seriesWidget) seriesWidget.hidden = false;
    } else if (seriesWidget) {
      seriesWidget.hidden = true;
    }
  }

  const regionsSection = document.querySelector('[data-home-regions-section]');
  const regionsRoot = document.querySelector('[data-home-regions]');
  if (regionsSection && regionsRoot) {
    renderHomepageBlockCopy('regions');
    const regionItems = editorialCatalogValue('regions');
    if (Array.isArray(regionItems) && regionItems.length) {
      regionsRoot.innerHTML = regionItems
        .slice(0, 4)
        .map((entry) => `
          <section class="content-card hub-card">
            <h2><a href="${entry.url || '#'}">${escapeHtml(entry.title)}</a></h2>
            <div class="hub-card__meta">Материалов: ${new Intl.NumberFormat('ru-KZ').format(entry.count || 0)}</div>
            ${Array.isArray(entry.latest) && entry.latest.length ? `
              <ul class="content-list hub-card__latest" role="list">
                ${entry.latest.slice(0, 3).map((article) => `<li><a href="${articleUrl(article.slug || article.id || '')}">${escapeHtml(article.title)}</a></li>`).join('')}
              </ul>
            ` : ''}
          </section>
        `)
        .join('');
      regionsSection.hidden = false;
    } else {
      regionsSection.hidden = true;
    }
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
          ${articleImageHtml(v.thumb, {
            alt: v && v.title,
            width: 480,
            height: 270,
            loading: 'lazy',
            decoding: 'async',
            fallback: (v && v.thumb_fallback) || `https://i.ytimg.com/vi/${v.id}/hqdefault.jpg`,
          })}
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
      if (!videos.length) { root.closest('.section').style.display = 'none'; return; }
      render(videos);
    })
    .catch(() => { root.closest('.section').style.display = 'none'; });
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
  const heroDek = articleHeroDek(a, sectionItems);
  const bodySections = trimRepeatedLeadFromSections(sectionItems.length ? sectionItems : fallbackParagraphs, heroDek);
  const articleDateLabel = articleDateLabelFromData(a);

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
  const postbarHtml = `<div class="article__postbar">
    <p class="article__back"><a href="/">← Все материалы</a></p>
    ${shareHtml}
  </div>`;
  const rawTags = articleTags(a);
  const visibleEntities = articleEntities(a.entities, rawTags);
  const tldrHtml = renderArticleTldr(a);
  const entitiesHtml = renderArticleEntities(visibleEntities);
  const tagsHtml = renderArticleTags(articleTags(a, visibleEntities.map((e) => e.name)));
  const sourceUrl = safeArticleUrl(a.source || '');
  const sourceHost = sourceUrl ? safeSourceHost(a.source || '') : '';
  const relatedPool = fullArticles.length
    ? fullArticles
    : (archive.length ? archive : primary);
  const relatedItems = pickRelatedArticlesClient(a, relatedPool, 3);
  const relatedHtml = relatedItems.length ? `
      <section class="related">
        <h2 class="related__title">Читайте также</h2>
        <div class="card-grid">
          ${relatedItems.map((item) => {
            const hasImg = !!imageMeta(item).url;
            const cardCls = hasImg ? 'card' : 'card card--no-image';
            const mediaInner = hasImg ? cardImageHtml(item) : '';
            return `
            <article class="${cardCls}">
              <a href="${articleHref(item)}">
                <div class="card__media ${imageKindClass(item)}">
                  ${mediaInner}
                  <span class="card__date-badge">${fmtDateShort(item.dateIso) || item.date}</span>
                  ${importanceBadgeHtml(item)}
                </div>
                <h3 class="card__title">${escapeHtml(item.title)}</h3>
              </a>
              ${cardEditorialBadgesHtml(item, { limitLabels: 1 })}
            </article>`;
          }).join('')}
        </div>
      </section>
  ` : '';
  const editorialHtml = articleEditorialBadgesHtml(a);

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
        ${editorialHtml}
      </header>
      <div class="article__cover ${imageKindClass(a)}">
        ${articleImageHtml(fullCover(a), {alt: a && a.title, width: 1440, height: 810, loading: "eager"})}
        ${imageCaptionHtml(a)}
      </div>
      <div class="article__body">
        ${bodySections.map((s) => {
          const h = String((s && s.h) || '').trim();
          const p = String((s && s.p) || '').trim();
          const headingText = formatArticleSectionHeading(h, a.title);
          const hHtml = headingText ? `<h2>${escapeHtml(headingText)}</h2>` : '';
          const pHtml = p ? renderArticleParagraphs(p) : '';
          return hHtml + pHtml;
        }).join('')}
      </div>
      ${tldrHtml}
      ${entitiesHtml}
      ${tagsHtml}
      ${sourceUrl && !String(a.source || '').includes('fbrk.kz') ? `<div class="article__source">Источник: <a href="${sourceUrl}" target="_blank" rel="noopener">${sourceHost}</a></div>` : ''}
      ${postbarHtml}

      <div class="ad-block ad-block--article" data-ad-slot="article-bottom"></div>
      ${relatedHtml}
      <div class="ad-block ad-block--footer" data-ad-slot="article-footer"></div>
    </article>
  `;
})();

// ---------- util ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function articleDateLabelFromData(a) {
  const raw = String(((a && (a.dateIso || a.date)) || '')).trim();
  if (!raw) return '';
  const short = fmtDateLong(raw.slice(0, 10));
  if (short) return short;
  const match = raw.match(/^(\d{1,2})\s+([А-Яа-яёЁ]+)\s+\d{4}$/);
  if (match) {
    const day = parseInt(match[1], 10);
    const month = match[2];
    return Number.isNaN(day) ? raw : `${day} ${month}`;
  }
  return raw;
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

function safeSourceHost(rawSource) {
  const source = String(rawSource || '').trim();
  if (!source) return '';
  try {
    const url = new URL(source, location.origin);
    return escapeHtml(url.hostname.replace(/^www\./i, ''));
  } catch (_) {
    return escapeHtml(source);
  }
}

function sanitizeArticleInlineHtml(raw) {
  const template = document.createElement('template');
  const source = String(raw || '');
  template.innerHTML = source;
  const allowedTextTags = new Set(['b', 'strong', 'i', 'em', 'u', 's', 'sub', 'sup', 'code']);
  const allowedBlockTags = new Set(['p', 'blockquote', 'ul', 'ol', 'li']);

  function clean(node) {
    if (node.nodeType === Node.TEXT_NODE) return escapeHtml(node.textContent || '');
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    const tag = node.tagName.toLowerCase();
    const children = Array.from(node.childNodes).map(clean).join('');
    if (allowedTextTags.has(tag)) return `<${tag}>${children}</${tag}>`;
    if (allowedBlockTags.has(tag)) return `<${tag}>${children}</${tag}>`;
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
      return articleImageHtml(src, { alt: node.getAttribute('alt') || '', loading: 'lazy', decoding: 'async' });
    }
    return children;
  }

  const nodes = template.content && template.content.childNodes ? Array.from(template.content.childNodes) : [];
  if (!nodes.length && /<[^>]+>/.test(source)) {
    return source;
  }
  return nodes.map(clean).join('');
}

const BLOCK_HTML_TAG_RE = /<(?:p|div|ul|ol|li|blockquote|pre|figure|table|iframe|video|audio|h[1-6]|hr)\b/i;
const BLOCK_HTML_FRAGMENT_RE = /(<(?<tag>p|div|ul|ol|li|blockquote|pre|figure|table|iframe|video|audio|h[1-6])\b[^>]*>[\s\S]*?<\/\k<tag>>|<hr\b[^>]*>)/gi;

function renderArticleTextFragments(raw) {
  return String(raw || '')
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => `<p>${part.replace(/\n/g, '<br>')}</p>`);
}

function renderArticleParagraphs(raw) {
  const normalized = String(raw || '').replace(/\r\n/g, '\n').trim();
  if (!normalized) return '';
  const sanitized = sanitizeArticleInlineHtml(normalized);
  if (!BLOCK_HTML_TAG_RE.test(sanitized)) {
    return renderArticleTextFragments(sanitized).join('');
  }

  const parts = [];
  let cursor = 0;
  BLOCK_HTML_FRAGMENT_RE.lastIndex = 0;
  for (const match of sanitized.matchAll(BLOCK_HTML_FRAGMENT_RE)) {
    const index = typeof match.index === 'number' ? match.index : 0;
    if (index > cursor) {
      parts.push(...renderArticleTextFragments(sanitized.slice(cursor, index)));
    }
    parts.push(match[0].trim());
    cursor = index + match[0].length;
  }
  if (cursor < sanitized.length) {
    parts.push(...renderArticleTextFragments(sanitized.slice(cursor)));
  }
  return parts.join('');
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

  if (!normalizedSections.length) {
    const compactCandidates = [summaryShort, firstParagraph, dek];
    for (const candidate of compactCandidates) {
      const text = String(candidate || '').trim();
      if (!text || isMetadataOnlyLead(text)) continue;
      return truncateText(text, 420);
    }
    return '';
  }

  const firstSectionText = normalizedArticleText(`${normalizedSections[0]?.h || ''} ${normalizedSections[0]?.p || ''}`);
  const candidates = [
    dek,
    firstParagraph,
    summaryShort,
  ];

  for (const candidate of candidates) {
    const text = String(candidate || '').trim();
    if (!text || text.length > 420) continue;
    if (/\n\s*\n/.test(text)) continue;
    if (isMetadataOnlyLead(text)) continue;
    const normalizedDek = normalizedArticleText(text);
    if (normalizedDek && firstSectionText.startsWith(normalizedDek)) continue;
    return text;
  }

  return '';
}

function trimRepeatedLeadFromSections(sections, heroDek) {
  const items = Array.isArray(sections) ? sections.slice() : [];
  const normalizedLead = normalizedArticleText(heroDek);
  if (!items.length || !normalizedLead) return items;

  const first = items[0] || {};
  const heading = String(first.h || '').trim();
  const paragraph = String(first.p || '').trim();
  if (!paragraph) return items;

  const normalizedParagraph = normalizedArticleText(paragraph);
  const lengthDelta = Math.abs(normalizedParagraph.length - normalizedLead.length);
  const looksRepeatedLead = normalizedParagraph
    && (normalizedParagraph === normalizedLead
      || normalizedParagraph.startsWith(normalizedLead)
      || normalizedLead.startsWith(normalizedParagraph))
    && lengthDelta <= Math.max(48, Math.round(normalizedLead.length * 0.2));

  if (!looksRepeatedLead) return items;
  if (items.length < 2) {
    return heading ? [{ ...first, p: '' }].filter((section) => String(section?.h || '').trim()) : [];
  }
  if (heading) {
    return [{ ...first, p: '' }, ...items.slice(1)].filter((section) => {
      return String(section?.h || '').trim() || String(section?.p || '').trim();
    });
  }
  return items.slice(1);
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
  const points = articleTldrPoints(a);
  if (!points.length) return '';
  return `
    <aside class="article__tldr" aria-label="Кратко">
      ${points.length ? `<ul class="article__tldr-list">${points.map((p) => `<li>${escapeHtml(p)}</li>`).join('')}</ul>` : ''}
    </aside>
  `;
}

function articleTldrPoints(a) {
  const keyPoints = Array.isArray(a && a.keyPoints)
    ? a.keyPoints.map(tidyKeyPoint).filter(Boolean).slice(0, 5)
    : [];
  if (keyPoints.length && !looksLikeTruncatedKeyPoints(keyPoints)) {
    return keyPoints;
  }
  return articleTldrFallbackPoints(a).slice(0, 5);
}

function tidyKeyPoint(value) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  if (/[.!?…)"»]$/.test(text)) return text;

  const danglingWords = new Set(['а', 'в', 'во', 'для', 'до', 'и', 'из', 'к', 'ко', 'на', 'не', 'о', 'об', 'от', 'по', 'при', 'с', 'со', 'у']);
  const words = text.split(' ');
  const lastWord = words[words.length - 1].toLowerCase().replace(/[^\p{L}\p{N}-]+/gu, '');
  if (words.length > 1 && danglingWords.has(lastWord)) {
    return words.slice(0, -1).join(' ').replace(/[,:;\s]+$/, '');
  }

  return text;
}

function looksLikeTruncatedKeyPoints(points) {
  if (!Array.isArray(points) || !points.length) return false;
  let suspicious = 0;
  points.forEach((point) => {
    const text = String(point || '').trim();
    if (!text || /[.!?…)"»]$/.test(text)) return;
    const words = text.split(/\s+/);
    const lastWord = words[words.length - 1].replace(/[^\p{L}\p{N}-]+/gu, '');
    if (text.length >= 36 && lastWord && lastWord.length <= 6) suspicious += 1;
  });
  return suspicious >= 2;
}

function articleTldrFallbackPoints(a) {
  const sectionItems = Array.isArray(a && a.sections) ? a.sections : [];
  const seen = new Set();
  const points = [];

  sectionItems.forEach((section) => {
    String((section && section.p) || '')
      .replace(/\r\n/g, '\n')
      .split(/\n{2,}/)
      .map(normalizedArticleText)
      .forEach((part) => {
        if (!part || part.length < 48 || points.length >= 5) return;
        const sentence = firstArticleSentence(part);
        const key = sentence.toLocaleLowerCase('ru-RU');
        if (!sentence || seen.has(key)) return;
        seen.add(key);
        points.push(sentence);
      });
  });

  return points;
}

function firstArticleSentence(text) {
  const value = String(text || '').replace(/\s+/g, ' ').trim();
  if (!value) return '';
  const match = value.match(/^(.{24,220}?[.!?])(?:\s|$)/);
  return (match ? match[1] : truncateText(value, 220)).trim();
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-copy]');
  if (!btn) return;
  e.preventDefault();
  navigator.clipboard?.writeText(location.href).then(() => {
    const prev = btn.innerHTML;
    btn.innerHTML = '<span class="article__copy-label">Скопировано</span>';
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

  const pageRoot = document.querySelector('[data-archive-page]') || grid.closest('.archive') || document.body;
  const catSel = document.querySelector('[data-archive-cat]');
  const yearSel = document.querySelector('[data-archive-year]');
  const monthSel = document.querySelector('[data-archive-month]');
  const topicSel = document.querySelector('[data-archive-topic]');
  const regionSel = document.querySelector('[data-archive-region]');
  const seriesSel = document.querySelector('[data-archive-series]');
  const statusSel = document.querySelector('[data-archive-status]');
  const labelSel = document.querySelector('[data-archive-label]');
  const qInput = document.querySelector('[data-archive-q]');
  const moreBtn = document.querySelector('[data-archive-more]');
  const emptyEl = document.querySelector('[data-archive-empty]');
  const resetButtons = Array.from(document.querySelectorAll('[data-archive-reset]'));
  const countEl = document.querySelector('[data-archive-count]');
  const kickerEl = document.querySelector('[data-archive-kicker]');
  const titleEl = document.querySelector('[data-archive-title]');
  const descriptionEl = document.querySelector('[data-archive-description]');
  const headEl = document.querySelector('.archive__head');
  const activeEl = document.querySelector('[data-archive-active]');
  const activeListEl = document.querySelector('[data-archive-active-list]');
  const emptyMessageEl = document.querySelector('[data-archive-empty-message]');
  const filtersEl = document.querySelector('.archive__filters');
  const advancedToggleBtn = document.querySelector('[data-archive-advanced-toggle]');

  const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  const PAGE = 24;
  const preset = String(pageRoot.getAttribute('data-archive-preset') || '').trim();
  const presetResonance = preset === 'resonance';
  const catalogTopics = editorialCatalogValue('topics');
  const catalogRegions = editorialCatalogValue('regions');
  const catalogSeries = editorialCatalogValue('series');
  const all = ((typeof ARTICLES_ARCHIVE !== 'undefined' && ARTICLES_ARCHIVE.articles)
    ? ARTICLES_ARCHIVE.articles.slice()
    : FBRK_DATA.articles.slice()).map((article) => ensureEditorialFields(article));

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
  if (topicSel && Array.isArray(catalogTopics)) {
    catalogTopics.forEach((topic) => {
      const o = document.createElement('option');
      o.value = topic.slug;
      o.textContent = `${topic.title} (${new Intl.NumberFormat('ru-KZ').format(topic.count || 0)})`;
      topicSel.appendChild(o);
    });
  }
  if (regionSel && Array.isArray(catalogRegions)) {
    catalogRegions.forEach((region) => {
      const o = document.createElement('option');
      o.value = region.slug;
      o.textContent = `${region.title} (${new Intl.NumberFormat('ru-KZ').format(region.count || 0)})`;
      regionSel.appendChild(o);
    });
  }
  if (seriesSel && Array.isArray(catalogSeries)) {
    catalogSeries.forEach((series) => {
      const o = document.createElement('option');
      o.value = series.slug;
      o.textContent = `${series.title} (${new Intl.NumberFormat('ru-KZ').format(series.count || 0)})`;
      seriesSel.appendChild(o);
    });
  }
  if (statusSel) {
    EDITORIAL_STATUSES.forEach((status) => {
      const count = all.filter((article) => articleEditorialStatusSlug(article) === status.slug).length;
      if (!count) return;
      const o = document.createElement('option');
      o.value = status.slug;
      o.textContent = `${status.title} (${new Intl.NumberFormat('ru-KZ').format(count)})`;
      statusSel.appendChild(o);
    });
  }
  if (labelSel) {
    EDITORIAL_LABELS.forEach((label) => {
      const count = all.filter((article) => articleEditorialLabelSlugs(article).includes(label.slug)).length;
      if (!count) return;
      const o = document.createElement('option');
      o.value = label.slug;
      o.textContent = `${label.title} (${new Intl.NumberFormat('ru-KZ').format(count)})`;
      labelSel.appendChild(o);
    });
  }

  // URL state
  const params = new URLSearchParams(location.search);
  if (catSel && params.get('cat')) catSel.value = params.get('cat');
  if (yearSel && params.get('year')) yearSel.value = params.get('year');
  if (monthSel && params.get('month')) monthSel.value = params.get('month');
  if (topicSel && params.get('topic')) topicSel.value = params.get('topic');
  if (regionSel && params.get('region')) regionSel.value = params.get('region');
  if (seriesSel && params.get('series')) seriesSel.value = params.get('series');
  if (statusSel && params.get('status')) statusSel.value = params.get('status');
  if (labelSel && params.get('label')) labelSel.value = params.get('label');
  if (qInput && params.get('q')) qInput.value = params.get('q');
  let queryResonance = params.get('resonance') === '1';

  function archiveState() {
    return {
      cat: catSel ? catSel.value : '',
      year: yearSel ? yearSel.value : '',
      month: monthSel ? monthSel.value : '',
      topic: topicSel ? topicSel.value : '',
      region: regionSel ? regionSel.value : '',
      series: seriesSel ? seriesSel.value : '',
      status: statusSel ? statusSel.value : '',
      label: labelSel ? labelSel.value : '',
      q: qInput ? qInput.value.trim() : '',
      resonance: presetResonance || queryResonance,
    };
  }

  function renderArchiveActiveFilters(state) {
    const items = archiveActiveFilters(state).map((item) => {
      if (item.key === 'month') {
        const monthIndex = Number(String(state.month || '0')) - 1;
        if (monthIndex >= 0 && monthIndex < MONTHS.length) {
          return { ...item, label: `Месяц: ${MONTHS[monthIndex]}` };
        }
      }
      return item;
    });
    if (activeEl) activeEl.hidden = !items.length;
    if (activeListEl) {
      activeListEl.innerHTML = items.map((item) => `<span class="archive__chip">${escapeHtml(item.label)}</span>`).join('');
    }
    resetButtons.forEach((button) => {
      button.disabled = !items.length;
      button.hidden = button.classList.contains('archive__reset--ghost') ? !items.length : false;
    });
    return items;
  }

  function archiveHasAdvancedFilters(state) {
    return Boolean(state.topic || state.region || state.series || state.status || state.label);
  }

  function syncArchiveAdvancedFilters(state) {
    if (!filtersEl || !advancedToggleBtn) return;
    const expanded = archiveHasAdvancedFilters(state) || filtersEl.classList.contains('is-expanded');
    filtersEl.classList.toggle('is-expanded', expanded);
    advancedToggleBtn.setAttribute('aria-expanded', String(expanded));
    advancedToggleBtn.textContent = expanded ? 'Скрыть доп. фильтры' : 'Ещё фильтры';
  }

  function setArchiveSeo(title, description, state) {
    document.title = `${title} — ФБРК`;
    const descEl = document.querySelector('meta[name="description"]');
    if (descEl) descEl.setAttribute('content', description);
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) ogTitle.setAttribute('content', `${title} — ФБРК`);
    const ogDesc = document.querySelector('meta[property="og:description"]');
    if (ogDesc) ogDesc.setAttribute('content', description);
    const ogUrl = document.querySelector('meta[property="og:url"]');
    const canonical = document.querySelector('link[rel="canonical"]');
    const next = new URLSearchParams();
    if (state.cat) next.set('cat', state.cat);
    if (state.year) next.set('year', state.year);
    if (state.month) next.set('month', state.month);
    if (state.topic) next.set('topic', state.topic);
    if (state.region) next.set('region', state.region);
    if (state.series) next.set('series', state.series);
    if (state.status) next.set('status', state.status);
    if (state.label) next.set('label', state.label);
    if (state.q) next.set('q', state.q);
    if (state.resonance && !presetResonance) next.set('resonance', '1');
    const qs = next.toString();
    const href = `${siteOrigin()}${location.pathname}${qs ? `?${qs}` : ''}`;
    if (canonical) canonical.setAttribute('href', href);
    if (ogUrl) ogUrl.setAttribute('content', href);
  }

  // Update page title based on filter
  function updateHeader(state) {
    const topicMeta = state.topic ? editorialCatalogEntry('topics', state.topic) : null;
    const regionMeta = state.region ? editorialCatalogEntry('regions', state.region) : null;
    const seriesMeta = state.series ? editorialCatalogEntry('series', state.series) : null;
    const statusMeta = state.status ? editorialStatusMeta(state.status) : null;
    const labelMeta = state.label ? editorialLabelMeta(state.label) : null;
    const resonancePage = editorialHubPageMeta('resonance');
    if (!titleEl) return;
    const categoryView = !topicMeta && !regionMeta && !seriesMeta && !statusMeta && !labelMeta && !state.resonance && (state.cat === 'investigation' || state.cat === 'news');
    if (headEl) headEl.classList.toggle('archive__head--compact', categoryView);
    if (kickerEl) kickerEl.hidden = categoryView;
    if (seriesMeta) {
      titleEl.textContent = seriesMeta.title;
      if (kickerEl) {
        kickerEl.hidden = false;
        kickerEl.textContent = 'Серия';
      }
      if (descriptionEl) descriptionEl.textContent = seriesMeta.description;
      setArchiveSeo(seriesMeta.title, seriesMeta.description, state);
    }
    else if (topicMeta) {
      titleEl.textContent = topicMeta.title;
      if (kickerEl) {
        kickerEl.hidden = false;
        kickerEl.textContent = 'Тема';
      }
      if (descriptionEl) descriptionEl.textContent = topicMeta.description;
      setArchiveSeo(topicMeta.title, topicMeta.description, state);
    }
    else if (regionMeta) {
      titleEl.textContent = regionMeta.title;
      if (kickerEl) {
        kickerEl.hidden = false;
        kickerEl.textContent = 'Регион';
      }
      if (descriptionEl) descriptionEl.textContent = regionMeta.description;
      setArchiveSeo(regionMeta.title, regionMeta.description, state);
    }
    else if (statusMeta) {
      titleEl.textContent = statusMeta.title;
      if (kickerEl) {
        kickerEl.hidden = false;
        kickerEl.textContent = 'Статус';
      }
      if (descriptionEl) descriptionEl.textContent = statusMeta.description;
      setArchiveSeo(statusMeta.title, statusMeta.description, state);
    }
    else if (labelMeta) {
      titleEl.textContent = labelMeta.title;
      if (kickerEl) {
        kickerEl.hidden = false;
        kickerEl.textContent = 'Метка';
      }
      if (descriptionEl) descriptionEl.textContent = labelMeta.description;
      setArchiveSeo(labelMeta.title, labelMeta.description, state);
    }
    else if (state.resonance) {
      titleEl.textContent = resonancePage.title;
      if (kickerEl) {
        kickerEl.hidden = false;
        kickerEl.textContent = resonancePage.eyebrow;
      }
      if (descriptionEl) descriptionEl.textContent = resonancePage.description;
      setArchiveSeo(resonancePage.seo_title || resonancePage.title, resonancePage.seo_description || resonancePage.description, state);
    }
    else if (state.cat === 'investigation') {
      titleEl.textContent = 'Расследования';
      if (kickerEl) kickerEl.textContent = 'Архив';
      if (descriptionEl) descriptionEl.textContent = 'Большие расследования ФБРК о коррупции, активах, земле и влиятельных связях.';
      setArchiveSeo('Расследования', 'Большие расследования ФБРК о коррупции, активах, земле и влиятельных связях.', state);
    }
    else if (state.cat === 'news') {
      titleEl.textContent = 'Новости';
      if (kickerEl) kickerEl.textContent = 'Архив';
      if (descriptionEl) descriptionEl.textContent = 'Оперативные материалы ФБРК о чиновниках, судах, силовиках и публичных деньгах.';
      setArchiveSeo('Новости', 'Оперативные материалы ФБРК о чиновниках, судах, силовиках и публичных деньгах.', state);
    }
    else {
      titleEl.textContent = 'Архив материалов';
      if (kickerEl) {
        kickerEl.hidden = false;
        kickerEl.textContent = 'Архив';
      }
      if (descriptionEl) descriptionEl.textContent = 'Полный архив публикаций ФБРК с фильтрами по рубрике, году, месяцу, теме, региону и серии.';
      setArchiveSeo('Архив материалов', 'Полный архив публикаций ФБРК с фильтрами по рубрике, году, месяцу, теме, региону и серии.', state);
    }
  }

  let rendered = 0;
  let filtered = [];

  function filter() {
    const state = archiveState();
    const q = state.q.toLowerCase();
    syncArchiveAdvancedFilters(state);
    updateHeader(state);
    const activeFilters = renderArchiveActiveFilters(state);
    filtered = all.filter((a) => {
      if (state.cat && a.category !== state.cat) return false;
      const iso = a.dateIso || '';
      if (state.year && iso.slice(0, 4) !== state.year) return false;
      if (state.month && iso.slice(5, 7) !== state.month) return false;
      if (state.topic && !articleTopicSlugs(a).includes(state.topic)) return false;
      if (state.region && articleRegionSlug(a) !== state.region) return false;
      if (state.series && articleSeriesSlug(a) !== state.series) return false;
      if (state.status && articleEditorialStatusSlug(a) !== state.status) return false;
      if (state.label && !articleEditorialLabelSlugs(a).includes(state.label)) return false;
      if (state.resonance && !isResonanceArticle(a)) return false;
      if (q) {
        const hay = normalizeSearchText([
          a.title,
          a.dek,
          a.region,
          ((a.regionRef || {}).title || ''),
          (a.tags || []).join(' '),
          (a.topics || []).map((item) => item.title).join(' '),
          ((a.series || {}).title || ''),
          ((a.editorialStatus || {}).title || ''),
          (editorialLabels(a) || []).map((item) => item.title).join(' '),
        ].join(' '));
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    rendered = 0;
    grid.innerHTML = '';
    if (countEl) {
      const formattedFiltered = new Intl.NumberFormat('ru-KZ').format(filtered.length);
      const formattedTotal = new Intl.NumberFormat('ru-KZ').format(all.length);
      countEl.textContent = activeFilters.length
        ? `Показано материалов: ${formattedFiltered} из ${formattedTotal}`
        : `Материалов в архиве: ${formattedTotal}`;
    }
    if (!filtered.length) {
      if (emptyEl) emptyEl.hidden = false;
      if (emptyMessageEl) {
        emptyMessageEl.textContent = state.q
          ? `По запросу «${state.q}» и выбранным фильтрам ничего не найдено.`
          : activeFilters.length
            ? 'По выбранным параметрам ничего не найдено.'
            : 'Пока нечего показать.';
      }
      if (moreBtn) moreBtn.style.display = 'none';
      return;
    }
    if (emptyEl) emptyEl.hidden = true;
    renderMore();
    // sync URL
    const next = new URLSearchParams();
    if (state.cat) next.set('cat', state.cat);
    if (state.year) next.set('year', state.year);
    if (state.month) next.set('month', state.month);
    if (state.topic) next.set('topic', state.topic);
    if (state.region) next.set('region', state.region);
    if (state.series) next.set('series', state.series);
    if (state.status) next.set('status', state.status);
    if (state.label) next.set('label', state.label);
    if (state.q) next.set('q', state.q);
    if (state.resonance && !presetResonance) next.set('resonance', '1');
    queryResonance = state.resonance && !presetResonance;
    const qs = next.toString();
    history.replaceState(null, '', qs ? `${location.pathname}?${qs}` : location.pathname);
  }

  function itemHtml(a) {
    const hasImg = !!imageMeta(a).url;
    const cardCls = hasImg ? 'card' : 'card card--no-image';
    const mediaInner = hasImg ? cardImageHtml(a) : '';
    const previewDek = cardPreviewDek(a);
    return `
      <article class="${cardCls}">
        <a href="${articleHref(a)}">
          <div class="card__media ${imageKindClass(a)}">
            ${mediaInner}
            <span class="card__date-badge">${fmtDateShort(a.dateIso) || a.date}</span>
            ${importanceBadgeHtml(a)}
          </div>
          <h2 class="card__title">${escapeHtml(a.title)}</h2>
        </a>
        ${cardEditorialBadgesHtml(a)}
        ${previewDek ? `<p class="card__dek">${escapeHtml(previewDek)}</p>` : ''}
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

  [catSel, yearSel, monthSel, topicSel, regionSel, seriesSel, statusSel, labelSel].forEach((el) => el && el.addEventListener('change', filter));
  if (advancedToggleBtn && filtersEl) {
    advancedToggleBtn.addEventListener('click', () => {
      const nextExpanded = !filtersEl.classList.contains('is-expanded');
      filtersEl.classList.toggle('is-expanded', nextExpanded);
      advancedToggleBtn.setAttribute('aria-expanded', String(nextExpanded));
      advancedToggleBtn.textContent = nextExpanded ? 'Скрыть доп. фильтры' : 'Ещё фильтры';
    });
  }
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
  resetButtons.forEach((button) => button.addEventListener('click', () => {
    if (catSel) catSel.value = '';
    if (yearSel) yearSel.value = '';
    if (monthSel) monthSel.value = '';
    if (topicSel) topicSel.value = '';
    if (regionSel) regionSel.value = '';
    if (seriesSel) seriesSel.value = '';
    if (statusSel) statusSel.value = '';
    if (labelSel) labelSel.value = '';
    if (qInput) qInput.value = '';
    if (!presetResonance) queryResonance = false;
    filter();
  }));

  filter();
})();

// ---------- Topics / regions / series directory pages ----------
(function () {
  const root = document.querySelector('[data-hub-directory]');
  if (!root) return;

  const kind = root.getAttribute('data-hub-directory');
  const grid = root.querySelector('[data-hub-grid]');
  const count = root.querySelector('[data-hub-count]');
  const eyebrow = root.querySelector('.content-page__eyebrow');
  const title = root.querySelector('.content-page__title');
  const description = root.querySelector('.content-page__head p:not(.archive__count)');
  const entries = kind === 'series'
    ? editorialCatalogValue('series')
    : kind === 'regions'
      ? editorialCatalogValue('regions')
      : editorialCatalogValue('topics');
  const pageMeta = editorialHubPageMeta(kind);
  if (!grid) return;

  if (eyebrow) eyebrow.textContent = pageMeta.eyebrow;
  if (title) title.textContent = pageMeta.title;
  if (description) description.textContent = pageMeta.description;
  document.title = `${pageMeta.seo_title || pageMeta.title} — ФБРК`;
  const descMeta = document.querySelector('meta[name="description"]');
  if (descMeta) descMeta.setAttribute('content', pageMeta.seo_description || pageMeta.description);
  const ogTitle = document.querySelector('meta[property="og:title"]');
  if (ogTitle) ogTitle.setAttribute('content', `${pageMeta.seo_title || pageMeta.title} — ФБРК`);
  const ogDesc = document.querySelector('meta[property="og:description"]');
  if (ogDesc) ogDesc.setAttribute('content', pageMeta.seo_description || pageMeta.description);
  if (!Array.isArray(entries) || !entries.length) return;

  if (count) {
    const noun = kind === 'series' ? 'серий' : kind === 'regions' ? 'регионов' : 'тем';
    count.textContent = `${new Intl.NumberFormat('ru-KZ').format(entries.length)} ${noun}`;
  }

  grid.innerHTML = entries
    .map((entry) => `
      <section class="content-card hub-card">
        <div class="hub-card__eyebrow">${kind === 'series' ? 'Серия' : kind === 'regions' ? 'Регион' : 'Тема'}</div>
        <h2><a href="${entry.url || '#'}">${escapeHtml(entry.title)}</a></h2>
        <p>${escapeHtml(entry.description || '')}</p>
        <div class="hub-card__meta">Материалов: ${new Intl.NumberFormat('ru-KZ').format(entry.count || 0)}</div>
        ${Array.isArray(entry.latest) && entry.latest.length ? `
          <ul class="content-list hub-card__latest" role="list">
            ${entry.latest.map((article) => `<li><a href="${articleUrl(article.slug || article.id || '')}">${escapeHtml(article.title)}</a></li>`).join('')}
          </ul>
        ` : ''}
      </section>
    `)
    .join('');
})();

// ---------- Sitemap page hub lists ----------
(function () {
  const topicsRoot = document.querySelector('[data-sitemap-topics]');
  if (topicsRoot) {
    const topics = editorialCatalogValue('topics');
    topicsRoot.innerHTML = (topics || []).map((topic) => `<li><a href="${topic.url || '#'}">${escapeHtml(topic.title)}</a></li>`).join('');
  }

  const regionsRoot = document.querySelector('[data-sitemap-regions]');
  if (regionsRoot) {
    const regions = editorialCatalogValue('regions');
    regionsRoot.innerHTML = (regions || []).map((region) => `<li><a href="${region.url || '#'}">${escapeHtml(region.title)}</a></li>`).join('');
  }

  const seriesRoot = document.querySelector('[data-sitemap-series]');
  if (seriesRoot) {
    const seriesItems = editorialCatalogValue('series');
    seriesRoot.innerHTML = (seriesItems || []).map((series) => `<li><a href="${series.url || '#'}">${escapeHtml(series.title)}</a></li>`).join('');
  }

  const resonanceRoot = document.querySelector('[data-sitemap-resonance]');
  if (resonanceRoot) {
    resonanceRoot.innerHTML = `<li><a href="${RESONANCE_META.url}">${escapeHtml(RESONANCE_META.title)}</a></li>`;
  }
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
  const emptyMessage = document.querySelector('[data-search-empty-message]');
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

  function render() {
    const q = (input?.value || '').trim();
    const cat = catSel?.value || '';
    const qLower = q.toLowerCase();
    const allMatches = data.filter((a) => {
      if (cat && a.category !== cat) return false;
      if (!qLower) return true;
      return searchableArticleText(a).includes(qLower);
    });
    const previewLimit = qLower ? 80 : cat ? 40 : 24;
    const matches = allMatches.slice(0, previewLimit);
    if (count) {
      const formattedShown = new Intl.NumberFormat('ru-KZ').format(matches.length);
      const formattedTotal = new Intl.NumberFormat('ru-KZ').format(allMatches.length);
      const formattedIndex = new Intl.NumberFormat('ru-KZ').format(data.length);
      if (qLower) {
        count.textContent = allMatches.length > matches.length
          ? `Найдено: ${formattedTotal} · показано ${formattedShown}`
          : `Найдено: ${formattedTotal}`;
      } else if (cat) {
        count.textContent = allMatches.length > matches.length
          ? `Материалов в рубрике: ${formattedTotal} · показано ${formattedShown}`
          : `Материалов в рубрике: ${formattedShown}`;
      } else {
        count.textContent = `Последние материалы: ${formattedShown} из ${formattedIndex}`;
      }
    }
    if (!allMatches.length) {
      if (results) results.innerHTML = '';
      if (empty) {
        empty.hidden = false;
        const text = empty.querySelector('[data-empty-query]');
        if (text) text.textContent = q;
        if (emptyMessage) {
          emptyMessage.innerHTML = q
            ? `По запросу «<span data-empty-query>${escapeHtml(q)}</span>» ничего не найдено.`
            : cat
              ? 'В выбранной рубрике пока ничего не найдено.'
              : 'Ничего не найдено. Попробуйте уточнить запрос или открыть архив.';
        }
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
    <p>Только функциональные cookie.</p>
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
