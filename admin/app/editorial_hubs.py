"""Curated editorial topics, regions, series, statuses, and related-material helpers for FBRK."""
from __future__ import annotations

import json
import re
from sqlite3 import Connection
from typing import Iterable


TOPIC_DEFINITIONS = (
    {
        "slug": "corruption",
        "title": "Коррупция и Антикор",
        "description": "Взятки, хищения, служебные злоупотребления, расследования и проверки вокруг публичных денег.",
        "strong_terms": ("коррупц", "антикор", "взятк", "растра", "хищен", "отмыв"),
        "support_terms": ("ущерб", "аффилиир", "злоупотреб", "подкуп", "легализ"),
    },
    {
        "slug": "budget-and-procurement",
        "title": "Бюджет и госзакупки",
        "description": "Госрасходы, аудит, тендеры, субсидии и цена управленческих решений в цифрах.",
        "strong_terms": ("госзакуп", "тендер", "бюджет", "аудит", "вап", "расходы ведомств", "расходы регионов"),
        "support_terms": ("субсид", "контракт", "закуп", "финанс", "вознагражден", "нацкомпан"),
    },
    {
        "slug": "land-and-agro",
        "title": "Земля и агробизнес",
        "description": "Земельные ресурсы, латифундисты, пастбища, фермеры и аграрная политика по регионам.",
        "strong_terms": ("земл", "латифунд", "пастбищ", "фермер", "сельхоз", "агро"),
        "support_terms": ("орошен", "саранч", "выпас", "урож", "мсх", "скот"),
    },
    {
        "slug": "courts-and-siloviki",
        "title": "Суды и силовики",
        "description": "Судебные процессы, прокурорский надзор, МВД, КНБ и громкие уголовные дела.",
        "strong_terms": ("прокуратур", "суд", "мвд", "кнб", "полиц", "приговор"),
        "support_terms": ("задерж", "экстрад", "террор", "арест", "следств", "подозрев"),
    },
    {
        "slug": "ecology-and-resources",
        "title": "Экология и ресурсы",
        "description": "Вода, воздух, отходы, природные ресурсы и экологические последствия решений государства и бизнеса.",
        "strong_terms": ("эколог", "загряз", "воздух", "вода", "полигон", "отход"),
        "support_terms": ("нефть", "рудник", "уран", "сайгак", "река", "канал"),
    },
    {
        "slug": "assets-and-elites",
        "title": "Активы и элиты",
        "description": "Недвижимость, корпоративные активы, семьи элит и крупные интересы вокруг государства.",
        "strong_terms": ("актив", "недвижим", "олигарх", "самрук", "казатомпром", "назарбаев"),
        "support_terms": ("кулибаев", "масимов", "особняк", "пентхаус", "владел", "бизнес-центр"),
    },
)

SERIES_DEFINITIONS = (
    {
        "slug": "latifundisty-kazakhstana",
        "title": "Латифундисты Казахстана",
        "description": "Длинная серия ФБРК о крупнейших землевладельцах, изъятиях и реальном балансе сельхозземель по регионам.",
        "match_terms": ("латифундисты казахстана",),
    },
    {
        "slug": "rashody-vedomstv-2024",
        "title": "Расходы ведомств - 2024",
        "description": "Разбор бюджетов министерств и ведомств: на что уходили деньги в 2024 году.",
        "match_terms": ("расходы ведомств - 2024", "расходы ведомств – 2024"),
    },
    {
        "slug": "rashody-regionov-2024",
        "title": "Расходы регионов - 2024",
        "description": "Серия о тратах региональных бюджетов и приоритетах областных администраций.",
        "match_terms": ("расходы регионов - 2024", "расходы регионов – 2024"),
    },
    {
        "slug": "top-menedzhery-nackompaniy",
        "title": "Вознаграждения топ-менеджеров нацкомпаний",
        "description": "Цикл о зарплатах, бонусах и управленческих вознаграждениях в крупнейших компаниях с госучастием.",
        "match_terms": ("впечатляющие вознаграждения топ-менеджеров нацкомпаний",),
    },
    {
        "slug": "dezinsekciya-2025",
        "title": "Дезинсекция-2025",
        "description": "Региональная серия ФБРК о химических и биологических обработках, их подрядчиках и последствиях.",
        "match_terms": ("дезинсекция-2025",),
    },
)

