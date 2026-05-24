"""Publish articles from SQLite -> public js/data.js + sitemap.xml + feed.xml."""
from __future__ import annotations

import html
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .db import db, row_to_article


SITE_URL = (os.environ.get("FBRK_SITE_URL") or "https://fbrk.qdev.run").rstrip("/")

HEADER = """// ============================================================
// ФБРК — данные статей
// Автоматически сгенерировано админкой. Не редактировать руками.
// ============================================================

const FBRK_DATA =
"""

SITE_META = {
    "site": {
        "name": "ФБРК",
        "fullName": "Фонд-бюро расследования коррупции",
        "tagline": "Независимые расследования · Казахстан",
        "about": "Фонд-бюро расследования коррупции (ФБРК) — сетевое издание, "
                 "свидетельство о регистрации СМИ № KZ83VPY00075165 от 21.08.2023. "
                 "Мы делаем журналистские расследования, новости, публикуем информацию "
                 "о борьбе с коррупцией в Казахстане.",
        "mission": "Наши материалы содержат досье на олигархов, списки земель латифундистов, "
                   "информацию о бизнесе семей чиновников и многое другое.",
        "telegram": "https://t.me/fund_kz_bot",
        "telegramName": "@fund_kz_bot",
        "youtube": "https://www.youtube.com/@fbrk_news",
        "registration": "KZ83VPY00075165 от 21.08.2023",
    },
    "tags": [
        "Коррупция", "Госзакупки", "Недвижимость чиновников", "Олигархи",
        "Силовые структуры", "Нефтегаз", "ЕНПФ", "Назарбаев", "КНБ",
        "Уголовные дела", "Экология", "Агробизнес", "КТЖ", "Мусин",
    ],
}


