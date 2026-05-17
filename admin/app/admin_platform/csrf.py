"""Stateless CSRF token helpers.

The current FBRK admin has not wired CSRF enforcement yet. These helpers are
kept framework-neutral so templates/routes can adopt them incrementally.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time


DEFAULT_TTL_SECONDS = 2 * 60 * 60


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def make_csrf_token(
    *,
    secret: str,
    subject: str,
    now: int | None = None,
    nonce: str | None = None,
) -> str:
    ts = int(time.time() if now is None else now)
    safe_subject = str(subject or "-")
    safe_nonce = nonce or secrets.token_urlsafe(12)
    payload = f"{ts}:{safe_nonce}:{safe_subject}".encode("utf-8")
    body = _b64(payload)
    sig = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_csrf_token(
    token: str,
    *,
    secret: str,
    subject: str,
    now: int | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        raw = _unb64(body).decode("utf-8")
        ts_raw, _nonce, token_subject = raw.split(":", 2)
        if not hmac.compare_digest(token_subject, str(subject or "-")):
            return False
        ts = int(ts_raw)
        current = int(time.time() if now is None else now)
        return 0 <= current - ts <= ttl_seconds
    except Exception:
        return False