REGION_DEFINITIONS = (
    {
        "slug": "astana",
        "title": "Астана",
        "description": "Материалы о столице, республиканских органах и событиях в Астане.",
        "aliases": ("астана",),
    },
    {
        "slug": "almaty",
        "title": "Алматы",
        "description": "Городские и республиканские сюжеты, связанные с Алматы.",
        "aliases": ("алматы",),
    },
    {
        "slug": "shymkent",
        "title": "Шымкент",
        "description": "Материалы о Шымкенте и локальных кейсах юга страны.",
        "aliases": ("шымкент",),
    },
    {
        "slug": "akmolinskaya-oblast",
        "title": "Акмолинская область",
        "description": "Региональные публикации по Акмолинской области и близлежащим городам.",
        "aliases": ("акмолинская область", "кокшетау", "степногорск"),
    },
    {
        "slug": "almatinskaya-oblast",
        "title": "Алматинская область",
        "description": "Материалы о районах и инфраструктуре Алматинской области.",
        "aliases": ("алматинская область",),
    },
    {
        "slug": "aktyubinskaya-oblast",
        "title": "Актюбинская область",
        "description": "Публикации по Актюбинской области и Актобе.",
        "aliases": ("актюбинская область", "актобе"),
    },
    {
        "slug": "atyrauskaya-oblast",
        "title": "Атырауская область",
        "description": "Материалы по Атырауской области и нефтегазовым кейсам региона.",
        "aliases": ("атырауская область", "атырау"),
    },
    {
        "slug": "vostochno-kazakhstanskaya-oblast",
        "title": "Восточно-Казахстанская область",
        "description": "Сюжеты по Восточному Казахстану и окрестностям Усть-Каменогорска.",
        "aliases": ("восточно-казахстанская область", "вко", "восточный казахстан", "усть-каменогорск"),
    },
    {
        "slug": "zhambylskaya-oblast",
        "title": "Жамбылская область",
        "description": "Публикации по Жамбылской области и Таразу.",
        "aliases": ("жамбылская область", "тараз"),
    },
    {
        "slug": "zapadno-kazakhstanskaya-oblast",
        "title": "Западно-Казахстанская область",
        "description": "Материалы по Западно-Казахстанской области и Уральску.",
        "aliases": ("западно-казахстанская область", "уральск"),
    },
    {
        "slug": "karagandinskaya-oblast",
        "title": "Карагандинская область",
        "description": "Публикации о Карагандинской области, Караганде, Темиртау и Балхаше.",
        "aliases": ("карагандинская область", "караганда", "темиртау", "балхаш"),
    },
    {
        "slug": "kostanayskaya-oblast",
        "title": "Костанайская область",
        "description": "Сюжеты по Костанайской области и Костанаю.",
        "aliases": ("костанайская область", "костанай"),
    },
    {
        "slug": "kyzylordinskaya-oblast",
        "title": "Кызылординская область",
        "description": "Материалы по Кызылординской области и Кызылорде.",
        "aliases": ("кызылординская область", "кызылорда"),
    },
    {
        "slug": "mangistauskaya-oblast",
        "title": "Мангистауская область",
        "description": "Публикации по Мангистауской области и Актау.",
        "aliases": ("мангистауская область", "актау"),
    },
    {
        "slug": "oblast-abay",
        "title": "Область Абай",
        "description": "Материалы по области Абай и Семею.",
        "aliases": ("область абай", "область абай", "абайская область", "область абай", "семей", "абай"),
    },
    {
        "slug": "pavlodarskaya-oblast",
        "title": "Павлодарская область",
        "description": "Публикации по Павлодарской области и Павлодару.",
        "aliases": ("павлодарская область", "павлодар"),
    },
    {
        "slug": "severo-kazakhstanskaya-oblast",
        "title": "Северо-Казахстанская область",
        "description": "Сюжеты по Северо-Казахстанской области и Петропавловску.",
        "aliases": ("северо-казахстанская область", "петропавловск"),
    },
    {
        "slug": "turkestanskaya-oblast",
        "title": "Туркестанская область",
        "description": "Материалы по Туркестанской области и Туркестану.",
        "aliases": ("туркестанская область", "туркестан", "арысь"),
    },
    {
        "slug": "ulytauskaya-oblast",
        "title": "Улытауская область",
        "description": "Публикации по Улытауской области и Жезказгану.",
        "aliases": ("улытауская область", "область улытау", "улытау", "ұлытау", "жезказган"),
    },
    {
        "slug": "zhetysu-oblast",
        "title": "Жетысуская область",
        "description": "Материалы по области Жетысу и Талдыкоргану.",
        "aliases": (
            "жетысу",
            "жетысуская область",
            "область жетысу",
            "жетісу область",
            "жетісуская область",
            "жетiсу область",
            "талдыкорган",
        ),
    },
)

