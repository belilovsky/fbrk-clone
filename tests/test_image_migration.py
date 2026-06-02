from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "admin"))

from app.image_migration import MigratedImage, normalize_fbrk_source_image_url, rewrite_article_images
from scripts.migrate_fbrk_images import fetch_candidate_rows, requestable_url, validate_downloaded_image


def test_normalize_fbrk_source_image_url_strips_drupal_style_wrapper() -> None:
    raw = "https://fbrk.kz/sites/default/files/styles/wide/public/2026-05/foo%20bar.png?itok=token"
    assert normalize_fbrk_source_image_url(raw) == "https://fbrk.kz/sites/default/files/2026-05/foo bar.png"


def test_normalize_fbrk_source_image_url_rejects_non_fbrk_hosts() -> None:
    assert normalize_fbrk_source_image_url("https://example.com/image.jpg") == ""


def test_normalize_fbrk_source_image_url_ignores_local_upload_paths() -> None:
    assert normalize_fbrk_source_image_url("img/uploads/thumb/test.webp") == ""
    assert normalize_fbrk_source_image_url("/img/uploads/web/test.webp") == ""
    assert normalize_fbrk_source_image_url("https://fbrk.kz/img/uploads/thumb/test.webp") == ""


def test_rewrite_article_images_updates_cover_body_and_sections() -> None:
    source = "https://fbrk.kz/sites/default/files/styles/wide/public/2026-05/foo.png?itok=abc"
    migrated = {
        "https://fbrk.kz/sites/default/files/2026-05/foo.png": MigratedImage(
            source_url="https://fbrk.kz/sites/default/files/2026-05/foo.png",
            thumb_url="/img/uploads/thumb/foo.webp",
            full_url="/img/uploads/web/foo.webp",
        )
    }
    body = {
        "blocks": [
            {"type": "paragraph", "data": {"text": "Лид"}},
            {
                "type": "image",
                "data": {
                    "file": {"url": source},
                    "caption": "Подпись",
                },
            },
        ]
    }
    sections = [
        {"h": "", "p": '<img src="https://fbrk.kz/sites/default/files/styles/wide/public/2026-05/foo.png?itok=abc" alt="Подпись"/>'}
    ]

    rewrite = rewrite_article_images(
        source,
        json.dumps(body, ensure_ascii=False),
        json.dumps(sections, ensure_ascii=False),
        migrated,
    )

    assert rewrite.image == "/img/uploads/thumb/foo.webp"
    body_out = json.loads(rewrite.body_json)
    assert body_out["blocks"][1]["data"]["file"]["url"] == "/img/uploads/web/foo.webp"
    sections_out = json.loads(rewrite.sections_json)
    assert "/img/uploads/web/foo.webp" in sections_out[0]["p"]
    assert rewrite.stats.cover_refs == 1
    assert rewrite.stats.body_refs == 1
    assert rewrite.stats.total_refs >= 2


def test_requestable_url_quotes_spaces_for_fetching() -> None:
    raw = "https://fbrk.kz/sites/default/files/2026-05/ChatGPT Image 26 мая 2026 г., 16_18_56.png"
    assert requestable_url(raw).startswith("https://fbrk.kz/sites/default/files/2026-05/ChatGPT%20Image%2026%20")


def test_fetch_candidate_rows_applies_slug_filter_to_entire_external_image_clause() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE articles (
            id TEXT,
            slug TEXT,
            title TEXT,
            image TEXT,
            body_json TEXT,
            sections_json TEXT,
            date_iso TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("1", "wanted", "Wanted", "https://fbrk.kz/sites/default/files/a.png", "{}", "[]", "2026-06-01"),
    )
    conn.execute(
        "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2", "other", "Other", "https://fbrk.kz/sites/default/files/b.png", "{}", "[]", "2026-05-31"),
    )

    rows = fetch_candidate_rows(conn, "wanted", limit=0)

    assert [row["slug"] for row in rows] == ["wanted"]


def test_validate_downloaded_image_prefers_detected_mime_when_source_suffix_lies() -> None:
    raw = b"RIFF1234WEBPVP8 " + b"\x00" * 16

    validation = validate_downloaded_image(
        raw,
        "https://fbrk.kz/sites/default/files/2025-10/example.jpeg",
        "image/jpeg",
    )

    assert validation.ok is True
    assert validation.detected_mime == "image/webp"
