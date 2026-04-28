"""FBRK admin — FastAPI app.

Routes:
- GET  /admin/login          login form
- POST /admin/login          process login (cookie)
- GET  /admin/logout
- GET  /admin/                dashboard (list articles)
- GET  /admin/new             new article (Editor.js)
- GET  /admin/edit/{id}      edit article
- POST /api/articles          create
- PUT  /api/articles/{id}    update
- DELETE /api/articles/{id}  delete
- POST /api/articles/{id}/publish  toggle
- POST /api/upload           upload image (-> /img/uploads/)
- POST /api/publish          regenerate js/data.js
"""
from __future__ import annotations

import io
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (
    Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from slugify import slugify

from .config import settings
from .db import db, init_db, row_to_article
from .editorjs import editorjs_to_sections, sections_to_editorjs
from .publish import regenerate_data_js
from .security import (
    COOKIE_NAME, current_user, hash_password, issue_token, require_auth,
    verify_password,
)
from .seo import router as seo_router

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent  # admin/

app = FastAPI(title="FBRK Admin", docs_url=None, redoc_url=None)

app.mount(
    "/admin/static",
    StaticFiles(directory=str(BASE / "static")),
    name="admin-static",
)

templates = Jinja2Templates(directory=str(BASE / "templates"))

# Public SEO/OG/IA routes — /a/{slug}, /sitemap.xml, /robots.txt, /feed.xml, /feed/ia.xml
app.include_router(seo_router)

# Russian month names for date formatting
MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _date_label(iso: str) -> str:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return f"{d.day} {MONTHS_RU[d.month - 1]} {d.year}"
    except Exception:
        return iso


def _ensure_seed_user() -> None:
    """If no users exist, seed from env FBRK_ADMIN_USER / FBRK_ADMIN_PASSWORD."""
    with db() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        if row["n"] == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (settings.admin_user, hash_password(settings.admin_password)),
            )


@app.on_event("startup")
def _startup() -> None:
    init_db()
    from .meta_schema import ensure_meta_schema
    ensure_meta_schema()
    _ensure_seed_user()


# -----------------------------------------------------------------------------
# Auth routes
# -----------------------------------------------------------------------------
@app.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None):
    if current_user(request):
        return RedirectResponse(url="/admin/", status_code=302)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": error}
    )


@app.post("/admin/login")
def login_submit(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return RedirectResponse(
            url="/admin/login?error=1", status_code=302
        )
    token = issue_token(username)
    resp = RedirectResponse(url="/admin/", status_code=302)
    resp.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return resp


@app.get("/admin/logout")
def logout():
    resp = RedirectResponse(url="/admin/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


# -----------------------------------------------------------------------------
# UI routes (Jinja)
# -----------------------------------------------------------------------------
def _auth_or_redirect(request: Request):
    user = current_user(request)
    if not user:
        raise HTTPException(
            status_code=302, detail="redir",
            headers={"Location": "/admin/login"},
        )
    return user


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY date_iso DESC, created_at DESC"
        ).fetchall()
    articles = [row_to_article(r) for r in rows]
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "articles": articles, "user": user},
    )


@app.get("/admin/new", response_class=HTMLResponse)
def new_article_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    today = datetime.utcnow().date().isoformat()
    empty = {
        "id": "",
        "slug": "",
        "title": "",
        "dek": "",
        "author": "fbrk_news",
        "dateIso": today,
        "date": _date_label(today),
        "category": "news",
        "categoryLabel": "Новости",
        "image": "",
        "tags": [],
        "source": "",
        "body": {"blocks": []},
        "featured": False,
        "published": True,
    }
    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "article": empty, "is_new": True, "user": user},
    )


@app.get("/admin/edit/{article_id}", response_class=HTMLResponse)
def edit_article_page(article_id: str, request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    article = row_to_article(row)
    # If body has no blocks but sections exist (legacy imports), hydrate
    if not article["body"].get("blocks") and article["sections"]:
        article["body"] = sections_to_editorjs(article["sections"])
    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "article": article, "is_new": False, "user": user},
    )