EDITORIAL_STATUS_DEFINITIONS = (
    {
        "slug": "follow-up",
        "title": "Продолжение темы",
        "description": "Материал развивает уже идущую редакционную линию и добавляет новое звено в историю.",
    },
    {
        "slug": "state-response",
        "title": "Ответ госоргана",
        "description": "Публикация с официальной реакцией ведомства, акимата или другого публичного органа.",
    },
    {
        "slug": "court-stage",
        "title": "Судебный процесс",
        "description": "Материал о судебном этапе: заседании, ходатайстве, решении или приговоре.",
    },
    {
        "slug": "archive-context",
        "title": "Контекст",
        "description": "Фоновый или архивный материал, который помогает удержать длинную тему в одном контуре.",
    },
)

EDITORIAL_LABEL_DEFINITIONS = (
    {
        "slug": "documents",
        "title": "Документы",
        "description": "Опора на письма, договоры, ответы ведомств и другие первичные документы.",
    },
    {
        "slug": "data",
        "title": "Данные",
        "description": "Материал строится на цифрах, таблицах, выборках или статистике.",
    },
    {
        "slug": "monitoring",
        "title": "Мониторинг",
        "description": "Редакция наблюдает за развитием кейса и собирает новые эпизоды в одну линию.",
    },
    {
        "slug": "explain",
        "title": "Разбор",
        "description": "Материал помогает объяснить механику сюжета, участников и последствия.",
    },
)

RESONANCE = {
    "slug": "resonance",
    "title": "Резонанс",
    "description": "Важные материалы редакции.",
    "url": "/resonance.html",
}

OVERRIDE_PREFIX = "editorial_hubs.article."
PAGE_PREFIX = "editorial_hubs.page."
HOME_PREFIX = "editorial_hubs.home."

HUB_PAGE_DEFAULTS = {
    "topics": {
        "eyebrow": "Навигация",
        "title": "Темы",
        "description": "Самые важные редакционные линии ФБРК, через которые удобнее заходить в архив и разбирать большие сюжеты по слоям.",
        "seo_title": "Темы",
        "seo_description": "Ключевые темы ФБРК: коррупция, бюджет, земля, суды, экология и активы элит.",
    },
    "regions": {
        "eyebrow": "География",
        "title": "Регионы",
        "description": "Материалы по городам и областям.",
        "seo_title": "Регионы",
        "seo_description": "Региональные хабы ФБРК: Астана, Алматы, Шымкент и ключевые области Казахстана.",
    },
    "series": {
        "eyebrow": "Редакционный формат",
        "title": "Серии",
        "description": "Редакционные сюжеты в развитии.",
        "seo_title": "Серии",
        "seo_description": "Редакционные серии ФБРК: длительные расследовательские и дата-циклы, собранные в понятные линии.",
    },
    "resonance": {
        "eyebrow": "Подборка",
        "title": "Резонанс",
        "description": "Важные материалы редакции.",
        "seo_title": "Резонанс",
        "seo_description": "Подборка материалов ФБРК с повышенной редакционной значимостью.",
    },
}

