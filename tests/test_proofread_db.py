from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "admin" / "scripts" / "proofread_db.py"))

_candidate_reasons = MODULE["_candidate_reasons"]
_fallback_lead = MODULE["_fallback_lead"]
_is_metadata_only_dek = MODULE["_is_metadata_only_dek"]
_needs_lead_generation = MODULE["_needs_lead_generation"]


def _article(**overrides):
    base = {
        "title": "Минздрав запретил определённую серию препарата в Казахстане",
        "dek": "(3 марта 2026 | Источник: пресс-служба министерства здравоохранения РК)",
        "sections": [
            {
                "h": "ЧТО ПРОИЗОШЛО",
                "p": "Министерство здравоохранения Казахстана приостановило обращение серии препарата после проверки качества и уведомило аптеки о необходимости изъятия упаковок.",
            }
        ],
    }
    base.update(overrides)
    return base


def test_metadata_only_dek_is_detected() -> None:
    assert _is_metadata_only_dek("(3 марта 2026 | Источник: ФБРК)")
    assert _is_metadata_only_dek("Источник: пресс-служба министерства")
    assert not _is_metadata_only_dek("Министерство изъяло препарат из обращения после проверки качества.")


def test_candidate_reasons_include_lead_and_caps_headings() -> None:
    reasons = _candidate_reasons(_article())
    assert reasons == ["caps_headings", "lead"]


def test_empty_or_title_like_dek_requests_lead_generation() -> None:
    assert _needs_lead_generation(_article(dek=""))
    assert _needs_lead_generation(_article(dek="Минздрав запретил определённую серию препарата в Казахстане"))
    assert not _needs_lead_generation(_article(dek="Министерство остановило обращение серии препарата после проверки качества."))


def test_fallback_lead_uses_first_section_when_dek_is_service_only() -> None:
    lead = _fallback_lead(_article(), fallback="")
    assert "Министерство здравоохранения Казахстана приостановило обращение серии препарата" in lead
    assert len(lead) <= 240