# -----------------------------------------------------------------------------
# API — articles
# -----------------------------------------------------------------------------
def _save_article(payload: dict, article_id: Optional[str] = None) -> dict:
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "title required")
    date_iso = payload.get("dateIso") or payload.get("date_iso") or datetime.utcnow().date().isoformat()
    slug_src = payload.get("slug") or payload.get("id") or title
    slug = slugify(slug_src, lowercase=True, allow_unicode=False) or f"article-{uuid.uuid4().hex[:8]}"
    aid = article_id or (payload.get("id") or slug)
    # Accept either Editor.js blocks (from admin UI) or pre-built sections (from importers)
    if payload.get("body"):
        body = payload["body"]
        sections = editorjs_to_sections(body)
    elif payload.get("sections") is not None:
        sections = payload["sections"]
        from app.editorjs import sections_to_editorjs
        body = sections_to_editorjs(sections)
    else:
        body = {"blocks": []}
        sections = []

    category = payload.get("category") or "news"
    category_label = payload.get("categoryLabel") or (
        "Расследование" if category == "investigation" else "Новости"
    )

    record = (
        aid, slug, title,
        (payload.get("dek") or "").strip(),
        (payload.get("author") or "fbrk_news").strip(),
        date_iso, _date_label(date_iso),
        category, category_label,
        (payload.get("image") or "").strip(),
        json.dumps(payload.get("tags") or [], ensure_ascii=False),
        (payload.get("source") or "").strip(),
        json.dumps(body, ensure_ascii=False),
        json.dumps(sections, ensure_ascii=False),
        1 if payload.get("featured") else 0,
        1 if payload.get("published", True) else 0,
    )

    with db() as conn:
        if article_id:
            conn.execute(
                """UPDATE articles SET slug=?, title=?, dek=?, author=?, date_iso=?,
                       date_label=?, category=?, category_label=?, image=?, tags_json=?,
                       source=?, body_json=?, sections_json=?, featured=?, published=?,
                       updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (*record[1:], article_id),
            )
        else:
            conn.execute(
                """INSERT INTO articles (id, slug, title, dek, author, date_iso, date_label,
                                          category, category_label, image, tags_json, source,
                                          body_json, sections_json, featured, published)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                record,
            )
        # Only one featured article at a time
        if payload.get("featured"):
            conn.execute("UPDATE articles SET featured=0 WHERE id != ?", (aid,))
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (aid,)).fetchone()
    return row_to_article(row)


@app.get("/api/articles/list")
def api_list(_: str = Depends(require_auth)):
    """Minimal listing for importer resumability."""
    with db() as conn:
        rows = conn.execute("SELECT id, slug, title, date_iso FROM articles ORDER BY date_iso DESC").fetchall()
    return {
        "articles": [
            {"id": r["id"], "slug": r["slug"], "title": r["title"], "date_iso": r["date_iso"]}
            for r in rows
        ]
    }


@app.post("/api/articles")
async def api_create(request: Request, _: str = Depends(require_auth)):
    payload = await request.json()
    art = _save_article(payload)
    regenerate_data_js()
    return {"ok": True, "article": art}


@app.put("/api/articles/{article_id}")
async def api_update(article_id: str, request: Request, _: str = Depends(require_auth)):
    payload = await request.json()
    with db() as conn:
        if not conn.execute("SELECT 1 FROM articles WHERE id=?", (article_id,)).fetchone():
            raise HTTPException(404, "Not found")
    art = _save_article(payload, article_id=article_id)
    regenerate_data_js()
    return {"ok": True, "article": art}


@app.delete("/api/articles/{article_id}")
def api_delete(article_id: str, _: str = Depends(require_auth)):
    with db() as conn:
        conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
    regenerate_data_js()
    return {"ok": True}


@app.post("/api/articles/{article_id}/publish")
def api_toggle_publish(article_id: str, _: str = Depends(require_auth)):
    with db() as conn:
        row = conn.execute("SELECT published FROM articles WHERE id=?", (article_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        new_val = 0 if row["published"] else 1
        conn.execute("UPDATE articles SET published=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (new_val, article_id))
    regenerate_data_js()
    return {"ok": True, "published": bool(new_val)}


@app.post("/api/publish")
def api_publish(_: str = Depends(require_auth)):
    return {"ok": True, **regenerate_data_js()}


# -----------------------------------------------------------------------------
# Image upload
# -----------------------------------------------------------------------------
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...), _: str = Depends(require_auth)):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"unsupported type: {file.content_type}")
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(400, "file too large (max 20MB)")

    # Normalize to webp, write full + thumb
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "web").mkdir(exist_ok=True)
    (uploads_dir / "thumb").mkdir(exist_ok=True)

    name = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:
        raise HTTPException(400, f"bad image: {e}")

    w, h = im.size
    if w > 1600:
        im_full = im.resize((1600, int(h * 1600 / w)), Image.LANCZOS)
    else:
        im_full = im
    fw, fh = im_full.size
    if fw > 800:
        im_th = im_full.resize((800, int(fh * 800 / fw)), Image.LANCZOS)
    else:
        im_th = im_full

    full_path = uploads_dir / "web" / f"{name}.webp"
    thumb_path = uploads_dir / "thumb" / f"{name}.webp"
    im_full.save(full_path, "WEBP", quality=82, method=6)
    im_th.save(thumb_path, "WEBP", quality=78, method=6)

    # URLs for the public site (relative so it works with any base path)
    full_url = f"{settings.uploads_url_prefix}/web/{name}.webp"
    thumb_url = f"{settings.uploads_url_prefix}/thumb/{name}.webp"

    with db() as conn:
        conn.execute(
            "INSERT INTO uploads (filename, url, size_bytes) VALUES (?, ?, ?)",
            (f"{name}.webp", thumb_url, full_path.stat().st_size),
        )

    # Editor.js image tool expects {success:1, file:{url}}
    return {
        "success": 1,
        "file": {"url": thumb_url, "urlFull": full_url},
        "thumb": thumb_url,
        "full": full_url,
    }


# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/admin/healthz")
def healthz():
    return {"ok": True, "time": datetime.utcnow().isoformat()}