HOME_BLOCK_DEFAULTS = {
    "resonance": {
        "eyebrow": "Выбор редакции",
        "title": "Резонанс",
        "description": "Что открыть в первую очередь.",
        "link_label": "Вся подборка",
    },
    "regions": {
        "eyebrow": "География",
        "title": "По регионам",
        "description": "Материалы по городам и областям.",
        "link_label": "Все регионы",
    },
}

_TOPIC_BY_SLUG = {item["slug"]: item for item in TOPIC_DEFINITIONS}
_REGION_BY_SLUG = {item["slug"]: item for item in REGION_DEFINITIONS}
_SERIES_BY_SLUG = {item["slug"]: item for item in SERIES_DEFINITIONS}
_STATUS_BY_SLUG = {item["slug"]: item for item in EDITORIAL_STATUS_DEFINITIONS}
_LABEL_BY_SLUG = {item["slug"]: item for item in EDITORIAL_LABEL_DEFINITIONS}


def _string(value: object) -> str:
    return str(value or "").strip()


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", _string(value).casefold()).strip()


_REGION_ALIAS_TO_SLUG = {
    _norm(alias): item["slug"]
    for item in REGION_DEFINITIONS
    for alias in (item["title"], *item.get("aliases", ()))
}


def topic_options() -> list[dict]:
    return [
        {
            "slug": item["slug"],
            "title": item["title"],
            "description": item["description"],
        }
        for item in TOPIC_DEFINITIONS
    ]


def series_options() -> list[dict]:
    return [
        {
            "slug": item["slug"],
            "title": item["title"],
            "description": item["description"],
        }
        for item in SERIES_DEFINITIONS
    ]


def region_options() -> list[dict]:
    return [
        {
            "slug": item["slug"],
            "title": item["title"],
            "description": item["description"],
        }
        for item in REGION_DEFINITIONS
    ]


def status_options() -> list[dict]:
    return [
        {
            "slug": item["slug"],
            "title": item["title"],
            "description": item["description"],
        }
        for item in EDITORIAL_STATUS_DEFINITIONS
    ]


def label_options() -> list[dict]:
    return [
        {
            "slug": item["slug"],
            "title": item["title"],
            "description": item["description"],
        }
        for item in EDITORIAL_LABEL_DEFINITIONS
    ]


def empty_override() -> dict:
    return {
        "topic_slugs": [],
        "region_slug": "",
        "series_slug": "",
        "resonance": None,
        "status_slug": "",
        "label_slugs": [],
    }


def _ensure_settings_schema(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def hub_page_keys() -> tuple[str, ...]:
    return ("eyebrow", "title", "description", "seo_title", "seo_description")


def home_block_keys() -> tuple[str, ...]:
    return ("eyebrow", "title", "description", "link_label")


def load_hub_pages(conn: Connection) -> dict[str, dict[str, str]]:
    _ensure_settings_schema(conn)
    pages = {
        kind: dict(values)
        for kind, values in HUB_PAGE_DEFAULTS.items()
    }
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE ?",
        (f"{PAGE_PREFIX}%",),
    ).fetchall()
    for row in rows:
        key = str(row["key"] if hasattr(row, "keys") else row[0])
        parts = key.removeprefix(PAGE_PREFIX).split(".", 1)
        if len(parts) != 2:
            continue
        kind, field = parts
        if kind not in pages or field not in hub_page_keys():
            continue
        value = str(row["value"] if hasattr(row, "keys") else row[1]).strip()
        if value:
            pages[kind][field] = value
    return pages


def load_homepage_blocks(conn: Connection) -> dict[str, dict[str, str]]:
    _ensure_settings_schema(conn)
    blocks = {
        kind: dict(values)
        for kind, values in HOME_BLOCK_DEFAULTS.items()
    }
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE ?",
        (f"{HOME_PREFIX}%",),
    ).fetchall()
    for row in rows:
        key = str(row["key"] if hasattr(row, "keys") else row[0])
        parts = key.removeprefix(HOME_PREFIX).split(".", 1)
        if len(parts) != 2:
            continue
        kind, field = parts
        if kind not in blocks or field not in home_block_keys():
            continue
        value = str(row["value"] if hasattr(row, "keys") else row[1]).strip()
        if value:
            blocks[kind][field] = value
    return blocks


