#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-node}"
BACKEND_ORIGIN="${BACKEND_ORIGIN:-https://fbrk.qdev.run}"
NEW_ORIGIN="${NEW_ORIGIN:-${BACKEND_ORIGIN}}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: python interpreter not found: ${PYTHON_BIN}" >&2
  echo "Hint: use the repo venv or export PYTHON_BIN=/path/to/python" >&2
  exit 1
fi

cd "${REPO_ROOT}"

echo "[1/6] Local generated payload hygiene"
"${PYTHON_BIN}" ./scripts/check_generated_payload_hygiene.py

echo "[2/6] JS syntax"
"${NODE_BIN}" --check js/app.js

echo "[3/6] JS unit tests"
"${NODE_BIN}" --test tests/article_js_filters.test.mjs

echo "[4/6] Python test suite"
"${PYTHON_BIN}" -m pytest -q

echo "[5/6] Python compile checks"
"${PYTHON_BIN}" -m py_compile admin/app/*.py admin/enrich.py admin/scripts/*.py scripts/*.py

echo "[6/6] Live frontend linkage"
./admin/scripts/check_split_linkage.sh "${NEW_ORIGIN}" "${BACKEND_ORIGIN}" --strict

echo "STATUS=ok"
