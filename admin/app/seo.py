"""SEO/OG/Instant Articles/RSS routes served live by FastAPI.

Endpoints:
- GET /a/{slug}          SSR-rendered article page with full Schema.org + OG
- GET /sitemap.xml       Extended sitemap with <lastmod> for every article
- GET /robots.txt        Allows AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended)
- GET /feed.xml          RSS 2.0 with <content:encoded> full body (MediaRSS)
- GET /feed/ia.xml       Facebook Instant Articles RSS feed

The SPA (index/archive/article.html) keeps working — nginx still serves them.
For external consumers (social crawlers, LLM bots, search engines, RSS readers),
these server-rendered routes expose full HTML with metadata.
"""
from __future__ import annotations

import html
import json
import os
import re
import sqlite3 as _ad_sqlite
import time as _ad_time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from .admin_platform.templating import AdminJinja2Templates
from .config import settings
from .db import db, row_to_article

DEFAULT_SITE_URL = (os.environ.get("FBRK_SITE_URL") or "https://fbrk.qdev.run").rstrip("/")
ORG_NAME = "ФБРК"
ORG_FULL = "Фонд-бюро расследования коррупции"
TELEGRAM = "https://t.me/fund_kz_bot"
YOUTUBE = "https://www.youtube.com/@fbrk_news"

BASE = Path(__file__).resolve().parent.parent  # admin/
templates = AdminJinja2Templates(directory=str(BASE / "templates"))

# SSR template uses ad("slot") helper for promo blocks.
# Keep it resilient: if ad table is unavailable we return empty HTML.
_AD_DB_PATH = settings.db_path
_AD_CACHE = {"t": 0.0, "data": {}}


def _ads_load() -> dict:
    now = _ad_time.time()
    if now - float(_AD_CACHE.get("t", 0)) < 60 and _AD_CACHE.get("data"):
        return _AD_CACHE["data"]
    out: dict = {}
    try:
        con = _ad_sqlite.connect(_AD_DB_PATH)
        con.row_factory = _ad_sqlite.Row
        rows = con.execute(
            "SELECT slot_id, client_name, client_url, image_url, notes "
            "FROM ad_placements WHERE is_active=1 AND COALESCE(image_url, '') != ''"
        ).fetchall()
        for r in rows:
            out[r["slot_id"]] = dict(r)
        con.close()
    except Exception:
        pass
    _AD_CACHE["t"] = now
    _AD_CACHE["data"] = out
    return out


def _ad(slot_id: str) -> str:
    a = _ads_load().get(slot_id)
    if not a:
        return ""
    url = a.get("client_url") or "#"
    img = a.get("image_url") or ""
    name = str(a.get("client_name") or "").replace('"', "&quot;")
    return (
        f'<a class="ad-slot ad-{slot_id}" href="{url}" target="_blank" rel="sponsored noopener" '
        f'data-slot="{slot_id}" aria-label="Реклама: {name}">'
        f'<img src="{img}" alt="{name}" loading="lazy"></a>'
    )


templates.env.globals["ad"] = _ad

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _site_url(request: Request | None = None) -> str:
    if request is not None:
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
        if host:
            return f"{proto}://{host}"
    return DEFAULT_SITE_URL


def _brand_logo(site_url: str) -> str:
    return f"{site_url}/img/brand/logo-white-512.png"


def _brand_logo_mark(site_url: str) -> str:
    return f"{site_url}/img/brand/logo-brand-256.png"


def _default_og(site_url: str) -> str:
    return f"{site_url}/img/brand/logo-on-brand-640.png"


def _abs_url(u: str, site_url: str) -> str:
    if not u:
        return _default_og(site_url)
    if u.startswith("http"):
        return u
    if u.startswith("/"):
        return f"{site_url}{u}"
    return f"{site_url}/{u}"