def save_hub_pages(conn: Connection, values: dict[str, object]) -> list[str]:
    _ensure_settings_schema(conn)
    current = load_hub_pages(conn)
    changed: list[str] = []
    for kind, defaults in HUB_PAGE_DEFAULTS.items():
        for field in hub_page_keys():
            form_key = f"page_{kind}_{field}"
            value = str(values.get(form_key, defaults[field]) or "").strip()
            if not value:
                value = defaults[field]
            if value != current[kind][field]:
                changed.append(f"{kind}.{field}")
            conn.execute(
                """
                INSERT INTO settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE
                SET value = excluded.value, updated_at = datetime('now')
                """,
                (f"{PAGE_PREFIX}{kind}.{field}", value),
            )
    return changed


def save_homepage_blocks(conn: Connection, values: dict[str, object]) -> list[str]:
    _ensure_settings_schema(conn)
    current = load_homepage_blocks(conn)
    changed: list[str] = []
    for kind, defaults in HOME_BLOCK_DEFAULTS.items():
        for field in home_block_keys():
            form_key = f"home_{kind}_{field}"
            value = str(values.get(form_key, defaults[field]) or "").strip()
            if not value:
                value = defaults[field]
            if value != current[kind][field]:
                changed.append(f"{kind}.{field}")
            conn.execute(
                """
                INSERT INTO settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE
                SET value = excluded.value, updated_at = datetime('now')
                """,
                (f"{HOME_PREFIX}{kind}.{field}", value),
            )
    return changed


def _normalize_resonance(value: object) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = _norm(value)
    if text in {"yes", "true", "1", "on", "force"}:
        return True
    if text in {"no", "false", "0", "off"}:
        return False
    return None


def normalize_override(value: object) -> dict:
    if not isinstance(value, dict):
        return empty_override()

    raw_topics = value.get("topic_slugs")
    if not isinstance(raw_topics, list):
        raw_topics = value.get("topics")
    topic_slugs: list[str] = []
    seen_topics: set[str] = set()
    for item in raw_topics or []:
        slug = _string(item)
        if not slug or slug not in _TOPIC_BY_SLUG or slug in seen_topics:
            continue
        topic_slugs.append(slug)
        seen_topics.add(slug)

    region_slug = _string(value.get("region_slug") or value.get("region"))
    if region_slug not in _REGION_BY_SLUG:
        region_slug = ""

    series_slug = _string(value.get("series_slug") or value.get("series"))
    if series_slug not in _SERIES_BY_SLUG:
        series_slug = ""

    status_slug = _string(value.get("status_slug") or value.get("editorial_status") or value.get("status"))
    if status_slug not in _STATUS_BY_SLUG:
        status_slug = ""

    raw_labels = value.get("label_slugs")
    if raw_labels is None:
        raw_labels = value.get("editorial_labels")
    if raw_labels is None:
        raw_labels = value.get("labels")
    if isinstance(raw_labels, str):
        raw_labels = [part.strip() for part in raw_labels.split(",")]
    label_slugs: list[str] = []
    seen_labels: set[str] = set()
    for item in raw_labels or []:
        slug = _string(item)
        if not slug or slug not in _LABEL_BY_SLUG or slug in seen_labels:
            continue
        label_slugs.append(slug)
        seen_labels.add(slug)

    return {
        "topic_slugs": topic_slugs,
        "region_slug": region_slug,
        "series_slug": series_slug,
        "resonance": _normalize_resonance(value.get("resonance")),
        "status_slug": status_slug,
        "label_slugs": label_slugs,
    }


