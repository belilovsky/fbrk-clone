"""Scrape fbrk.kz articles and POST them to the admin API.

Usage:
    python3 scrape_fbrk.py urls_300.txt

Env vars:
    FBRK_API_BASE   default https://fbrk.qdev.run
    FBRK_API_KEY    admin key (required)

Each URL is scraped into:
    {id, slug, title, dek, author, date_iso, date_label, category,
     category_label, image, tags, source, sections[{h,p}], featured, published}

Image is downloaded from fbrk.kz (original, not resized),
uploaded via POST /api/upload (multipart), and the returned path is stored.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import html as html_mod
from datetime import datetime
from pathlib import Path

import requests

API_BASE = os.environ.get("FBRK_API_BASE", "https://fbrk.qdev.run")
API_KEY = os.environ.get("FBRK_API_KEY") or sys.exit("set FBRK_API_KEY")

MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15")


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>\s*<p[^>]*>", "\n\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html_mod.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def ru_date_label(iso: str) -> str:
    # iso like "2026-04-22" → "22 апреля 2026"
    try:
        dt = datetime.fromisoformat(iso)
    except Exception:
        return iso
    return f"{dt.day} {MONTHS_RU[dt.month-1]} {dt.year}"


def slug_from_url(url: str) -> str:
    # https://fbrk.kz/articles/slug  →  slug
    p = urllib.parse.urlparse(url).path
    parts = [x for x in p.split("/") if x]
    return parts[-1]


def parse_article(url: str, html: str) -> dict | None:
    # H1
    h1 = re.search(r"<h1[^>]*>(.+?)</h1>", html, re.S)
    if not h1:
        return None
    title = strip_tags(h1.group(1))

    # Date: <p class="post-date">DD.MM.YYYY HH:MM</p>
    dm = re.search(r'<p class="post-date"[^>]*>([^<]+)</p>', html)
    if dm:
        raw = dm.group(1).strip()
        m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", raw)
        if m:
            d, mo, y = m.groups()
            date_iso = f"{y}-{mo}-{d}"
        else:
            date_iso = datetime.utcnow().date().isoformat()
    else:
        date_iso = datetime.utcnow().date().isoformat()

    # Primary image (largest size)
    img_src = None
    img_match = re.search(
        r'<div class="wide-content primary-image[^"]*"[^>]*>\s*<img[^>]+src="([^"]+)"',
        html,
    )
    if img_match:
        img_src = img_match.group(1)
        # Strip Drupal image style, e.g. /sites/default/files/styles/wide/public/2026-04/foo.png?itok=xxx
        # → /sites/default/files/2026-04/foo.png
        img_src = re.sub(r"/styles/[^/]+/public/", "/", img_src)
        img_src = img_src.split("?")[0]
        if img_src.startswith("/"):
            img_src = "https://fbrk.kz" + img_src
        img_src = urllib.parse.unquote(img_src)

    # Body: .text-content field__item
    body_m = re.search(
        r'<div class="text-content[^"]*field field--name-body[^"]*field__item"[^>]*>(.+?)</div>\s*<ul class="links',
        html,
        re.S,
    )
    if not body_m:
        return None
    body_html = body_m.group(1)

    # Dek = first <p> before any h2/h3
    dek = ""
    sections: list[dict] = []

    # Split body by h2/h3 boundaries
    # First, find the lead paragraph before the first heading
    parts = re.split(r"(<h[23][^>]*>.*?</h[23]>)", body_html, flags=re.S)
    # parts[0] = pre-heading content; then alternating heading/content

    def clean_para(raw: str) -> str:
        # Convert inline HTML into plain text with soft line breaks.
        return strip_tags(raw)

    def collect_paragraphs(chunk: str) -> list[str]:
        # Grab <p>, <ul>, <ol>, <blockquote> blocks; drop everything else.
        blocks: list[str] = []
        for m in re.finditer(r"<(p|ul|ol|blockquote)[^>]*>(.*?)</\1>", chunk, re.S):
            tag = m.group(1)
            inner = m.group(2)
            if tag in ("ul", "ol"):
                lis = re.findall(r"<li[^>]*>(.*?)</li>", inner, re.S)
                joined = "\n".join(f"• {clean_para(li)}" for li in lis if clean_para(li))
                if joined:
                    blocks.append(joined)
            elif tag == "blockquote":
                txt = clean_para(inner)
                if txt:
                    blocks.append("«" + txt + "»")
            else:
                txt = clean_para(inner)
                if txt:
                    blocks.append(txt)
        return blocks

    pre_paras = collect_paragraphs(parts[0])
    if pre_paras:
        dek = pre_paras[0]
        rest = pre_paras[1:]
        if rest:
            # They form the first section without a header
            sections.append({"h": "", "p": "\n\n".join(rest)})

    # Walk the rest pairwise: heading, body, heading, body, ...
    it = iter(parts[1:])
    for head_raw in it:
        try:
            body_raw = next(it)
        except StopIteration:
            break
        head_txt = clean_para(head_raw)
        para_blocks = collect_paragraphs(body_raw)
        if head_txt or para_blocks:
            sections.append({
                "h": head_txt,
                "p": "\n\n".join(para_blocks),
            })

    return {
        "slug": slug_from_url(url),
        "title": title,
        "dek": dek,
        "date_iso": date_iso,
        "date_label": ru_date_label(date_iso),
        "image_remote": img_src,
        "sections": sections,
        "source_url": url,
        # fields we'll fill default
        "author": "fbrk_news",
        "source": "fbrk.kz",
        "category": "news",
        "category_label": "Новости",
        "tags": [],
        "featured": False,
        "published": True,
    }


def upload_image(session: requests.Session, img_url: str) -> str | None:
    """Download image from fbrk.kz, upload to admin, return stored thumb path."""
    try:
        r = session.get(img_url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        # guess filename
        fn = os.path.basename(urllib.parse.urlparse(img_url).path) or "cover.jpg"
        mime = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            # Try to guess from extension
            ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png", "webp": "image/webp",
                    "gif": "image/gif"}.get(ext, "image/jpeg")
        files = {"file": (fn, r.content, mime)}
        u = session.post(
            f"{API_BASE}/api/upload",
            headers={"X-API-Key": API_KEY},
            files=files,
            timeout=60,
        )
        u.raise_for_status()
        data = u.json()
        # Admin returns {"web": "...", "thumb": "..."}
        return data.get("thumb") or data.get("web")
    except Exception as e:
        print(f"  ! image upload failed: {e}")
        return None


def upsert_article(session: requests.Session, article: dict) -> bool:
    # Admin expects a payload compatible with POST /api/articles
    payload = {
        "id": article["slug"],
        "slug": article["slug"],
        "title": article["title"],
        "dek": article["dek"],
        "author": article["author"],
        "date_iso": article["date_iso"],
        "date_label": article["date_label"],
        "category": article["category"],
        "category_label": article["category_label"],
        "image": article["image_local"],
        "tags": article["tags"],
        "source": article["source"],
        "sections": article["sections"],
        "featured": article["featured"],
        "published": article["published"],
        "source_url": article["source_url"],
    }
    r = session.post(
        f"{API_BASE}/api/articles",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"  ! upsert failed {r.status_code}: {r.text[:200]}")
        return False
    return True


def main() -> None:
    url_file = Path(sys.argv[1])
    urls = [u.strip() for u in url_file.read_text().splitlines() if u.strip()]

    session = requests.Session()
    session.headers["User-Agent"] = UA

    ok = 0
    failed = 0
    skipped = 0
    t0 = time.time()

    # Cache of which slugs already exist (to allow resumable runs)
    existing_resp = session.get(
        f"{API_BASE}/api/articles/list",
        headers={"X-API-Key": API_KEY}, timeout=30,
    )
    existing = set()
    if existing_resp.status_code == 200:
        for a in existing_resp.json().get("articles", []):
            existing.add(a.get("slug") or a.get("id"))
    print(f"Already in DB: {len(existing)}")

    for i, url in enumerate(urls, 1):
        slug = slug_from_url(url)
        if slug in existing:
            skipped += 1
            if i % 25 == 0:
                print(f"[{i}/{len(urls)}] skipped (already imported)")
            continue

        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            art = parse_article(url, r.text)
            if not art:
                print(f"[{i}/{len(urls)}] ! parse failed: {url}")
                failed += 1
                continue

            if art["image_remote"]:
                art["image_local"] = upload_image(session, art["image_remote"])
            else:
                art["image_local"] = None

            if upsert_article(session, art):
                ok += 1
                if i % 10 == 0 or i < 5:
                    elapsed = time.time() - t0
                    rate = ok / elapsed if elapsed else 0
                    print(f"[{i}/{len(urls)}] ok: {art['title'][:60]}  "
                          f"({rate:.1f}/s, {ok}/{failed} ok/fail)")
            else:
                failed += 1
        except Exception as e:
            print(f"[{i}/{len(urls)}] ! error: {e}")
            failed += 1

        time.sleep(0.2)  # gentle

    # Final publish
    print(f"\nImport complete: {ok} new, {skipped} skipped, {failed} failed.")
    print("Triggering publish…")
    r = session.post(
        f"{API_BASE}/api/publish",
        headers={"X-API-Key": API_KEY}, timeout=60,
    )
    print(f"Publish HTTP {r.status_code}: {r.text[:200]}")


if __name__ == "__main__":
    main()
