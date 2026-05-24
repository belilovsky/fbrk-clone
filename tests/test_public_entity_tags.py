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
            )
        )
        self.assertTrue(
            enrich._needs_quality_rerun(
                "Заголовок",
                "Краткое описание статьи без финальной точки",
                "deepseek-chat",
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


if __name__ == "__main__":
    unittest.main()
