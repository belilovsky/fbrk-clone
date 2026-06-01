"""Admin-managed public trust pages for FBRK."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import html
from pathlib import Path
import re
from sqlite3 import Connection
from typing import Mapping

from .config import settings
from .public_page_shell import load_site_shell, site_url as public_site_url


PREFIX = "public_pages."


@dataclass(frozen=True)
class PublicPageField:
    name: str
    label: str
    kind: str = "text"
    required: bool = True


ABOUT_FIELDS: tuple[PublicPageField, ...] = (
    PublicPageField("about_seo_title", "SEO title"),
    PublicPageField("about_seo_description", "SEO description", "textarea"),
    PublicPageField("about_eyebrow", "Eyebrow"),
    PublicPageField("about_title", "Заголовок"),
    PublicPageField("about_lede", "Лид", "textarea"),
    PublicPageField("about_founded_year", "Год основания"),
    PublicPageField("about_independence_value", "Независимость - значение"),
    PublicPageField("about_independence_label", "Независимость - подпись"),
    PublicPageField("about_intro_title", "Блок 1 - заголовок"),
    PublicPageField("about_intro_body", "Блок 1 - текст", "textarea"),
    PublicPageField("about_coverage_title", "Блок 2 - заголовок"),
    PublicPageField("about_coverage_body", "Блок 2 - текст", "textarea"),
    PublicPageField("about_contact_title", "Блок 3 - заголовок"),
    PublicPageField("about_contact_body", "Блок 3 - текст", "textarea"),
    PublicPageField("about_legal_title", "Блок 4 - заголовок"),
    PublicPageField("about_legal_body", "Блок 4 - текст", "textarea"),
    PublicPageField("about_policy_title", "Блок 5 - заголовок"),
    PublicPageField("about_policy_body", "Блок 5 - текст", "textarea"),
)


CONTACT_FIELDS: tuple[PublicPageField, ...] = (
    PublicPageField("contacts_seo_title", "SEO title"),
    PublicPageField("contacts_seo_description", "SEO description", "textarea"),
    PublicPageField("contacts_eyebrow", "Eyebrow"),
    PublicPageField("contacts_title", "Заголовок"),
    PublicPageField("contacts_lede", "Лид", "textarea"),
    PublicPageField("contacts_editor_title", "Карточка - редакция"),
    PublicPageField("contacts_editor_name", "Название редакции"),
    PublicPageField("contacts_editor_email", "Email редакции"),
    PublicPageField("contacts_tip_email", "Email для писем читателей"),
    PublicPageField("contacts_press_email", "Email для СМИ и партнёров"),
    PublicPageField("contacts_telegram_label", "Telegram label"),
    PublicPageField("contacts_telegram_url", "Telegram URL"),
    PublicPageField("contacts_youtube_label", "YouTube label"),
    PublicPageField("contacts_youtube_url", "YouTube URL"),
    PublicPageField("contacts_legal_title", "Карточка - юридический адрес"),
    PublicPageField("contacts_legal_city", "Город и страна"),
    PublicPageField("contacts_legal_address", "Адрес / пояснение"),
    PublicPageField("contacts_reach_title", "Карточка - связь с нами"),
    PublicPageField("contacts_partners_title", "Карточка - для СМИ и партнёров"),
    PublicPageField("contacts_registration_title", "Карточка - регистрация СМИ"),
    PublicPageField("contacts_registration_number", "Номер регистрации"),
    PublicPageField("contacts_registration_date", "Дата регистрации"),
)


PRIVACY_FIELDS: tuple[PublicPageField, ...] = (
    PublicPageField("privacy_seo_title", "SEO title"),
    PublicPageField("privacy_seo_description", "SEO description", "textarea"),
    PublicPageField("privacy_eyebrow", "Eyebrow"),
    PublicPageField("privacy_title", "Заголовок"),
    PublicPageField("privacy_lede", "Лид", "textarea"),
    PublicPageField("privacy_cookies_title", "Блок 1 - заголовок"),
    PublicPageField("privacy_cookies_body", "Блок 1 - текст", "textarea"),
    PublicPageField("privacy_feedback_title", "Блок 2 - заголовок"),
    PublicPageField("privacy_feedback_body", "Блок 2 - текст", "textarea"),
    PublicPageField("privacy_logs_title", "Блок 3 - заголовок"),
    PublicPageField("privacy_logs_body", "Блок 3 - текст", "textarea"),
    PublicPageField("privacy_contact_title", "Блок 4 - заголовок"),
    PublicPageField("privacy_contact_body", "Блок 4 - текст", "textarea"),
)


DEFAULT_PUBLIC_PAGES: dict[str, str] = {
    "about_seo_title": "О нас",
    "about_seo_description": (
        "ФБРК — независимое казахстанское медиа о коррупции, госзакупках, "
        "конфликте интересов и концентрации влияния."
    ),
    "about_eyebrow": "Редакция",
    "about_title": "Фонд-бюро расследования коррупции",
    "about_lede": (
        "Независимое казахстанское медиа, которое расследует коррупцию, "
        "конфликт интересов, госзакупки, влияние денег на решения государства "
        "и концентрацию активов."
    ),
    "about_founded_year": "2023",
    "about_independence_value": "100%",
    "about_independence_label": "Редакционная независимость",
    "about_intro_title": "Что такое ФБРК",
    "about_intro_body": (
        "Фонд-бюро расследования коррупции — независимая редакция, которая "
        "работает в общественном интересе. Мы выпускаем расследования, новости "
        "и объясняющие материалы о решениях власти, деньгах, влиянии и "
        "подотчётности в Казахстане."
    ),
    "about_coverage_title": "Что мы расследуем",
    "about_coverage_body": (
        "В фокусе ФБРК — госзакупки, земля и активы, связи бизнеса и чиновников, "
        "региональные конфликты интересов, судебные сюжеты и долгие редакционные "
        "линии. Мы работаем с документами, данными и публичными источниками, а "
        "когда это возможно — добираем право на ответ и позицию всех сторон."
    ),
    "about_contact_title": "Как передать информацию",
    "about_contact_body": (
        "Если у вас есть документы, сведения о коррупции, нарушениях при "
        "госзакупках, конфликте интересов или злоупотреблении полномочиями, "
        "напишите редакции. Мы рассматриваем каждое сообщение, проверяем факты "
        "и не раскрываем источник без его согласия."
    ),
    "about_legal_title": "Статус и права",
    "about_legal_body": (
        "ФБРК зарегистрирован как сетевое издание в Республике Казахстан и "
        "работает по законодательству о СМИ. Перепечатка допускается только с "
        "обязательной ссылкой на источник, а редакция оставляет за собой право "
        "уточнять и обновлять публикации по мере верификации новых фактов."
    ),
    "about_policy_title": "Как мы работаем",
    "about_policy_body": (
        "Мы отделяем факты от оценок, проверяем документы и цифры, даём право "
        "на ответ, публично исправляем ошибки и отмечаем использование AI там, "
        "где он участвовал в подготовке служебных элементов материала."
    ),
    "contacts_seo_title": "Контакты",
    "contacts_seo_description": (
        "Каналы связи редакции ФБРК для читателей, информаторов, СМИ и "
        "партнёрских запросов."
    ),
    "contacts_eyebrow": "Редакция",
    "contacts_title": "Контакты",
    "contacts_lede": (
        "Ниже — официальные каналы связи ФБРК для читателей, источников, "
        "журналистских запросов, комментариев и партнёрств."
    ),
    "contacts_editor_title": "Редакция",
    "contacts_editor_name": "Фонд-бюро расследования коррупции",
    "contacts_editor_email": "redaktor@fbrk.kz",
    "contacts_tip_email": "tip@fbrk.kz",
    "contacts_press_email": "press@fbrk.kz",
    "contacts_telegram_label": "@fund_kz_bot",
    "contacts_telegram_url": "https://t.me/fund_kz_bot",
    "contacts_youtube_label": "YouTube-канал редакции",
    "contacts_youtube_url": "https://www.youtube.com/@fbrk_news",
    "contacts_legal_title": "Юридические данные",
    "contacts_legal_city": "010000, г. Астана, Республика Казахстан",
    "contacts_legal_address": (
        "Официальные запросы, документы и уточнения по публикациям можно "
        "направлять на редакционный email."
    ),
    "contacts_reach_title": "Для читателей и информаторов",
    "contacts_partners_title": "Для СМИ, комментариев и партнёрств",
    "contacts_registration_title": "Регистрация СМИ",
    "contacts_registration_number": "KZ83VPY00075165",
    "contacts_registration_date": "21.08.2023",
    "privacy_seo_title": "Политика конфиденциальности",
    "privacy_seo_description": (
        "Как ФБРК обращается с сообщениями читателей и минимальными техническими "
        "данными сайта."
    ),
    "privacy_eyebrow": "Документы",
    "privacy_title": "Политика конфиденциальности",
    "privacy_lede": (
        "Мы собираем только те данные, без которых нельзя обеспечить работу "
        "сайта, безопасность сервисов и обратную связь с редакцией. ФБРК не "
        "торгует персональными данными и не использует их для рекламного "
        "профилирования."
    ),
    "privacy_cookies_title": "Cookie и настройки",
    "privacy_cookies_body": (
        "Сайт использует только функциональные cookie и локальное хранилище "
        "браузера для сохранения выбранной темы, согласия с cookie и базовых "
        "пользовательских настроек.\n\n"
        "Эти данные не продаются и не передаются третьим лицам в рекламных целях."
    ),
    "privacy_feedback_title": "Обратная связь",
    "privacy_feedback_body": (
        "Если вы пишете в редакцию по email или через Telegram-бот, мы "
        "обрабатываем только те контактные данные, документы и содержание "
        "сообщения, которые вы отправили самостоятельно.\n\n"
        "Такие обращения хранятся столько, сколько это нужно для проверки фактов, "
        "ответа вам и защиты редакции. Мы не раскрываем персональные данные и "
        "источники без согласия, кроме случаев, прямо предусмотренных законом."
    ),
    "privacy_logs_title": "Технические журналы",
    "privacy_logs_body": (
        "Сервер может фиксировать технические сведения о запросах: IP-адрес, "
        "дату и время обращения, адрес страницы, user-agent и код ответа.\n\n"
        "Эти журналы нужны для безопасности, диагностики ошибок и защиты сайта "
        "от злоупотреблений. Мы не используем их для рекламного профилирования."
    ),
    "privacy_contact_title": "Связь по вопросам данных",
    "privacy_contact_body": (
        "Если у вас есть вопрос об обработке сообщения, которое вы отправили "
        "редакции, или о данных в сервисах ФБРК, напишите нам."
    ),
}


def all_field_names() -> list[str]:
    return [field.name for field in ABOUT_FIELDS + CONTACT_FIELDS + PRIVACY_FIELDS]


def ensure_settings_schema(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def load_public_pages(conn: Connection) -> dict[str, str]:
    ensure_settings_schema(conn)
    pages = dict(DEFAULT_PUBLIC_PAGES)
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE ?",
        (f"{PREFIX}%",),
    ).fetchall()
    for row in rows:
        key = str(row["key"] if hasattr(row, "keys") else row[0])
        value = str(row["value"] if hasattr(row, "keys") else row[1])
        pages[key.removeprefix(PREFIX)] = value
    return pages


def save_public_pages(conn: Connection, values: Mapping[str, object]) -> list[str]:
    ensure_settings_schema(conn)
    current = load_public_pages(conn)
    changed: list[str] = []
    for name in all_field_names():
        default = DEFAULT_PUBLIC_PAGES.get(name, "")
        raw = values.get(name, default)
        value = str(raw if raw is not None else "").strip()
        if not value:
            value = default
        if value != current.get(name, default):
            changed.append(name)
        conn.execute(
            """
            INSERT INTO settings(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE
            SET value = excluded.value, updated_at = datetime('now')
            """,
            (f"{PREFIX}{name}", value),
        )
    return changed


def public_pages_status(public_root: Path | None = None) -> dict[str, dict[str, object]]:
    root = public_root or Path(settings.public_root)
    return {
        "about": _page_status(root / "about.html"),
        "contacts": _page_status(root / "contacts.html"),
        "privacy": _page_status(root / "privacy.html"),
    }


def write_public_pages(
    conn: Connection,
    *,
    public_root: Path | None = None,
    site_url: str | None = None,
) -> dict[str, dict[str, object]]:
    root = public_root or Path(settings.public_root)
    pages = load_public_pages(conn)
    about_path = root / "about.html"
    contacts_path = root / "contacts.html"
    privacy_path = root / "privacy.html"
    about_path.write_text(render_about_html(pages, public_root=root, site_url=site_url), encoding="utf-8")
    contacts_path.write_text(render_contacts_html(pages, public_root=root, site_url=site_url), encoding="utf-8")
    privacy_path.write_text(render_privacy_html(pages, public_root=root, site_url=site_url), encoding="utf-8")
    return {
        "about": {"path": str(about_path), "bytes": about_path.stat().st_size},
        "contacts": {"path": str(contacts_path), "bytes": contacts_path.stat().st_size},
        "privacy": {"path": str(privacy_path), "bytes": privacy_path.stat().st_size},
    }


def site_profile(values: Mapping[str, str]) -> dict[str, str]:
    registration = (
        f"{_value(values, 'contacts_registration_number')} "
        f"от {_value(values, 'contacts_registration_date')}"
    ).strip()
    about = (
        f"{_value(values, 'about_title')} (ФБРК) — сетевое издание, "
        f"свидетельство о регистрации СМИ № {registration}. "
        f"{_value(values, 'about_intro_body')}"
    ).strip()
    mission = _value(values, "about_coverage_body")
    footer_about = (
        f"{_value(values, 'about_title')} — независимое сетевое издание. "
        f"Свидетельство СМИ № {registration}."
    ).strip()
    return {
        "name": "ФБРК",
        "fullName": _value(values, "about_title"),
        "tagline": "Независимые расследования · Казахстан",
        "about": about,
        "mission": mission,
        "telegram": _safe_http_url(_value(values, "contacts_telegram_url")),
        "telegramName": _value(values, "contacts_telegram_label"),
        "youtube": _safe_http_url(_value(values, "contacts_youtube_url")),
        "youtubeName": _value(values, "contacts_youtube_label"),
        "registration": registration,
        "footerAbout": footer_about,
        "contactEmail": _value(values, "contacts_editor_email"),
        "tipEmail": _value(values, "contacts_tip_email"),
        "pressEmail": _value(values, "contacts_press_email"),
        "city": _site_city(values),
    }


def render_about_html(
    pages: Mapping[str, str],
    *,
    public_root: Path | None = None,
    site_url: str | None = None,
) -> str:
    root = public_root or Path(settings.public_root)
    shell = load_site_shell(root)
    base_url = (site_url or public_site_url()).rstrip("/")
    title = _value(pages, "about_title")
    seo_title = _value(pages, "about_seo_title") or title
    description = _value(pages, "about_seo_description")
    lede = _value(pages, "about_lede")
    founded_year = _value(pages, "about_founded_year")
    independence_value = _value(pages, "about_independence_value")
    independence_label = _value(pages, "about_independence_label")
    telegram_label = _value(pages, "contacts_telegram_label")
    telegram_url = _safe_http_url(_value(pages, "contacts_telegram_url"))
    youtube_label = _value(pages, "contacts_youtube_label")
    youtube_url = _safe_http_url(_value(pages, "contacts_youtube_url"))
    contact_email = _safe_email(_value(pages, "contacts_editor_email"))

    about_blocks = "\n".join(
        [
            _render_text_block(pages, "about_intro"),
            _render_text_block(pages, "about_coverage"),
            _render_about_contact_block(
                pages,
                telegram_label=telegram_label,
                telegram_url=telegram_url,
                youtube_label=youtube_label,
                youtube_url=youtube_url,
            ),
            _render_about_legal_block(pages, contact_email),
            _render_about_policy_block(pages),
        ]
    )

    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(seo_title)} — ФБРК</title>
    <meta name="description" content="{html.escape(description)}" />
    <meta name="theme-color" content="#0C115F" />
    <link rel="canonical" href="{base_url}/about.html" />
    <meta property="og:site_name" content="ФБРК" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{html.escape(seo_title)} — ФБРК" />
    <meta property="og:description" content="{html.escape(description)}" />
    <meta property="og:url" content="{base_url}/about.html" />
    <meta property="og:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{html.escape(seo_title)} — ФБРК" />
    <meta name="twitter:description" content="{html.escape(description)}" />
    <meta name="twitter:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <link rel="icon" type="image/png" sizes="32x32" href="/img/brand/favicon-32.png" />
    <link rel="icon" type="image/png" sizes="192x192" href="/img/brand/favicon-192.png" />
    <link rel="apple-touch-icon" href="/img/brand/apple-touch-icon.png" />
    <link rel="icon" type="image/svg+xml" href="/img/brand/logo.svg" />
    <link rel="stylesheet" href="/fonts/avds/avds-fonts.css?v={shell["version"]}" />
    <link rel="stylesheet" href="/css/style.css?v={shell["version"]}" />
    <script>
      try {{
        const t = localStorage.getItem('theme') || localStorage.getItem('fbrk_theme');
        document.documentElement.dataset.theme = t === 'dark' || t === 'light' ? t : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      }} catch (_) {{}}
    </script>
  </head>
  <body>
    <a class="skip-link" href="#main">Перейти к содержимому</a>
{shell["header"]}
    <main id="main">
      <section class="about">
        <div class="container">
          <div class="about__intro">
            <div class="kicker about__eyebrow">{html.escape(_value(pages, "about_eyebrow"))}</div>
            <h1 class="about__title">{html.escape(title)}</h1>
            <p class="about__lede">{html.escape(lede)}</p>
          </div>

          <div class="about__stats">
            <div class="stat">
              <div class="stat__value">{html.escape(founded_year)}</div>
              <div class="stat__label">Год основания</div>
            </div>
            <div class="stat">
              <div class="stat__value" data-stat-articles>—</div>
              <div class="stat__label">Опубликовано материалов</div>
            </div>
            <div class="stat">
              <div class="stat__value">{html.escape(independence_value)}</div>
              <div class="stat__label">{html.escape(independence_label)}</div>
            </div>
          </div>

          <div class="about__body">
{about_blocks}
          </div>
        </div>
      </section>
    </main>
{shell["footer"]}
    <script src="/js/runtime-config.js?v={shell["version"]}"></script>
    <script src="/js/data.js?v={shell["version"]}"></script>
    <script src="/js/app.js?v={shell["version"]}"></script>
  </body>
</html>
"""


def render_contacts_html(
    pages: Mapping[str, str],
    *,
    public_root: Path | None = None,
    site_url: str | None = None,
) -> str:
    root = public_root or Path(settings.public_root)
    shell = load_site_shell(root)
    base_url = (site_url or public_site_url()).rstrip("/")
    title = _value(pages, "contacts_title")
    seo_title = _value(pages, "contacts_seo_title") or title
    description = _value(pages, "contacts_seo_description")
    lede = _value(pages, "contacts_lede")
    telegram_label = _value(pages, "contacts_telegram_label")
    telegram_url = _safe_http_url(_value(pages, "contacts_telegram_url"))
    youtube_label = _value(pages, "contacts_youtube_label")
    youtube_url = _safe_http_url(_value(pages, "contacts_youtube_url"))
    editor_email = _safe_email(_value(pages, "contacts_editor_email"))
    tip_email = _safe_email(_value(pages, "contacts_tip_email"))
    press_email = _safe_email(_value(pages, "contacts_press_email"))

    cards = "\n".join(
        [
            _render_contacts_editor_card(pages, editor_email, telegram_label, telegram_url),
            _render_contacts_legal_card(pages),
            _render_contacts_reach_card(pages, tip_email, telegram_label, telegram_url, youtube_label, youtube_url),
            _render_contacts_partners_card(pages, press_email),
            _render_contacts_registration_card(pages),
        ]
    )

    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(seo_title)} — ФБРК</title>
    <meta name="description" content="{html.escape(description)}" />
    <meta name="theme-color" content="#0C115F" />
    <link rel="canonical" href="{base_url}/contacts.html" />
    <meta property="og:site_name" content="ФБРК" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{html.escape(seo_title)} — ФБРК" />
    <meta property="og:description" content="{html.escape(description)}" />
    <meta property="og:url" content="{base_url}/contacts.html" />
    <meta property="og:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{html.escape(seo_title)} — ФБРК" />
    <meta name="twitter:description" content="{html.escape(description)}" />
    <meta name="twitter:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <link rel="icon" type="image/png" sizes="32x32" href="/img/brand/favicon-32.png" />
    <link rel="icon" type="image/png" sizes="192x192" href="/img/brand/favicon-192.png" />
    <link rel="apple-touch-icon" href="/img/brand/apple-touch-icon.png" />
    <link rel="icon" type="image/svg+xml" href="/img/brand/logo.svg" />
    <link rel="stylesheet" href="/fonts/avds/avds-fonts.css?v={shell["version"]}" />
    <link rel="stylesheet" href="/css/style.css?v={shell["version"]}" />
    <script>
      try {{
        const t = localStorage.getItem('theme') || localStorage.getItem('fbrk_theme');
        document.documentElement.dataset.theme = t === 'dark' || t === 'light' ? t : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      }} catch (_) {{}}
    </script>
  </head>
  <body>
    <a class="skip-link" href="#main">Перейти к содержимому</a>
{shell["header"]}
    <main id="main" class="content-page">
      <div class="container content-page__inner">
        <header class="content-page__head">
          <div class="kicker content-page__eyebrow">{html.escape(_value(pages, "contacts_eyebrow"))}</div>
          <h1 class="content-page__title">{html.escape(title)}</h1>
          <p class="about__lede">{html.escape(lede)}</p>
        </header>
        <div class="content-grid">
{cards}
        </div>
      </div>
    </main>
{shell["footer"]}
    <script src="/js/runtime-config.js?v={shell["version"]}"></script>
    <script src="/js/data.js?v={shell["version"]}"></script>
    <script src="/js/app.js?v={shell["version"]}"></script>
  </body>
