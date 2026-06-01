"""Admin-managed public editorial policy page."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import html
import re
from pathlib import Path
from sqlite3 import Connection
from typing import Mapping

from .config import settings
from .public_page_shell import load_site_shell, site_url as public_site_url


PREFIX = "editorial_policy."


@dataclass(frozen=True)
class PolicyField:
    name: str
    label: str
    kind: str = "text"
    required: bool = True


POLICY_FIELDS: tuple[PolicyField, ...] = (
    PolicyField("title", "Заголовок"),
    PolicyField("description", "SEO-описание", "textarea"),
    PolicyField("standard_name", "Название стандарта"),
    PolicyField("standard_url", "Ссылка на Editorial Hub"),
    PolicyField("status_label", "Статус"),
    PolicyField("effective_from", "Действует с"),
    PolicyField("owner", "Ответственный"),
    PolicyField("contact_email", "Email для обращений"),
    PolicyField("contact_telegram_label", "Telegram label"),
    PolicyField("contact_telegram_url", "Telegram URL"),
    PolicyField("lede", "Лид страницы", "textarea"),
)


SECTION_FIELDS: tuple[tuple[str, str], ...] = (
    ("scope", "Статус документа"),
    ("factcheck", "Проверка информации"),
    ("sources", "Источники и право на ответ"),
    ("corrections", "Исправления и снятие материалов"),
    ("ai", "AI и синтетические материалы"),
    ("appeals", "Публичные обращения"),
)


DEFAULT_POLICY: dict[str, str] = {
    "title": "Редакционная политика",
    "description": (
        "Как ФБРК проверяет информацию, работает с источниками, правом на ответ, "
        "исправлениями и использованием AI."
    ),
    "standard_name": "Editorial Hub v1.2",
    "standard_url": "https://edpol.qdev.run/",
    "status_label": "Действует",
    "effective_from": "2026-05-27",
    "owner": "Редакция ФБРК",
    "contact_email": "redaktor@fbrk.kz",
    "contact_telegram_label": "@fund_kz_bot",
    "contact_telegram_url": "https://t.me/fund_kz_bot",
    "lede": (
        "Эта страница описывает публичные правила ФБРК: как мы проверяем факты, "
        "работаем с источниками, даём право на ответ, исправляем ошибки и "
        "обозначаем использование AI."
    ),
    "scope_title": "Статус документа",
    "scope_body": (
        "Редакционная политика действует для новостей, расследований, досье, "
        "карточек, видео, публикаций в социальных сетях и архивных обновлений, "
        "которые выходят от имени ФБРК."
    ),
    "factcheck_title": "Проверка информации",
    "factcheck_body": (
        "Факты отделяются от оценок. Для чувствительных утверждений редакция "
        "хранит evidence file: ссылки, документы, скриншоты, запросы, ответы и "
        "историю правок.\n\n"
        "Если факт не подтверждён достаточно надёжно, он формулируется как "
        "утверждение источника или не публикуется до дополнительной проверки."
    ),
    "sources_title": "Источники и право на ответ",
    "sources_body": (
        "Редакция проверяет первоисточник, избегает circular sourcing и даёт "
        "фигурантам разумную возможность прокомментировать существенные обвинения "
        "до публикации.\n\n"
        "Анонимность источника возможна только когда раскрытие личности может "
        "создать риск для человека, его работы, безопасности материала или "
        "редакционного процесса."
    ),
    "corrections_title": "Исправления и снятие материалов",
    "corrections_body": (
        "Если в материале обнаружена ошибка, редакция исправляет её и при "
        "необходимости добавляет пометку об обновлении. Существенные исправления "
        "не скрываются.\n\n"
        "Материал не снимается молча: для существенных правок, уточнений и "
        "ответов редакция сохраняет понятный публичный след."
    ),
    "ai_title": "AI и синтетические материалы",
    "ai_body": (
        "AI может использоваться для черновой аналитики, резюме, извлечения "
        "сущностей и технической подготовки текста, но не заменяет редактора и "
        "фактчек.\n\n"
        "Если изображение или важный фрагмент материала создан синтетически, "
        "читатель должен видеть понятную маркировку."
    ),
    "appeals_title": "Публичные обращения",
    "appeals_body": (
        "Обращения читателей, источников, фигурантов и представителей организаций "
        "рассматриваются редакцией. В сообщении желательно указать ссылку на "
        "материал, суть ошибки или запроса и документы, если они есть.\n\n"
        "Для конфиденциальной информации используйте Telegram-бот, а для "
        "официальных комментариев и уточнений — редакционную почту."
    ),
}


def all_field_names() -> list[str]:
    names = [field.name for field in POLICY_FIELDS]
    for key, _label in SECTION_FIELDS:
        names.extend([f"{key}_title", f"{key}_body"])
    return names


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


def load_policy(conn: Connection) -> dict[str, str]:
    ensure_settings_schema(conn)
    policy = dict(DEFAULT_POLICY)
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE ?",
        (f"{PREFIX}%",),
    ).fetchall()
    for row in rows:
        key = str(row["key"] if hasattr(row, "keys") else row[0])
        value = str(row["value"] if hasattr(row, "keys") else row[1])
        policy[key.removeprefix(PREFIX)] = value
    return policy


def save_policy(conn: Connection, values: Mapping[str, object]) -> list[str]:
    ensure_settings_schema(conn)
    current = load_policy(conn)
    changed: list[str] = []
    for name in all_field_names():
        default = DEFAULT_POLICY.get(name, "")
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


def policy_status(public_root: Path | None = None) -> dict[str, object]:
    root = public_root or Path(settings.public_root)
    path = root / "editorial-policy.html"
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


def write_public_policy_page(
    conn: Connection,
    *,
    public_root: Path | None = None,
    site_url: str | None = None,
) -> dict[str, object]:
    root = public_root or Path(settings.public_root)
    policy = load_policy(conn)
    html_text = render_policy_html(policy, public_root=root, site_url=site_url)
    path = root / "editorial-policy.html"
    path.write_text(html_text, encoding="utf-8")
    stat = path.stat()
    return {"path": str(path), "bytes": stat.st_size}


def render_policy_html(
    policy: Mapping[str, str],
    *,
    public_root: Path | None = None,
    site_url: str | None = None,
) -> str:
    root = public_root or Path(settings.public_root)
    shell = load_site_shell(root)
    header = shell["header"]
    footer = shell["footer"]
    version = shell["version"]
    base_url = (site_url or public_site_url()).rstrip("/")

    title = _value(policy, "title")
    description = _value(policy, "description")
    lede = _value(policy, "lede")
    standard_name = _value(policy, "standard_name")
    standard_url = _safe_http_url(_value(policy, "standard_url"))
    contact_email = _safe_email(_value(policy, "contact_email"))
    contact_tg_label = _value(policy, "contact_telegram_label")
    contact_tg_url = _safe_http_url(_value(policy, "contact_telegram_url"))

    sections = [_render_status_section(policy, standard_name, standard_url)]
    for key, _label in SECTION_FIELDS:
        if key == "scope":
            continue
        sections.append(_render_policy_section(policy, key))
    sections.insert(
        4,
        _render_contacts_section(contact_email, contact_tg_label, contact_tg_url),
    )
    content = "\n".join(sections)

    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(title)} — ФБРК</title>
    <meta name="description" content="{html.escape(description)}" />
    <meta name="theme-color" content="#0C115F" />
    <link rel="canonical" href="{base_url}/editorial-policy.html" />
    <meta property="og:site_name" content="ФБРК" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{html.escape(title)} — ФБРК" />
    <meta property="og:description" content="{html.escape(description)}" />
    <meta property="og:url" content="{base_url}/editorial-policy.html" />
    <meta property="og:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{html.escape(title)} — ФБРК" />
    <meta name="twitter:description" content="{html.escape(description)}" />
    <meta name="twitter:image" content="{base_url}/img/brand/logo-on-brand-640.png" />
    <link rel="icon" type="image/png" sizes="32x32" href="/img/brand/favicon-32.png" />
    <link rel="icon" type="image/png" sizes="192x192" href="/img/brand/favicon-192.png" />
    <link rel="apple-touch-icon" href="/img/brand/apple-touch-icon.png" />
    <link rel="icon" type="image/svg+xml" href="/img/brand/logo.svg" />
    <link rel="stylesheet" href="/fonts/avds/avds-fonts.css?v={version}" />
    <link rel="stylesheet" href="/css/style.css?v={version}" />
    <script>
      try {{
        const t = localStorage.getItem('theme') || localStorage.getItem('fbrk_theme');
        document.documentElement.dataset.theme = t === 'dark' || t === 'light' ? t : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      }} catch (_) {{}}
    </script>
  </head>
  <body>
    <a class="skip-link" href="#main">Перейти к содержимому</a>

{header}

    <main id="main" class="content-page">
      <div class="container content-page__inner">
        <header class="content-page__head">
          <div class="kicker content-page__eyebrow">Редакция</div>
          <h1 class="content-page__title">{html.escape(title)}</h1>
          <p class="about__lede">{html.escape(lede)}</p>
        </header>

        <div class="content-grid">
{content}
        </div>
      </div>
    </main>

{footer}
    <script src="/js/runtime-config.js?v={version}"></script>
    <script src="/js/data.js?v={version}"></script>
    <script src="/js/app.js?v={version}"></script>
  </body>
</html>
"""