def has_override(value: object) -> bool:
    normalized = normalize_override(value)
    return bool(
        normalized["topic_slugs"]
        or normalized["region_slug"]
        or normalized["series_slug"]
        or normalized["resonance"] is not None
        or normalized["status_slug"]
        or normalized["label_slugs"]
    )


def load_editorial_override(conn: Connection, article_id: str) -> dict:
    key = _string(article_id)
    if not key:
        return empty_override()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?",
        (f"{OVERRIDE_PREFIX}{key}",),
    ).fetchone()
    if not row:
        return empty_override()
    try:
        raw = json.loads(row["value"] if hasattr(row, "keys") else row[0])
    except (TypeError, ValueError, json.JSONDecodeError):
        return empty_override()
    return normalize_override(raw)


def load_editorial_overrides(conn: Connection) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE ?",
        (f"{OVERRIDE_PREFIX}%",),
    ).fetchall()
    overrides: dict[str, dict] = {}
    for row in rows:
        key = str(row["key"] if hasattr(row, "keys") else row[0])
        try:
            raw = json.loads(row["value"] if hasattr(row, "keys") else row[1])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        article_id = key.removeprefix(OVERRIDE_PREFIX)
        overrides[article_id] = normalize_override(raw)
    return overrides


def save_editorial_override(conn: Connection, article_id: str, value: object) -> dict:
    key = _string(article_id)
    normalized = normalize_override(value)
    if not key:
        return normalized
    if not has_override(normalized):
        conn.execute(
            "DELETE FROM settings WHERE key = ?",
            (f"{OVERRIDE_PREFIX}{key}",),
        )
        return normalized
    conn.execute(
        """
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE
        SET value = excluded.value, updated_at = datetime('now')
        """,
        (
            f"{OVERRIDE_PREFIX}{key}",
            json.dumps(normalized, ensure_ascii=False),
        ),
    )
    return normalized


def _topic_ref(slug: str) -> dict | None:
    topic = _TOPIC_BY_SLUG.get(_string(slug))
    if not topic:
        return None
    return {
        "slug": topic["slug"],
        "title": topic["title"],
        "description": topic["description"],
        "url": f"/archive.html?topic={topic['slug']}",
    }


def _series_ref(slug: str) -> dict | None:
    series = _SERIES_BY_SLUG.get(_string(slug))
    if not series:
        return None
    return {
        "slug": series["slug"],
        "title": series["title"],
        "description": series["description"],
        "url": f"/archive.html?series={series['slug']}",
    }


def _region_ref(slug: str) -> dict | None:
    region = _REGION_BY_SLUG.get(_string(slug))
    if not region:
        return None
    return {
        "slug": region["slug"],
        "title": region["title"],
        "description": region["description"],
        "url": f"/archive.html?region={region['slug']}",
    }


def _status_ref(slug: str) -> dict | None:
    status = _STATUS_BY_SLUG.get(_string(slug))
    if not status:
        return None
    return {
        "slug": status["slug"],
        "title": status["title"],
        "description": status["description"],
        "url": f"/archive.html?status={status['slug']}",
    }


def _label_ref(slug: str) -> dict | None:
    label = _LABEL_BY_SLUG.get(_string(slug))
    if not label:
        return None
    return {
        "slug": label["slug"],
        "title": label["title"],
        "description": label["description"],
        "url": f"/archive.html?label={label['slug']}",
    }


def apply_override(article: dict, override: object) -> dict:
    normalized = normalize_override(override)
    if not has_override(normalized):
        return dict(article)

    updated = dict(article)
    if normalized["topic_slugs"]:
        updated["topics"] = [
            item for item in (_topic_ref(slug) for slug in normalized["topic_slugs"])
            if item
        ]
    if normalized["region_slug"]:
        region = _region_ref(normalized["region_slug"])
        if region:
            updated["regionRef"] = region
            updated["region"] = region["title"]
    if normalized["series_slug"]:
        series = _series_ref(normalized["series_slug"])
        if series:
            updated["series"] = series
    if normalized["resonance"] is True:
        updated["resonance"] = True
    elif normalized["resonance"] is False:
        updated.pop("resonance", None)
    if normalized["status_slug"]:
        status = _status_ref(normalized["status_slug"])
        if status:
            updated["editorialStatus"] = status
    if normalized["label_slugs"]:
        updated["editorialLabels"] = [
            item for item in (_label_ref(slug) for slug in normalized["label_slugs"])
            if item
        ]
    return updated


