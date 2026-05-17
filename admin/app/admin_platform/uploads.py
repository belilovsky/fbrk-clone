"""Upload validation primitives for admin media flows."""
from __future__ import annotations

from dataclasses import dataclass


ALLOWED_IMAGE_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")
DEFAULT_MAX_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class UploadPolicy:
    allowed_mime: tuple[str, ...] = ALLOWED_IMAGE_MIME
    max_bytes: int = DEFAULT_MAX_BYTES


@dataclass(frozen=True)
class UploadValidation:
    ok: bool
    detected_mime: str = ""
    error: str = ""


def detect_image_mime(raw: bytes) -> str:
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return ""


def validate_image_upload(
    raw: bytes,
    *,
    content_type: str | None,
    policy: UploadPolicy = UploadPolicy(),
) -> UploadValidation:
    declared = (content_type or "").split(";", 1)[0].strip().lower()
    if declared not in policy.allowed_mime:
        return UploadValidation(False, error=f"unsupported type: {declared or 'unknown'}")
    if not raw:
        return UploadValidation(False, error="empty file")
    if len(raw) > policy.max_bytes:
        return UploadValidation(False, error=f"file too large (max {policy.max_bytes // (1024 * 1024)}MB)")
    detected = detect_image_mime(raw)
    if not detected:
        return UploadValidation(False, error="unsupported or corrupt image signature")
    if detected != declared:
        return UploadValidation(False, detected, f"file content does not match MIME type: {detected}")
    return UploadValidation(True, detected)

