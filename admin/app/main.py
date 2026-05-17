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
from .admin_platform.audit import record_audit
from .admin_platform.csrf import make_csrf_token, verify_csrf_token
from .admin_platform.paths import upload_url_to_public_path, uploads_dir as platform_uploads_dir
from .admin_platform.uploads import validate_image_upload
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


def admin_asset_url(value: str | None) -> str:
    url = (value or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://", "//", "data:", "blob:")):
        return url
    if url.startswith("/"):
        return url
    return "/" + url.lstrip("/")


templates.env.globals["admin_asset_url"] = admin_asset_url


def csrf_token(request: Request) -> str:
    user = current_user(request)
    if not user:
        return ""
    return make_csrf_token(secret=settings.jwt_secret, subject=user)


templates.env.globals["csrf_token"] = csrf_token

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


async def require_admin_csrf(request: Request) -> None:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = request.headers.get("X-CSRF-Token", "")
    if not token:
        form = await request.form()
        token = str(form.get("csrf_token") or "")
    if not verify_csrf_token(token, secret=settings.jwt_secret, subject=user):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def _safe_count(conn, sql: str, params: tuple = ()) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def _dashboard_widgets(conn) -> tuple[dict, list[dict], list[dict]]:
    stats = {
        "articles_total": _safe_count(conn, "SELECT COUNT(*) FROM articles"),
        "articles_pub": _safe_count(conn, "SELECT COUNT(*) FROM articles WHERE published = 1"),
        "articles_draft": _safe_count(
            conn,
            "SELECT COUNT(*) FROM articles WHERE COALESCE(published, 0) = 0",
        ),
        "categories": 0,
        "tags": 0,
        "entities": 0,
        "ads_total": 0,
        "ads_active": 0,
    }
    if _table_exists(conn, "categories"):
        stats["categories"] = _safe_count(conn, "SELECT COUNT(*) FROM categories")
    if not stats["categories"]:
        stats["categories"] = _safe_count(
            conn,
            "SELECT COUNT(DISTINCT category) FROM articles WHERE COALESCE(category, '') != ''",
        )
    if _table_exists(conn, "ad_placements"):
        stats["ads_total"] = _safe_count(conn, "SELECT COUNT(*) FROM ad_placements")
        stats["ads_active"] = _safe_count(
            conn,
            "SELECT COUNT(*) FROM ad_placements WHERE is_active = 1",
        )

    tags: set[str] = set()
    try:
        for row in conn.execute("SELECT tags_json FROM articles"):
            try:
                for tag in json.loads(row["tags_json"] or "[]"):
                    tag = str(tag).strip().lower()
                    if tag:
                        tags.add(tag)
            except Exception:
                continue
    except Exception:
        pass
    stats["tags"] = len(tags)

    if _table_exists(conn, "article_meta"):
        entities = 0
        try:
            for row in conn.execute("SELECT entities_json FROM article_meta"):
                try:
                    data = json.loads(row["entities_json"] or "[]")
                except Exception:
                    continue
                if isinstance(data, dict):
                    entities += sum(len(v) for v in data.values() if isinstance(v, list))
                elif isinstance(data, list):
                    entities += len(data)
        except Exception:
            entities = 0
        stats["entities"] = entities

    recent = [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, title, COALESCE(NULLIF(date_label, ''), date_iso, '') AS date
            FROM articles
            ORDER BY date_iso DESC, created_at DESC
            LIMIT 8
            """
        ).fetchall()
    ]

    audit = []
    if _table_exists(conn, "audit_log"):
        audit = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  ts,
                  COALESCE(user, '-') AS user,
                  COALESCE(action, '') AS action,
                  COALESCE(entity, '') AS entity,
                  COALESCE(entity_id, '') AS entity_id
                FROM audit_log
                ORDER BY id DESC
                LIMIT 8
                """
            ).fetchall()
        ]

    return stats, recent, audit


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
        stats, recent, audit = _dashboard_widgets(conn)
    articles = [row_to_article(r) for r in rows]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "articles": articles,
            "user": user,
            "stats": stats,
            "recent": recent,
            "audit": audit,
        },
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
    meta = {"entities": [], "tags_auto": [], "importance": None, "sentiment": None, "region": "", "summary_short": ""}
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
        # Stage 2: fetch enrichment meta
        meta = {"entities": [], "tags_auto": [], "importance": None, "sentiment": None, "region": "", "summary_short": ""}
        try:
            mrow = conn.execute("SELECT entities_json, tags_auto, importance, sentiment, region, summary_short FROM article_meta WHERE article_id = ?", (article_id,)).fetchone()
            if mrow:
                import json as _json
                meta["entities"] = _json.loads(mrow["entities_json"] or "[]")
                meta["tags_auto"] = _json.loads(mrow["tags_auto"] or "[]")
                meta["importance"] = mrow["importance"]
                meta["sentiment"] = mrow["sentiment"]
                meta["region"] = mrow["region"] or ""
                meta["summary_short"] = mrow["summary_short"] or ""
        except Exception:
            pass
    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "article": article, "is_new": False, "user": user, "meta": meta},
    )


