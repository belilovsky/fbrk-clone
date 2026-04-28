# Backend Audit Notes

## Checked

- FastAPI routes imported successfully with `PYTHONPATH=admin`; route count: 22.
- `ruff check admin import`: 16 existing findings.
- `mypy admin --ignore-missing-imports`: 3 existing type errors.
- DB helper uses `with db()` context manager with commit/rollback and `PRAGMA journal_mode = WAL`.
- `publish.regenerate_data_js()` uses process lock + file lock + atomic replace.

## Findings

- README/ops env used `FBRK_DB`, code only read `FBRK_DB_PATH`; fixed in `audit/backend/env-compat`.
- No pytest suite found in repo; backend regression coverage should be added before larger validation or CSRF changes.
- Pydantic request models are not used for article create/update; validation is mostly manual.
- AI enrichment catches provider errors per article, but `traceback` import is unused and mypy flags a few loosely typed paths.
