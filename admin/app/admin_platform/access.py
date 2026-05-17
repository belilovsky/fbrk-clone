"""Small RBAC helpers for the FBRK admin surface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


ROLE_ADMIN = "admin"


@dataclass(frozen=True)
class Principal:
    username: str
    roles: tuple[str, ...] = (ROLE_ADMIN,)


def principal_from_user(user: str | dict | None) -> Principal | None:
    if not user:
        return None
    if isinstance(user, dict):
        username = str(user.get("username") or user.get("sub") or "").strip()
        raw_roles = user.get("roles") or (ROLE_ADMIN,)
    else:
        username = str(user).strip()
        raw_roles = (ROLE_ADMIN,)
    if not username:
        return None
    roles = tuple(str(role).strip() for role in raw_roles if str(role).strip())
    return Principal(username=username, roles=roles or (ROLE_ADMIN,))


def has_role(user: str | dict | Principal | None, role: str) -> bool:
    if isinstance(user, Principal):
        principal = user
    else:
        principal = principal_from_user(user)
    return bool(principal and role in principal.roles)


def require_role(user: str | dict | Principal | None, role: str = ROLE_ADMIN) -> Principal:
    if isinstance(user, Principal):
        principal = user
    else:
        principal = principal_from_user(user)
    if not principal or role not in principal.roles:
        raise PermissionError(f"admin role required: {role}")
    return principal


def role_labels(roles: Iterable[str]) -> str:
    return ", ".join(sorted({str(role).strip() for role in roles if str(role).strip()}))

