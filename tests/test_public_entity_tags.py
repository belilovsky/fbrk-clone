from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "admin"))

import enrich  # noqa: E402
from app.editorial_hubs import annotate_article  # noqa: E402
from app.publish import _article_full_shape, _public_shape  # noqa: E402
from app.seo import _visible_entities  # noqa: E402


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
    def test_enrich_routes_deepseek_to_openai_compatible_provider(self) -> None:
        calls: list[tuple[str, str, str]] = []
        old = enrich._call_openai_compatible
        old_key = enrich.DEEPSEEK_API_KEY
        try:
            enrich.DEEPSEEK_API_KEY = "test-deepseek-key"

            def fake_call(text: str, model: str, *, api_key: str, base_url: str, provider: str) -> dict:
                calls.append((model, base_url, provider))
                return {"summary_short": "ok"}

            enrich._call_openai_compatible = fake_call
            enrich._call_model("текст", "deepseek-chat")
        finally:
            enrich._call_openai_compatible = old
            enrich.DEEPSEEK_API_KEY = old_key

        self.assertEqual(calls, [("deepseek-chat", "https://api.deepseek.com", "deepseek")])

    def test_enrich_falls_back_from_deepseek_rate_limit_to_openai(self) -> None:
        old_key = enrich.OPENAI_API_KEY
        try:
            enrich.OPENAI_API_KEY = "test-openai-key"
            self.assertTrue(enrich._should_fallback_to_openai("deepseek-chat", "RuntimeError: deepseek 429: rate limit"))
        finally:
            enrich.OPENAI_API_KEY = old_key

    def test_fallback_does_not_promote_tags_to_entities(self) -> None:
        result = enrich._fallback_result(_article())

        entity_names = {item["name"].casefold() for item in result["entities"]}
        tag_names = {tag.casefold() for tag in ["БНР", "мясопотребление", "статистика"]}

        self.assertTrue(entity_names.isdisjoint(tag_names))
        self.assertEqual(result["tags_auto"][:3], ["БНР", "мясопотребление", "Казахстан"])

    def test_sanitize_result_trims_summary_and_keeps_meaningful_sentence(self) -> None:
        raw = {
            "summary_short": (
                "В Казахстане реализуют длинную реформу регулирования частных детективов, "
                "которая устанавливает квалификационные требования, порядок лицензирования "
                "и расширенный перечень ограничений для участников рынка."
            ),
            "summary_tts": "ok",
            "entities": [{"name": "Министерство юстиции", "type": "other"}],
        }

        result = enrich._sanitize_result(raw, article=_article())

        self.assertLessEqual(len(result["summary_short"]), 180)
        self.assertTrue(result["summary_short"].endswith((".", "!", "?")))
        self.assertEqual(result["entities"][0]["type"], "gov")

    def test_sanitize_result_backfills_second_entity_from_article_context(self) -> None:
        raw = {
            "summary_short": "В Атырау прошёл форум по правовой культуре и безопасности молодёжи.",
            "summary_tts": "ok",
            "entities": [{"name": "Атырау", "type": "place"}],
        }
        article = _article(
            title="Форум по правовой культуре прошёл в Атырау",
            dek="В Атырау обсудили безопасность молодёжи и роль прокуратуры.",
        )

        result = enrich._sanitize_result(raw, article=article)

        self.assertGreaterEqual(len(result["entities"]), 2)
        self.assertIn("Атырау", {item["name"] for item in result["entities"]})

    def test_fallback_result_strips_source_prefix_and_guesses_entity_types(self) -> None:
        article = _article(
            title="МВД сообщило о задержании в Алматы",
            dek="(27 февраля 2026 | Источник: BES.media) МВД задержало подозреваемого в Алматы после спецоперации.",
            tags=["МВД", "Алматы"],
        )

        result = enrich._fallback_result(article)

        self.assertFalse(result["summary_short"].startswith("("))
        entity_types = {item["name"]: item["type"] for item in result["entities"]}
        self.assertEqual(entity_types.get("МВД"), "gov")
        self.assertEqual(entity_types.get("Алматы"), "place")

    def test_quality_rerun_marks_fallback_and_long_summary_rows(self) -> None:
        self.assertTrue(
            enrich._needs_quality_rerun(
                "Заголовок",
                "Нормальная строка",
                "fallback-local",
            )
        )
        self.assertTrue(
            enrich._needs_quality_rerun(
                "Заголовок",
                "Это очень длинное краткое описание " + "слово " * 40,
                "deepseek-chat",
            )
        )
        self.assertFalse(
            enrich._needs_quality_rerun(
                "Заголовок",
                "Краткое описание статьи без мусора и в пределах разумной длины.",
                "deepseek-chat",
                json.dumps(
                    [
                        {"name": "Астана", "type": "place"},
                        {"name": "Минфин", "type": "gov"},
                    ],
                    ensure_ascii=False,
                ),
            )
        )
        self.assertTrue(
            enrich._needs_quality_rerun(
                "Заголовок",
                "Краткое описание статьи без финальной точки",
                "deepseek-chat",
            )
        )
        self.assertTrue(
            enrich._needs_quality_rerun(
                "Заголовок",
                "Краткое описание статьи без мусора и в пределах разумной длины.",
                "deepseek-chat",
                json.dumps([{"name": f"Entity {i}", "type": "org"} for i in range(13)], ensure_ascii=False),
            )
        )
        self.assertTrue(
            enrich._needs_quality_rerun(
                "Заголовок",
                "Краткое описание статьи без мусора и в пределах разумной длины.",
                "deepseek-chat",
                json.dumps([{"name": "Астана", "type": "place"}], ensure_ascii=False),
            )
        )

    def test_trim_summary_short_keeps_hard_cap_when_period_lands_at_181(self) -> None:
        text = (
            "В 20 социально-значимых пассажирских поездах выявлено 284 нарушения, включая отсутствие "
            "кондиционеров и несоответствие санитарным нормам, общая сумма штрафов превысила 10 млн тенге."
        )

        trimmed = enrich._trim_summary_short(text)

        self.assertLessEqual(len(trimmed), 180)

    def test_trim_summary_short_adds_period_even_at_exact_hard_cap(self) -> None:
        text = (
            "В 20 социально-значимых пассажирских поездах выявлено 284 нарушения, включая отсутствие "
            "кондиционеров и несоответствие санитарным нормам, общая сумма штрафов превысила 10 млн тенге"
        )

        self.assertEqual(len(text), 180)

        trimmed = enrich._trim_summary_short(text)

        self.assertLessEqual(len(trimmed), 180)
        self.assertTrue(trimmed.endswith("."))

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
            ["статистика"],
        )

    def test_sanitize_result_caps_entities_at_twelve(self) -> None:
        raw = {
            "summary_short": "Краткое описание статьи без мусора и в пределах разумной длины.",
            "summary_tts": "ok",
            "entities": [{"name": f"Entity {i}", "type": "org"} for i in range(20)],
        }

        result = enrich._sanitize_result(raw, article=_article())

        self.assertEqual(len(result["entities"]), 12)

    def test_public_shape_limits_entity_chips_to_twelve(self) -> None:
        article = _article(
            _meta_entities_json=json.dumps(
                [{"name": f"Entity {i}", "type": "org"} for i in range(20)],
                ensure_ascii=False,
            ),
            _meta_tags_auto=json.dumps([], ensure_ascii=False),
        )

        shape = _article_full_shape(article)

        self.assertEqual(len(shape["entities"]), 12)

    def test_public_shape_backfills_second_visible_entity_from_summary(self) -> None:
        article = _article(
            title="Казспецэкспорт продает аварийный самолёт АН-26",
            dek="Стоимость лота выросла до 26 млн тенге, но торги отменили.",
            _meta_summary_short="Казспецэкспорт выставил на торги аварийный самолёт АН-26, цена выросла до 26 млн тенге.",
            _meta_entities_json=json.dumps(
                [{"name": "Казспецэкспорт", "type": "org"}],
                ensure_ascii=False,
            ),
            _meta_tags_auto=json.dumps([], ensure_ascii=False),
        )

        shape = _article_full_shape(article)

        self.assertGreaterEqual(len(shape["entities"]), 2)
        self.assertEqual(shape["entities"][0], {"name": "Казспецэкспорт", "type": "org"})

    def test_visible_entities_defaults_to_twelve(self) -> None:
        raw = [
            {"name": "Астана", "type": "place"},
            {"name": "Минфин", "type": "gov"},
        ] + [
            {"name": f"Entity {i}", "type": "org"} for i in range(20)
        ] + [{"name": "Таблица", "type": "other"}]

        entities = _visible_entities(raw)

        self.assertEqual(len(entities), 12)
        self.assertTrue(all(item["type"] in {"person", "org", "gov", "place", "law", "case", "money"} for item in entities))
        self.assertEqual([item["name"] for item in entities], [e["name"] for e in raw[:12] if e["type"] in {"person", "org", "gov", "place", "law", "case", "money"}][:12])

    def test_auto_topics_are_not_rendered_as_manual_tags(self) -> None:
        article = _article(
            tags=["БНР", "мясопотребление", "Казахстан", "Расследование"],
            _meta_entities_json=json.dumps(
                [
                    {"name": "БНР", "type": "other"},
                    {"name": "мясопотребление", "type": "other"},
                    {"name": "Казахстан", "type": "other"},
                ],
                ensure_ascii=False,
            ),
            _meta_tags_auto=json.dumps(["БНР"], ensure_ascii=False),
        )

        shape = _article_full_shape(article)

        self.assertEqual(shape["tags"], ["Расследование"])

    def test_article_full_payload_omits_volatile_updated_at(self) -> None:
        shape = _article_full_shape(
            _article(updatedAt="2026-05-15 10:20:02")
        )

        self.assertNotIn("updatedAt", shape)

    def test_public_shape_adds_curated_topics_series_and_resonance(self) -> None:
        shape = _public_shape(
            _article(
                title="Латифундисты Казахстана. Глава 9: Шымкент",
                dek="ФБРК разбирает крупнейшие земельные массивы, пастбища и агробизнес региона.",
                category="investigation",
                categoryLabel="Расследование",
                _meta_importance=4,
                _meta_region="Шымкент",
                _meta_tags_auto=json.dumps(["земля", "латифундисты"], ensure_ascii=False),
            )
        )

        self.assertEqual(shape["series"]["slug"], "latifundisty-kazakhstana")
        self.assertIn("land-and-agro", {item["slug"] for item in shape["topics"]})
        self.assertTrue(shape["resonance"])

    def test_annotate_article_respects_manual_editorial_override(self) -> None:
        annotated = annotate_article(
            _article(
                title="Министерство обновило планы сезонной обработки полей",
                dek="Материал про региональные работы, подрядчиков и сельхозсезон.",
                tags=["сельхоз", "земля"],
                importance=5,
            ),
            override={
                "topic_slugs": ["corruption"],
                "series_slug": "dezinsekciya-2025",
                "resonance": False,
                "status_slug": "follow-up",
                "label_slugs": ["documents", "data"],
            },
        )

        self.assertEqual(
            [item["slug"] for item in annotated.get("topics") or []],
            ["corruption"],
        )
        self.assertEqual(
            (annotated.get("series") or {}).get("slug"),
            "dezinsekciya-2025",
        )
        self.assertEqual(
            (annotated.get("editorialStatus") or {}).get("slug"),
            "follow-up",
        )
        self.assertEqual(
            [item["slug"] for item in annotated.get("editorialLabels") or []],
            ["documents", "data"],
        )
        self.assertNotIn("resonance", annotated)


if __name__ == "__main__":
    unittest.main()