def _rfc822(iso: str) -> str:
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return d.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def _iso8601(iso: str) -> str:
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return d.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _strip_html(s: str) -> str:
    """Drop tags, collapse whitespace — for JSON-LD / meta description."""
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sections_to_plain(sections: list) -> str:
    parts: list[str] = []
    for s in sections or []:
        if not isinstance(s, dict):
            continue
        if s.get("h"):
            parts.append(str(s["h"]))
        if s.get("p"):
            parts.append(_strip_html(str(s["p"])))
    return "\n\n".join(p for p in parts if p)


def _header_dek(dek: str, sections: list) -> str:
    value = _strip_html(dek or "").strip()
    if not value or not sections:
        return ""
    if len(value) > 420 or "\n\n" in value:
        return ""

    first = sections[0] if isinstance(sections[0], dict) else {}
    first_text = _strip_html(f"{first.get('h') or ''} {first.get('p') or ''}")
    if first_text.startswith(value):
        return ""
    return value


def _sections_to_html(sections: list, site_url: str) -> str:
    """Render sections as clean semantic HTML for SSR body + RSS content:encoded."""
    out: list[str] = []
    for s in sections or []:
        if not isinstance(s, dict):
            continue
        h = s.get("h")
        p = s.get("p")
        img = s.get("img") or s.get("image")
        if h:
            out.append(f"<h2>{html.escape(str(h))}</h2>")
        if img:
            src = _abs_url(str(img), site_url)
            cap = html.escape(str(s.get("caption") or ""))
            out.append(f'<figure><img src="{src}" alt="{cap}" /></figure>')
        if p:
            # Body may already contain <p>/<strong>/<em>/<a>. Keep as-is.
            out.append(str(p))
    return "\n".join(out)


def _load_article_by_slug(slug: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE (slug=? OR id=?) AND published=1 LIMIT 1",
            (slug, slug),
        ).fetchone()
    return row_to_article(row) if row else None


def _load_article_meta(article_id: str) -> dict | None:
    with db() as conn:
        try:
            row = conn.execute(
                "SELECT * FROM article_meta WHERE article_id = ? AND error = ''",
                (article_id,),
            ).fetchone()
        except Exception:
            return None
    if not row:
        return None
    return {
        "summary_short": row["summary_short"],
        "summary_tts": row["summary_tts"],
        "key_points": json.loads(row["key_points"] or "[]"),
        "importance": row["importance"],
        "sentiment": row["sentiment"],
        "entities": json.loads(row["entities_json"] or "[]"),
        "region": row["region"],
        "tags_auto": json.loads(row["tags_auto"] or "[]"),
    }


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


def _visible_entities(raw: list, exclude_names: set[str] | None = None, limit: int = 12) -> list[dict]:
    """Return public-facing named entities, excluding topic tags and fallback noise."""
    excluded = {str(x or "").strip().casefold() for x in (exclude_names or set()) if str(x or "").strip()}
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        kind = str(item.get("type") or "other").strip().lower()
        if not name or kind not in PUBLIC_ENTITY_TYPES:
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


def _visible_tags(raw: list, auto_raw: list, exclude_names: set[str] | None = None, limit: int = 16) -> list[str]:
    """Return manually curated tags only; auto topics are kept for metadata, not chips."""
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


def _load_recent_articles(limit: int | None = None) -> list[dict]:
    with db() as conn:
        q = "SELECT * FROM articles WHERE published=1 ORDER BY date_iso DESC, created_at DESC"
        if limit:
            q += f" LIMIT {int(limit)}"
        rows = conn.execute(q).fetchall()
    return [row_to_article(r) for r in rows]


