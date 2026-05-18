#!/usr/bin/env bash
# Sync the generated split frontend to the dedicated new.fbrk.kz VPS.
#
# This intentionally reuses the package builder from sync_new_frontend_to_plesk.py
# but deploys with SSH/rsync instead of the Plesk File Manager API.
set -euo pipefail

PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-https://new.fbrk.kz}"
BACKEND_ORIGIN="${BACKEND_ORIGIN:-https://fbrk.qdev.run}"
FBRK_WEB_ROOT="${FBRK_WEB_ROOT:-/var/www/fbrk.qdev.run}"
TARGET_HOST="${NEW_FBRK_VPS_HOST:-213.155.22.190}"
TARGET_USER="${NEW_FBRK_VPS_USER:-root}"
TARGET_ROOT="${NEW_FBRK_VPS_ROOT:-/var/www/new.fbrk.kz}"
TARGET="${TARGET_USER}@${TARGET_HOST}"
WORKDIR="${NEW_FBRK_SYNC_WORKDIR:-/tmp}"
ASSET_VERSION="${ASSET_VERSION:-$(date -u +%Y%m%d%H%M%S)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLESK_BUILDER="${SCRIPT_DIR}/sync_new_frontend_to_plesk.py"

if [[ ! -x "${PLESK_BUILDER}" && ! -f "${PLESK_BUILDER}" ]]; then
  echo "ERROR: package builder not found: ${PLESK_BUILDER}" >&2
  exit 1
fi

log_file="$(mktemp)"
package_dir=""
cleanup() {
  rm -f "${log_file}"
  if [[ -n "${package_dir}" && -d "${package_dir}" ]]; then
    rm -rf "${package_dir}"
  fi
}
trap cleanup EXIT

PUBLIC_ORIGIN="${PUBLIC_ORIGIN}" \
BACKEND_ORIGIN="${BACKEND_ORIGIN}" \
FBRK_WEB_ROOT="${FBRK_WEB_ROOT}" \
PLESK_SYNC_WORKDIR="${WORKDIR}" \
ASSET_VERSION="${ASSET_VERSION}" \
GENERATE_STATIC_ARTICLE_PAGES=1 \
python3 "${PLESK_BUILDER}" --force --full --dry-run --keep-package --no-verify | tee "${log_file}"

package_dir="$(awk -F= '/^PACKAGE_DIR=/{print $2}' "${log_file}" | tail -1)"
if [[ -z "${package_dir}" || ! -d "${package_dir}" ]]; then
  echo "ERROR: package directory was not produced" >&2
  exit 1
fi

# The Plesk delta builder includes generated payloads, AV DS assets, and
# referenced upload images. A fresh VPS also needs small static image assets
# such as favicons and legacy covers. Keep the heavy uploads directory governed
# by the referenced-asset packager above.
rsync -a --exclude '/uploads/' "${FBRK_WEB_ROOT}/img/" "${package_dir}/img/"

# Historical 404.html used /favicon.ico while the AV DS site uses brand PNGs.
# Keep this defensive replace here so older generated packages do not ship a
# missing favicon on a clean VPS.
python3 - "${package_dir}/404.html" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace(
    '<link rel="icon" href="/favicon.ico" />',
    '<link rel="icon" type="image/png" sizes="32x32" href="/img/brand/favicon-32.png" />',
)
path.write_text(text, encoding="utf-8")
PY

ssh -o BatchMode=yes "${TARGET}" "mkdir -p '${TARGET_ROOT}'"
rsync -az "${package_dir}/" "${TARGET}:${TARGET_ROOT}/"
ssh -o BatchMode=yes "${TARGET}" \
  "chown -R www-data:www-data '${TARGET_ROOT}' && nginx -t && systemctl reload nginx"

echo "STATUS=synced"
echo "TARGET=${TARGET}:${TARGET_ROOT}"
echo "ASSET_VERSION=${ASSET_VERSION}"