def _article_blob(article: dict, auto_tags: Iterable[str] | None = None, entities: Iterable[dict] | None = None) -> str:
    parts: list[str] = [
        _string(article.get("title")),
        _string(article.get("dek")),
        _string(article.get("slug")),
        _string(article.get("category")),
        _string(article.get("categoryLabel")),
        _string(article.get("region") or article.get("_meta_region")),
    ]
    parts.extend(_string(tag) for tag in (article.get("tags") or []))
    parts.extend(_string(tag) for tag in (auto_tags or []))
    for item in entities or []:
        if not isinstance(item, dict):
            continue
        parts.append(_string(item.get("name")))
    return _norm(" ".join(part for part in parts if part))


def _topic_score(topic: dict, text: str) -> int:
    strong_hits = sum(1 for term in topic["strong_terms"] if term in text)
    support_hits = sum(1 for term in topic["support_terms"] if term in text)
    if strong_hits == 0 and strong_hits + support_hits < 2:
        return 0
    return strong_hits * 4 + support_hits


def classify_topics(
    article: dict,
    *,
    auto_tags: Iterable[str] | None = None,
    entities: Iterable[dict] | None = None,
    limit: int = 3,
) -> list[dict]:
    text = _article_blob(article, auto_tags=auto_tags, entities=entities)
    scored: list[tuple[int, int, dict]] = []
    for idx, topic in enumerate(TOPIC_DEFINITIONS):
        score = _topic_score(topic, text)
        if score <= 0:
            continue
        scored.append((score, -idx, topic))
    scored.sort(reverse=True)
    return [
        {
            "slug": topic["slug"],
            "title": topic["title"],
            "description": topic["description"],
            "url": f"/archive.html?topic={topic['slug']}",
        }
        for _, __, topic in scored[: max(0, int(limit))]
    ]


def classify_series(article: dict) -> dict | None:
    text = _article_blob(article)
    for series in SERIES_DEFINITIONS:
        if any(term in text for term in series["match_terms"]):
            return {
                "slug": series["slug"],
                "title": series["title"],
                "description": series["description"],
                "url": f"/archive.html?series={series['slug']}",
            }
    return None


def classify_region(article: dict) -> dict | None:
    raw = _norm(article.get("region") or article.get("_meta_region"))
    if not raw:
        return None
    slug = _REGION_ALIAS_TO_SLUG.get(raw)
    if not slug:
        return None
    return _region_ref(slug)


def is_resonance(article: dict) -> bool:
    try:
        return int(article.get("importance") or article.get("_meta_importance") or 0) >= 4
    except (TypeError, ValueError):
        return False


def annotate_article(
    article: dict,
    *,
    auto_tags: Iterable[str] | None = None,
    entities: Iterable[dict] | None = None,
    override: object = None,
) -> dict:
    topics = classify_topics(article, auto_tags=auto_tags, entities=entities)
    region = classify_region(article)
    series = classify_series(article)
    annotated = dict(article)
    if topics:
        annotated["topics"] = topics
    if region:
        annotated["regionRef"] = region
        if not _string(annotated.get("region")):
            annotated["region"] = region["title"]
    if series:
        annotated["series"] = series
    if is_resonance(article):
        annotated["resonance"] = True
    return apply_override(annotated, override)


def _preview(article: dict) -> dict:
    return {
        "slug": _string(article.get("slug") or article.get("id")),
        "title": _string(article.get("title")),
        "date": _string(article.get("date")),
        "dateIso": _string(article.get("dateIso")),
        "image": _string(article.get("image")),
        "category": _string(article.get("category")),
        "categoryLabel": _string(article.get("categoryLabel")),
    }


