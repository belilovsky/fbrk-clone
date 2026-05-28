from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "admin"))

from app.editorjs import editorjs_to_sections, normalize_section_heading, sections_to_editorjs


def test_normalize_section_heading_sentence_cases_all_caps() -> None:
    assert normalize_section_heading("ЧТО ЗАЯВИЛИ В МВД") == "Что заявили в МВД"
    assert (
        normalize_section_heading(
            "КАКИЕ ДОГОВОРЕННОСТИ ДОСТИГЛИ КАЗАХСТАН И РОССИЯ",
            context="Казахстан и Россия протестировали беспилотный маршрут Астана - Москва",
        )
        == "Какие договоренности достигли Казахстан и Россия"
    )
    assert normalize_section_heading("Обычный подзаголовок") == "Обычный подзаголовок"


def test_editorjs_roundtrip_normalizes_uppercase_h2() -> None:
    data = {
        "blocks": [
            {"type": "header", "data": {"text": "ЧТО СООБЩИЛИ В ПОЛИЦИИ", "level": 2}},
            {"type": "paragraph", "data": {"text": "Первый абзац."}},
        ]
    }

    sections = editorjs_to_sections(data)

    assert sections == [{"h": "Что сообщили в полиции", "p": "Первый абзац."}]
    assert sections_to_editorjs(sections)["blocks"][0]["data"]["text"] == "Что сообщили в полиции"
