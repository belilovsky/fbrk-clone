#!/usr/bin/env bash
set -euo pipefail

STATE_ROOT="${NEW_FBRK_STATE_ROOT:-/opt/new-fbrk-frontend/state}"
TARGET_ROOT="${NEW_FBRK_TARGET_ROOT:-/var/www/new.fbrk.kz}"
LAST_GOOD_ROOT="${STATE_ROOT}/last-good-web-root"
EXPECTED_HASH_FILE="${STATE_ROOT}/expected-app-sha256"
LOG_TAG="new-fbrk-frontend-guard"

log() {
  logger -t "${LOG_TAG}" "$*"
  printf '%s: %s\n' "${LOG_TAG}" "$*"
}

if [ ! -f "${EXPECTED_HASH_FILE}" ] || [ ! -f "${TARGET_ROOT}/js/app.js" ] || [ ! -f "${LAST_GOOD_ROOT}/js/app.js" ]; then
  log "state is not initialized; skipping drift check"
  exit 0
fi

expected_hash="$(tr -d '\r\n' < "${EXPECTED_HASH_FILE}")"
current_hash="$(shasum -a 256 "${TARGET_ROOT}/js/app.js" | awk '{print $1}')"

if [ "${current_hash}" = "${expected_hash}" ]; then
  exit 0
fi

log "hash drift detected current=${current_hash} expected=${expected_hash}; restoring last-good web root"
rsync -a --delete "${LAST_GOOD_ROOT}/" "${TARGET_ROOT}/"
chown -R www-data:www-data "${TARGET_ROOT}"

restored_hash="$(shasum -a 256 "${TARGET_ROOT}/js/app.js" | awk '{print $1}')"
if [ "${restored_hash}" != "${expected_hash}" ]; then
  log "restore failed restored=${restored_hash} expected=${expected_hash}"
  exit 1
fi

log "restore completed hash=${restored_hash}"
