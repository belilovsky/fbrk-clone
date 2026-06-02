"""Audit helpers that degrade safely when the legacy table is absent."""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def actor_name(user: str | dict | None) -> str:
    if isinstance(user, dict):
        return str(user.get("username") or user.get("sub") or "-")
    return str(user or "-")


def compact_details(details: Any, *, limit: int = 1000) -> str:
    if details is None:
        return ""
    if isinstance(details, str):
        text = details
    else:
        try:
            text = json.dumps(details, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = str(details)
    return text[:limit]


def record_audit(
    conn: Any,
    *,
    user: str | dict | None,
    action: str,
    entity: str,
    entity_id: str = "",
    details: Any = None,
) -> None:
    """Write an audit event and never break the primary mutation flow.

    The production DB has grown historically, so this helper treats the audit
    table as optional. If the table or details column is missing, the caller's
    mutation still succeeds.
    """

    try:
        conn.execute(
            """
            INSERT INTO audit_log(user, action, entity, entity_id, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (actor_name(user), action, entity, str(entity_id or ""), compact_details(details)),
        )
    except Exception:
        try:
            conn.execute(
                """
                INSERT INTO audit_log(user, action, entity, entity_id)
                VALUES (?, ?, ?, ?)
                """,
                (actor_name(user), action, entity, str(entity_id or "")),
            )
        except Exception:
            logger.debug(
                "Audit log write skipped because the legacy audit table shape is unavailable",
                exc_info=True,
            )
            return
