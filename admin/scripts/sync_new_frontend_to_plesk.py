#!/usr/bin/env python3
"""Sync generated split-frontend payloads from the VPS backend to Plesk.

The script intentionally keeps Plesk credentials in an external env file. It
does not mutate the SQLite DB or the backend process; it only uploads static
files to the configured Plesk File Manager directory when hashes drift.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from uuid import uuid4


DEFAULT_PUBLIC_ORIGIN = "https://new.fbrk.kz"
DEFAULT_BACKEND_ORIGIN = "https://fbrk.qdev.run"
DEFAULT_WEB_ROOT = "/var/www/fbrk.qdev.run"
DEFAULT_PLESK_ROOT = "/new.fbrk.kz"
GENERATED_FILES = ("data.js", "data-archive.js", "article-full.js", "search-index.js")
DATA_FILES = ("videos.json",)
ROOT_FILES = (
    "index.html",
    "archive.html",
    "about.html",
    "article.html",
    "contacts.html",
    "privacy.html",
    "search.html",
    "sitemap.html",
    "404.html",
)
SEO_FILES = ("robots.txt", "sitemap.xml", "feed.xml")

HTACCESS_TEXT = """# Pretty article URLs: /a/<slug> -> /article.html?id=<slug>&spa=1
RewriteEngine On
RewriteBase /

# Use the AV DS 404 page instead of the default Plesk error document.
ErrorDocument 404 /404.html

# Skip if request is for an existing file or directory.
RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]

# /a/<slug> -> internal article.html
RewriteRule ^a/([A-Za-z0-9_\\-]+)/?$ /article.html?id=$1&spa=1 [L,QSA]

# Cache stable static assets, but never freeze generated article payloads.
<IfModule mod_headers.c>
  <FilesMatch "\\.(css|js|svg|png|jpg|jpeg|webp|woff2)$">
    Header set Cache-Control "public, max-age=86400"
  </FilesMatch>

  <FilesMatch "^(data|data-archive|article-full|search-index)\\.js$">
    Header set Cache-Control "no-cache, no-store, must-revalidate"
    Header set Pragma "no-cache"
    Header set Expires "0"
  </FilesMatch>
