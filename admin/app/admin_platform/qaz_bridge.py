"""Optional bridge to shared qaz-admin-kit primitives.

The FBRK admin service must keep working when the shared private package is not
installed on a deploy host.  This module therefore treats qaz-admin-kit as an
optional runtime accelerator and keeps the local primitives as the fallback.
"""
from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any


def admin_kit_version() -> str | None:
    """Return the installed qaz-admin-kit version, if available."""
    try:
        package = import_module("qaz_admin")
    except Exception:
        return None
    version = getattr(package, "__version__", None)
    return str(version) if version else "unknown"


def bridge_status() -> dict[str, Any]:
    """Expose a small status payload for admin diagnostics and tests."""
    try:
        bridge = import_module("qaz_admin.bridge")
        return bridge.bridge_status(
            primitives=("uploads.detect_image_mime",),
            fallback="project-local upload MIME policy",
        )
    except Exception:
        pass
    version = admin_kit_version()
    return {
        "available": version is not None,
        "version": version or "",
        "primitives": ["uploads.detect_image_mime"] if version is not None else [],
    }


def detect_image_mime(raw: bytes, fallback: Callable[[bytes], str]) -> str:
    """Detect image MIME through qaz-admin-kit when it is installed."""
    try:
        bridge = import_module("qaz_admin.bridge")
        return str(bridge.detect_image_mime(raw, fallback=fallback) or "")
    except Exception:
        pass
    try:
        uploads = import_module("qaz_admin.uploads")
        detector = getattr(uploads, "detect_image_mime")
        detected = detector(raw)
    except Exception:
        return fallback(raw)
    return str(detected or "") or fallback(raw)
