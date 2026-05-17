"""Shared shell context for admin templates."""
from __future__ import annotations

from . import ADMIN_PLATFORM_VERSION, AV_DS_VERSION


def shell_context(*, request, user: str | dict | None, section: str = "", title: str = "", **extra) -> dict:
    context = {
        "request": request,
        "user": user,
        "section": section,
        "title": title,
        "admin_platform_version": ADMIN_PLATFORM_VERSION,
        "av_ds_version": AV_DS_VERSION,
    }
    context.update(extra)
    return context