</IfModule>
"""


class SyncError(RuntimeError):
    pass


def load_env_file(path: str | None) -> None:
    if not path:
        return
    env_path = Path(path)
    if not env_path.exists():
        raise SyncError(f"env file does not exist: {env_path}")
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SyncError(f"missing required env var: {name}")
    return value


def fetch_bytes(url: str, *, timeout: int = 45, cache_bust: bool = False) -> bytes:
    if cache_bust:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}_sync={int(time.time())}"
    request = urllib.request.Request(
        url,
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "fbrk-split-sync/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def url_sha(origin: str, path: str, *, cache_bust: bool = True) -> str:
    return sha256(fetch_bytes(f"{origin.rstrip('/')}/{path.lstrip('/')}", cache_bust=cache_bust))


def url_sha_or_missing(origin: str, path: str, *, cache_bust: bool = True) -> str:
    try:
        return url_sha(origin, path, cache_bust=cache_bust)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "missing"
        raise


def rewrite_public(text: str, public_origin: str, asset_version: str) -> str:
    text = text.replace(DEFAULT_BACKEND_ORIGIN, public_origin)
    text = text.replace("http://fbrk.qdev.run", public_origin)
    text = re.sub(r"\?v=\d+", f"?v={asset_version}", text)
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def referenced_upload_assets(out_dir: Path, web_root: Path) -> list[Path]:
    refs: set[str] = set()
    for name in GENERATED_FILES:
        payload = (out_dir / "js" / name).read_text(encoding="utf-8", errors="ignore")
        for raw in re.findall(r"""["'](/?img/uploads/[^"']+)["']""", payload):
            rel = urllib.parse.unquote(raw.replace("\\/", "/").split("?", 1)[0]).lstrip("/")
            if rel.startswith("img/uploads/") and ".." not in Path(rel).parts:
                refs.add(rel)

    web_root_resolved = web_root.resolve()
    assets: list[Path] = []
    for rel in sorted(refs):
        source = (web_root / rel).resolve()
        if not str(source).startswith(f"{web_root_resolved}{os.sep}"):
            raise SyncError(f"unsafe upload asset path: {rel}")
        if not source.exists():
            raise SyncError(f"referenced upload asset is missing in backend web-root: {source}")
        if source.is_file():
            target = out_dir / rel
            write_bytes(target, source.read_bytes())
            assets.append(target)
    return assets


def parse_article_full(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    marker = "window.ARTICLE_FULL ="
    idx = text.find(marker)
    if idx < 0:
        raise SyncError(f"article-full marker missing: {path}")
    payload = text[idx + len(marker):].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    parsed = json.loads(payload)
    articles = parsed.get("articles")
    if not isinstance(articles, list):
        raise SyncError(f"article-full articles missing: {path}")
    return articles


def absolute_public_url(public_origin: str, value: str) -> str:
    if not value:
        return f"{public_origin}/img/brand/logo-on-brand-640.png"
    if value.startswith(("http://", "https://")):
        return value
    return urllib.parse.urljoin(f"{public_origin}/", value.lstrip("/"))


def replace_meta(html_text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, html_text, count=1, flags=re.S)
    if count != 1:
        raise SyncError(f"article template pattern did not match: {pattern}")
    return updated


def render_static_article_shell(template: str, article: dict, public_origin: str) -> str:
    slug = str(article.get("slug") or article.get("id") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
        raise SyncError(f"unsafe article slug for static shell: {slug!r}")

    title = str(article.get("title") or "Материал").strip()
    dek = str(article.get("dek") or "").strip()
    summary_short = str(article.get("summaryShort") or "").strip()
    category = str(article.get("categoryLabel") or article.get("category") or "Материал").strip()
    date_iso = str(article.get("dateIso") or "").strip()
    image = absolute_public_url(public_origin, str(article.get("image") or ""))
    article_url = f"{public_origin}/a/{slug}"

    title_text = f"{title} — ФБРК"
    description = summary_short or dek or f"{category} ФБРК."

    page = template
    page = replace_meta(
        page,
        r"<title[^>]*>.*?</title>",
        f"<title data-article-title>{html.escape(title_text)}</title>",
    )
    page = replace_meta(
        page,
        r'<meta name="description" content="[^"]*" data-article-desc\s*/>',
        f'<meta name="description" content="{html.escape(description, quote=True)}" data-article-desc />',
    )
    page = replace_meta(
        page,
        r'<link rel="canonical" href="[^"]*" data-article-canonical\s*/>',
        f'<link rel="canonical" href="{html.escape(article_url, quote=True)}" data-article-canonical />',
    )
    page = replace_meta(
        page,
        r'<link rel="alternate" hreflang="ru" href="[^"]*" data-article-hreflang\s*/>',
        f'<link rel="alternate" hreflang="ru" href="{html.escape(article_url, quote=True)}" data-article-hreflang />',
    )

    replacements = {
        "data-article-og-title": title_text,
        "data-article-og-desc": description,
        "data-article-og-image": image,
        "data-article-og-url": article_url,
        "data-article-tw-title": title_text,
        "data-article-tw-desc": description,
        "data-article-tw-image": image,
    }
    for marker, value in replacements.items():
        page = replace_meta(
            page,
            rf'(<meta [^>]*content=")[^"]*("[^>]*{marker}[^>]*/>)',
            rf"\g<1>{html.escape(value, quote=True)}\g<2>",
        )

    json_ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "mainEntityOfPage": {"@type": "WebPage", "@id": article_url},
        "headline": title,
        "description": description,
        "image": [image],
        "datePublished": date_iso,
        "dateModified": date_iso,
        "author": {"@type": "Organization", "name": "ФБРК", "url": public_origin},
        "publisher": {
            "@type": "Organization",
            "name": "ФБРК",
            "logo": {
                "@type": "ImageObject",
                "url": f"{public_origin}/img/brand/logo-brand-256.png",
                "width": 256,
                "height": 256,
            },
        },
        "articleSection": category,
        "inLanguage": "ru",
        "isAccessibleForFree": True,
    }
    json_ld_text = json.dumps(json_ld, ensure_ascii=False, separators=(",", ":"))
    page = replace_meta(
        page,
        r"</head>",
        f'    <script type="application/ld+json" data-static-article-jsonld>{json_ld_text}</script>\n  </head>',
    )
    return page


def generate_static_article_shells(out_dir: Path, public_origin: str) -> list[Path]:
    template = (out_dir / "article.html").read_text(encoding="utf-8")
    articles = parse_article_full(out_dir / "js" / "article-full.js")
    generated: list[Path] = []
    for article in articles:
        slug = str(article.get("slug") or article.get("id") or "").strip()
        if not slug:
            continue
        target = out_dir / "a" / slug / "index.html"
        write_text(target, render_static_article_shell(template, article, public_origin))
        generated.append(target)
    return generated


def build_package(
    out_dir: Path,
    *,
    public_origin: str,
    backend_origin: str,
    web_root: Path,
    asset_version: str,
    include_static: bool,
    generate_article_pages: bool,
) -> list[Path]:
    uploaded: list[Path] = []
    for name in ROOT_FILES:
        source = web_root / name
        if not source.exists():
            raise SyncError(f"missing source HTML: {source}")
        target = out_dir / name
        write_text(target, rewrite_public(source.read_text(encoding="utf-8"), public_origin, asset_version))
        uploaded.append(target)

    htaccess = out_dir / ".htaccess"
    write_text(htaccess, HTACCESS_TEXT)
    uploaded.append(htaccess)

    runtime = out_dir / "js" / "runtime-config.js"
    write_text(
        runtime,
        "\n".join(
            [
                "// Runtime overrides for split hosting.",
                f"window.FBRK_PUBLIC_ORIGIN = '{public_origin}';",
                f"window.FBRK_BACKEND_ORIGIN = '{backend_origin}';",
                f"window.__FBRK_V = '{asset_version}';",
                "",
            ]
        ),
    )
    uploaded.append(runtime)

    for name in GENERATED_FILES:
        target = out_dir / "js" / name
        write_bytes(target, fetch_bytes(f"{backend_origin.rstrip('/')}/js/{name}", cache_bust=True))
        uploaded.append(target)

    for name in DATA_FILES:
        source = web_root / "data" / name
        if not source.exists():
            raise SyncError(f"missing source data file: {source}")
        target = out_dir / "data" / name
        write_bytes(target, source.read_bytes())
        uploaded.append(target)

    if generate_article_pages:
        uploaded.extend(generate_static_article_shells(out_dir, public_origin))

    uploaded.extend(referenced_upload_assets(out_dir, web_root))

    for name in SEO_FILES:
        raw = fetch_bytes(f"{backend_origin.rstrip('/')}/{name}", cache_bust=True).decode("utf-8")
        target = out_dir / name
        write_text(target, rewrite_public(raw, public_origin, asset_version))
        uploaded.append(target)

    if include_static:
        for rel in (
            "css/style.css",
            "css/av-ds/tokens.css",
            "js/app.js",
            "img/brand/logo.svg",
            "img/favicon.svg",
        ):
            source = web_root / rel
            if not source.exists():
                raise SyncError(f"missing source static file: {source}")
            target = out_dir / rel
            write_bytes(target, source.read_bytes())
            uploaded.append(target)

        font_css = fetch_bytes(f"{backend_origin.rstrip('/')}/fonts/avds/avds-fonts.css", cache_bust=True)
        font_css_path = out_dir / "fonts" / "avds" / "avds-fonts.css"
        write_bytes(font_css_path, font_css)
        uploaded.append(font_css_path)

        font_css_text = font_css.decode("utf-8", "ignore")
        for raw_url in sorted(set(re.findall(r"url\(['\"]?([^)'\"\s]+)['\"]?\)", font_css_text))):
            if raw_url.startswith("data:"):
                continue
            font_url = urllib.parse.urljoin(f"{backend_origin.rstrip('/')}/fonts/avds/", raw_url)
            font_name = Path(raw_url.split("?", 1)[0]).name
            if not font_name:
                raise SyncError(f"cannot resolve font URL: {raw_url}")
            target = out_dir / "fonts" / "avds" / font_name
            write_bytes(target, fetch_bytes(font_url, cache_bust=True))
            uploaded.append(target)

    return uploaded


class PleskClient:
    def __init__(self, base_url: str, login: str, password: str, domain_id: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.login = login
        self.password = password
        self.domain_id = domain_id
        self.context = ssl._create_unverified_context()
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies),
            urllib.request.HTTPSHandler(context=self.context),
        )
        self.token = ""

    def open(self, path: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
        url = path if path.startswith(("http://", "https://")) else f"{self.base_url}{path}"
        request = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with self.opener.open(request, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "ignore")[:500]
            raise SyncError(f"Plesk HTTP {exc.code} for {path}: {body}") from exc

    def login_session(self) -> None:
        self.open("/login_up.php")
        body = urllib.parse.urlencode(
            {
                "login_name": self.login,
                "passwd": self.password,
                "locale_id": os.environ.get("PLESK_LOCALE", "en-US"),
            }
        ).encode()
        self.open("/login_up.php", body, {"Content-Type": "application/x-www-form-urlencoded"})
        page = self.open(f"/smb/file-manager/list/domainId/{self.domain_id}").decode("utf-8", "ignore")
        match = re.search(r'id="forgery_protection_token" content="([^"]+)"', page)
        if not match:
            raise SyncError("Plesk login succeeded but CSRF token was not found")
        self.token = match.group(1)

    def upload_file(self, current_dir: str, file_path: Path) -> None:
        boundary = f"----FBRKSync{uuid4().hex}"
        body = bytearray()

        def add_field(name: str, value: str) -> None:
            body.extend(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n".encode()
            )

        def add_file(field_name: str, filename: str, payload: bytes) -> None:
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            body.extend(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                f"Content-Type: {mime}\r\n\r\n".encode()
            )
            body.extend(payload)
            body.extend(b"\r\n")

        add_field("forgery_protection_token", self.token)
        field_name = urllib.parse.quote(file_path.name, safe="-_.!~*'()")
        add_file(field_name, file_path.name, file_path.read_bytes())
        body.extend(f"--{boundary}--\r\n".encode())

        query = urllib.parse.urlencode({"currentDir": current_dir, "recursively": "1"})
        response = self.open(
            f"/smb/file-manager/upload/domainId/{self.domain_id}/?{query}",
            bytes(body),
            {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        try:
            payload = json.loads(response.decode("utf-8", "ignore"))
        except json.JSONDecodeError as exc:
            raise SyncError(f"bad Plesk upload response for {file_path}: {response[:200]!r}") from exc
        if payload.get("status") != "SUCCESS":
            raise SyncError(f"Plesk upload failed for {file_path}: {payload}")


def package_upload_plan(files: list[Path], out_dir: Path, plesk_root: str) -> list[tuple[str, Path]]:
    plan: list[tuple[str, Path]] = []
    for file_path in files:
        rel_parent = file_path.relative_to(out_dir).parent.as_posix()
        current_dir = plesk_root.rstrip("/")
        if rel_parent != ".":
            current_dir = f"{current_dir}/{rel_parent}"
        plan.append((current_dir, file_path))
    return plan


def run_linkage_check(script_dir: Path, public_origin: str, backend_origin: str) -> None:
    checker = script_dir / "check_split_linkage.sh"
    if not checker.exists():
        print(f"WARN: checker missing: {checker}", file=sys.stderr)
        return
    subprocess.run([str(checker), public_origin, backend_origin, "--strict"], check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=os.environ.get("PLESK_SYNC_ENV"))
    parser.add_argument("--force", action="store_true", help="upload even if generated file hashes already match")
    parser.add_argument("--full", action="store_true", help="also upload css/app.js/AV DS fonts")
    parser.add_argument("--no-verify", action="store_true", help="skip final strict linkage check")
    parser.add_argument("--dry-run", action="store_true", help="build package and print upload plan without uploading")
    parser.add_argument("--keep-package", action="store_true", help="keep the generated package after a successful upload")
    args = parser.parse_args(argv)

    load_env_file(args.env_file)

    public_origin = os.environ.get("PUBLIC_ORIGIN", DEFAULT_PUBLIC_ORIGIN).rstrip("/")
    backend_origin = os.environ.get("BACKEND_ORIGIN", DEFAULT_BACKEND_ORIGIN).rstrip("/")
    script_dir = Path(__file__).resolve().parent
    web_root = Path(os.environ.get("FBRK_WEB_ROOT", DEFAULT_WEB_ROOT))
    if not web_root.exists():
        repo_root = script_dir.parent.parent
        if (repo_root / "index.html").exists():
            web_root = repo_root
    plesk_root = os.environ.get("PLESK_ROOT_DIR", DEFAULT_PLESK_ROOT).rstrip("/")
    domain_id = os.environ.get("PLESK_DOMAIN_ID", "1507")

    backend_hashes = {name: url_sha(backend_origin, f"js/{name}") for name in GENERATED_FILES}
    public_hashes = {name: url_sha_or_missing(public_origin, f"js/{name}") for name in GENERATED_FILES}
    drift = [name for name in GENERATED_FILES if backend_hashes[name] != public_hashes[name]]

    print(f"PUBLIC_ORIGIN={public_origin}")
    print(f"BACKEND_ORIGIN={backend_origin}")
    print(f"DRIFT_FILES={','.join(drift) if drift else '-'}")
    for name in GENERATED_FILES:
        print(f"{name}: backend={backend_hashes[name]} public={public_hashes[name]}")

    if not args.force and not drift:
        print("STATUS=already-synced")
        if not args.no_verify:
            run_linkage_check(script_dir, public_origin, backend_origin)
        return 0

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    asset_version = os.environ.get("ASSET_VERSION", dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S"))
    out_root = Path(os.environ.get("PLESK_SYNC_WORKDIR", tempfile.gettempdir()))
    out_dir = out_root / f"fbrk-new-plesk-sync-{stamp}"
    files = build_package(
        out_dir,
        public_origin=public_origin,
        backend_origin=backend_origin,
        web_root=web_root,
        asset_version=asset_version,
        include_static=args.full,
        generate_article_pages=os.environ.get("GENERATE_STATIC_ARTICLE_PAGES") == "1",
    )
    plan = package_upload_plan(files, out_dir, plesk_root)

    print(f"PACKAGE_DIR={out_dir}")
    print(f"ASSET_VERSION={asset_version}")
    print(f"UPLOAD_FILES={len(plan)}")
    for current_dir, file_path in plan:
        print(f"PLAN {current_dir}/{file_path.name}")

    if args.dry_run:
        print("STATUS=dry-run")
        return 0

    client = PleskClient(
        base_url=require_env("PLESK_BASE_URL"),
        login=require_env("PLESK_LOGIN"),
        password=require_env("PLESK_PASSWORD"),
        domain_id=domain_id,
    )
    client.login_session()
    for current_dir, file_path in plan:
        client.upload_file(current_dir, file_path)
        print(f"UPLOADED {current_dir}/{file_path.name}")

    if not args.no_verify:
        run_linkage_check(script_dir, public_origin, backend_origin)
    if not args.keep_package:
        shutil.rmtree(out_dir, ignore_errors=True)
    print("STATUS=synced")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
