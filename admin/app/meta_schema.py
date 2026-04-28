"""article_meta table — AI-enrichment results (summary, importance, sentiment, entities).

Keeps AI outputs separate from the core `articles` table so reruns/updates are
cheap and we can evolve the schema without touching the main import pipeline.
"""
from __future__ import annotations

from .db import db


META_SCHEMA = """
CREATE TABLE IF NOT EXISTS article_meta (
    article_id     TEXT PRIMARY KEY,
    summary_short  TEXT NOT NULL DEFAULT '',   -- 1-sentence abstract (<180 chars)
    summary_tts    TEXT NOT NULL DEFAULT '',   -- 2-4 sentence speakable intro
    key_points     TEXT NOT NULL DEFAULT '[]', -- JSON array of bullet strings
    importance     INTEGER NOT NULL DEFAULT 0, -- 0..5
    sentiment      TEXT    NOT NULL DEFAULT '',-- positive | negative | neutral | mixed
    entities_json  TEXT    NOT NULL DEFAULT '[]',
    -- entities: [{"name": str, "type": person|org|gov|place|law|case|money,
    --            "wikidata": "Q123" | null, "wiki_url": str | null}]
    region         TEXT NOT NULL DEFAULT '',   -- e.g. 'Астана', 'Алматы', 'Атырауская обл.'
    category_auto  TEXT NOT NULL DEFAULT '',   -- AI-suggested category
    tags_auto      TEXT NOT NULL DEFAULT '[]', -- JSON array
    model          TEXT NOT NULL DEFAULT '',   -- e.g. 'gpt-4o-mini'
    input_chars    INTEGER NOT NULL DEFAULT 0,
    processed_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error          TEXT NOT NULL DEFAULT '',   -- last error message (empty if ok)
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_article_meta_importance ON article_meta(importance DESC);
CREATE INDEX IF NOT EXISTS idx_article_meta_processed ON article_meta(processed_at DESC);
"""


def ensure_meta_schema() -> None:
    with db() as conn:
        conn.executescript(META_SCHEMA)


def meta_stats() -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "       SUM(CASE WHEN error='' THEN 1 ELSE 0 END) AS ok, "
            "       SUM(CASE WHEN error<>'' THEN 1 ELSE 0 END) AS err "
            "FROM article_meta"
        ).fetchone()
        arts = conn.execute(
            "SELECT COUNT(*) AS n FROM articles WHERE published=1"
        ).fetchone()
    return {
        "articles_total": arts["n"],
        "meta_total": row["total"] or 0,
        "meta_ok": row["ok"] or 0,
        "meta_err": row["err"] or 0,
        "pending": (arts["n"] or 0) - (row["total"] or 0),
    }
