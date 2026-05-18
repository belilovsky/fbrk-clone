"""Shared shell context and template helpers for admin templates."""
from __future__ import annotations

from typing import Any

from fastapi.templating import Jinja2Templates

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


class AdminJinja2Templates(Jinja2Templates):
    """Jinja templates with a compatibility bridge for legacy route code.

    The admin still has older CRUD routes that call
    ``TemplateResponse(name, {"request": request, ...})``. Starlette now wants
    ``TemplateResponse(request, name, context)``. Normalize the old call shape
    in one place so we can remove runtime deprecation warnings without a broad
    route rewrite.
    """

    def TemplateResponse(self, *args: Any, **kwargs: Any):  # noqa: N802 - Starlette API name
        if args and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.pop("context", {})
            if "request" not in context:
                raise ValueError('context must include a "request" key')
            request = context["request"]
            status_code = args[2] if len(args) > 2 else kwargs.pop("status_code", 200)
            headers = args[3] if len(args) > 3 else kwargs.pop("headers", None)
            media_type = args[4] if len(args) > 4 else kwargs.pop("media_type", None)
            background = args[5] if len(args) > 5 else kwargs.pop("background", None)
            return super().TemplateResponse(
                request,
                name,
                context,
                status_code=status_code,
                headers=headers,
                media_type=media_type,
                background=background,
                **kwargs,
            )
        return super().TemplateResponse(*args, **kwargs)
