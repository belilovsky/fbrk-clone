"""Settings loaded from env with sensible local defaults."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_first(names: tuple[str, ...], default: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


@dataclass
class Settings:
    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent       # admin/
    project_root: Path = Path(__file__).resolve().parent.parent.parent  # fbrk/
    db_path: str = _env_first(("FBRK_DB_PATH", "FBRK_DB"), str(Path(__file__).resolve().parent.parent / "fbrk.db"))
    public_root: str = _env("FBRK_PUBLIC_ROOT", str(Path(__file__).resolve().parent.parent.parent))
    uploads_dir: str = _env("FBRK_UPLOADS_DIR", str(Path(__file__).resolve().parent.parent.parent / "img" / "uploads"))
    uploads_url_prefix: str = _env("FBRK_UPLOADS_URL", "img/uploads")

    # Auth
    admin_user: str = _env("FBRK_ADMIN_USER", "admin")
    admin_password: str = _env("FBRK_ADMIN_PASSWORD", "admin")  # dev default; override in prod
    jwt_secret: str = _env("FBRK_JWT_SECRET", secrets.token_urlsafe(32))
    api_key: str = _env("FBRK_API_KEY", "dev-api-key-change-me")
    session_days: int = int(_env("FBRK_SESSION_DAYS", "7"))
    cookie_secure: bool = _env_bool("FBRK_COOKIE_SECURE", True)

    # URLs
    admin_prefix: str = _env("FBRK_ADMIN_PREFIX", "/admin")

    # Public site regeneration
    data_js_path: str = _env("FBRK_DATA_JS", str(Path(__file__).resolve().parent.parent.parent / "js" / "data.js"))
    # Tier 1 (homepage data.js): how many recent articles to embed for fast initial load.
    # Full archive lives in data-archive.js and is loaded only on /archive.html.
    home_latest_limit: int = int(_env("FBRK_HOME_LATEST_LIMIT", "200"))


settings = Settings()
