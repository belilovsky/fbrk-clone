#!/usr/bin/env bash
set -euo pipefail

NEW_ORIGIN="https://new.fbrk.kz"
BACKEND_ORIGIN="https://fbrk.qdev.run"
STRICT=""
FBRK_NEW_RESOLVE_IP="${FBRK_NEW_RESOLVE_IP:-}"
CURL_CONNECT_TIMEOUT="${CURL_CONNECT_TIMEOUT:-8}"
CURL_MAX_TIME="${CURL_MAX_TIME:-120}"
new_origin_set=0
backend_origin_set=0

for arg in "$@"; do
  case "$arg" in
    --strict)
      STRICT="--strict"
      ;;
    http://*|https://*)
      if [ "$new_origin_set" -eq 0 ]; then
        NEW_ORIGIN="${arg%/}"
        new_origin_set=1
      elif [ "$backend_origin_set" -eq 0 ]; then
        BACKEND_ORIGIN="${arg%/}"
        backend_origin_set=1
      else
        echo "ERROR: unexpected origin argument: ${arg}" >&2
        exit 2
      fi
      ;;
    *)
      echo "ERROR: unexpected argument: ${arg}" >&2
      exit 2
      ;;
  esac
done

fail=0
CURL_NEW_RESOLVE_ARGS=()

if [ -n "$FBRK_NEW_RESOLVE_IP" ]; then
  NEW_HOST="${NEW_ORIGIN#*://}"
  NEW_HOST="${NEW_HOST%%/*}"
  NEW_HOST="${NEW_HOST%%:*}"
  if [ -n "$NEW_HOST" ]; then
    CURL_NEW_RESOLVE_ARGS=(
      --resolve "${NEW_HOST}:443:${FBRK_NEW_RESOLVE_IP}"
      --resolve "${NEW_HOST}:80:${FBRK_NEW_RESOLVE_IP}"
    )
  fi
fi

curl_url() {
  local url="$1"
  shift
  if [[ "$url" == "${NEW_ORIGIN}"* ]] && [ "${#CURL_NEW_RESOLVE_ARGS[@]}" -gt 0 ]; then
    curl --connect-timeout "${CURL_CONNECT_TIMEOUT}" --max-time "${CURL_MAX_TIME}" "${CURL_NEW_RESOLVE_ARGS[@]}" "$@" "$url"
  else
    curl --connect-timeout "${CURL_CONNECT_TIMEOUT}" --max-time "${CURL_MAX_TIME}" "$@" "$url"
  fi
}

http_code() {
  local url="$1"
  curl_url "$url" -sS -o /dev/null -w '%{http_code}'
}

extract_total_count() {
  local origin="$1"
  local value
  value="$(
    curl_url "${origin}/js/data.js" -fsS \
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
    curl_url "${origin}/js/data.js" -fsS \
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

extract_article_full_count() {
  local origin="$1"
  local value
  value="$(
    curl_url "${origin}/js/article-full.js" -fsS \
      | python3 -c '
import json, sys
origin = sys.argv[1]
text = sys.stdin.read().strip()
marker = "window.ARTICLE_FULL ="
idx = text.find(marker)
if idx < 0:
    sys.stderr.write(f"ERROR: bad article-full.js payload from {origin}\n")
    sys.exit(2)
payload = text[idx + len(marker):].strip()
if payload.endswith(";"):
    payload = payload[:-1]
obj = json.loads(payload)
arts = obj.get("articles") or []
print(len(arts))
' "$origin"
  )"
  if [ -z "$value" ]; then
    echo "ERROR: failed to parse article-full.js from ${origin}" >&2
    return 1
  fi
  echo "$value"
}

sha256_url() {
  local url="$1"
  curl_url "$url" -fsS \
    | python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
}

extract_canonical() {
  local url="$1"
  local canon
  canon="$(
    curl_url "$url" -fsS \
      | tr '\n' ' ' \
      | sed -n 's/.*<link rel="canonical" href="\([^"]*\)".*/\1/p' \
      | head -n1
  )"
  echo "$canon"
}

extract_cache_control() {
  local url="$1"
  curl_url "$url" -sSI \
    | tr -d '\r' \
    | awk 'tolower($1) == "cache-control:" {sub(/^[^:]*:[[:space:]]*/, "", $0); print; exit}'
}

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
new_total="$(extract_total_count "$NEW_ORIGIN")"
backend_total="$(extract_total_count "$BACKEND_ORIGIN")"
delta=$((backend_total - new_total))
new_article_full_total="$(extract_article_full_count "$NEW_ORIGIN")"
backend_article_full_total="$(extract_article_full_count "$BACKEND_ORIGIN")"

backend_data_sha="$(sha256_url "${BACKEND_ORIGIN}/js/data.js")"
new_data_sha="$(sha256_url "${NEW_ORIGIN}/js/data.js")"
backend_archive_sha="$(sha256_url "${BACKEND_ORIGIN}/js/data-archive.js")"
new_archive_sha="$(sha256_url "${NEW_ORIGIN}/js/data-archive.js")"
backend_article_full_sha="$(sha256_url "${BACKEND_ORIGIN}/js/article-full.js")"
new_article_full_sha="$(sha256_url "${NEW_ORIGIN}/js/article-full.js")"
backend_videos_sha="$(sha256_url "${BACKEND_ORIGIN}/data/videos.json")"
new_videos_sha="$(sha256_url "${NEW_ORIGIN}/data/videos.json")"

first_slug="$(extract_first_slug "$BACKEND_ORIGIN")"

