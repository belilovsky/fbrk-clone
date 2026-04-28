"""Auth helpers: password hashing, JWT cookie sessions, API key."""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Optional

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from .config import settings

COOKIE_NAME = "fbrk_admin"

# scrypt-based password hashing (stdlib). Format: scrypt$n$r$p$salt_hex$hash_hex
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2 ** 14, 8, 1


def hash_password(raw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(raw.encode("utf-8"), salt=salt,
                        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${dk.hex()}"


def verify_password(raw: str, hashed: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, hash_hex = hashed.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(raw.encode("utf-8"), salt=bytes.fromhex(salt_hex),
                            n=int(n), r=int(r), p=int(p), dklen=len(hash_hex) // 2)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def issue_token(username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + settings.session_days * 86400,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        return None


def current_user(request: Request) -> Optional[str]:
    """For Jinja pages — None if unauthenticated."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    data = decode_token(token)
    return data.get("sub") if data else None


def require_session(request: Request) -> str:
    """For UI routes: raises 401 (caller redirects to login)."""
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_auth(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    """For API routes: accept either session cookie OR X-API-Key."""
    if x_api_key and x_api_key == settings.api_key:
        return "api-key"
    user = current_user(request)
    if user:
        return user
    raise HTTPException(status_code=401, detail="Unauthorized")
