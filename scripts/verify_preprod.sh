#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
NODE_BIN="${NODE_BIN:-node}"
NEW_ORIGIN="${NEW_ORIGIN:-https://new.fbrk.kz}"
BACKEND_ORIGIN="${BACKEND_ORIGIN:-https://fbrk.qdev.run}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: python interpreter not found: ${PYTHON_BIN}" >&2
  echo "Hint: use the repo venv or export PYTHON_BIN=/path/to/python" >&2
  exit 1
fi

cd "${REPO_ROOT}"

echo "[1/5] JS syntax"
"${NODE_BIN}" --check js/app.js

echo "[2/5] JS unit tests"
"${NODE_BIN}" --test tests/article_js_filters.test.mjs

echo "[3/5] Python test suite"
"${PYTHON_BIN}" -m pytest -q

echo "[4/5] Python compile checks"
"${PYTHON_BIN}" -m py_compile admin/app/*.py admin/enrich.py admin/scripts/*.py

echo "[5/5] Live split linkage"
./admin/scripts/check_split_linkage.sh "${NEW_ORIGIN}" "${BACKEND_ORIGIN}" --strict

echo "STATUS=ok"