new_home_code="$(http_code "${NEW_ORIGIN}/")"
new_archive_code="$(http_code "${NEW_ORIGIN}/archive.html")"
new_article_code="$(http_code "${NEW_ORIGIN}/a/${first_slug}")"
new_videos_code="$(http_code "${NEW_ORIGIN}/data/videos.json")"
backend_home_code="$(http_code "${BACKEND_ORIGIN}/")"
backend_health_code="$(http_code "${BACKEND_ORIGIN}/admin/healthz")"

new_canonical_home="$(extract_canonical "${NEW_ORIGIN}/")"
new_canonical_article="$(extract_canonical "${NEW_ORIGIN}/a/${first_slug}")"
new_home_cache_control="$(extract_cache_control "${NEW_ORIGIN}/")"
new_article_cache_control="$(extract_cache_control "${NEW_ORIGIN}/a/${first_slug}")"

echo "CHECK_TS_UTC=${ts}"
echo "NEW_ORIGIN=${NEW_ORIGIN}"
echo "BACKEND_ORIGIN=${BACKEND_ORIGIN}"
echo "BACKEND_TOTAL=${backend_total}"
echo "NEW_TOTAL=${new_total}"
echo "DELTA_BACKEND_MINUS_NEW=${delta}"
echo "BACKEND_ARTICLE_FULL_TOTAL=${backend_article_full_total}"
echo "NEW_ARTICLE_FULL_TOTAL=${new_article_full_total}"
echo "BACKEND_DATA_SHA256=${backend_data_sha}"
echo "NEW_DATA_SHA256=${new_data_sha}"
echo "BACKEND_ARCHIVE_SHA256=${backend_archive_sha}"
echo "NEW_ARCHIVE_SHA256=${new_archive_sha}"
echo "BACKEND_ARTICLE_FULL_SHA256=${backend_article_full_sha}"
echo "NEW_ARTICLE_FULL_SHA256=${new_article_full_sha}"
echo "BACKEND_VIDEOS_SHA256=${backend_videos_sha}"
echo "NEW_VIDEOS_SHA256=${new_videos_sha}"
echo "FIRST_BACKEND_SLUG=${first_slug}"
echo "HTTP_NEW_HOME=${new_home_code}"
echo "HTTP_NEW_ARCHIVE=${new_archive_code}"
echo "HTTP_NEW_ARTICLE=${new_article_code}"
echo "HTTP_NEW_VIDEOS=${new_videos_code}"
echo "HTTP_BACKEND_HOME=${backend_home_code}"
echo "HTTP_BACKEND_ADMIN_HEALTHZ=${backend_health_code}"
echo "NEW_CANONICAL_HOME=${new_canonical_home}"
echo "NEW_CANONICAL_ARTICLE=${new_canonical_article}"
echo "NEW_HOME_CACHE_CONTROL=${new_home_cache_control:-missing}"
echo "NEW_ARTICLE_CACHE_CONTROL=${new_article_cache_control:-missing}"

if [ "$STRICT" = "--strict" ]; then
  if [ "$backend_health_code" != "200" ]; then
    echo "FAIL: backend /admin/healthz is not 200" >&2
    fail=1
  fi
  if [ "$new_home_code" != "200" ] || [ "$new_archive_code" != "200" ] || [ "$new_article_code" != "200" ] || [ "$new_videos_code" != "200" ]; then
    echo "FAIL: one or more NEW endpoints are not 200" >&2
    fail=1
  fi
  if [ "$delta" -ne 0 ]; then
    echo "FAIL: new/front data.js is stale (delta=${delta})" >&2
    fail=1
  fi
  if [ "$backend_article_full_total" -ne "$backend_total" ] || [ "$new_article_full_total" -ne "$backend_total" ]; then
    echo "FAIL: article-full.js is missing or stale" >&2
    fail=1
  fi
  if [ "$backend_data_sha" != "$new_data_sha" ]; then
    echo "FAIL: new data.js hash differs from backend" >&2
    fail=1
  fi
  if [ "$backend_archive_sha" != "$new_archive_sha" ]; then
    echo "FAIL: new data-archive.js hash differs from backend" >&2
    fail=1
  fi
  if [ "$backend_article_full_sha" != "$new_article_full_sha" ]; then
    echo "FAIL: new article-full.js hash differs from backend" >&2
    fail=1
  fi
  if [ "$backend_videos_sha" != "$new_videos_sha" ]; then
    echo "FAIL: new data/videos.json hash differs from backend" >&2
    fail=1
  fi
  new_home_cache_control_lc="$(printf '%s' "${new_home_cache_control}" | tr '[:upper:]' '[:lower:]')"
  new_article_cache_control_lc="$(printf '%s' "${new_article_cache_control}" | tr '[:upper:]' '[:lower:]')"
  case "${new_home_cache_control_lc}" in
    *no-cache*|*no-store*) : ;;
    *)
      echo "FAIL: new home shell is missing no-cache cache-control" >&2
      fail=1
      ;;
  esac
  case "${new_article_cache_control_lc}" in
    *no-cache*|*no-store*) : ;;
    *)
      echo "FAIL: new article shell is missing no-cache cache-control" >&2
      fail=1
      ;;
  esac
  case "$new_canonical_home" in
    "${NEW_ORIGIN}"/*) : ;;
    *)
      echo "FAIL: new homepage canonical is not on NEW_ORIGIN" >&2
      fail=1
      ;;
  esac
  case "$new_canonical_article" in
    "${NEW_ORIGIN}/a/${first_slug}") : ;;
    *)
      echo "FAIL: new article canonical is not the static article URL" >&2
      fail=1
      ;;
  esac
fi

exit "$fail"
