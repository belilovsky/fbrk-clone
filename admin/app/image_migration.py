"""Helpers for migrating legacy fbrk.kz images into local optimized uploads."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

from .editorjs import editorjs_to_sections


FBRK_SOURCE_ORIGIN = "https://fbrk.kz"
FBRK_SOURCE_HOSTS = {"fbrk.kz", "www.fbrk.kz"}
DRUPAL_STYLE_RE = re.compile(r"/sites/default/files/styles/[^/]+/public/")
IMAGE_PATH_RE = re.compile(r"\.(?:avif|gif|jpe?g|png|svg|webp)$", re.IGNORECASE)
IMG_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'])', re.IGNORECASE)


@dataclass(frozen=True)
class MigratedImage:
    source_url: str
    thumb_url: str
    full_url: str


@dataclass(frozen=True)
class ArticleImageStats:
    cover_refs: int = 0
    body_refs: int = 0
    section_refs: int = 0

    @property
    def total_refs(self) -> int:
        return self.cover_refs + self.body_refs + self.section_refs


@dataclass(frozen=True)
class ArticleImageRewrite:
    image: str
    body_json: str
    sections_json: str
    stats: ArticleImageStats

    @property
    def changed(self) -> bool:
        return self.stats.total_refs > 0


def normalize_fbrk_source_image_url(url: str, base_origin: str = FBRK_SOURCE_ORIGIN) -> str:
    raw = str(url or "").strip()
    if not raw or raw.startswith("data:"):
        return ""
    if raw.startswith("//"):
        raw = f"https:{raw}"
    absolute = urljoin(base_origin, raw)
    parsed = urlparse(absolute)
    host = (parsed.netloc or "").lower()
    if host and host not in FBRK_SOURCE_HOSTS:
        return ""

    path = unquote(parsed.path or "")
    if not path:
        return ""
    path = DRUPAL_STYLE_RE.sub("/sites/default/files/", path)
    if not IMAGE_PATH_RE.search(path):
        return ""
    return urljoin(base_origin, path)


def collect_external_image_urls(
    image_url: str,
    body_json_raw: str,
    sections_json_raw: str,
) -> set[str]:
    found: set[str] = set()
    normalized = normalize_fbrk_source_image_url(image_url)
    if normalized:
        found.add(normalized)

    body, _ = _load_json(body_json_raw, default={})
    for block in body.get("blocks", []) or []:
        if not isinstance(block, dict):
            continue
        data = block.get("data") or {}
        block_url = ""
        if isinstance(data, dict):
            file_meta = data.get("file") or {}
            if isinstance(file_meta, dict):
                block_url = str(file_meta.get("url") or "").strip()
            if not block_url:
                block_url = str(data.get("url") or "").strip()
            if block.get("type") in {"paragraph", "quote"}:
                found.update(_extract_inline_html_images(str(data.get("text") or "")))
        normalized = normalize_fbrk_source_image_url(block_url)
        if normalized:
            found.add(normalized)

    sections, _ = _load_json(sections_json_raw, default=[])
    for section in sections:
        if not isinstance(section, dict):
            continue
        found.update(_extract_inline_html_images(str(section.get("p") or "")))
    return found


def rewrite_article_images(
    image_url: str,
    body_json_raw: str,
    sections_json_raw: str,
    migrated_by_source: dict[str, MigratedImage],
) -> ArticleImageRewrite:
    stats = ArticleImageStats()
    new_image = image_url

    normalized_cover = normalize_fbrk_source_image_url(image_url)
    if normalized_cover and normalized_cover in migrated_by_source:
        new_image = migrated_by_source[normalized_cover].thumb_url
        stats = ArticleImageStats(
            cover_refs=1 if new_image != image_url else 0,
            body_refs=stats.body_refs,
            section_refs=stats.section_refs,
        )

    body, body_valid = _load_json(body_json_raw, default={})
    body_work = copy.deepcopy(body)
    body_refs = 0
    for block in body_work.get("blocks", []) or []:
        if not isinstance(block, dict):
            continue
        data = block.get("data") or {}
        if not isinstance(data, dict):
            continue
        file_meta = data.get("file")
        if isinstance(file_meta, dict):
            raw = str(file_meta.get("url") or "").strip()
            normalized = normalize_fbrk_source_image_url(raw)
            if normalized and normalized in migrated_by_source:
                file_meta["url"] = migrated_by_source[normalized].full_url
                body_refs += 1
        raw = str(data.get("url") or "").strip()
        normalized = normalize_fbrk_source_image_url(raw)
        if normalized and normalized in migrated_by_source:
            data["url"] = migrated_by_source[normalized].full_url
            body_refs += 1
        if block.get("type") in {"paragraph", "quote"}:
            rewritten_text, changed = rewrite_inline_image_html(
                str(data.get("text") or ""),
                migrated_by_source,
                variant="full",
            )
            if changed:
                data["text"] = rewritten_text
                body_refs += changed

    regenerated_sections = False
    if body_valid and body_work:
        sections = editorjs_to_sections(body_work)
        sections_work = copy.deepcopy(sections)
        regenerated_sections = True
    else:
        sections_work, _ = _load_json(sections_json_raw, default=[])

    section_refs = 0
    for section in sections_work:
        if not isinstance(section, dict):
            continue
        rewritten_paragraph, changed = rewrite_inline_image_html(
            str(section.get("p") or ""),
            migrated_by_source,
            variant="full",
        )
        if changed:
            section["p"] = rewritten_paragraph
            section_refs += changed

    stats = ArticleImageStats(
        cover_refs=stats.cover_refs,
        body_refs=body_refs,
        section_refs=section_refs,
    )
    body_json_out = body_json_raw if not body_valid and body_refs == 0 else json.dumps(body_work, ensure_ascii=False)
    if regenerated_sections or section_refs > 0:
        sections_json_out = json.dumps(sections_work, ensure_ascii=False)
    else:
        sections_json_out = sections_json_raw
    return ArticleImageRewrite(
        image=new_image,
        body_json=body_json_out,
        sections_json=sections_json_out,
        stats=stats,
    )


def rewrite_inline_image_html(
    html_text: str,
    migrated_by_source: dict[str, MigratedImage],
    *,
    variant: str,
) -> tuple[str, int]:
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        normalized = normalize_fbrk_source_image_url(match.group(2))
        if not normalized:
            return match.group(0)
        migrated = migrated_by_source.get(normalized)
        if not migrated:
            return match.group(0)
        changed += 1
        target = migrated.full_url if variant == "full" else migrated.thumb_url
        return f"{match.group(1)}{target}{match.group(3)}"

    return IMG_SRC_RE.sub(replace, str(html_text or "")), changed


def _extract_inline_html_images(html_text: str) -> set[str]:
    found: set[str] = set()
    for match in IMG_SRC_RE.finditer(str(html_text or "")):
        normalized = normalize_fbrk_source_image_url(match.group(2))
        if normalized:
            found.add(normalized)
    return found


def _load_json(raw: str, *, default: Any) -> tuple[Any, bool]:
    try:
        value = json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return copy.deepcopy(default), False
    if isinstance(default, dict) and not isinstance(value, dict):
        return copy.deepcopy(default), False
    if isinstance(default, list) and not isinstance(value, list):
        return copy.deepcopy(default), False
    return value, True
