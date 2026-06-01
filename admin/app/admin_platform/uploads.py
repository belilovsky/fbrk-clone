"""Upload validation primitives for admin media flows."""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
from .qaz_bridge import detect_image_mime as detect_image_mime_bridge


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


@dataclass(frozen=True)
class StoredImage:
    basename: str
    full_path: Path
    thumb_path: Path
    full_url: str
    thumb_url: str
    full_size_bytes: int
    thumb_size_bytes: int


def _detect_image_mime_local(raw: bytes) -> str:
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return ""


def detect_image_mime(raw: bytes) -> str:
    return detect_image_mime_bridge(raw, _detect_image_mime_local)


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


def store_optimized_image(
    raw: bytes,
    *,
    uploads_dir: str | Path,
    uploads_url_prefix: str,
    basename: str | None = None,
) -> StoredImage:
    """Convert an uploaded source image into the canonical FBRK full+thumb pair."""
    root = Path(uploads_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "web").mkdir(exist_ok=True)
    (root / "thumb").mkdir(exist_ok=True)

    name = basename or f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    try:
        with Image.open(io.BytesIO(raw)) as source:
            image = source.convert("RGB")
    except Exception as exc:
        raise ValueError(f"bad image: {exc}") from exc

    width, height = image.size
    if width > 1600:
        full_image = image.resize((1600, int(height * 1600 / width)), Image.LANCZOS)
    else:
        full_image = image

    full_width, full_height = full_image.size
    if full_width > 800:
        thumb_image = full_image.resize((800, int(full_height * 800 / full_width)), Image.LANCZOS)
    else:
        thumb_image = full_image

    full_path = root / "web" / f"{name}.webp"
    thumb_path = root / "thumb" / f"{name}.webp"
    full_image.save(full_path, "WEBP", quality=82, method=6)
    thumb_image.save(thumb_path, "WEBP", quality=78, method=6)

    prefix = str(uploads_url_prefix or "").strip().rstrip("/") or "img/uploads"
    full_url = f"{prefix}/web/{name}.webp"
    thumb_url = f"{prefix}/thumb/{name}.webp"
    return StoredImage(
        basename=f"{name}.webp",
        full_path=full_path,
        thumb_path=thumb_path,
        full_url=full_url,
        thumb_url=thumb_url,
        full_size_bytes=full_path.stat().st_size,
        thumb_size_bytes=thumb_path.stat().st_size,
    )
