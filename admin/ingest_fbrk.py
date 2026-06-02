#!/usr/bin/env python3
"""
ingest_fbrk.py — pulls articles from fbrk.kz into the local fbrk.db.

Modes:
  rss                       — fetch /rss.xml (last ~10), upsert.
  sitemap                   — discover all article URLs from sitemap.xml
                              (and sitemap_indexN.xml children if present).
  fill-missing              — for each article in DB whose body_json is empty
                              or whose Editor.js produces <2 sections, refetch
                              the article from fbrk.kz and rebuild body.
  one <url>                 — single URL (debug).

Notes:
  - fbrk.kz URL slugs come in two flavours: /news/<slug> and /articles/<slug>.
    We use the slug part as the stable id (matches existing keys in DB
    populated from data.js).
  - Run from /opt/fbrk-admin with venv. We import app.editorjs to convert
    blocks → sections and app.publish.regenerate_data_js to refresh public
    JSON files on disk.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# We're meant to be invoked from /opt/fbrk-admin so app.* is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.editorjs import editorjs_to_sections  # noqa: E402

LOG = logging.getLogger("ingest_fbrk")
BASE = "https://fbrk.kz"
UA = "Mozilla/5.0 (compatible; FBRK-clone-sync/1.0; +https://fbrk.qdev.run/about)"
DB_PATH = os.environ.get("FBRK_DB", "/opt/fbrk-admin/fbrk.db")
MEDIA_BASE = os.environ.get("FBRK_MEDIA_BASE", "/img/uploads")  # local proxy if any
TIMEOUT = 30
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})

RU_MONTHS_NOM = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


# ─── http helpers ──────────────────────────────────────────────────────────────
def fetch(url: str, retries: int = 3) -> Optional[str]:
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                LOG.warning("fetch %s -> %s (skip)", url, r.status_code)
                return None
            LOG.warning("fetch %s -> %s (retry %d)", url, r.status_code, i + 1)
        except Exception as e:
            LOG.warning("fetch %s err %s (retry %d)", url, e, i + 1)
        time.sleep(1.5 * (i + 1))
    return None


# ─── slug & date helpers ───────────────────────────────────────────────────────
def slug_from_url(url: str) -> str:
    p = urlparse(url)
    parts = [s for s in p.path.split("/") if s]
    return parts[-1] if parts else ""


def fmt_date_label(iso: str) -> str:
    try:
        dt = datetime.strptime(iso[:10], "%Y-%m-%d")
        return f"{dt.day} {RU_MONTHS_NOM[dt.month - 1]} {dt.year}"
    except Exception:
        return iso[:10]


# ─── HTML → Editor.js blocks ───────────────────────────────────────────────────
INLINE_TAGS = {"a", "b", "strong", "i", "em", "u", "s", "code", "br", "span", "mark", "small", "sup", "sub"}


def _inline_html(node: Tag) -> str:
    """Render node's children to html, keeping only inline tools allowed by Editor.js."""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(unescape(str(child)))
        elif isinstance(child, Tag):
            t = child.name.lower()
            if t == "br":
                parts.append("<br>")
            elif t == "a":
                href = (child.get("href") or "").strip()
                inner = _inline_html(child)
                if href:
                    parts.append(f'<a href="{href}">{inner}</a>')
                else:
                    parts.append(inner)
            elif t in ("strong", "b"):
                parts.append(f"<b>{_inline_html(child)}</b>")
            elif t in ("em", "i"):
                parts.append(f"<i>{_inline_html(child)}</i>")
            elif t in INLINE_TAGS:
                parts.append(_inline_html(child))
            else:
                parts.append(_inline_html(child))
    txt = "".join(parts)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _split_paragraph_on_double_br(text: str) -> list[str]:
    """fbrk.kz often packs an entire article body into one <p> with <br><br>
    as paragraph separators. Split such an HTML fragment into multiple paragraphs.
    Single <br> stays as a soft line-break."""
    if not text:
        return []
    # Normalise variants of br tag, then split on >=2 consecutive <br>
    norm = re.sub(r"<br\s*/?>\s*", "<br>", text, flags=re.I)
    parts = re.split(r"(?:<br>\s*){2,}", norm)
    return [p.strip() for p in parts if p.strip()]


