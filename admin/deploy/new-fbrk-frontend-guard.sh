#!/usr/bin/env bash
set -euo pipefail

STATE_ROOT="${NEW_FBRK_STATE_ROOT:-/opt/new-fbrk-frontend/state}"
TARGET_ROOT="${NEW_FBRK_TARGET_ROOT:-/var/www/new.fbrk.kz}"
LAST_GOOD_ROOT="${STATE_ROOT}/last-good-web-root"
EXPECTED_HASH_FILE="${STATE_ROOT}/expected-app-sha256"
EXPECTED_MANIFEST_FILE="${STATE_ROOT}/expected-sha256s"
LOG_TAG="new-fbrk-frontend-guard"

log() {
  logger -t "${LOG_TAG}" "$*"
  printf '%s: %s\n' "${LOG_TAG}" "$*"
}

if [ ! -f "${LAST_GOOD_ROOT}/js/app.js" ]; then
  log "state is not initialized; skipping drift check"
  exit 0
fi

if [ -f "${EXPECTED_MANIFEST_FILE}" ]; then
  if (cd "${TARGET_ROOT}" && shasum -a 256 -c "${EXPECTED_MANIFEST_FILE}" >/dev/null 2>&1); then
    exit 0
  fi

  drift_reason="manifest"
  current_hash="$(shasum -a 256 "${TARGET_ROOT}/js/app.js" | awk '{print $1}')"
  expected_hash="$(awk '$2 == "js/app.js" {print $1; exit}' "${EXPECTED_MANIFEST_FILE}")"
else
  if [ ! -f "${EXPECTED_HASH_FILE}" ] || [ ! -f "${TARGET_ROOT}/js/app.js" ]; then
    log "state is not initialized; skipping drift check"
    exit 0
  fi

  expected_hash="$(tr -d '\r\n' < "${EXPECTED_HASH_FILE}")"
  current_hash="$(shasum -a 256 "${TARGET_ROOT}/js/app.js" | awk '{print $1}')"

  if [ "${current_hash}" = "${expected_hash}" ]; then
    exit 0
  fi
  drift_reason="app hash"
fi

log "${drift_reason} drift detected current_app=${current_hash} expected_app=${expected_hash}; restoring last-good web root"
rsync -a --delete "${LAST_GOOD_ROOT}/" "${TARGET_ROOT}/"
chown -R www-data:www-data "${TARGET_ROOT}"

restored_hash="$(shasum -a 256 "${TARGET_ROOT}/js/app.js" | awk '{print $1}')"
if [ "${restored_hash}" != "${expected_hash}" ]; then
  log "restore failed restored=${restored_hash} expected=${expected_hash}"
  exit 1
fi

if [ -f "${EXPECTED_MANIFEST_FILE}" ] && ! (cd "${TARGET_ROOT}" && shasum -a 256 -c "${EXPECTED_MANIFEST_FILE}" >/dev/null 2>&1); then
  log "restore failed manifest check"
  exit 1
fi

log "restore completed hash=${restored_hash}"