def build_catalog(articles: list[dict]) -> dict:
    topics: list[dict] = []
    for topic in TOPIC_DEFINITIONS:
        matches = [article for article in articles if any(item.get("slug") == topic["slug"] for item in article.get("topics") or [])]
        if not matches:
            continue
        topics.append(
            {
                "slug": topic["slug"],
                "title": topic["title"],
                "description": topic["description"],
                "count": len(matches),
                "url": f"/archive.html?topic={topic['slug']}",
                "latest": [_preview(article) for article in matches[:3]],
            }
        )

    series_items: list[dict] = []
    for series in SERIES_DEFINITIONS:
        matches = [article for article in articles if (article.get("series") or {}).get("slug") == series["slug"]]
        if not matches:
            continue
        series_items.append(
            {
                "slug": series["slug"],
                "title": series["title"],
                "description": series["description"],
                "count": len(matches),
                "url": f"/archive.html?series={series['slug']}",
                "latest": [_preview(article) for article in matches[:3]],
            }
        )

    regions: list[dict] = []
    for region in REGION_DEFINITIONS:
        matches = [article for article in articles if ((article.get("regionRef") or {}).get("slug") == region["slug"])]
        if not matches:
            continue
        regions.append(
            {
                "slug": region["slug"],
                "title": region["title"],
                "description": region["description"],
                "count": len(matches),
                "url": f"/archive.html?region={region['slug']}",
                "latest": [_preview(article) for article in matches[:3]],
            }
        )

    resonance_count = sum(1 for article in articles if article.get("resonance"))
    return {
        "topics": topics,
        "regions": regions,
        "series": series_items,
        "resonance": {**RESONANCE, "count": resonance_count},
    }


def _article_region_slug(article: dict) -> str:
    region_ref = article.get("regionRef") or {}
    if isinstance(region_ref, dict):
        slug = _string(region_ref.get("slug"))
        if slug:
            return slug
    raw = _norm(article.get("region"))
    return _string(_REGION_ALIAS_TO_SLUG.get(raw))


def _article_tags(article: dict) -> set[str]:
    return {_norm(tag) for tag in article.get("tags") or [] if _string(tag)}


def pick_related_articles(target: dict, articles: list[dict], limit: int = 3) -> list[dict]:
    target_slug = _string(target.get("slug") or target.get("id"))
    target_topics = {item.get("slug") for item in target.get("topics") or [] if item.get("slug")}
    target_series = _string((target.get("series") or {}).get("slug"))
    target_tags = _article_tags(target)
    target_category = _string(target.get("category"))
    target_region = _article_region_slug(target)

    scored: list[tuple[float, str, dict]] = []
    fallback: list[tuple[str, dict]] = []
    for article in articles:
        slug = _string(article.get("slug") or article.get("id"))
        if not slug or slug == target_slug:
            continue

        score = 0.0
        article_topics = {item.get("slug") for item in article.get("topics") or [] if item.get("slug")}
        article_series = _string((article.get("series") or {}).get("slug"))
        article_tags = _article_tags(article)
        article_region = _article_region_slug(article)

        if target_series and article_series == target_series:
            score += 10
        if target_topics:
            score += 4 * len(target_topics & article_topics)
        if target_tags:
            score += 2 * len(target_tags & article_tags)
        if target_category and _string(article.get("category")) == target_category:
            score += 1.5
        if target_region and article_region and article_region == target_region:
            score += 1
        if article.get("image"):
            score += 0.25

        preview = _preview(article)
        if score > 0:
            scored.append((score, _string(article.get("dateIso")), preview))
        elif target_category and _string(article.get("category")) == target_category:
            fallback.append((_string(article.get("dateIso")), preview))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    picked = [item for _, __, item in scored[: max(0, int(limit))]]
    if len(picked) >= limit:
        return picked[:limit]

    seen = {item["slug"] for item in picked}
    fallback.sort(key=lambda item: item[0], reverse=True)
    for _, preview in fallback:
        if preview["slug"] in seen:
            continue
        picked.append(preview)
        seen.add(preview["slug"])
        if len(picked) >= limit:
            break
    return picked[:limit]