def _json_list(raw: object) -> list:
    try:
        value = json.loads(str(raw or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def _unique_strings(*groups: list, limit: int = 16) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group or []:
            value = str(item or "").strip()
            key = value.casefold()
            if not value or key in seen:
                continue
            out.append(value[:64])
            seen.add(key)
            if len(out) >= limit:
                return out
    return out


def _derive_image_meta(url: str) -> dict[str, object]:
    """Normalize image display metadata for public payloads."""
    if not url:
        return {
            "imageKind": "other",
            "imageSource": "",
            "imageHasRealPerson": False,
        }

    lowered = str(url).lower().strip()
    if "chatgpt" in lowered or "midjourney" in lowered or "dall" in lowered or "stable" in lowered or "openai" in lowered:
        kind = "ai"
    else:
        kind = "photo"

    if lowered.startswith("/"):
        if "/img/covers/" in lowered:
            source = "cover"
        elif "/img/" in lowered:
            source = "upload"
        else:
            source = "internal"
    elif lowered.startswith("data:"):
        source = "inline"
    else:
        source = "external"

    return {
        "imageKind": kind,
        "imageSource": source,
        "imageHasRealPerson": False,
    }


def _manual_public_tags(
    raw: list,
    auto_raw: list,
    limit: int = 16,
    exclude_names: set[str] | None = None,
) -> list[str]:
    auto_names = {str(item or "").strip().casefold() for item in auto_raw or [] if str(item or "").strip()}
    excluded = {str(item or "").strip().casefold() for item in (exclude_names or set()) if str(item or "").strip()}
    out: list[str] = []
    seen: set[str] = set()
    for item in raw or []:
        value = str(item or "").strip()
        key = value.casefold()
        if not value or key in seen or key in auto_names or key in excluded:
            continue
        out.append(value[:64])
        seen.add(key)
        if len(out) >= limit:
            break
    return out


PUBLIC_ENTITY_TYPES = {"person", "org", "gov", "place", "law", "case", "money"}


def _hidden_entity_names(raw: list) -> set[str]:
    out: set[str] = set()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        kind = str(item.get("type") or "other").strip().lower()
        if name and kind not in PUBLIC_ENTITY_TYPES:
            out.add(name.casefold())
    return out


def _public_entities(raw: list, limit: int = 32, exclude_names: set[str] | None = None) -> list[dict]:
    excluded = {str(x or "").strip().casefold() for x in (exclude_names or set()) if str(x or "").strip()}
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        kind = str(item.get("type") or "other").strip().lower()
        if kind not in PUBLIC_ENTITY_TYPES:
            continue
        if name.casefold() in excluded:
            continue
        key = f"{kind}:{name.casefold()}"
        if key in seen:
            continue
        out.append({"name": name[:80], "type": kind})
        seen.add(key)
        if len(out) >= limit:
            break
    return out


def _load_articles() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT a.*, "
            "m.importance AS _meta_importance, "
            "m.sentiment AS _meta_sentiment, "
            "m.region AS _meta_region, "
            "m.summary_short AS _meta_summary_short, "
            "m.key_points AS _meta_key_points, "
            "m.entities_json AS _meta_entities_json, "
            "m.tags_auto AS _meta_tags_auto "
            "FROM articles a LEFT JOIN article_meta m ON m.article_id=a.id "
            "WHERE a.published=1 ORDER BY a.date_iso DESC, a.created_at DESC"
        ).fetchall()
    out = []
    for r in rows:
        art = row_to_article(r)
        # stash meta fields for _public_shape
        try:
            art["_meta_importance"] = r["_meta_importance"]
            art["_meta_sentiment"] = r["_meta_sentiment"]
            art["_meta_region"] = r["_meta_region"]
            art["_meta_summary_short"] = r["_meta_summary_short"]
            art["_meta_key_points"] = r["_meta_key_points"]
            art["_meta_entities_json"] = r["_meta_entities_json"]
            art["_meta_tags_auto"] = r["_meta_tags_auto"]
        except Exception:
            pass
        out.append(art)
    return out


def _public_shape(a: dict) -> dict:
    """Strip admin-only fields; keep ONLY listing-card fields.
    Full body (sections), author, source live on SSR /a/<slug> page —
    not in client-side data.js (saves ~95% bandwidth)."""
    shape = {
        "id": a["id"],
        "slug": a["slug"],
        "title": a["title"],
        "dek": a["dek"],
        "date": a["date"],
        "dateIso": a["dateIso"],
        "category": a["category"],
        "categoryLabel": a["categoryLabel"],
        "image": a["image"],
        "tags": a["tags"],
        **({"featured": True} if a.get("featured") else {}),
    }

    source_override = str(a.get("imageSource") or "").strip()
    shape["imageSource"] = source_override or _derive_image_meta(a.get("image") or "")["imageSource"]

    kind_override = str(a.get("imageKind") or "").strip().lower()
    shape["imageKind"] = kind_override or _derive_image_meta(a.get("image") or "")["imageKind"]

    has_person_override = a.get("imageHasRealPerson")
    if isinstance(has_person_override, bool):
        shape["imageHasRealPerson"] = bool(has_person_override)
    else:
        shape["imageHasRealPerson"] = bool(_derive_image_meta(a.get("image") or "").get("imageHasRealPerson"))

    imp = a.get("_meta_importance")
    if imp is not None and imp != 0:
        shape["importance"] = int(imp)
    sent = a.get("_meta_sentiment")
    if sent:
        shape["sentiment"] = sent
    reg = a.get("_meta_region")
    if reg:
        shape["region"] = reg
    return shape


def _article_full_shape(a: dict) -> dict:
    """Public article-page payload for split static hosting.

    This intentionally keeps only public article fields and rendered sections:
    no admin body_json, no author names, no private editor metadata.
    """
    shape = _public_shape(a)
    shape["sections"] = a.get("sections") or []
    raw_entities = _json_list(a.get("_meta_entities_json"))
    manual_tags = _manual_public_tags(
        shape.get("tags") or [],
        _json_list(a.get("_meta_tags_auto")),
        limit=16,
        exclude_names=_hidden_entity_names(raw_entities),
    )
    entities = _public_entities(
        raw_entities,
        limit=32,
    )
    entity_names = {str(e.get("name") or "").casefold() for e in entities}
    shape["tags"] = [
        tag for tag in manual_tags
        if tag.casefold() not in entity_names
    ]
    summary_short = str(a.get("_meta_summary_short") or "").strip()
    if summary_short:
        shape["summaryShort"] = summary_short[:240]
    key_points = _unique_strings(_json_list(a.get("_meta_key_points")), limit=5)
    if key_points:
        shape["keyPoints"] = key_points
    if entities:
        shape["entities"] = entities
    source = (a.get("source") or "").strip()
    if source and "fbrk.kz" not in source:
        shape["source"] = source
    return shape


def _write_sitemap(articles: list[dict], web_root: Path) -> None:
    """Generate sitemap.xml with static pages + every article."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls: list[tuple[str, str, str, str]] = [
        # (loc, lastmod, changefreq, priority)
        (f"{SITE_URL}/", now, "hourly", "1.0"),
        (f"{SITE_URL}/archive.html", now, "daily", "0.9"),
        (f"{SITE_URL}/archive.html?cat=investigation", now, "daily", "0.8"),
        (f"{SITE_URL}/archive.html?cat=news", now, "daily", "0.8"),
        (f"{SITE_URL}/about.html", now, "monthly", "0.5"),
    ]
    for a in articles:
        iso = (a.get("dateIso") or now)
        slug_or_id = a.get("slug") or a["id"]
        urls.append((f"{SITE_URL}/a/{slug_or_id}", iso, "weekly", "0.7"))
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, cf, pr in urls:
        body.append("  <url>")
        body.append(f"    <loc>{html.escape(loc)}</loc>")
        body.append(f"    <lastmod>{lastmod}</lastmod>")
        body.append(f"    <changefreq>{cf}</changefreq>")
        body.append(f"    <priority>{pr}</priority>")
        body.append("  </url>")
    body.append("</urlset>")
    (web_root / "sitemap.xml").write_text("\n".join(body), encoding="utf-8")


def _rfc822(iso: str) -> str:
    """'2026-04-23' → 'Thu, 23 Apr 2026 00:00:00 +0000'."""
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return d.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def _write_feed(articles: list[dict], web_root: Path) -> None:
    """Generate RSS 2.0 feed with the 50 most recent articles."""
    items = articles[:50]
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        '  <channel>',
        '    <title>ФБРК — Независимые расследования</title>',
        f'    <link>{SITE_URL}/</link>',
        '    <description>Фонд-бюро расследования коррупции. Журналистские расследования и новости Казахстана.</description>',
        '    <language>ru</language>',
        f'    <lastBuildDate>{now_rfc}</lastBuildDate>',
        f'    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />',
    ]
    for a in items:
        slug_or_id = a.get("slug") or a["id"]
        url = f"{SITE_URL}/a/{slug_or_id}"
        img = a.get("image") or ""
        if img and not img.startswith("http"):
            img = f"{SITE_URL}{img}"
        dek = (a.get("dek") or "")[:500]
        lines.append("    <item>")
        lines.append(f"      <title>{html.escape(a.get('title') or '')}</title>")
        lines.append(f"      <link>{html.escape(url)}</link>")
        lines.append(f"      <guid isPermaLink=\"true\">{html.escape(url)}</guid>")
        lines.append(f"      <pubDate>{_rfc822(a.get('dateIso') or '')}</pubDate>")
        lines.append(f"      <description>{html.escape(dek)}</description>")
        lines.append(f"      <category>{html.escape(a.get('categoryLabel') or '')}</category>")
        if img:
            lines.append(f'      <enclosure url="{html.escape(img)}" type="image/jpeg" />')
        lines.append("    </item>")
    lines.append("  </channel>")
    lines.append("</rss>")
    (web_root / "feed.xml").write_text("\n".join(lines), encoding="utf-8")


import fcntl
import tempfile
import threading
from contextlib import contextmanager

_PUBLISH_LOCK = threading.Lock()


def _atomic_write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try: os.unlink(tmp)
            except OSError: pass


@contextmanager
def _file_lock(lock_path: str):
    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            os.chmod(lock_path, 0o666)
        except OSError:
            pass
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try: fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError: pass
        os.close(fd)


def regenerate_data_js() -> dict:
    out = Path(settings.data_js_path)
    lock_key = hashlib.sha256(str(out.resolve()).encode("utf-8")).hexdigest()[:16]
    lock_file = str(Path(tempfile.gettempdir()) / f"fbrk-publish-{lock_key}.lock")
    with _PUBLISH_LOCK, _file_lock(lock_file):
        source_articles = _load_articles()
        articles = [_public_shape(a) for a in source_articles]

        # Tier 1: data.js — homepage (last N articles). Fast initial load.
        # N is tunable via FBRK_HOME_LATEST_LIMIT env var (default 200).
        limit = max(1, int(getattr(settings, "home_latest_limit", 200)))
        recent = articles[:limit]
        data = {**SITE_META, "articles": recent, "totalCount": len(articles)}
        body = HEADER + json.dumps(data, ensure_ascii=False) + ";\n"
        _atomic_write(out, body)

        # Tier 2: data-archive.js — full archive (all articles, compact).
        # Loaded only by archive.html, not by index/article pages.
        archive_out = out.parent / "data-archive.js"
        archive_data = {"articles": articles}
        archive_body = "/* ФБРК archive — auto-generated. */\nwindow.ARTICLES_ARCHIVE = " + json.dumps(archive_data, ensure_ascii=False) + ";\n"
        _atomic_write(archive_out, archive_body)

        # Tier 3: article-full.js — full public body for static /a/<slug>
        # fallback on split hosting. Loaded only by article.html.
        article_full_out = out.parent / "article-full.js"
        article_full_data = {"articles": [_article_full_shape(a) for a in source_articles]}
        article_full_body = (
            "/* ФБРК full article bodies — auto-generated. */\n"
            "window.ARTICLE_FULL = "
            + json.dumps(article_full_data, ensure_ascii=False, separators=(",", ":"))
            + ";\n"
        )
        _atomic_write(article_full_out, article_full_body)

        # Note: sitemap.xml, feed.xml, feed/ia.xml and robots.txt are now served
        # dynamically by FastAPI (app.seo). Legacy static writers removed so stale
        # files don't override live routes.
        return {"articles": len(articles), "path": str(out)}