# -----------------------------------------------------------------------------
# API — articles
# -----------------------------------------------------------------------------
def _save_article(payload: dict, article_id: Optional[str] = None, actor: str | None = None) -> dict:
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
            audit_action = "update"
        else:
            conn.execute(
                """INSERT INTO articles (id, slug, title, dek, author, date_iso, date_label,
                                          category, category_label, image, tags_json, source,
                                          body_json, sections_json, featured, published)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                record,
            )
            audit_action = "create"
        # Only one featured article at a time
        if payload.get("featured"):
            conn.execute("UPDATE articles SET featured=0 WHERE id != ?", (aid,))
        record_audit(
            conn,
            user=actor,
            action=audit_action,
            entity="article",
            entity_id=aid,
            details={
                "slug": slug,
                "title": title,
                "published": bool(payload.get("published", True)),
                "featured": bool(payload.get("featured")),
            },
        )
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
async def api_create(request: Request, actor: str = Depends(require_auth)):
    payload = await request.json()
    art = _save_article(payload, actor=actor)
    regenerate_data_js()
    return {"ok": True, "article": art}


@app.put("/api/articles/{article_id}")
async def api_update(article_id: str, request: Request, actor: str = Depends(require_auth)):
    payload = await request.json()
    with db() as conn:
        if not conn.execute("SELECT 1 FROM articles WHERE id=?", (article_id,)).fetchone():
            raise HTTPException(404, "Not found")
    art = _save_article(payload, article_id=article_id, actor=actor)
    regenerate_data_js()
    return {"ok": True, "article": art}


@app.delete("/api/articles/{article_id}")
def api_delete(article_id: str, actor: str = Depends(require_auth)):
    with db() as conn:
        row = conn.execute("SELECT slug, title FROM articles WHERE id=?", (article_id,)).fetchone()
        conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
        record_audit(
            conn,
            user=actor,
            action="delete",
            entity="article",
            entity_id=article_id,
            details={"slug": row["slug"], "title": row["title"]} if row else {},
        )
    regenerate_data_js()
    return {"ok": True}


@app.post("/api/articles/{article_id}/publish")
def api_toggle_publish(article_id: str, actor: str = Depends(require_auth)):
    with db() as conn:
        row = conn.execute("SELECT published FROM articles WHERE id=?", (article_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        new_val = 0 if row["published"] else 1
        conn.execute("UPDATE articles SET published=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (new_val, article_id))
        record_audit(
            conn,
            user=actor,
            action="publish" if new_val else "unpublish",
            entity="article",
            entity_id=article_id,
            details={"published": bool(new_val)},
        )
    regenerate_data_js()
    return {"ok": True, "published": bool(new_val)}


@app.post("/api/articles/{article_id}/toggle-featured")
def api_toggle_featured(article_id: str, actor: str = Depends(require_auth)):
    with db() as conn:
        row = conn.execute("SELECT featured FROM articles WHERE id=?", (article_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        new_val = 0 if row["featured"] else 1
        if new_val == 1:
            conn.execute("UPDATE articles SET featured=0")
        conn.execute("UPDATE articles SET featured=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_val, article_id))
        record_audit(
            conn,
            user=actor,
            action="feature" if new_val else "unfeature",
            entity="article",
            entity_id=article_id,
            details={"featured": bool(new_val)},
        )
    regenerate_data_js()
    return {"ok": True, "featured": bool(new_val)}


@app.post("/api/publish")
def api_publish(actor: str = Depends(require_auth)):
    result = regenerate_data_js()
    with db() as conn:
        record_audit(
            conn,
            user=actor,
            action="regenerate",
            entity="public_data",
            entity_id="data.js",
            details=result,
        )
    return {"ok": True, **result}


# -----------------------------------------------------------------------------
# Image upload
# -----------------------------------------------------------------------------
@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...), actor: str = Depends(require_auth)):
    raw = await file.read()
    validation = validate_image_upload(raw, content_type=file.content_type)
    if not validation.ok:
        raise HTTPException(400, validation.error)

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
        record_audit(
            conn,
            user=actor,
            action="upload",
            entity="media",
            entity_id=f"{name}.webp",
            details={"source": file.filename or "", "mime": validation.detected_mime},
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


# ---- v0.3 section stubs ----
from fastapi.responses import HTMLResponse as _HR
try:
    _templates
except NameError:
    from fastapi.templating import Jinja2Templates as _J
    _templates = _J(directory=str(Path(__file__).resolve().parent.parent/"templates"))
_templates.env.globals["admin_asset_url"] = admin_asset_url


@app.get("/admin/articles/list")
def _articles_list_alias(request: Request):
    from fastapi.responses import RedirectResponse as _RR
    return _RR(url="/admin/articles", status_code=302)
# DISABLED_OLD_STUB @app.get_disabled("/admin/articles", response_class=_HR)  # OLD_STUB_DISABLED
def _section_articles(request: Request):
    u=current_user(request)
    if not u: return _auth_or_redirect(request)
    return _templates.TemplateResponse("section.html", {"request":request,"user":u,"title":"Материалы","section":"articles","url":"/admin/articles"})

@app.get("/admin/categories", response_class=_HR)
def _section_categories(request: Request):
    from fastapi.responses import RedirectResponse as _RR_
    return _RR_(url="/admin/categories/list", status_code=302)
@app.get("/admin/tags", response_class=_HR)
def _section_tags(request: Request):
    from fastapi.responses import RedirectResponse as _RR_
    return _RR_(url="/admin/tags/list", status_code=302)
@app.get("/admin/entities", response_class=_HR)
def _section_entities(request: Request):
    from fastapi.responses import RedirectResponse as _RR_
    return _RR_(url="/admin/entities/list", status_code=302)
@app.get("/admin/ads", response_class=_HR)
def _section_ads(request: Request):
    from fastapi.responses import RedirectResponse as _RR_
    return _RR_(url="/admin/ads/list", status_code=302)
@app.get("/admin/uploads", response_class=_HR)
def _section_uploads(request: Request):
    from fastapi.responses import RedirectResponse as _RR_
    return _RR_(url="/admin/uploads/list", status_code=302)

@app.get("/admin/uploads/list", response_class=_HR)
def _u_list(r:Request, q:str="", page:int=1):
    u=current_user(r)
    if not u: return _auth_or_redirect(r)
    per=60
    db=_adb(); c=db.cursor()
    where=""; args=[]
    if q:
        where=" WHERE filename LIKE ? OR url LIKE ?"
        args=[f"%{q}%",f"%{q}%"]
    total=c.execute(f"SELECT COUNT(*) FROM uploads{where}", args).fetchone()[0]
    pages=max(1,(total+per-1)//per)
    page=max(1,min(page,pages))
    off=(page-1)*per
    rows=c.execute(f"SELECT id,filename,url,size_bytes,created_at FROM uploads{where} ORDER BY id DESC LIMIT ? OFFSET ?", args+[per,off]).fetchall()
    db.close()
    return _templates.TemplateResponse("media.html",{"request":r,"user":u,"items":[dict(x) for x in rows],"total":total,"page":page,"pages":pages,"q":q,"section":"uploads","title":"Медиа"})

@app.post("/admin/uploads/{upload_id}/delete")
def _u_delete(upload_id:int, r:Request, _csrf: None = Depends(require_admin_csrf)):
    u=current_user(r)
    if not u: return _auth_or_redirect(r)
    import os
    db=_adb(); c=db.cursor()
    row=c.execute("SELECT url FROM uploads WHERE id=?", (upload_id,)).fetchone()
    if row:
        url=row["url"]
        # try delete physical file
        try:
            if url and url.startswith("/"):
                fp="/opt/fbrk-admin/static"+url
                if os.path.exists(fp): os.remove(fp)
                # also delete thumb if exists
                if "/uploads/" in url and "/thumb/" not in url:
                    th=fp.replace("/uploads/","/uploads/thumb/")
                    if os.path.exists(th): os.remove(th)
        except Exception:
            pass
        c.execute("DELETE FROM uploads WHERE id=?", (upload_id,))
        db.commit()
    db.close()
    return {"ok":True}

@app.get("/admin/users", response_class=_HR)
def _section_users(request: Request):
    from fastapi.responses import RedirectResponse as _RR_
    return _RR_(url="/admin/users/list", status_code=302)
@app.get("/admin/settings", response_class=_HR)
def _section_settings_page(request: Request):
    u=current_user(request)
    if not u: return _auth_or_redirect(request)
    return _templates.TemplateResponse("section.html", {"request":request,"user":u,"title":"Настройки","section":"settings_page","url":"/admin/settings"})

@app.get("/admin/audit", response_class=_HR)
def _section_audit(request: Request):
    from fastapi.responses import RedirectResponse as _RR_
    return _RR_(url="/admin/audit/list", status_code=302)
# ---- v0.4 dashboard widgets ----
from fastapi.responses import HTMLResponse as _HR2
_t2 = _templates if '_templates' in globals() else None
from pathlib import Path as _P2
if _t2 is None:
    from fastapi.templating import Jinja2Templates as _J2
    _t2 = _J2(directory=str(_P2(__file__).resolve().parent.parent/"templates"))

def _kpi_stats():
    import sqlite3, json
    db = sqlite3.connect(settings.db_path)
    db.row_factory = sqlite3.Row
    c = db.cursor()
    def q1(sql, *a):
        try:
            r = c.execute(sql, a).fetchone()
            return r[0] if r else 0
        except Exception:
            return 0
    stats = {
        'articles_total': q1('SELECT COUNT(*) FROM articles'),
        'articles_pub': q1('SELECT COUNT(*) FROM articles WHERE published=1'),
        'articles_draft': q1('SELECT COUNT(*) FROM articles WHERE COALESCE(published,0)=0'),
        'categories': q1('SELECT COUNT(*) FROM categories'),
        'ads_total': q1('SELECT COUNT(*) FROM ad_placements'),
        'ads_active': q1('SELECT COUNT(*) FROM ad_placements WHERE is_active=1'),
    }
    tags=set(); ents=0
    try:
        for row in c.execute('SELECT tags_json FROM articles'):
            try:
                arr = json.loads(row[0] or '[]')
                for t in arr:
                    if t: tags.add(str(t).strip().lower())
            except Exception: pass
    except Exception: pass
    try:
        for row in c.execute('SELECT entities_json FROM article_meta'):
            try:
                obj = json.loads(row[0] or '{}')
                if isinstance(obj, dict):
                    for v in obj.values():
                        if isinstance(v, list): ents += len(v)
                elif isinstance(obj, list):
                    ents += len(obj)
            except Exception: pass
    except Exception: pass
    stats['tags'] = len(tags)
    stats['entities'] = ents
    recent = []
    try:
        for row in c.execute("SELECT id,title,COALESCE(date_label,date_iso,'') as date FROM articles ORDER BY id DESC LIMIT 8"):
            recent.append({'id':row[0],'title':row[1],'date':row[2]})
    except Exception: pass
    audit = []
    try:
        for row in c.execute("SELECT ts,COALESCE(user,'-') as user,COALESCE(action,'') as action,COALESCE(entity,'') as entity,COALESCE(entity_id,'') as entity_id FROM audit_log ORDER BY id DESC LIMIT 8"):
            audit.append({'ts':row[0],'user':row[1],'action':row[2],'entity':row[3],'entity_id':row[4]})
    except Exception: pass
    db.close()
    return stats, recent, audit

@app.get("/admin/home", response_class=_HR2)
def _admin_home(request: Request):
    u = current_user(request)
    if not u: return _auth_or_redirect(request)
    stats, recent, audit = _kpi_stats()
    return _t2.TemplateResponse("dashboard.html", {"request":request,"user":u,"stats":stats,"recent":recent,"audit":audit})


# ---- v0.5 ads management ----
from fastapi import Form as _Form
from fastapi.responses import RedirectResponse as _RR

def _adb():
    import sqlite3
    db = sqlite3.connect(settings.db_path)
    db.row_factory = sqlite3.Row
    return db

@app.get("/admin/ads/list", response_class=_HR2)
def _ads_list(request: Request):
    u = current_user(request)
    if not u: return _auth_or_redirect(request)
    db = _adb(); c = db.cursor()
    rows = c.execute("SELECT id,slot_id,name,page,position,size_desktop,size_mobile,is_active,impressions,clicks FROM ad_placements ORDER BY page,slot_id").fetchall()
    items = [dict(r) for r in rows]
    db.close()
    return _t2.TemplateResponse("ads.html", {"request":request,"user":u,"items":items,"section":"ads","title":"Реклама"})


@app.get("/admin/ads/{ad_id}/edit", response_class=_HR2)
def _ads_edit(ad_id: int, request: Request):
    u = current_user(request)
    if not u: return _auth_or_redirect(request)
    db = _adb(); c = db.cursor()
    row = c.execute("SELECT id,slot_id,name,page,position,size_desktop,size_mobile,is_active,client_name,client_url,image_url,start_date,end_date,impressions,clicks,notes FROM ad_placements WHERE id=?", (ad_id,)).fetchone()
    db.close()
    if not row:
        return _RR(url="/admin/ads/list", status_code=303)
    item = dict(row)
    return _t2.TemplateResponse("ad_edit.html", {"request":request,"user":u,"item":item,"section":"ads","title":"Редактирование слота"})

@app.post("/admin/ads/{ad_id}/toggle")
def _ads_toggle(ad_id: int, request: Request, _csrf: None = Depends(require_admin_csrf)):
    u = current_user(request)
    if not u: return _auth_or_redirect(request)
    db = _adb(); c = db.cursor()
    c.execute("UPDATE ad_placements SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?", (ad_id,))
    try:
        c.execute("INSERT INTO audit_log(user,action,entity,entity_id) VALUES(?,?,?,?)", (u.get("username") if isinstance(u,dict) else str(u), "toggle", "ad_placement", str(ad_id)))
    except Exception: pass
    db.commit(); db.close()
    return _RR(url="/admin/ads/list", status_code=303)



def _validate_ad_image(url: str, ad_id: int | None = None):
    """Return (ok, normalized_url, error). Allowed: empty, http(s) to *.webp/.jpg/.jpeg/.png, or local /img/uploads/... existing file with allowed ext."""
    import os
    import re
    u = (url or "").strip()
    if not u:
        return True, "", None
    low = u.lower().split("?")[0]
    allowed_ext = (".webp", ".jpg", ".jpeg", ".png")
    if not low.endswith(allowed_ext):
        return False, u, "Недопустимый формат. Разрешены: webp, jpg, jpeg, png"
    if u.startswith("http://") or u.startswith("https://"):
        return True, u, None
    if not u.startswith("/"):
        u = "/" + u
    if not u.startswith("/img/uploads/"):
        return False, u, "Локальный путь должен начинаться с /img/uploads/"
    fp = upload_url_to_public_path(u)
    if not fp or not fp.exists():
        return False, u, "Файл не найден на диске"
    try:
        sz = os.path.getsize(fp)
        if sz > 2*1024*1024:
            return False, u, f"Слишком большой файл: {sz//1024} KB (лимит 2048 KB)"
    except Exception: pass
    try:
        from PIL import Image
        with Image.open(fp) as im:
            w,h = im.size
            fmt = (im.format or "").lower()
            if fmt not in ("webp","jpeg","jpg","png"):
                return False, u, f"Недопустимый внутренний формат: {fmt}"
            if w < 50 or h < 30 or w > 2000 or h > 2000:
                return False, u, f"Недопустимые размеры: {w}x{h}"
    except ImportError:
        pass
    except Exception as e:
        return False, u, f"Не удалось прочитать изображение: {e}"
    # --- slot size enforcement ---
    if ad_id is not None:
        try:
            from PIL import Image as _Img
            _db = _adb(); _cur = _db.cursor()
            _row = _cur.execute("SELECT size_desktop,size_mobile,slot_id FROM ad_placements WHERE id=?",(ad_id,)).fetchone()
            _db.close()
            def _parse(sz):
                if not sz or str(sz).lower() in ('hidden','none',''): return None
                m = re.match(r'^\s*(\d+)\s*[x×хХ]\s*(\d+)\s*$', str(sz))
                return (int(m.group(1)), int(m.group(2))) if m else None
            _fp = upload_url_to_public_path(u)
            if _row and _fp and _fp.exists():
                with _Img.open(_fp) as _im:
                    _w,_h = _im.size
                _exp_d = _parse(_row[0]); _exp_m = _parse(_row[1])
                _tol = 2
                def _match(exp):
                    return exp and abs(_w-exp[0])<=_tol and abs(_h-exp[1])<=_tol
                if (_exp_d or _exp_m) and not (_match(_exp_d) or _match(_exp_m)):
                    _need = []
                    if _exp_d: _need.append(f"{_exp_d[0]}×{_exp_d[1]} (desktop)")
                    if _exp_m: _need.append(f"{_exp_m[0]}×{_exp_m[1]} (mobile)")
                    return False, u, f"Размер картинки ({_w}×{_h}) не соответствует слоту {_row[2]}. Требуется: " + ' или '.join(_need)
        except Exception as _e:
            return False, u, f"Не удалось проверить размер креатива: " + str(_e)

    return True, u, None

@app.post("/admin/ads/{ad_id}/update")
def _ads_update(ad_id: int, request: Request, _csrf: None = Depends(require_admin_csrf), client_name: str = _Form(""), client_url: str = _Form(""), image_url: str = _Form(""), notes: str = _Form("")):
    u = current_user(request)
    if not u: return _auth_or_redirect(request)
    db = _adb(); c = db.cursor()
    ok,_iu,err = _validate_ad_image(image_url, ad_id=ad_id)
    if not ok:
        db.close(); return _t2.TemplateResponse('ad_edit.html', {'request':request,'user':u,'item':{'id':ad_id,'client_name':client_name,'client_url':client_url,'image_url':image_url,'notes':notes},'section':'ads','title':'Ошибка','error':err}, status_code=400)
    image_url = _iu
    c.execute("UPDATE ad_placements SET client_name=?, client_url=?, image_url=?, notes=?, updated_at=datetime('now') WHERE id=?", (client_name, client_url, image_url, notes, ad_id))
    try:
        c.execute("INSERT INTO audit_log(user,action,entity,entity_id,details) VALUES(?,?,?,?,?)", (u.get("username") if isinstance(u,dict) else str(u), "update", "ad_placement", str(ad_id), client_name))
    except Exception: pass
    db.commit(); db.close()
    return _RR(url="/admin/ads/list", status_code=303)


# ---- v0.6 tags+entities ----
import json as _json2

def _agg_tags(limit=500):
    db = _adb(); c = db.cursor()
    counts = {}
    try:
        for row in c.execute("SELECT tags_json FROM articles"):
            try:
                arr = _json2.loads(row[0] or "[]")
                for t in arr:
                    if not t: continue
                    k = str(t).strip()
                    if not k: continue
                    counts[k] = counts.get(k, 0) + 1
            except Exception: pass
    except Exception: pass
    db.close()
    items = sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))[:limit]
    return [{"tag": k, "count": v} for k, v in items]

def _agg_entities(limit=500):
    db = _adb(); c = db.cursor()
    type_map = {"person":"person","per":"person","people":"person",
                 "org":"org","organization":"org","company":"org","gov":"org",
                 "location":"location","loc":"location","place":"location","geo":"location","city":"location","country":"location"}
    buckets = {"person": {}, "org": {}, "location": {}, "other": {}}
    try:
        for row in c.execute("SELECT entities_json FROM article_meta"):
            try:
                obj = _json2.loads(row[0] or "[]")
            except Exception:
                continue
            entries = []
            if isinstance(obj, list):
                entries = obj
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, list):
                        for e in v:
                            if isinstance(e, dict):
                                d = dict(e); d.setdefault("type", k); entries.append(d)
                            else:
                                entries.append({"name": str(e), "type": k})
            for e in entries:
                if isinstance(e, dict):
                    name = (e.get("name") or e.get("text") or "").strip()
                    t = (e.get("type") or "other").lower()
                else:
                    name = str(e).strip(); t = "other"
                if not name: continue
                bk = type_map.get(t, "other")
                buckets[bk][name] = buckets[bk].get(name, 0) + 1
    except Exception: pass
    db.close()
    out = {}
    for bk, d in buckets.items():
        items = sorted(d.items(), key=lambda x: (-x[1], x[0].lower()))[:limit]
        out[bk] = [{"name": k, "count": v} for k, v in items]
    return out

@app.get("/admin/tags/list", response_class=_HR2)
def _tags_list(request: Request):
    u = current_user(request)
    if not u: return _auth_or_redirect(request)
    return _t2.TemplateResponse("tags.html", {"request":request,"user":u,"items":_agg_tags(),"section":"tags","title":"Теги"})

@app.get("/admin/entities/list", response_class=_HR2)
def _ents_list(request: Request):
    u = current_user(request)
    if not u: return _auth_or_redirect(request)
    return _t2.TemplateResponse("entities.html", {"request":request,"user":u,"buckets":_agg_entities(),"section":"entities","title":"Сущности"})


# ---- v0.7 categories CRUD ----
@app.get("/admin/categories/list", response_class=_HR2)
def _cats_list(request: Request):
    u=current_user(request)
    if not u: return _auth_or_redirect(request)
    db=_adb(); c=db.cursor()
    rows=c.execute("SELECT id,slug,label,sort_order,is_featured FROM categories ORDER BY sort_order,label").fetchall()
    items=[dict(r) for r in rows]; db.close()
    return _t2.TemplateResponse("categories.html",{"request":request,"user":u,"items":items,"section":"categories","title":"Категории"})

@app.post("/admin/categories/add")
def _cats_add(request: Request, _csrf: None = Depends(require_admin_csrf), slug: str=_Form(""), label: str=_Form(""), sort_order: int=_Form(0)):
    u=current_user(request)
    if not u: return _auth_or_redirect(request)
    if slug.strip() and label.strip():
        db=_adb(); c=db.cursor()
        try:
            c.execute("INSERT INTO categories(slug,label,sort_order,is_featured) VALUES(?,?,?,0)",(slug.strip(),label.strip(),sort_order))
            c.execute("INSERT INTO audit_log(user,action,entity,details) VALUES(?,?,?,?)",(str(u),"add","category",slug))
        except Exception as e: print(e)
        db.commit(); db.close()
    return _RR(url="/admin/categories/list", status_code=303)

@app.post("/admin/categories/{cid}/delete")
def _cats_del(cid: int, request: Request, _csrf: None = Depends(require_admin_csrf)):
    u=current_user(request)
    if not u: return _auth_or_redirect(request)
    db=_adb(); c=db.cursor()
    c.execute("DELETE FROM categories WHERE id=?",(cid,))
    c.execute("INSERT INTO audit_log(user,action,entity,entity_id) VALUES(?,?,?,?)",(str(u),"delete","category",str(cid)))
    db.commit(); db.close()
    return _RR(url="/admin/categories/list", status_code=303)


# v0.8 jkl
@app.get("/admin/users/list", response_class=_HR2)
def _u_list(r:Request):
    u=current_user(r)
    if not u: return _auth_or_redirect(r)
    db=_adb(); c=db.cursor()
    rows=c.execute("SELECT rowid as id,username,created_at FROM users ORDER BY username").fetchall()
    db.close()
    return _t2.TemplateResponse("users.html",{"request":r,"user":u,"items":[dict(x) for x in rows],"section":"users","title":"Users"})

@app.get("/admin/settings/list", response_class=_HR2)
def _s_list(r:Request):
    u=current_user(r)
    if not u: return _auth_or_redirect(r)
    db=_adb(); c=db.cursor()
    rows=c.execute("SELECT key,value,updated_at FROM settings ORDER BY key").fetchall()
    db.close()
    return _t2.TemplateResponse("settings.html",{"request":r,"user":u,"items":[dict(x) for x in rows],"section":"settings","title":"Settings"})

@app.post("/admin/settings/set")
def _s_set(r:Request, _csrf: None = Depends(require_admin_csrf), key:str=_Form(""), value:str=_Form("")):
    u=current_user(r)
    if not u: return _auth_or_redirect(r)
    if key.strip():
        db=_adb(); c=db.cursor()
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",(key.strip(),value))
        c.execute("INSERT INTO audit_log(user,action,entity,entity_id,details) VALUES(?,?,?,?,?)",(str(u),"set","setting",key.strip(),value[:200]))
        db.commit(); db.close()
    return _RR(url="/admin/settings/list", status_code=303)

@app.get("/admin/audit/list", response_class=_HR2)
def _a_list(r:Request):
    u=current_user(r)
    if not u: return _auth_or_redirect(r)
    db=_adb(); c=db.cursor()
    rows=c.execute("SELECT id,ts,user,action,entity,entity_id,details FROM audit_log ORDER BY id DESC LIMIT 500").fetchall()
    db.close()
    return _t2.TemplateResponse("audit.html",{"request":r,"user":u,"items":[dict(x) for x in rows],"section":"audit","title":"Audit"})

# --- Ads public API ---
@app.get("/api/ads")
def _api_ads():
    out = {}
    try:
        con = _adb()
        for r in con.execute("SELECT slot_id,client_name,client_url,image_url FROM ad_placements WHERE is_active=1 AND COALESCE(image_url,'')!=''"):
            out[r['slot_id']] = {'name': r['client_name'] or '', 'url': r['client_url'] or '#', 'image': r['image_url']}
        con.close()
    except Exception as e:
        return {'error': str(e), 'ads': {}}
    from fastapi.responses import JSONResponse
    resp = JSONResponse({'ads': out})
    resp.headers['Cache-Control'] = 'public, max-age=60'
    return resp
# --- end ads api ---

@app.get("/api/ads/impr/{slot_id}")
def _api_ad_impr(slot_id: str, request: Request):
    try:
        with _adb() as _c:
            _c.execute("UPDATE ad_placements SET impressions=COALESCE(impressions,0)+1 WHERE slot_id=?",(slot_id,))
            _c.execute("INSERT INTO ad_events(slot_id,event,ip,referer) VALUES(?,?,?,?)",(slot_id,'impr',(request.client.host if request.client else None),request.headers.get('referer')))
            _c.commit()
    except Exception: pass
    from fastapi.responses import Response as _R
    px = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    return _R(content=px, media_type='image/gif', headers={'Cache-Control':'no-store'})

@app.get("/api/ads/click/{slot_id}")
def _api_ad_click(slot_id: str, request: Request):
    from fastapi.responses import RedirectResponse as _RR
    url = '/'
    try:
        with _adb() as _c:
            cur=_c.execute("SELECT client_url FROM ad_placements WHERE slot_id=?",(slot_id,))
            row=cur.fetchone()
            if row and row[0]: url=row[0]
            _c.execute("UPDATE ad_placements SET clicks=COALESCE(clicks,0)+1 WHERE slot_id=?",(slot_id,))
            _c.execute("INSERT INTO ad_events(slot_id,event,ip,referer) VALUES(?,?,?,?)",(slot_id,'click',(request.client.host if request.client else None),request.headers.get('referer')))
            _c.commit()
    except Exception: pass
    return _RR(url=url, status_code=302)
@app.get("/api/ads/stats/daily")
def _api_ads_stats_daily(days: int = 14):
    days = max(1, min(int(days or 14), 90))
    out = {"days":[], "impr":[], "click":[], "by_slot":[]}
    try:
        with _adb() as _c:
            rows = _c.execute(f"SELECT substr(ts,1,10) AS d, event, COUNT(*) AS n FROM ad_events WHERE ts >= date('now', '-{days} day') GROUP BY d,event ORDER BY d").fetchall()
            agg = {}
            for r in rows:
                d=r['d']; agg.setdefault(d,{'impr':0,'click':0})[r['event']] = r['n']
            ds = sorted(agg.keys())
            out['days']=ds
            out['impr']=[agg[d]['impr'] for d in ds]
            out['click']=[agg[d]['click'] for d in ds]
            top = _c.execute(f"SELECT slot_id, SUM(CASE WHEN event='impr' THEN 1 ELSE 0 END) AS impr, SUM(CASE WHEN event='click' THEN 1 ELSE 0 END) AS clk FROM ad_events WHERE ts >= date('now','-{days} day') GROUP BY slot_id ORDER BY impr DESC LIMIT 10").fetchall()
            out['by_slot']=[{"slot_id":r['slot_id'],"impr":r['impr'],"click":r['clk']} for r in top]
    except Exception as e:
        out['error']=str(e)
    return out

@app.get("/api/admin/uploads")
def _api_admin_uploads(request: Request, limit: int = 200):
    u = current_user(request)
    if not u: return {"error":"auth"}
    import os
    base = str(platform_uploads_dir() / "thumb")
    out = []
    try:
        files = []
        for n in os.listdir(base):
            fp = os.path.join(base, n)
            try:
                st = os.stat(fp)
                files.append((st.st_mtime, n, st.st_size))
            except Exception: pass
        files.sort(reverse=True)
        for mt, n, sz in files[:max(1,min(int(limit or 200), 500))]:
            out.append({"name": n, "url": "/img/uploads/thumb/"+n, "size": sz})
    except Exception as e:
        return {"error": str(e)}
    return {"items": out}


@app.get("/admin/articles")
def _articles_list_real(request: Request, q: str = "", page: int = 1, cat: str = "", status: str = "", featured: str = "", sort: str = "date", dir: str = "desc"):
    u = current_user(request)
    if not u: return _RR(url="/admin/login", status_code=302)
    import math
    db=_adb()
    page=max(1,int(page or 1)); per=30; off=(page-1)*per
    conds=[]; args=[]
    if q:
        conds.append("(title LIKE ? OR id LIKE ?)"); args+=[f"%{q}%", f"%{q}%"]
    if cat:
        conds.append("category = ?"); args.append(cat)
    if status == "published":
        conds.append("published = 1")
    elif status == "draft":
        conds.append("published = 0")
    if featured == "1":
        conds.append("featured = 1")
    elif featured == "0":
        conds.append("featured = 0")
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    sort_col = {"date":"date_iso","updated":"updated_at","title":"title"}.get(sort, "date_iso")
    sort_dir = "ASC" if str(dir).lower()=="asc" else "DESC"
    secondary = "updated_at DESC" if sort_col != "updated_at" else "date_iso DESC"
    order_clause = f"ORDER BY {sort_col} {sort_dir}, {secondary}"
    total=db.execute(f"SELECT COUNT(*) FROM articles {where}",args).fetchone()[0]
    rows=db.execute(f"SELECT id,title,category,category_label,date_label,published,featured,image,updated_at FROM articles {where} {order_clause} LIMIT ? OFFSET ?",args+[per,off]).fetchall()
    cat_rows=db.execute("SELECT category, category_label, COUNT(*) c FROM articles GROUP BY category, category_label ORDER BY c DESC").fetchall()
    db.close()
    items=[dict(r) for r in rows]
    cats=[dict(r) for r in cat_rows]
    pages=max(1, math.ceil(total/per))
    return _templates.TemplateResponse("articles_list.html", {"request":request,"user":u,"title":"Материалы","section":"articles","items":items,"q":q,"cat":cat,"status":status,"featured":featured,"cats":cats,"page":page,"pages":pages,"total":total,"sort":sort,"dir":sort_dir.lower()})

@app.post("/admin/articles/bulk")
async def _articles_bulk(request: Request, _csrf: None = Depends(require_admin_csrf)):
    u = current_user(request)
    if not u:
        return _RR(url="/admin/login", status_code=302)
    form = await request.form()
    op = (form.get("op") or "").strip()
    ids = form.getlist("ids") if hasattr(form, "getlist") else form.getall("ids")
    ids = [str(x) for x in ids if x]
    back = form.get("back") or "/admin/articles"
    if not ids or op not in ("publish","unpublish","feature","unfeature","delete"):
        return _RR(url=back, status_code=303)
    db = _adb()
    try:
        qmarks = ",".join("?" for _ in ids)
        if op == "publish":
            db.execute(f"UPDATE articles SET published=1, updated_at=CURRENT_TIMESTAMP WHERE id IN ({qmarks})", ids)
        elif op == "unpublish":
            db.execute(f"UPDATE articles SET published=0, updated_at=CURRENT_TIMESTAMP WHERE id IN ({qmarks})", ids)
        elif op == "feature":
            db.execute(f"UPDATE articles SET featured=1, updated_at=CURRENT_TIMESTAMP WHERE id IN ({qmarks})", ids)
        elif op == "unfeature":
            db.execute(f"UPDATE articles SET featured=0, updated_at=CURRENT_TIMESTAMP WHERE id IN ({qmarks})", ids)
        elif op == "delete":
            db.execute(f"DELETE FROM articles WHERE id IN ({qmarks})", ids)
            try:
                db.execute(f"DELETE FROM article_meta WHERE article_id IN ({qmarks})", ids)
            except Exception:
                pass
        record_audit(
            db,
            user=u,
            action=f"bulk_{op}",
            entity="article",
            entity_id=",".join(ids[:20]),
            details={"count": len(ids), "truncated_ids": len(ids) > 20},
        )
        db.commit()
    finally:
        db.close()
    return _RR(url=back, status_code=303)
