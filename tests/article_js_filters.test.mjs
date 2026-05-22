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
