"""SQLite schema + connection helpers for FBRK admin."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id            TEXT PRIMARY KEY,            -- stable slug/id like 'vena-musin'
    slug          TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    dek           TEXT NOT NULL DEFAULT '',
    author        TEXT NOT NULL DEFAULT 'fbrk_news',
    date_iso      TEXT NOT NULL,               -- 'YYYY-MM-DD'
    date_label    TEXT NOT NULL,               -- '23 апреля 2026'
    category      TEXT NOT NULL DEFAULT 'news',        -- news | investigation
    category_label TEXT NOT NULL DEFAULT 'Новости',
    image         TEXT NOT NULL DEFAULT '',
    tags_json     TEXT NOT NULL DEFAULT '[]',
    source        TEXT NOT NULL DEFAULT '',
    body_json     TEXT NOT NULL DEFAULT '{}',  -- Editor.js output
    sections_json TEXT NOT NULL DEFAULT '[]',  -- rendered [{h,p}, ...] for public site
    featured      INTEGER NOT NULL DEFAULT 0,
    published     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date_iso DESC);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);

CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uploads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT NOT NULL,
    url           TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)


def row_to_article(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "dek": row["dek"],
        "author": row["author"],
        "dateIso": row["date_iso"],
        "date": row["date_label"],
        "category": row["category"],
        "categoryLabel": row["category_label"],
        "image": row["image"],
        "tags": json.loads(row["tags_json"] or "[]"),
        "source": row["source"],
        "body": json.loads(row["body_json"] or "{}"),
        "sections": json.loads(row["sections_json"] or "[]"),
        "featured": bool(row["featured"]),
        "published": bool(row["published"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }
