from __future__ import annotations

import sqlite3
import sys
import tempfile
import types
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "admin"))

from app.admin_platform.access import ROLE_ADMIN, has_role, principal_from_user, require_role
from app.admin_platform.audit import compact_details, record_audit
from app.admin_platform.csrf import make_csrf_token, verify_csrf_token
from app.admin_platform.qaz_bridge import bridge_status
from app.admin_platform.paths import safe_join
from app.admin_platform.session import session_cookie_from_settings
from app.admin_platform.uploads import detect_image_mime, store_optimized_image, validate_image_upload


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

    def test_store_optimized_image_creates_full_and_thumb_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = BytesIO()
            Image.new("RGB", (2200, 1100), color=(10, 20, 30)).save(buf, format="PNG")
            stored = store_optimized_image(
                buf.getvalue(),
                uploads_dir=tmp,
                uploads_url_prefix="/img/uploads",
                basename="fixed-name",
            )
            self.assertEqual(stored.thumb_url, "/img/uploads/thumb/fixed-name.webp")
            self.assertEqual(stored.full_url, "/img/uploads/web/fixed-name.webp")
            self.assertTrue(stored.thumb_path.exists())
            self.assertTrue(stored.full_path.exists())
            with Image.open(stored.full_path) as full_image:
                self.assertEqual(full_image.width, 1600)
            with Image.open(stored.thumb_path) as thumb_image:
                self.assertEqual(thumb_image.width, 800)

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
