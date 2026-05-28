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
