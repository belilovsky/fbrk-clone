"""Response helpers for admin routes."""
from __future__ import annotations


def see_other(location: str):
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=location, status_code=303)


def found(location: str):
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=location, status_code=302)

