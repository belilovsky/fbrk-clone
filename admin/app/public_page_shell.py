"""Shared helpers for static public pages rendered from admin settings."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re

from .config import settings


def extract_shell_block(source: str, block: str, path: Path) -> str:
    match = re.search(rf"(?P<block>[ \t]*<{block} class=\"site-{block}\"[\s\S]*?</{block}>)", source)
    if not match:
        raise ValueError(f"{path}: missing site {block}")
    return match.group("block")


def asset_version(index_html: str) -> str:
    match = re.search(r"(?:/)?css/style\.css\?v=(\d{14})", index_html)
    if match:
        return match.group(1)
    return datetime.now().strftime("%Y%m%d%H%M%S")


def site_url() -> str:
    return (os.environ.get("FBRK_SITE_URL") or "https://fbrk.qdev.run").rstrip("/")


def load_site_shell(public_root: Path | None = None) -> dict[str, str]:
    root = public_root or Path(settings.public_root)
    index_path = root / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    return {
        "header": extract_shell_block(index_html, "header", index_path),
        "footer": extract_shell_block(index_html, "footer", index_path),
        "version": asset_version(index_html),
    }
