#!/usr/bin/env bash
set -euo pipefail

# Build a Plesk/File-Manager delta package for new.fbrk.kz.
# This does not mutate production. Upload the resulting files only after a
# normal web-root snapshot/rollback check on the target hosting.

PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-https://new.fbrk.kz}"
BACKEND_ORIGIN="${BACKEND_ORIGIN:-https://fbrk.qdev.run}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${1:-${REPO_ROOT}/../fbrk_audit/new-fbrk-deploy-${STAMP}}"

mkdir -p "${OUT_DIR}/css" "${OUT_DIR}/js"

rewrite_host() {
  sed "s#https://fbrk.qdev.run#${PUBLIC_ORIGIN}#g"
}

cd "${REPO_ROOT}"

for file in index.html archive.html about.html article.html 404.html; do
  rewrite_host < "${file}" > "${OUT_DIR}/${file}"
done

cp js/app.js "${OUT_DIR}/js/app.js"
cp css/style.css "${OUT_DIR}/css/style.css"

cat > "${OUT_DIR}/js/runtime-config.js" <<EOF
// Runtime overrides for split hosting.
window.FBRK_PUBLIC_ORIGIN = '${PUBLIC_ORIGIN}';
window.FBRK_BACKEND_ORIGIN = '${BACKEND_ORIGIN}';
EOF

curl -fsSL "${BACKEND_ORIGIN}/js/data.js" -o "${OUT_DIR}/js/data.js"
curl -fsSL "${BACKEND_ORIGIN}/js/data-archive.js" -o "${OUT_DIR}/js/data-archive.js"
curl -fsSL "${BACKEND_ORIGIN}/js/article-full.js" -o "${OUT_DIR}/js/article-full.js"
curl -fsSL "${BACKEND_ORIGIN}/robots.txt" | rewrite_host > "${OUT_DIR}/robots.txt"
curl -fsSL "${BACKEND_ORIGIN}/sitemap.xml" | rewrite_host > "${OUT_DIR}/sitemap.xml"
curl -fsSL "${BACKEND_ORIGIN}/feed.xml" | rewrite_host > "${OUT_DIR}/feed.xml"

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

print(f"OUT_DIR={out}")
print(f"DATA_JS_ARTICLES={len(data.get('articles') or [])}")
print(f"DATA_JS_TOTAL={data.get('totalCount')}")
print(f"ARCHIVE_ARTICLES={len(archive.get('articles') or [])}")
print(f"ARTICLE_FULL_ARTICLES={len(article_full.get('articles') or [])}")
PY
