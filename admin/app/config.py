"""Settings loaded from env with sensible local defaults."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_BASE_DIR = _THIS_FILE.parent.parent
_PROJECT_ROOT = _THIS_FILE.parent.parent.parent


def _clean_env_value(raw: str) -> str:
    value = str(raw or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_env_defaults(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            if not key:
                continue
            os.environ.setdefault(key, _clean_env_value(value))


_load_env_defaults(
    (
        Path("/etc/fbrk-admin/fbrk-admin.env"),
        _PROJECT_ROOT / ".env",
    )
)


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
    base_dir: Path = field(default_factory=lambda: _BASE_DIR)       # admin/
    project_root: Path = field(default_factory=lambda: _PROJECT_ROOT)  # fbrk/
    db_path: str = field(default_factory=lambda: _env_first(("FBRK_DB_PATH", "FBRK_DB"), str(_BASE_DIR / "fbrk.db")))
    public_root: str = field(default_factory=lambda: _env("FBRK_PUBLIC_ROOT", str(_PROJECT_ROOT)))
    uploads_dir: str = field(default_factory=lambda: _env("FBRK_UPLOADS_DIR", str(_PROJECT_ROOT / "img" / "uploads")))
    uploads_url_prefix: str = field(default_factory=lambda: _env("FBRK_UPLOADS_URL", "img/uploads"))

    # Auth
    admin_user: str = field(default_factory=lambda: _env("FBRK_ADMIN_USER", "admin"))
    admin_password: str = field(default_factory=lambda: _env("FBRK_ADMIN_PASSWORD", "admin"))  # dev default; override in prod
    jwt_secret: str = field(default_factory=lambda: _env("FBRK_JWT_SECRET", secrets.token_urlsafe(32)))
    api_key: str = field(default_factory=lambda: _env("FBRK_API_KEY", "dev-api-key-change-me"))
    session_days: int = field(default_factory=lambda: int(_env("FBRK_SESSION_DAYS", "7")))
    cookie_secure: bool = field(default_factory=lambda: _env_bool("FBRK_COOKIE_SECURE", True))

    # URLs
    admin_prefix: str = field(default_factory=lambda: _env("FBRK_ADMIN_PREFIX", "/admin"))

    # Public site regeneration
    data_js_path: str = field(default_factory=lambda: _env("FBRK_DATA_JS", str(_PROJECT_ROOT / "js" / "data.js")))
    # Tier 1 (homepage data.js): how many recent articles to embed for fast initial load.
    # Full archive lives in data-archive.js and is loaded only on /archive.html.
    home_latest_limit: int = field(default_factory=lambda: int(_env("FBRK_HOME_LATEST_LIMIT", "200")))


settings = Settings()
