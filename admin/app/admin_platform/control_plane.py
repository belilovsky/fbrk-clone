"""Local control-plane profile for the FBRK admin shell."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


CONTROL_PLANE_MANIFEST_URL = "https://platform.qdev.run/catalog/inventory/ecosystem.generated.json"
CONTROL_PLANE_ADOPTION_TARGET = "content_admins"
FBRK_PROJECT_ID = "fbrk"

LOCAL_PRODUCT_PACKAGES = (
    {
        "id": "media_compliance_kit",
        "name": "Media Compliance Kit",
        "wave": "second",
        "readiness": "prototype-to-pilot",
    },
    {
        "id": "narrative_visibility_suite",
        "name": "Narrative Visibility Suite",
        "wave": "first",
        "readiness": "pilot-ready",
    },
)
LOCAL_PIPELINE_STAGES = (
    "ingest",
    "normalize_classify",
    "entity_linking",
    "draft_enrich",
    "policy_check",
    "human_review",
    "publish",
    "distribution_visibility",
)
LOCAL_EVIDENCE_EVENTS = (
    "source_ingested",
    "entity_linked",
    "draft_created",
    "policy_checked",
    "human_reviewed",
    "published",
    "measurement_recorded",
)
LOCAL_ENTITY_TYPES = (
    "person",
    "organization",
    "region",
    "topic",
    "source",
    "document",
    "statement",
    "story",
    "event",
    "report",
)
LOCAL_POLICY_HOOKS = (
    "editorial_policy",
    "source_verification",
    "corrections_workflow",
    "visibility_measurement",
)
LOCAL_NEXT_GATE = (
    "держать FBRK как manifest-aware content admin consumer: "
    "split-host publishing, source checks, correction trail и visibility measurement"
)


def _mapping(value: Any) -> Mapping[str, Any]:
    """Return mapping values only; bad manifest fragments become empty."""
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any, fallback: tuple[str, ...]) -> list[str]:
    """Return clean string values from manifest data or local fallback."""
    if not isinstance(value, list):
        return list(fallback)
    return [str(item) for item in value if str(item).strip()]


def _manifest_product_packages(manifest: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """Resolve FBRK package labels from platform manifest data when supplied."""
    source_packages = _mapping(_mapping(manifest).get("product_packages"))
    packages: list[dict[str, str]] = []
    for fallback in LOCAL_PRODUCT_PACKAGES:
        package_id = fallback["id"]
        source = _mapping(source_packages.get(package_id))
        packages.append(
            {
                "id": package_id,
                "name": str(source.get("name") or fallback["name"]),
                "wave": str(source.get("wave") or fallback["wave"]),
                "readiness": str(source.get("readiness") or fallback["readiness"]),
            }
        )
    return packages


def build_control_plane_profile(manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Собрать безопасный профиль FBRK для единого control-plane каталога."""
    manifest_root = _mapping(manifest)
    adoption = _mapping(
        _mapping(manifest_root.get("consumer_adoption_targets")).get(
            CONTROL_PLANE_ADOPTION_TARGET
        )
    )
    binding = _mapping(_mapping(manifest_root.get("project_bindings")).get(FBRK_PROJECT_ID))
    has_manifest = bool(manifest_root)
    policy_hooks = _sequence(binding.get("policy_hooks"), LOCAL_POLICY_HOOKS)
    entity_types = _sequence(binding.get("entity_types"), LOCAL_ENTITY_TYPES)
    packages = _manifest_product_packages(manifest_root)
    pipeline_stages = list(LOCAL_PIPELINE_STAGES)
    evidence_events = list(LOCAL_EVIDENCE_EVENTS)
    status = str(adoption.get("status") or "partial-local")

    return {
        "project_id": FBRK_PROJECT_ID,
        "adoption_target": CONTROL_PLANE_ADOPTION_TARGET,
        "manifest_url": CONTROL_PLANE_MANIFEST_URL,
        "source": "manifest" if has_manifest else "local",
        "status": status,
        "variant": "success" if status == "done" else "info",
        "product_packages": packages,
        "pipeline_stages": pipeline_stages,
        "evidence_events": evidence_events,
        "entity_types": entity_types,
        "policy_hooks": policy_hooks,
        "counts": {
            "product_packages": len(packages),
            "pipeline_stages": len(pipeline_stages),
            "evidence_events": len(evidence_events),
            "entity_types": len(entity_types),
            "policy_hooks": len(policy_hooks),
        },
        "next_gate": str(adoption.get("next_gate") or LOCAL_NEXT_GATE),
    }
