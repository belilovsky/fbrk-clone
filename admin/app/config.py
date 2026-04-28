"""Settings loaded from env with sensible local defaults."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Settings:
    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent       # admin/
    project_root: Path = Path(__file__).resolve().parent.parent.parent  # fbrk/
    db_path: str = _env("FBRK_DB_PATH", str(Path(__file__).resolve().parent.parent / "fbrk.db"))
    public_root: str = _env("FBRK_PUBLIC_ROOT", str(Path(__file__).resolve().parent.parent.parent))
    uploads_dir: str = _env("FBRK_UPLOADS_DIR", str(Path(__file__).resolve().parent.parent.parent / "img" / "uploads"))
    uploads_url_prefix: str = _env("FBRK_UPLOADS_URL", "img/uploads")

    # Auth
    admin_user: str = _env("FBRK_ADMIN_USER", "admin")
    admin_password: str = _env("FBRK_ADMIN_PASSWORD", "admin")  # dev default; override in prod
    jwt_secret: str = _env("FBRK_JWT_SECRET", secrets.token_urlsafe(32))
    api_key: str = _env("FBRK_API_KEY", "dev-api-key-change-me")
    session_days: int = int(_env("FBRK_SESSION_DAYS", "7"))

    # URLs
    admin_prefix: str = _env("FBRK_ADMIN_PREFIX", "/admin")

    # Public site regeneration
    data_js_path: str = _env("FBRK_DATA_JS", str(Path(__file__).resolve().parent.parent.parent / "js" / "data.js"))


settings = Settings()
