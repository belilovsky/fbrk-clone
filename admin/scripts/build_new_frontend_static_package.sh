#!/usr/bin/env bash
set -euo pipefail

# Build a Plesk/File-Manager delta package for new.fbrk.kz.
# This does not mutate production. Upload the resulting files only after a
# normal web-root snapshot/rollback check on the target hosting.

PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-https://new.fbrk.kz}"
BACKEND_ORIGIN="${BACKEND_ORIGIN:-https://fbrk.qdev.run}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
ASSET_VERSION="${ASSET_VERSION:-$(date -u +%Y%m%d%H%M)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
OUT_DIR="${1:-${REPO_ROOT}/../fbrk_audit/new-fbrk-deploy-${STAMP}}"

mkdir -p "${OUT_DIR}/css" "${OUT_DIR}/js" "${OUT_DIR}/fonts/avds"

rewrite_public_html() {
  sed -E \
    -e "s#https://fbrk.qdev.run#${PUBLIC_ORIGIN}#g" \
    -e "s#\\?v=[0-9]+#?v=${ASSET_VERSION}#g"
}

cd "${REPO_ROOT}"

for file in index.html archive.html about.html article.html contacts.html privacy.html search.html sitemap.html 404.html .htaccess; do
  rewrite_public_html < "${file}" > "${OUT_DIR}/${file}"
done

cp js/app.js "${OUT_DIR}/js/app.js"
cp css/style.css "${OUT_DIR}/css/style.css"

curl -fsSL "${BACKEND_ORIGIN}/fonts/avds/avds-fonts.css" -o "${OUT_DIR}/fonts/avds/avds-fonts.css"
python3 - "${OUT_DIR}/fonts/avds/avds-fonts.css" "${BACKEND_ORIGIN}" "${OUT_DIR}/fonts/avds" <<'PY'
import pathlib
import re
import sys
import urllib.request
from urllib.parse import urljoin

css_path = pathlib.Path(sys.argv[1])
backend_origin = sys.argv[2].rstrip("/") + "/"
fonts_dir = pathlib.Path(sys.argv[3])

css = css_path.read_text(encoding="utf-8")
urls = sorted(set(re.findall(r"url\(['\"]?([^)'\"\s]+)['\"]?\)", css)))
base = urljoin(backend_origin, "fonts/avds/")

for raw in urls:
    if raw.startswith("data:"):
        continue
    url = raw if raw.startswith(("http://", "https://")) else urljoin(base, raw)
    name = pathlib.PurePosixPath(raw.split("?", 1)[0]).name
    if not name:
        raise SystemExit(f"cannot resolve font url: {raw}")
    target = fonts_dir / name
    with urllib.request.urlopen(url, timeout=30) as response:
        target.write_bytes(response.read())
    if target.stat().st_size == 0:
        raise SystemExit(f"empty font downloaded: {target}")

print(f"AVDS_FONT_FILES={len([p for p in fonts_dir.iterdir() if p.suffix == '.woff2'])}")
PY

cat > "${OUT_DIR}/js/runtime-config.js" <<EOF
// Runtime overrides for split hosting.
window.FBRK_PUBLIC_ORIGIN = '${PUBLIC_ORIGIN}';
window.FBRK_BACKEND_ORIGIN = '${BACKEND_ORIGIN}';
window.__FBRK_V = '${ASSET_VERSION}';
EOF

curl -fsSL "${BACKEND_ORIGIN}/js/data.js" -o "${OUT_DIR}/js/data.js"
curl -fsSL "${BACKEND_ORIGIN}/js/data-archive.js" -o "${OUT_DIR}/js/data-archive.js"
curl -fsSL "${BACKEND_ORIGIN}/js/article-full.js" -o "${OUT_DIR}/js/article-full.js"
curl -fsSL "${BACKEND_ORIGIN}/js/search-index.js" -o "${OUT_DIR}/js/search-index.js"
curl -fsSL "${BACKEND_ORIGIN}/robots.txt" | rewrite_public_html > "${OUT_DIR}/robots.txt"
curl -fsSL "${BACKEND_ORIGIN}/sitemap.xml" | rewrite_public_html > "${OUT_DIR}/sitemap.xml"
curl -fsSL "${BACKEND_ORIGIN}/feed.xml" | rewrite_public_html > "${OUT_DIR}/feed.xml"

python3 - "$OUT_DIR" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])

def parse_js(path: pathlib.Path, marker: str) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit(f"marker missing in {path}")
    payload = text[idx + len(marker):].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)

data = parse_js(out / "js" / "data.js", "const FBRK_DATA =")
archive = parse_js(out / "js" / "data-archive.js", "window.ARTICLES_ARCHIVE =")
article_full = parse_js(out / "js" / "article-full.js", "window.ARTICLE_FULL =")
search_index = parse_js(out / "js" / "search-index.js", "const FBRK_SEARCH_INDEX =")

print(f"OUT_DIR={out}")
print(f"DATA_JS_ARTICLES={len(data.get('articles') or [])}")
print(f"DATA_JS_TOTAL={data.get('totalCount')}")
print(f"ARCHIVE_ARTICLES={len(archive.get('articles') or [])}")
print(f"ARTICLE_FULL_ARTICLES={len(article_full.get('articles') or [])}")
print(f"SEARCH_INDEX_ITEMS={len(search_index.get('items') or [])}")
PY