</html>
"""


def render_privacy_html(
    pages: Mapping[str, str],
    *,
    public_root: Path | None = None,
    site_url: str | None = None,
) -> str:
    root = public_root or Path(settings.public_root)
    shell = load_site_shell(root)
    base_url = (site_url or public_site_url()).rstrip("/")
    title = _value(pages, "privacy_title")
    seo_title = _value(pages, "privacy_seo_title") or title
    description = _value(pages, "privacy_seo_description")
    lede = _value(pages, "privacy_lede")
    contact_email = _safe_email(_value(pages, "contacts_editor_email"))
    cards = "\n".join(
        [
            _content_card(_value(pages, "privacy_cookies_title"), _body_html(_value(pages, "privacy_cookies_body"))),
            _content_card(_value(pages, "privacy_feedback_title"), _body_html(_value(pages, "privacy_feedback_body"))),
            _content_card(_value(pages, "privacy_logs_title"), _body_html(_value(pages, "privacy_logs_body"))),
            _render_privacy_contact_card(pages, contact_email),
        ]
    )

    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(seo_title)} — ФБРК</title>
    <meta name="description" content="{html.escape(description)}" />
    <meta name="theme-color" content="#0C115F" />
    <link rel="canonical" href="{base_url}/privacy.html" />
    <meta property="og:site_name" content="ФБРК" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{html.escape(seo_title)} — ФБРК" />
    <meta property="og:description" content="{html.escape(description)}" />
    <meta property="og:url" content="{base_url}/privacy.html" />
    <meta property="og:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{html.escape(seo_title)} — ФБРК" />
    <meta name="twitter:description" content="{html.escape(description)}" />
    <meta name="twitter:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <link rel="icon" type="image/png" sizes="32x32" href="/img/brand/favicon-32.png" />
    <link rel="icon" type="image/png" sizes="192x192" href="/img/brand/favicon-192.png" />
    <link rel="apple-touch-icon" href="/img/brand/apple-touch-icon.png" />
    <link rel="icon" type="image/svg+xml" href="/img/brand/logo.svg" />
    <link rel="stylesheet" href="/fonts/avds/avds-fonts.css?v={shell["version"]}" />
    <link rel="stylesheet" href="/css/style.css?v={shell["version"]}" />
    <script>
      try {{
        const t = localStorage.getItem('theme') || localStorage.getItem('fbrk_theme');
        document.documentElement.dataset.theme = t === 'dark' || t === 'light' ? t : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      }} catch (_) {{}}
    </script>
  </head>
  <body>
    <a class="skip-link" href="#main">Перейти к содержимому</a>
{shell["header"]}
    <main id="main" class="content-page">
      <div class="container content-page__inner">
        <header class="content-page__head">
          <div class="kicker content-page__eyebrow">{html.escape(_value(pages, "privacy_eyebrow"))}</div>
          <h1 class="content-page__title">{html.escape(title)}</h1>
          <p class="about__lede">{html.escape(lede)}</p>
        </header>
        <div class="content-grid">
{cards}
        </div>
      </div>
    </main>
{shell["footer"]}
    <script src="/js/runtime-config.js?v={shell["version"]}"></script>
    <script src="/js/data.js?v={shell["version"]}"></script>
    <script src="/js/app.js?v={shell["version"]}"></script>
  </body>
</html>
"""


