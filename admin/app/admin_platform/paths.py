"""Path helpers for admin files and uploads."""
from __future__ import annotations

from pathlib import Path

from ..config import settings


def project_root() -> Path:
    return Path(settings.project_root).resolve()


def public_root() -> Path:
    return Path(settings.public_root).resolve()


def db_path() -> Path:
    return Path(settings.db_path).resolve()


def uploads_dir() -> Path:
    return Path(settings.uploads_dir).resolve()


def safe_join(root: str | Path, *parts: str) -> Path:
    base = Path(root).resolve()
    candidate = base.joinpath(*parts).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"path escapes base directory: {candidate}")
    return candidate


def upload_url_to_public_path(url: str) -> Path | None:
    raw = (url or "").strip()
    if not raw or "://" in raw or raw.startswith("//"):
        return None
    normalized = raw if raw.startswith("/") else "/" + raw
    if not normalized.startswith("/img/uploads/"):
        return None
    return safe_join(public_root(), normalized.lstrip("/"))

