from __future__ import annotations

import os
import re
import sys
import json
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "admin"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))


def _client(tmp_path: Path) -> TestClient:
    public_root = tmp_path / "public"
    uploads_dir = public_root / "img" / "uploads"
    data_js = public_root / "js" / "data.js"
    uploads_dir.mkdir(parents=True)
    data_js.parent.mkdir(parents=True)

    os.environ.update(
        {
            "FBRK_DB_PATH": str(tmp_path / "fbrk-test.db"),
            "FBRK_PUBLIC_ROOT": str(public_root),
            "FBRK_UPLOADS_DIR": str(uploads_dir),
            "FBRK_DATA_JS": str(data_js),
            "FBRK_ADMIN_USER": "admin",
            "FBRK_ADMIN_PASSWORD": "secret",
            "FBRK_JWT_SECRET": "test-secret",
            "FBRK_API_KEY": "test-api-key",
            "FBRK_COOKIE_SECURE": "false",
        }
    )

    # Settings are read at import time; keep this smoke test isolated from any
    # previously imported admin modules.
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    from app.main import app

    return TestClient(app)


def _login(client: TestClient) -> None:
    token = _login_csrf_from(client.get("/admin/login").text)
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/"


def _login_csrf_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "login csrf token is missing"
    return match.group(1)


def _csrf_from(html: str) -> str:
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    assert match, "csrf meta token is missing"
    return match.group(1)


def _article_payload(article_id: str = "codex-smoke") -> dict:
    return {
        "id": article_id,
        "slug": article_id,
        "title": "Codex smoke title",
        "dek": "Проверка сохранения из админки и публикации во фронтовые данные.",
        "dateIso": "2026-05-17",
        "category": "news",
        "categoryLabel": "Новости",
        "author": "fbrk_news",
        "image": "",
        "tags": ["smoke"],
        "source": "https://fbrk.kz/news/codex-smoke",
        "body": {
            "blocks": [
                {
                    "type": "paragraph",
                    "data": {"text": "Тестовый абзац для проверки data.js."},
                }
            ]
        },
        "featured": False,
        "published": True,
    }


def test_admin_login_and_protected_dashboard(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        login_page = client.get("/admin/login")
        assert login_page.status_code == 200
        assert "Вход" in login_page.text
        assert 'name="csrf_token" value="' in login_page.text

        login_without_csrf = client.post(
            "/admin/login",
            data={"username": "admin", "password": "secret"},
            follow_redirects=False,
        )
        assert login_without_csrf.status_code == 403

        protected = client.get("/admin/", follow_redirects=False)
        assert protected.status_code == 302
        assert protected.headers["location"] == "/admin/login"

        _login(client)
        dashboard = client.get("/admin/")
        assert dashboard.status_code == 200
        assert "Материалов пока нет" in dashboard.text
        assert 'name="csrf-token" content="' in dashboard.text


def test_admin_form_csrf_reject_and_accept(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)

        rejected = client.post("/admin/articles/bulk", data={"op": "publish"}, follow_redirects=False)
        assert rejected.status_code == 403

        page = client.get("/admin/")
        token = _csrf_from(page.text)
        accepted = client.post(
            "/admin/articles/bulk",
            data={"op": "publish", "csrf_token": token},
            follow_redirects=False,
        )
        assert accepted.status_code == 303


def test_upload_policy_rejects_bad_image(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        token = _csrf_from(client.get("/admin/").text)
        response = client.post(
            "/api/upload",
            files={"file": ("bad.png", b"not-an-image", "image/png")},
            headers={"X-CSRF-Token": token},
        )
        assert response.status_code == 400
        assert "signature" in response.text


def test_session_api_mutation_requires_csrf_and_updates_frontend_data(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        rejected = client.post("/api/articles", json=_article_payload())
        assert rejected.status_code == 403

        token = _csrf_from(client.get("/admin/").text)
        created = client.post(
            "/api/articles",
            json=_article_payload(),
            headers={"X-CSRF-Token": token},
        )
        assert created.status_code == 200
        assert created.json()["article"]["title"] == "Codex smoke title"

        data_js = tmp_path / "public" / "js" / "data.js"
        article_full = tmp_path / "public" / "js" / "article-full.js"
        assert data_js.exists()
        assert article_full.exists()
        data_text = data_js.read_text(encoding="utf-8")
        full_text = article_full.read_text(encoding="utf-8")
        assert "Codex smoke title" in data_text
        assert "codex-smoke" in data_text
        assert "Тестовый абзац для проверки data.js." in full_text

        # The homepage payload remains compact: full rendered sections live in
        # article-full.js for split static article pages.
        raw = data_text.split("const FBRK_DATA =", 1)[1].rsplit(";", 1)[0].strip()
        data = json.loads(raw)
        assert data["totalCount"] == 1
        assert "sections" not in data["articles"][0]


def test_api_key_mutation_keeps_working_without_csrf(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post(
            "/api/articles",
            json=_article_payload("codex-api-key-smoke"),
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        assert response.json()["article"]["id"] == "codex-api-key-smoke"
