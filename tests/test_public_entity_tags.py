from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "admin"))

import enrich  # noqa: E402
from app.publish import _article_full_shape  # noqa: E402


def _article(**overrides: object) -> dict:
    data = {
        "id": "sample",
        "slug": "sample",
        "title": "Расходы семей на продукты остаются высокими",
        "dek": "Доля расходов на продукты остается предметом первой необходимости.",
        "date": "15 мая 2026",
        "dateIso": "2026-05-15",
        "category": "news",
        "categoryLabel": "Новости",
        "image": "",
        "tags": ["БНР", "мясопотребление", "Казахстан", "статистика"],
        "sections": [],
    }
    data.update(overrides)
    return data


class PublicEntityTagsTest(unittest.TestCase):
    def test_fallback_does_not_promote_tags_to_entities(self) -> None:
        result = enrich._fallback_result(_article())

        entity_names = {item["name"].casefold() for item in result["entities"]}
        tag_names = {tag.casefold() for tag in ["БНР", "мясопотребление", "статистика"]}

        self.assertTrue(entity_names.isdisjoint(tag_names))
        self.assertEqual(result["tags_auto"][:3], ["БНР", "мясопотребление", "Казахстан"])

    def test_public_shape_keeps_manual_tags_only_and_hides_noisy_other_entities(self) -> None:
        article = _article(
            _meta_entities_json=json.dumps(
                [
                    {"name": "БНР", "type": "other"},
                    {"name": "мясопотребление", "type": "other"},
                    {"name": "Казахстан", "type": "place"},
                    {"name": "Министерство финансов", "type": "gov"},
                ],
                ensure_ascii=False,
            ),
            _meta_tags_auto=json.dumps(["бедность", "доходы"], ensure_ascii=False),
        )

        shape = _article_full_shape(article)

        self.assertEqual(
            shape["entities"],
            [
                {"name": "Казахстан", "type": "place"},
                {"name": "Министерство финансов", "type": "gov"},
            ],
        )
        self.assertEqual(
            shape["tags"],
            ["БНР", "мясопотребление", "статистика"],
        )

    def test_auto_topics_are_not_rendered_as_manual_tags(self) -> None:
        article = _article(
            tags=["БНР", "мясопотребление", "Казахстан", "Расследование"],
            _meta_entities_json=json.dumps([], ensure_ascii=False),
            _meta_tags_auto=json.dumps(["БНР", "мясопотребление", "Казахстан"], ensure_ascii=False),
        )

        shape = _article_full_shape(article)

        self.assertEqual(shape["tags"], ["Расследование"])


if __name__ == "__main__":
    unittest.main()
