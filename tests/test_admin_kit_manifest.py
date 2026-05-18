"""Tests for the FBRK admin-kit consumer manifest."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SMOKE = {
    "csrf_reject",
    "login_render",
    "protected_route",
    "system_dashboard",
    "unauth_redirect",
}


def test_admin_kit_manifest_is_safe_and_truthful():
    """Manifest should link the real admin to the central registry without secrets."""
    manifest = json.loads((ROOT / "admin-kit.json").read_text(encoding="utf-8"))

    assert manifest["project"] == "fbrk"
    assert manifest["framework"] == "fastapi"
    assert manifest["adapter_status"] == "optional-bridge"
    assert manifest["admin_kit_version"] == "0.3.0"
    assert manifest["risk"] == "medium"
    assert manifest["routes"] == 53
    assert set(manifest["smoke"]) == REQUIRED_SMOKE
    assert set(manifest["smoke"].values()) == {"pass"}
    assert "secret" not in json.dumps(manifest, ensure_ascii=False).lower()
