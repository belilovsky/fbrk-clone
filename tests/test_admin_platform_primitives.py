from __future__ import annotations

import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "admin"))

from app.admin_platform.access import ROLE_ADMIN, has_role, principal_from_user, require_role
from app.admin_platform.audit import compact_details, record_audit
from app.admin_platform.control_plane import build_control_plane_profile
from app.admin_platform.csrf import make_csrf_token, verify_csrf_token
from app.admin_platform.qaz_bridge import bridge_status
from app.admin_platform.paths import safe_join
from app.admin_platform.session import session_cookie_from_settings
from app.admin_platform.uploads import detect_image_mime, validate_image_upload


class AdminPlatformPrimitiveTests(unittest.TestCase):
    def test_access_defaults_authenticated_user_to_admin_role(self) -> None:
        principal = principal_from_user("editor")
        self.assertIsNotNone(principal)
        assert principal is not None
        self.assertEqual(principal.username, "editor")
        self.assertIn(ROLE_ADMIN, principal.roles)
        self.assertTrue(has_role(principal, ROLE_ADMIN))
        self.assertEqual(require_role("editor").username, "editor")

    def test_csrf_token_verifies_subject_signature_and_ttl(self) -> None:
        token = make_csrf_token(secret="secret", subject="admin", now=100, nonce="n")
        self.assertTrue(verify_csrf_token(token, secret="secret", subject="admin", now=120))
        self.assertFalse(verify_csrf_token(token, secret="secret", subject="other", now=120))
        self.assertFalse(verify_csrf_token(token, secret="bad", subject="admin", now=120))
        self.assertFalse(verify_csrf_token(token, secret="secret", subject="admin", now=10_000))

    def test_session_cookie_defaults_are_secure_lax_httponly(self) -> None:
        cookie = session_cookie_from_settings(name="fbrk_admin", session_days=7, secure=True)
        self.assertEqual(cookie.name, "fbrk_admin")
        self.assertEqual(cookie.max_age, 7 * 86400)
        self.assertEqual(
            cookie.as_kwargs(),
            {
                "max_age": 7 * 86400,
                "httponly": True,
                "samesite": "lax",
                "secure": True,
                "path": "/",
            },
        )

    def test_safe_join_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self.assertEqual(safe_join(root, "uploads", "a.webp"), root / "uploads" / "a.webp")
            with self.assertRaises(ValueError):
                safe_join(root, "..", "escape.txt")

    def test_upload_magic_byte_validation(self) -> None:
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        self.assertEqual(detect_image_mime(png), "image/png")
        self.assertTrue(validate_image_upload(png, content_type="image/png").ok)
        mismatch = validate_image_upload(png, content_type="image/jpeg")
        self.assertFalse(mismatch.ok)
        self.assertIn("does not match", mismatch.error)
        self.assertFalse(validate_image_upload(b"not-image", content_type="image/png").ok)

    def test_qaz_admin_bridge_delegates_when_package_is_available(self) -> None:
        fake_package = types.ModuleType("qaz_admin")
        fake_package.__version__ = "9.9.9"
        fake_uploads = types.ModuleType("qaz_admin.uploads")
        fake_uploads.detect_image_mime = lambda raw: "image/webp" if raw == b"central" else ""
        previous_package = sys.modules.get("qaz_admin")
        previous_uploads = sys.modules.get("qaz_admin.uploads")
        sys.modules["qaz_admin"] = fake_package
        sys.modules["qaz_admin.uploads"] = fake_uploads
        try:
            self.assertEqual(bridge_status()["version"], "9.9.9")
            self.assertEqual(detect_image_mime(b"central"), "image/webp")
            self.assertEqual(detect_image_mime(b"\x89PNG\r\n\x1a\n"), "image/png")
        finally:
            if previous_package is None:
                sys.modules.pop("qaz_admin", None)
            else:
                sys.modules["qaz_admin"] = previous_package
            if previous_uploads is None:
                sys.modules.pop("qaz_admin.uploads", None)
            else:
                sys.modules["qaz_admin.uploads"] = previous_uploads

    def test_control_plane_profile_uses_local_and_manifest_metadata(self) -> None:
        profile = build_control_plane_profile()
        self.assertEqual(profile["project_id"], "fbrk")
        self.assertEqual(profile["adoption_target"], "content_admins")
        self.assertEqual(profile["source"], "local")
        self.assertIn("policy_check", profile["pipeline_stages"])
        self.assertIn("source_verification", profile["policy_hooks"])
        self.assertGreaterEqual(profile["counts"]["entity_types"], 8)

        manifest_profile = build_control_plane_profile(
            {
                "consumer_adoption_targets": {
                    "content_admins": {
                        "status": "partial",
                        "next_gate": "manifest next gate",
                    }
                },
                "product_packages": {
                    "media_compliance_kit": {
                        "name": "Manifest Compliance",
                        "wave": "second",
                        "readiness": "ready",
                    }
                },
                "project_bindings": {
                    "fbrk": {
                        "entity_types": ["story", "report"],
                        "policy_hooks": ["editorial_policy"],
                    }
                },
            }
        )
        self.assertEqual(manifest_profile["source"], "manifest")
        self.assertEqual(manifest_profile["status"], "partial")
        self.assertEqual(manifest_profile["next_gate"], "manifest next gate")
        self.assertEqual(manifest_profile["product_packages"][0]["name"], "Manifest Compliance")
        self.assertEqual(manifest_profile["entity_types"], ["story", "report"])
        self.assertEqual(manifest_profile["policy_hooks"], ["editorial_policy"])

    def test_record_audit_is_best_effort(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY,
                user TEXT,
                action TEXT,
                entity TEXT,
                entity_id TEXT,
                details TEXT
            )
            """
        )
        record_audit(
            conn,
            user="admin",
            action="update",
            entity="article",
            entity_id="slug",
            details={"title": "Тест"},
        )
        row = conn.execute("SELECT user, action, entity, entity_id, details FROM audit_log").fetchone()
        self.assertEqual(row, ("admin", "update", "article", "slug", '{"title": "Тест"}'))
        self.assertEqual(compact_details("x" * 1100), "x" * 1000)


if __name__ == "__main__":
    unittest.main()
