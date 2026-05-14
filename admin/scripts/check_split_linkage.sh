#!/usr/bin/env bash
set -euo pipefail

NEW_ORIGIN="${1:-https://new.fbrk.kz}"
BACKEND_ORIGIN="${2:-https://fbrk.qdev.run}"
STRICT="${3:-}"

fail=0

http_code() {
  local url="$1"
  curl -sS -o /dev/null -w '%{http_code}' "$url"
}

extract_total_count() {
  local origin="$1"
  local value
  value="$(
    curl -fsS "${origin}/js/data.js" \
      | python3 -c '
import json, sys
origin = sys.argv[1]
text = sys.stdin.read().strip()
idx = text.find("{")
if idx < 0:
    sys.stderr.write(f"ERROR: bad data.js payload from {origin}\n")
    sys.exit(2)
payload = text[idx:]
if payload.endswith(";"):
    payload = payload[:-1]
obj = json.loads(payload)
total = obj.get("totalCount")
if not isinstance(total, int):
    sys.stderr.write(f"ERROR: totalCount missing in {origin}/js/data.js\n")
    sys.exit(3)
print(total)
' "$origin"
  )"
  if [ -z "$value" ]; then
    echo "ERROR: failed to parse totalCount from ${origin}/js/data.js" >&2
    return 1
  fi
  echo "$value"
}

extract_first_slug() {
  local origin="$1"
  local slug
  slug="$(
    curl -fsS "${origin}/js/data.js" \
      | python3 -c '
import json, sys
origin = sys.argv[1]
text = sys.stdin.read().strip()
idx = text.find("{")
if idx < 0:
    sys.stderr.write(f"ERROR: bad data.js payload from {origin}\n")
    sys.exit(2)
payload = text[idx:]
if payload.endswith(";"):
    payload = payload[:-1]
obj = json.loads(payload)
arts = obj.get("articles") or []
if not arts:
    sys.stderr.write(f"ERROR: empty articles in {origin}/js/data.js\n")
    sys.exit(3)
slug = arts[0].get("slug") or arts[0].get("id") or ""
if not slug:
    sys.stderr.write(f"ERROR: first article has no slug/id in {origin}/js/data.js\n")
    sys.exit(4)
print(slug)
' "$origin"
  )"
  if [ -z "$slug" ]; then
    echo "ERROR: failed to parse first slug from ${origin}/js/data.js" >&2
    return 1
  fi
  echo "$slug"
}

extract_canonical() {
  local url="$1"
  local canon
  canon="$(
    curl -fsS "$url" \
      | tr '\n' ' ' \
      | sed -n 's/.*<link rel="canonical" href="\([^"]*\)".*/\1/p' \
      | head -n1
  )"
  echo "$canon"
}

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
new_total="$(extract_total_count "$NEW_ORIGIN")"
backend_total="$(extract_total_count "$BACKEND_ORIGIN")"
delta=$((backend_total - new_total))

first_slug="$(extract_first_slug "$BACKEND_ORIGIN")"

new_home_code="$(http_code "${NEW_ORIGIN}/")"
new_archive_code="$(http_code "${NEW_ORIGIN}/archive.html")"
new_article_code="$(http_code "${NEW_ORIGIN}/a/${first_slug}")"
backend_home_code="$(http_code "${BACKEND_ORIGIN}/")"
backend_health_code="$(http_code "${BACKEND_ORIGIN}/admin/healthz")"

new_canonical_home="$(extract_canonical "${NEW_ORIGIN}/")"
new_canonical_article="$(extract_canonical "${NEW_ORIGIN}/a/${first_slug}")"

echo "CHECK_TS_UTC=${ts}"
echo "NEW_ORIGIN=${NEW_ORIGIN}"
echo "BACKEND_ORIGIN=${BACKEND_ORIGIN}"
echo "BACKEND_TOTAL=${backend_total}"
echo "NEW_TOTAL=${new_total}"
echo "DELTA_BACKEND_MINUS_NEW=${delta}"
echo "FIRST_BACKEND_SLUG=${first_slug}"
echo "HTTP_NEW_HOME=${new_home_code}"
echo "HTTP_NEW_ARCHIVE=${new_archive_code}"
echo "HTTP_NEW_ARTICLE=${new_article_code}"
echo "HTTP_BACKEND_HOME=${backend_home_code}"
echo "HTTP_BACKEND_ADMIN_HEALTHZ=${backend_health_code}"
echo "NEW_CANONICAL_HOME=${new_canonical_home}"
echo "NEW_CANONICAL_ARTICLE=${new_canonical_article}"

if [ "$STRICT" = "--strict" ]; then
  if [ "$backend_health_code" != "200" ]; then
    echo "FAIL: backend /admin/healthz is not 200" >&2
    fail=1
  fi
  if [ "$new_home_code" != "200" ] || [ "$new_archive_code" != "200" ] || [ "$new_article_code" != "200" ]; then
    echo "FAIL: one or more NEW endpoints are not 200" >&2
    fail=1
  fi
  if [ "$delta" -ne 0 ]; then
    echo "FAIL: new/front data.js is stale (delta=${delta})" >&2
    fail=1
  fi
  case "$new_canonical_home" in
    "${NEW_ORIGIN}"/*) : ;;
    *)
      echo "FAIL: new homepage canonical is not on NEW_ORIGIN" >&2
      fail=1
      ;;
  esac
fi

exit "$fail"