def _load_all_article_meta() -> list[dict]:
    """Minimal fields for sitemap generation — fast."""
    with db() as conn:
        rows = conn.execute(
            "SELECT id, slug, date_iso, updated_at, image, title FROM articles "
            "WHERE published=1 ORDER BY date_iso DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def _load_related_articles(article: dict, visible_tags: list[str], limit: int = 3) -> list[dict]:
    """Return a small SSR related set without relying on split-frontend JSON fetches."""
    slug = str(article.get("slug") or article.get("id") or "")
    category = str(article.get("category") or "")
    base_tags = {
        str(tag or "").strip().casefold()
        for tag in list(article.get("tags") or []) + list(visible_tags or [])
        if str(tag or "").strip()
    }

    with db() as conn:
        rows = conn.execute(
            """
            SELECT slug, title, date_iso, date_label, image, tags_json, category
            FROM articles
            WHERE published=1 AND slug != ?
            ORDER BY
              CASE WHEN category = ? THEN 0 ELSE 1 END,
              date_iso DESC,
              created_at DESC
            LIMIT 80
            """,
            (slug, category),
        ).fetchall()

    seen: set[str] = set()
    candidates: list[tuple[int, str, dict]] = []
    for row in rows:
        item = dict(row)
        item_slug = str(item.get("slug") or "")
        if not item_slug or item_slug in seen:
            continue
        seen.add(item_slug)
        try:
            item_tags = {
                str(tag or "").strip().casefold()
                for tag in json.loads(item.get("tags_json") or "[]")
                if str(tag or "").strip()
            }
        except Exception:
            item_tags = set()
        score = 0
        if category and item.get("category") == category:
            score += 2
        score += 3 * len(base_tags & item_tags)
        if item.get("image"):
            score += 1
        candidates.append(
            (
                score,
                str(item.get("date_iso") or ""),
                {
                    "slug": item_slug,
                    "title": str(item.get("title") or ""),
                    "date_label": str(item.get("date_label") or item.get("date_iso") or ""),
                    "image": str(item.get("image") or ""),
                },
            )
        )

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item for _, __, item in candidates[: max(0, int(limit))]]


# ---------------------------------------------------------------------------
# SSR article page — /a/{slug}
# ---------------------------------------------------------------------------
@router.api_route("/a/{slug}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def ssr_article(slug: str, request: Request):
    a = _load_article_by_slug(slug)
    if not a:
        raise HTTPException(404, "Article not found")

    meta = _load_article_meta(a["id"]) or {}
    site_url = _site_url(request)

    url = f"{site_url}/a/{a['slug']}"
    title = a["title"]
    raw_dek = a.get("dek") or ""
    dek = _strip_html(raw_dek)
    plain_body = _sections_to_plain(a.get("sections") or [])
    header_dek = _header_dek(raw_dek, a.get("sections") or [])
    hero_dek = (meta.get("summary_short") or header_dek or "").strip()
    # Prefer AI short summary when available (tighter, better for SEO/LLMs)
    desc = (meta.get("summary_short") or dek or plain_body[:240]).strip()[:240]
    image = _abs_url(a.get("image") or "", site_url)
    body_html = _sections_to_html(a.get("sections") or [], site_url)
    word_count = len((plain_body or "").split())
    read_min = max(1, round(len((" ".join(part for part in [hero_dek, plain_body] if part)).split()) / 180))

    date_iso = a.get("dateIso") or ""
    date_label = a.get("date") or ""
    published_iso = _iso8601(date_iso)
    modified_iso = _iso8601((a.get("updatedAt") or date_iso)[:10])
    category_label = a.get("categoryLabel") or "Новости"
    tags = []
    seen_tags = set()
    for item in list(a.get("tags") or []) + list(meta.get("tags_auto") or []):
        value = str(item or "").strip()
        key = value.casefold()
        if value and key not in seen_tags:
            tags.append(value)
            seen_tags.add(key)
    raw_entities = meta.get("entities") or []
    visible_entities = _visible_entities(raw_entities)
    meta = {**meta, "entities": visible_entities}
    entity_names = {
        str(item.get("name") or "").strip().casefold()
        for item in visible_entities
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    visible_tags = _visible_tags(
        a.get("tags") or [],
        meta.get("tags_auto") or [],
        exclude_names=entity_names | _hidden_entity_names(raw_entities),
    )

    # --- JSON-LD NewsArticle ---
    news_article_ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": title[:110],
        "description": desc,
        "image": [image],
        "datePublished": published_iso,
        "dateModified": modified_iso,
        "author": {
            "@type": "Organization",
            "name": ORG_NAME,
            "url": site_url,
        },
        "publisher": {
            "@type": "Organization",
            "name": ORG_NAME,
            "legalName": ORG_FULL,
            "logo": {
                "@type": "ImageObject",
                "url": _brand_logo_mark(site_url),
                "width": 256,
                "height": 256,
            },
        },
        "articleSection": category_label,
        "inLanguage": "ru",
        "isAccessibleForFree": True,
        "wordCount": word_count,
        "keywords": ", ".join(tags) if tags else None,
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [
                ".article__title",
                ".article__dek",
                ".article__tldr-list",
            ],
        },
    }
    # Remove nulls for cleanliness
    news_article_ld = {k: v for k, v in news_article_ld.items() if v is not None}

    # --- BreadcrumbList ---
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная", "item": f"{site_url}/"},
            {
                "@type": "ListItem",
                "position": 2,
                "name": category_label,
                "item": f"{site_url}/archive.html?cat={a.get('category') or 'news'}",
            },
            {"@type": "ListItem", "position": 3, "name": title, "item": url},
        ],
    }

    ctx = {
        "request": request,
        "a": a,
        "meta": meta,
        "url": url,
        "title": title,
        "desc": desc,
        "header_dek": header_dek,
        "hero_dek": hero_dek,
        "image": image,
        "body_html": body_html,
        "date_iso": date_iso,
        "date_label": date_label,
        "read_min": read_min,
        "published_iso": published_iso,
        "modified_iso": modified_iso,
        "category_label": category_label,
        "tags": tags,
        "visible_tags": visible_tags,
        "news_article_ld": json.dumps(news_article_ld, ensure_ascii=False),
        "breadcrumb_ld": json.dumps(breadcrumb_ld, ensure_ascii=False),
        "site_url": site_url,
        "org_name": ORG_NAME,
        "org_full": ORG_FULL,
        "telegram_url": TELEGRAM,
        "youtube_url": YOUTUBE,
        "related_articles": _load_related_articles(a, visible_tags),
    }

    response = templates.TemplateResponse("article_ssr.html", ctx)
    # Social crawlers + bots need real HTML + cachable
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=600"
    return response


# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------
def _robots_body(site_url: str) -> str:
    return f"""# ФБРК — robots.txt
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /img/uploads/

# Explicitly allow AI/LLM crawlers so our investigations are indexable
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: YandexBot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: CCBot
Allow: /

User-agent: FacebookExternalHit
Allow: /

User-agent: Twitterbot
Allow: /

User-agent: TelegramBot
Allow: /

Sitemap: {site_url}/sitemap.xml
"""


@router.api_route("/robots.txt", methods=["GET", "HEAD"], response_class=PlainTextResponse)
def robots_txt(request: Request):
    return PlainTextResponse(_robots_body(_site_url(request)), media_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# sitemap.xml — dynamic with <lastmod> per article
# ---------------------------------------------------------------------------
@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
def sitemap_xml(request: Request):
    arts = _load_all_article_meta()
    site_url = _site_url(request)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    newest = arts[0]["date_iso"] if arts else now

    # News sitemap supports last 48h only — pick recent ones for <news:news>
    recent_news: list[dict] = []
    try:
        cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        for a in arts[:200]:
            try:
                d = datetime.strptime(a["date_iso"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if (cutoff - d).days <= 2:
                    recent_news.append(a)
            except Exception:
                pass
    except Exception:
        pass

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:news="http://www.google.com/schemas/sitemaps-news/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml"',
        '        xmlns:image="http://www.google.com/schemas/sitemaps-image/1.1">',
    ]

    def _url(loc: str, lastmod: str, changefreq: str, priority: str,
             news: dict | None = None, image: str | None = None):
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(loc)}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        if image:
            lines.append("    <image:image>")
            lines.append(f"      <image:loc>{html.escape(image)}</image:loc>")
            lines.append("    </image:image>")
        if news:
            lines.append("    <news:news>")
            lines.append("      <news:publication>")
            lines.append(f"        <news:name>{html.escape(ORG_NAME)}</news:name>")
            lines.append("        <news:language>ru</news:language>")
            lines.append("      </news:publication>")
            lines.append(f"      <news:publication_date>{news['pubdate']}</news:publication_date>")
            lines.append(f"      <news:title>{html.escape(news['title'])}</news:title>")
            lines.append("    </news:news>")
        lines.append("  </url>")

    # Static pages
    _url(f"{site_url}/", newest, "hourly", "1.0")
    _url(f"{site_url}/archive.html", newest, "daily", "0.9")
    _url(f"{site_url}/archive.html?cat=investigation", newest, "daily", "0.8")
    _url(f"{site_url}/archive.html?cat=news", newest, "daily", "0.8")
    _url(f"{site_url}/about.html", now, "monthly", "0.5")

    recent_ids = {a["id"] for a in recent_news}
    for a in arts:
        slug = a.get("slug") or a["id"]
        loc = f"{site_url}/a/{slug}"
        lastmod = (a.get("updated_at") or a.get("date_iso") or now)[:10]
        news = None
        if a["id"] in recent_ids:
            news = {
                "pubdate": _iso8601(a["date_iso"]),
                "title": a["title"],
            }
        img = _abs_url(a.get("image") or "", site_url) if a.get("image") else None
        _url(loc, lastmod, "weekly", "0.7", news=news, image=img)

    lines.append("</urlset>")
    body = "\n".join(lines)
    return Response(content=body, media_type="application/xml; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=600"})