def safe_http_url(value: str) -> str:
    return _safe_http_url(value)


def _value(policy: Mapping[str, str], key: str) -> str:
    return str(policy.get(key) or DEFAULT_POLICY.get(key) or "").strip()


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


def _render_policy_section(policy: Mapping[str, str], key: str) -> str:
    title = _value(policy, f"{key}_title")
    paragraphs = _paragraphs(_value(policy, f"{key}_body"))
    body = "\n".join(f"            <p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)
    return f"""          <section class="content-card">
            <h2>{html.escape(title)}</h2>
{body}
          </section>"""


def _render_status_section(policy: Mapping[str, str], standard_name: str, standard_url: str) -> str:
    title = _value(policy, "scope_title")
    status = _value(policy, "status_label")
    effective_from = _value(policy, "effective_from")
    owner = _value(policy, "owner")
    paragraphs = _paragraphs(_value(policy, "scope_body"))
    body = "\n".join(f"            <p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)
    return f"""          <section class="content-card">
            <h2>{html.escape(title)}</h2>
            <p><strong>{html.escape(status)}</strong> · действует с {html.escape(effective_from)} · ответственный: {html.escape(owner)}.</p>
{body}
            <p>Полный операционный стандарт доступен в <a href="{html.escape(standard_url)}" target="_blank" rel="noopener">{html.escape(standard_name)}</a>. Для сайта ФБРК здесь опубликована краткая публичная версия этого стандарта.</p>
          </section>"""


def _render_contacts_section(email: str, tg_label: str, tg_url: str) -> str:
    email_link = (
        f'<a href="mailto:{html.escape(email)}">{html.escape(email)}</a>'
        if email
        else "редакционную почту"
    )
    tg_link = f'<a href="{html.escape(tg_url)}" target="_blank" rel="noopener">{html.escape(tg_label)}</a>'
    return f"""          <section class="content-card">
            <h2>Контакты по политике</h2>
            <p>Запросы на исправление, ответ, удаление или уточнение принимаются через {email_link} и Telegram-бот {tg_link}.</p>
            <p>Если вопрос касается конкретной публикации, приложите ссылку на материал, описание проблемы и подтверждающие документы, если они есть.</p>
          </section>"""
