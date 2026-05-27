#!/usr/bin/env python3
"""Build static sitemap.xml and a compact client-side search index."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://fbrk.kz"


def load_js_object(path: Path, const_name: str) -> dict:
    raw = path.read_text(encoding="utf-8")
    match = re.search(rf"(?:const\s+|window\.){re.escape(const_name)}\s*=\s*(\{{.*\}});?\s*$", raw, re.S)
    if not match:
        raise SystemExit(f"Could not parse {const_name} from {path}")
    return json.loads(match.group(1))


def file_lastmod(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def main() -> None:
    data = load_js_object(ROOT / "js" / "data-archive.js", "ARTICLES_ARCHIVE")
    articles = data.get("articles", [])
    static_paths = [
        "",
        "archive.html",
        "archive.html?cat=investigation",
        "archive.html?cat=news",
        "about.html",
        "contacts.html",
        "editorial-policy.html",
        "privacy.html",
        "search.html",
        "sitemap.html",
        "feed.xml",
    ]
    url_entries: list[tuple[str, str]] = []
    for path in static_paths:
      source = ROOT / (path.split("?")[0] or "index.html")
      url_entries.append((f"{BASE_URL}/{path}", file_lastmod(source) if source.exists() else file_lastmod(ROOT / "index.html")))
    for article in articles:
        slug = quote(str(article.get("slug") or article.get("id") or ""))
        if not slug:
            continue
        lastmod = str(article.get("dateIso") or file_lastmod(ROOT / "js" / "data-archive.js"))
        url_entries.append((f"{BASE_URL}/a/{slug}", lastmod))

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in url_entries:
        sitemap.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>")
    sitemap.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")

    index_items = []
    for article in articles:
        index_items.append({
            "id": article.get("id"),
            "slug": article.get("slug") or article.get("id"),
            "title": article.get("title", ""),
            "dek": article.get("dek", ""),
            "description": article.get("description", ""),
            "body": article.get("body", "")[:2400],
            "dateIso": article.get("dateIso", ""),
            "date": article.get("date", ""),
            "category": article.get("category", ""),
            "categoryLabel": article.get("categoryLabel", ""),
            "tags": article.get("tags", []),
        })
    payload = "const FBRK_SEARCH_INDEX = " + json.dumps({"items": index_items}, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (ROOT / "js" / "search-index.js").write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