def _block_from(el: Tag) -> Optional[dict] | list[dict]:
    name = el.name.lower()
    if name in ("p",):
        text = _inline_html(el)
        if not text or text in ("&nbsp;", " "):
            return None
        # If <p> contains <br><br>, split into multiple paragraphs.
        parts = _split_paragraph_on_double_br(text)
        if len(parts) > 1:
            return [{"type": "paragraph", "data": {"text": p}} for p in parts]
        return {"type": "paragraph", "data": {"text": text}}
    if name in ("h2", "h3"):
        text = el.get_text(" ", strip=True)
        if not text:
            return None
        # fbrk.kz uses h3 for sub-sections; map to header level=2 (our public
        # template treats anything h2 as a section break — that's what we want).
        return {"type": "header", "data": {"text": text, "level": 2}}
    if name == "h4":
        text = el.get_text(" ", strip=True)
        if not text:
            return None
        return {"type": "header", "data": {"text": text, "level": 3}}
    if name in ("ul", "ol"):
        items = []
        for li in el.find_all("li", recursive=False):
            inner = _inline_html(li)
            if inner:
                items.append(inner)
        if not items:
            return None
        return {"type": "list", "data": {"style": "ordered" if name == "ol" else "unordered", "items": items}}
    if name == "blockquote":
        text = _inline_html(el)
        if not text:
            return None
        return {"type": "quote", "data": {"text": text, "caption": "", "alignment": "left"}}
    if name == "figure":
        img = el.find("img")
        cap = el.find("figcaption")
        if img and img.get("src"):
            return {"type": "image", "data": {
                "file": {"url": urljoin(BASE, img["src"])},
                "caption": cap.get_text(" ", strip=True) if cap else "",
                "withBorder": False, "stretched": False, "withBackground": False,
            }}
        return None
    if name == "img":
        if el.get("src"):
            return {"type": "image", "data": {
                "file": {"url": urljoin(BASE, el["src"])},
                "caption": el.get("alt") or "",
                "withBorder": False, "stretched": False, "withBackground": False,
            }}
    if name == "hr":
        return {"type": "delimiter", "data": {}}
    return None


def html_to_editorjs(html_text: str | Tag) -> dict:
    """Parse the fbrk.kz article body container into Editor.js blocks.

    Accepts either a raw HTML string OR a Tag node — when a string is given
    we soup it and treat the entire soup as the container (since BS wraps
    a fragment in a top-level container).
    """
    if isinstance(html_text, Tag):
        root = html_text
    else:
        root = BeautifulSoup(html_text, "html.parser")
    blocks: list[dict] = []

    # Walk only direct children where useful; recurse into div containers.
    def walk(container: Tag):
        for el in container.children:
            if not isinstance(el, Tag):
                continue
            n = el.name.lower()
            if n in ("p", "h2", "h3", "h4", "ul", "ol", "blockquote", "figure", "hr"):
                b = _block_from(el)
                if b:
                    if isinstance(b, list):
                        blocks.extend(b)
                    else:
                        blocks.append(b)
            elif n == "img":
                b = _block_from(el)
                if b:
                    if isinstance(b, list):
                        blocks.extend(b)
                    else:
                        blocks.append(b)
            elif n in ("div", "article", "section", "aside"):
                # Skip Drupal field labels & social blocks
                klass = " ".join(el.get("class") or [])
                if any(s in klass for s in ("field--label", "addtoany", "social", "tags", "author", "submitted")):
                    continue
                walk(el)
            # ignore everything else

    walk(root)
    return {"time": 0, "blocks": blocks, "version": "2.30.0"}


# ─── article page parser ───────────────────────────────────────────────────────
ARTICLE_RE = re.compile(r"^/(news|articles)/[^/]+/?$")
GENERIC_SITE_IMAGE_RE = re.compile(r"/sites/default/files/fbrk\.jpg(?:$|\?)", re.I)


def _is_generic_site_image(url: str) -> bool:
    return bool(GENERIC_SITE_IMAGE_RE.search(str(url or "").strip()))


def _extract_article_cover_image(soup: BeautifulSoup) -> str:
    article = soup.find("article", class_=re.compile(r"node--type-"))
    candidates: list[str] = []

    if article:
        field_item = article.find("div", class_=re.compile(r"field--name-field-image"))
        if field_item:
            for img in field_item.find_all("img"):
                src = str(img.get("src") or "").strip()
                if src:
                    candidates.append(urljoin(BASE, src))
        for img in article.find_all("img"):
            src = str(img.get("src") or "").strip()
            if src:
                candidates.append(urljoin(BASE, src))

    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        candidates.append(str(og["content"]).strip())
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        candidates.append(str(tw["content"]).strip())

    for url in candidates:
        if not url or _is_generic_site_image(url):
            continue
        return url

    for url in candidates:
        if url:
            return url
    return ""


