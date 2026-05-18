"""Session-cookie defaults shared by UI and future tests."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionCookie:
    name: str
    max_age: int
    secure: bool
    httponly: bool = True
    samesite: str = "lax"
    path: str = "/"

    def as_kwargs(self) -> dict:
        return {
            "max_age": self.max_age,
            "httponly": self.httponly,
            "samesite": self.samesite,
            "secure": self.secure,
            "path": self.path,
        }


def session_cookie_from_settings(*, name: str, session_days: int, secure: bool) -> SessionCookie:
    return SessionCookie(name=name, max_age=int(session_days) * 86400, secure=bool(secure))