def _page_status(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "path": str(path), "size": 0, "updated_at": ""}
    stat = path.stat()
    updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).astimezone()
    return {
        "exists": True,
        "path": str(path),
        "size": stat.st_size,
        "updated_at": updated.strftime("%Y-%m-%d %H:%M"),
    }


def _value(values: Mapping[str, str], key: str) -> str:
    return str(values.get(key) or DEFAULT_PUBLIC_PAGES.get(key) or "").strip()


def _site_city(values: Mapping[str, str]) -> str:
    raw = _value(values, "contacts_legal_city")
    cleaned = re.sub(r"^\d{6},\s*", "", raw)
    cleaned = cleaned.replace("Республика Казахстан", "Казахстан")
    cleaned = cleaned.replace("г. ", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    return cleaned or "Астана, Казахстан"


def _safe_http_url(value: str) -> str:
    value = str(value or "").strip()
    if re.match(r"^https?://[^\s<>\"]+$", value, flags=re.IGNORECASE):
        return value
    return "#"


def _safe_email(value: str) -> str:
    value = str(value or "").strip()
    if re.match(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$", value):
        return value
    return ""


def _paragraphs(value: str) -> list[str]:
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", value or "")
        if paragraph.strip()
    ]


def _body_html(value: str) -> str:
    return "\n".join(f"              <p>{html.escape(paragraph)}</p>" for paragraph in _paragraphs(value))


def _render_text_block(values: Mapping[str, str], key: str) -> str:
    title = _value(values, f"{key}_title")
    body = _body_html(_value(values, f"{key}_body"))
    return f"""            <div class="about__block">
              <h2>{html.escape(title)}</h2>
{body}
            </div>"""


def _render_about_contact_block(
    values: Mapping[str, str],
    *,
    telegram_label: str,
    telegram_url: str,
    youtube_label: str,
    youtube_url: str,
) -> str:
    body = _body_html(_value(values, "about_contact_body"))
    links: list[str] = []
    if telegram_url != "#":
        links.append(
            f'              <p>Анонимный бот: <a href="{html.escape(telegram_url)}" target="_blank" rel="noopener">{html.escape(telegram_label)}</a>.</p>'
        )
    if youtube_url != "#":
        links.append(
            f'              <p>Видео, интервью и разборы документов: <a href="{html.escape(youtube_url)}" target="_blank" rel="noopener">{html.escape(youtube_label)}</a>.</p>'
        )
    links_html = "\n".join(links)
    return f"""            <div class="about__block">
              <h2>{html.escape(_value(values, "about_contact_title"))}</h2>
{body}
{links_html}
            </div>"""


def _render_about_legal_block(values: Mapping[str, str], contact_email: str) -> str:
    body = _body_html(_value(values, "about_legal_body"))
    email_line = ""
    if contact_email:
        email_line = (
            f'              <p>Email редакции: <a href="mailto:{html.escape(contact_email)}">{html.escape(contact_email)}</a>. '
            'Полные юридические контакты и каналы связи: <a href="/contacts.html">/contacts.html</a>.</p>'
        )
    return f"""            <div class="about__block">
              <h2>{html.escape(_value(values, "about_legal_title"))}</h2>
{body}
{email_line}
            </div>"""


def _render_about_policy_block(values: Mapping[str, str]) -> str:
    body = _body_html(_value(values, "about_policy_body"))
    links = (
        '              <p>Краткая версия стандарта опубликована на странице '
        '<a href="/editorial-policy.html">Редакционная политика</a>, '
        'полный стандарт доступен в <a href="https://edpol.qdev.run/" target="_blank" rel="noopener">Editorial Hub</a>.</p>'
    )
    return f"""            <div class="about__block">
              <h2>{html.escape(_value(values, "about_policy_title"))}</h2>
{body}
{links}
            </div>"""


def _render_contacts_editor_card(
    values: Mapping[str, str],
    editor_email: str,
    telegram_label: str,
    telegram_url: str,
) -> str:
    lines = [f"              <p>Редакция: {html.escape(_value(values, 'contacts_editor_name'))}</p>"]
    if editor_email:
        lines.append(
            f'              <p>Общие вопросы: <a href="mailto:{html.escape(editor_email)}">{html.escape(editor_email)}</a></p>'
        )
    if telegram_url != "#":
        lines.append(
            f'              <p>Оперативная связь: <a href="{html.escape(telegram_url)}" target="_blank" rel="noopener">{html.escape(telegram_label)}</a></p>'
        )
    return _content_card(_value(values, "contacts_editor_title"), "\n".join(lines))


def _render_contacts_legal_card(values: Mapping[str, str]) -> str:
    lines = [
        f"              <p>{html.escape(_value(values, 'contacts_legal_city'))}</p>",
        f"              <p>{html.escape(_value(values, 'contacts_legal_address'))}</p>",
    ]
    return _content_card(_value(values, "contacts_legal_title"), "\n".join(lines))


def _render_contacts_reach_card(
    values: Mapping[str, str],
    tip_email: str,
    telegram_label: str,
    telegram_url: str,
    youtube_label: str,
    youtube_url: str,
) -> str:
    lines: list[str] = [
        "              <p>Для сообщений, документов и обратной связи используйте любой удобный канал.</p>"
    ]
    if telegram_url != "#":
        lines.append(
            f'              <p>Telegram-бот: <a href="{html.escape(telegram_url)}" target="_blank" rel="noopener">{html.escape(telegram_label)}</a></p>'
        )
    if tip_email:
        lines.append(
            f'              <p>Email для писем и сигналов: <a href="mailto:{html.escape(tip_email)}">{html.escape(tip_email)}</a></p>'
        )
    if youtube_url != "#":
        lines.append(
            f'              <p>Публичные видео и интервью: <a href="{html.escape(youtube_url)}" target="_blank" rel="noopener">{html.escape(youtube_label)}</a></p>'
        )
    return _content_card(_value(values, "contacts_reach_title"), "\n".join(lines))


def _render_contacts_partners_card(values: Mapping[str, str], press_email: str) -> str:
    lines: list[str] = []
    if press_email:
        lines.append("              <p>Для комментариев, интервью, перепечаток и партнёрских запросов.</p>")
        lines.append(
            f'              <p><a href="mailto:{html.escape(press_email)}">{html.escape(press_email)}</a></p>'
        )
    body = "\n".join(lines)
    return _content_card(_value(values, "contacts_partners_title"), body)


def _render_contacts_registration_card(values: Mapping[str, str]) -> str:
    lines = [
        f"              <p>{html.escape(_value(values, 'contacts_registration_number'))}</p>",
        f"              <p>Дата регистрации: {html.escape(_value(values, 'contacts_registration_date'))}</p>",
    ]
    return _content_card(_value(values, "contacts_registration_title"), "\n".join(lines))


def _render_privacy_contact_card(values: Mapping[str, str], contact_email: str) -> str:
    body = _body_html(_value(values, "privacy_contact_body"))
    email_line = ""
    if contact_email:
        email_line = (
            f'              <p>Email редакции: <a href="mailto:{html.escape(contact_email)}">{html.escape(contact_email)}</a></p>'
        )
    return _content_card(_value(values, "privacy_contact_title"), "\n".join([body, email_line]).strip())


def _content_card(title: str, body_html: str) -> str:
    return f"""          <section class="content-card">
            <h2>{html.escape(title)}</h2>
{body_html}
          </section>"""