# ---------------------------------------------------------------------------
# RSS feed.xml with <content:encoded>
# ---------------------------------------------------------------------------
@router.api_route("/feed.xml", methods=["GET", "HEAD"])
def feed_xml(request: Request):
    arts = _load_recent_articles(limit=50)
    site_url = _site_url(request)
    org_logo_brand = _brand_logo_mark(site_url)
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        '     xmlns:atom="http://www.w3.org/2005/Atom"',
        '     xmlns:content="http://purl.org/rss/1.0/modules/content/"',
        '     xmlns:dc="http://purl.org/dc/elements/1.1/"',
        '     xmlns:media="http://search.yahoo.com/mrss/">',
        '  <channel>',
        f'    <title>{html.escape(ORG_NAME)} — Независимые расследования</title>',
        f'    <link>{site_url}/</link>',
        f'    <description>{html.escape(ORG_FULL)}. Журналистские расследования и новости Казахстана.</description>',
        '    <language>ru</language>',
        f'    <lastBuildDate>{now_rfc}</lastBuildDate>',
        f'    <atom:link href="{site_url}/feed.xml" rel="self" type="application/rss+xml" />',
        f'    <image><url>{org_logo_brand}</url><title>{html.escape(ORG_NAME)}</title><link>{site_url}/</link></image>',
    ]
    for a in arts:
        slug = a.get("slug") or a["id"]
        url = f"{site_url}/a/{slug}"
        img = _abs_url(a.get("image") or "", site_url) if a.get("image") else ""
        dek = _strip_html(a.get("dek") or "")[:500]
        body_html = _sections_to_html(a.get("sections") or [], site_url)
        content_encoded = f"<![CDATA[{body_html}]]>"
        lines.append("    <item>")
        lines.append(f"      <title>{html.escape(a.get('title') or '')}</title>")
        lines.append(f"      <link>{html.escape(url)}</link>")
        lines.append(f"      <guid isPermaLink=\"true\">{html.escape(url)}</guid>")
        lines.append(f"      <pubDate>{_rfc822(a.get('dateIso') or '')}</pubDate>")
        lines.append(f"      <dc:creator>{html.escape(ORG_NAME)}</dc:creator>")
        lines.append(f"      <category>{html.escape(a.get('categoryLabel') or '')}</category>")
        for tag in (a.get("tags") or [])[:8]:
            lines.append(f"      <category>{html.escape(str(tag))}</category>")
        lines.append(f"      <description>{html.escape(dek)}</description>")
        if img:
            lines.append(f'      <media:content url="{html.escape(img)}" medium="image" />')
            lines.append(f'      <enclosure url="{html.escape(img)}" type="image/jpeg" length="0" />')
        lines.append(f"      <content:encoded>{content_encoded}</content:encoded>")
        lines.append("    </item>")
    lines.append("  </channel>")
    lines.append("</rss>")
    body = "\n".join(lines)
    return Response(content=body, media_type="application/rss+xml; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=600"})


