from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "admin"))

from app.image_migration import MigratedImage, normalize_fbrk_source_image_url, rewrite_article_images


def test_normalize_fbrk_source_image_url_strips_drupal_style_wrapper() -> None:
    raw = "https://fbrk.kz/sites/default/files/styles/wide/public/2026-05/foo%20bar.png?itok=token"
    assert normalize_fbrk_source_image_url(raw) == "https://fbrk.kz/sites/default/files/2026-05/foo bar.png"


def test_normalize_fbrk_source_image_url_rejects_non_fbrk_hosts() -> None:
    assert normalize_fbrk_source_image_url("https://example.com/image.jpg") == ""


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