def parse_article(url: str) -> Optional[dict]:
    """Fetch + parse a fbrk.kz article URL → dict matching `articles` columns."""
    html_text = fetch(url)
    if not html_text:
        return None
    soup = BeautifulSoup(html_text, "html.parser")

    # ─ title
    title_tag = soup.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    # ─ pubdate (datetime attr most reliable)
    iso = ""
    for t in soup.find_all("time"):
        if t.get("datetime"):
            iso = t["datetime"][:10]
            break
    if not iso:
        # fall back to <meta property="article:published_time">
        m = soup.find("meta", attrs={"property": "article:published_time"})
        if m and m.get("content"):
            iso = m["content"][:10]
    if not iso:
        iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ─ image
    image = _extract_article_cover_image(soup)

    # ─ body field
    body_div = soup.find("div", class_=re.compile(r"field--name-body"))
    if not body_div:
        # site sometimes serves with .text-content wrapper
        body_div = soup.find("div", class_=re.compile(r"text-content"))
    if not body_div:
        return None

    editorjs = html_to_editorjs(body_div)
    blocks = editorjs.get("blocks", [])
    if not blocks:
        return None

    # ─ dek = first paragraph plain text (≤ 220 ch)
    dek = ""
    for b in blocks:
        if b.get("type") == "paragraph":
            t = re.sub(r"<[^>]+>", "", b["data"].get("text", "")).strip()
            if t:
                dek = t[:220]
                break

    # ─ category: fbrk.kz использует /news/* и /articles/* как формат (короткое vs длинное),
    # а не как рубрику расследований. Рубрика 'investigation' в нашей БД —
    # это отдельный флаг для фирменных расследований фонда. Импорт — всегда 'news'.
    category, category_label = "news", "Новости"

    sections = editorjs_to_sections(editorjs)

    slug = slug_from_url(url)
    return {
        "id": slug,
        "slug": slug,
        "title": title,
        "dek": dek,
        "author": "fbrk_news",
        "date_iso": iso,
        "date_label": fmt_date_label(iso),
        "category": category,
        "category_label": category_label,
        "image": image,
        "tags_json": "[]",
        "source": url,
        "body_json": json.dumps(editorjs, ensure_ascii=False),
        "sections_json": json.dumps(sections, ensure_ascii=False),
        "featured": 0,
        "published": 1,
    }


# ─── DB ────────────────────────────────────────────────────────────────────────
UPSERT_SQL = """
INSERT INTO articles (
  id, slug, title, dek, author, date_iso, date_label,
  category, category_label, image, tags_json, source,
  body_json, sections_json, featured, published, created_at, updated_at
) VALUES (
  :id, :slug, :title, :dek, :author, :date_iso, :date_label,
  :category, :category_label, :image, :tags_json, :source,
  :body_json, :sections_json, :featured, :published, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT(id) DO UPDATE SET
  title         = excluded.title,
  dek           = CASE WHEN length(excluded.dek) > length(articles.dek) THEN excluded.dek ELSE articles.dek END,
  date_iso      = excluded.date_iso,
  date_label    = excluded.date_label,
  category      = excluded.category,
  category_label= excluded.category_label,
  image         = CASE WHEN excluded.image <> '' THEN excluded.image ELSE articles.image END,
  source        = excluded.source,
  body_json     = excluded.body_json,
  sections_json = excluded.sections_json,
  updated_at    = CURRENT_TIMESTAMP
WHERE
  -- only overwrite body if the new one is *better* — compare total content length
  -- (sections_json count alone misses the case where a single section grows from
  --  one paragraph to many because fbrk.kz uses <br><br> as paragraph separator).
  length(excluded.sections_json) >= length(articles.sections_json)
"""


def upsert(con: sqlite3.Connection, art: dict) -> str:
    cur = con.execute("SELECT json_array_length(json_extract(body_json,'$.blocks')) FROM articles WHERE id = ?", (art["id"],))
    row = cur.fetchone()
    before = row[0] if row else None
    con.execute(UPSERT_SQL, art)
    cur = con.execute("SELECT json_array_length(json_extract(body_json,'$.blocks')) FROM articles WHERE id = ?", (art["id"],))
    after = cur.fetchone()[0]
    if before is None:
        return f"inserted ({after} blocks)"
    if after > before:
        return f"updated ({before} → {after} blocks)"
    return f"unchanged ({after} blocks)"