# ---------------------------------------------------------------------------
# Facebook Instant Articles RSS /feed/ia.xml
# ---------------------------------------------------------------------------
def _render_ia_body_html(a: dict, url: str, image: str, site_url: str) -> str:
    """Build the <content:encoded> HTML per Facebook IA Markup."""
    title = html.escape(a.get("title") or "")
    dek = html.escape(_strip_html(a.get("dek") or ""))
    image_cap = html.escape(a.get("title") or "")
    category = html.escape(a.get("categoryLabel") or "Новости")
    date_iso = a.get("dateIso") or ""
    pub_iso = _iso8601(date_iso)
    date_label = html.escape(a.get("date") or date_iso)
    body_inner = _sections_to_html(a.get("sections") or [], site_url)

    parts = [
        '<!doctype html>',
        '<html lang="ru" prefix="op: http://media.facebook.com/op#">',
        '<head>',
        '<meta charset="utf-8">',
        f'<link rel="canonical" href="{html.escape(url)}">',
        '<meta charset="utf-8">',
        '<meta property="op:markup_version" content="v1.0">',
        '<meta property="fb:article_style" content="default">',
        '</head>',
        '<body>',
        '<article>',
        '<header>',
        f'<h1>{title}</h1>',
    ]
    if dek:
        parts.append(f'<h2>{dek}</h2>')
    parts.extend([
        f'<time class="op-published" datetime="{pub_iso}">{date_label}</time>',
        f'<address><a>{html.escape(ORG_NAME)}</a></address>',
    ])
    if image:
        parts.append(
            f'<figure><img src="{html.escape(image)}" /><figcaption>{image_cap}</figcaption></figure>'
        )
    parts.extend([
        f'<h3 class="op-kicker">{category}</h3>',
        '</header>',
        body_inner,
        '<footer><small>© ФБРК — Фонд-бюро расследования коррупции</small></footer>',
        '</article>',
        '</body>',
        '</html>',
    ])
    return "".join(parts)


@router.api_route("/feed/ia.xml", methods=["GET", "HEAD"])
def feed_ia_xml(request: Request):
    arts = _load_recent_articles(limit=100)
    site_url = _site_url(request)
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [
        '<?xml version="1.0" encoding="utf-8" standalone="no"?>',
        '<rss version="2.0"',
        '     xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        '  <channel>',
        f'    <title>{html.escape(ORG_NAME)} — Instant Articles</title>',
        f'    <link>{site_url}/</link>',
        f'    <description>{html.escape(ORG_FULL)} — Facebook Instant Articles feed</description>',
        '    <language>ru</language>',
        f'    <lastBuildDate>{now_rfc}</lastBuildDate>',
    ]
    for a in arts:
        slug = a.get("slug") or a["id"]
        url = f"{site_url}/a/{slug}"
        img = _abs_url(a.get("image") or "", site_url) if a.get("image") else ""
        body_html_ia = _render_ia_body_html(a, url, img, site_url)
        lines.append("    <item>")
        lines.append(f"      <title>{html.escape(a.get('title') or '')}</title>")
        lines.append(f"      <link>{html.escape(url)}</link>")
        lines.append(f"      <guid>{html.escape(url)}</guid>")
        lines.append(f"      <pubDate>{_rfc822(a.get('dateIso') or '')}</pubDate>")
        lines.append(f"      <author>{html.escape(ORG_NAME)}</author>")
        lines.append(f"      <content:encoded><![CDATA[{body_html_ia}]]></content:encoded>")
        lines.append("    </item>")
    lines.append("  </channel>")
    lines.append("</rss>")
    body = "\n".join(lines)
    return Response(content=body, media_type="application/rss+xml; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=900"})