# ─── modes ─────────────────────────────────────────────────────────────────────
def mode_rss(con: sqlite3.Connection) -> int:
    xml = fetch(f"{BASE}/rss.xml")
    if not xml:
        return 0
    n = 0
    for m in re.finditer(r"<link>(https?://fbrk\.kz/(?:news|articles)/[^<]+)</link>", xml):
        url = m.group(1).strip()
        art = parse_article(url)
        if not art:
            LOG.warning("skip %s", url)
            continue
        msg = upsert(con, art)
        con.commit()
        LOG.info("rss %s %s", url, msg)
        n += 1
        time.sleep(0.5)
    return n


def discover_sitemap_urls() -> list[str]:
    """Return all /news/<slug> and /articles/<slug> URLs from sitemap(s)."""
    seen: list[str] = []
    todo = [f"{BASE}/sitemap.xml"]
    visited: set[str] = set()
    while todo:
        u = todo.pop(0)
        if u in visited:
            continue
        visited.add(u)
        xml = fetch(u)
        if not xml:
            continue
        # nested sitemaps
        for sm in re.findall(r"<sitemap>\s*<loc>([^<]+)</loc>", xml):
            todo.append(sm.strip())
        # article URLs
        for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
            loc = loc.strip()
            p = urlparse(loc)
            if p.netloc.endswith("fbrk.kz") and ARTICLE_RE.match(p.path):
                seen.append(loc)
    # dedup, keep order
    out, dedup = [], set()
    for u in seen:
        if u not in dedup:
            dedup.add(u)
            out.append(u)
    return out


def mode_sitemap(con: sqlite3.Connection, only_missing: bool = True, limit: int = 0,
                 throttle: float = 0.4) -> int:
    urls = discover_sitemap_urls()
    LOG.info("sitemap discovered %d urls", len(urls))
    # which slugs are already "well-formed" in DB?
    have = set()
    if only_missing:
        for row in con.execute(
            "SELECT id FROM articles WHERE json_array_length(sections_json) >= 2"
        ):
            have.add(row[0])
        urls = [u for u in urls if slug_from_url(u) not in have]
        LOG.info("after only_missing filter: %d urls", len(urls))
    if limit:
        urls = urls[:limit]
    n_ok = n_err = 0
    t0 = time.time()
    for i, url in enumerate(urls, 1):
        try:
            art = parse_article(url)
            if not art:
                n_err += 1
                continue
            msg = upsert(con, art)
            con.commit()
            n_ok += 1
            if i % 25 == 0:
                rate = i / max(time.time() - t0, 0.1)
                LOG.info("[%d/%d] %.1f/s ok=%d err=%d  %s %s",
                         i, len(urls), rate, n_ok, n_err, url, msg)
        except Exception as e:
            n_err += 1
            LOG.exception("err %s: %s", url, e)
        time.sleep(throttle)
    LOG.info("sitemap done ok=%d err=%d in %.1fs", n_ok, n_err, time.time() - t0)
    return n_ok


def mode_one(con: sqlite3.Connection, url: str) -> int:
    art = parse_article(url)
    if not art:
        LOG.error("could not parse %s", url)
        return 0
    msg = upsert(con, art)
    con.commit()
    LOG.info("one %s %s", url, msg)
    return 1


# ─── CLI ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["rss", "sitemap", "one"])
    ap.add_argument("url", nargs="?")
    ap.add_argument("--all", action="store_true",
                    help="(sitemap) also re-fetch articles already at >=2 blocks")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--throttle", type=float, default=0.4,
                    help="seconds between requests (default 0.4)")
    ap.add_argument("--no-regen", action="store_true",
                    help="skip publish.regenerate_data_js() at the end")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    n = 0
    if args.mode == "rss":
        n = mode_rss(con)
    elif args.mode == "sitemap":
        n = mode_sitemap(con, only_missing=not args.all, limit=args.limit, throttle=args.throttle)
    elif args.mode == "one":
        if not args.url:
            ap.error("one requires <url>")
        n = mode_one(con, args.url)

    con.close()

    if n > 0 and not args.no_regen:
        try:
            from app.publish import regenerate_data_js
            res = regenerate_data_js()
            LOG.info("regenerate_data_js: %s", res)
        except Exception as e:
            LOG.error("regenerate_data_js failed: %s", e)

    print(f"INGEST DONE: {n} articles processed")


if __name__ == "__main__":
    main()
