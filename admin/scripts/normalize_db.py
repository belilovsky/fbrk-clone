#!/usr/bin/env python3
"""
FBRK DB normalization (replaces Codex-blocked steps).

Run on VPS:
  cd /opt/fbrk-admin && set -a && . /etc/fbrk-admin/fbrk-admin.env && set +a \
    && python3 /tmp/normalize_db.py [--apply]

Without --apply: dry-run, prints what would change.
With --apply: makes a backup first, then applies, then regenerates data.js.

Steps:
  1. Remove duplicate "ocherednoe-massovoe-otravlenie-...-0" (suffix duplicate)
  2. Promote investigation candidates by heuristic:
     - body_json has >= 25 blocks AND date_iso older than 7 days
     - OR slug matches investigation patterns (latifundist, skhem, dezinsekc,
       riskovan, dele, dosie, presledov, korrupc, finans, monopol)
  3. Normalize source URLs:
     - source = 'fbrk.kz' (no URL) -> guess from slug pattern (try /articles/<slug>)
     - empty source -> same heuristic
  4. Regenerate sections_json from body_json for all articles (idempotent;
     only writes back if changed).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.environ.get("FBRK_DB") or os.environ.get("FBRK_DB_PATH") or "/opt/fbrk-admin/fbrk.db"

# STRICT patterns — auto-promote regardless of length (these slugs are exclusively
# used by long-form investigations on fbrk.kz; even 1-3 block summaries belong to
# a multi-part investigation series).
INV_STRICT_PATTERNS = [
    r"latifundist",          # latifundisty-kazakhstana-glava-N (multi-part series)
    r"^dosie-|-dosie-",      # dosie-N of named oligarchs
    r"otmyvani",             # otmyvanie-aktivov / otmyvanie-deneg
    r"vivod-aktivov",        # vivod-aktivov-cherez-...
    r"raskhody-regionov",    # multi-part regional spending series
    r"finansovye-pokazateli-regionov",  # series
    r"skhemy-raboty",        # full-length explainer
]
INV_STRICT_RE = re.compile("|".join(INV_STRICT_PATTERNS))

# WEAK patterns — only promote if ALSO long (>= MIN_BLOCKS). Many short news items
# legitimately mention these keywords without being investigations.
INV_WEAK_PATTERNS = [
    r"dezinsekci",           # mostly news, but long-forms exist
    r"khishchen",
    r"epshtey",              # mostly news, but possible long-form
    r"rakhat-alie",          # series of investigations into Rakhat Aliyev
    r"-skhem|^skhem",
    r"-masimov|^masimov",
    r"-dubae|-vena|-londone|-monako",
    r"prokuratur.*vskryla",
    r"presledovan",
]
INV_WEAK_RE = re.compile("|".join(INV_WEAK_PATTERNS))

INVESTIGATION_MIN_BLOCKS = 25
INVESTIGATION_AGE_DAYS = 7  # only articles older than this can be promoted (to avoid breaking news)


def get_con() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def step_remove_dup(con, apply: bool) -> dict:
    """Remove suffix-duplicates: rows where another row has the same title and
    base slug, and this slug ends in `-N` digit suffix."""
    rows = con.execute("""
        SELECT a.slug, a.title, a.date_iso
        FROM articles a
        WHERE EXISTS (
            SELECT 1 FROM articles b
            WHERE b.title = a.title
              AND b.slug != a.slug
              AND b.slug || '-0' = a.slug
        )
    """).fetchall()
    out = {"to_remove": [dict(r) for r in rows]}
    if apply and rows:
        for r in rows:
            con.execute("DELETE FROM articles WHERE slug = ?", (r["slug"],))
        con.commit()
    return out


def step_promote_investigations(con, apply: bool) -> dict:
    """Promote candidates to category=investigation."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=INVESTIGATION_AGE_DAYS)).strftime("%Y-%m-%d")
    rows = con.execute("""
        SELECT slug, title, date_iso,
               json_array_length(json_extract(body_json,'$.blocks')) AS blocks,
               length(sections_json) AS sec_len
        FROM articles
        WHERE category = 'news'
    """).fetchall()
    candidates = []
    for r in rows:
        slug = r["slug"]
        is_long = r["blocks"] is not None and r["blocks"] >= INVESTIGATION_MIN_BLOCKS and r["date_iso"] <= cutoff
        is_strict = bool(INV_STRICT_RE.search(slug))
        is_weak = bool(INV_WEAK_RE.search(slug))
        # Promote if: strict-pattern (always) OR (long AND weak-pattern) OR long
        if is_strict or is_long:
            reason = "+".join(filter(None, [
                "strict" if is_strict else "",
                "blocks" if is_long else "",
                "weak" if (is_weak and is_long) else "",
            ]))
            candidates.append({
                "slug": slug, "title": r["title"], "date_iso": r["date_iso"],
                "blocks": r["blocks"], "reason": reason,
            })
    if apply and candidates:
        for c in candidates:
            con.execute(
                "UPDATE articles SET category=?, category_label=?, updated_at=CURRENT_TIMESTAMP WHERE slug=?",
                ("investigation", "Расследование", c["slug"]),
            )
        con.commit()
    return {"count": len(candidates), "samples": candidates[:8]}


def step_normalize_source(con, apply: bool) -> dict:
    """
    For source = 'fbrk.kz' or empty: guess full URL from slug.
    fbrk.kz uses /articles/<slug> for everything.
    """
    rows = con.execute("""
        SELECT slug FROM articles
        WHERE source = 'fbrk.kz' OR source IS NULL OR source = ''
    """).fetchall()
    fixes = []
    for r in rows:
        slug = r["slug"]
        # Strip a -0/-1 numeric suffix that Drupal adds for slug collisions.
        # We'll leave them as-is — site URL is canonical with suffix.
        guessed = f"https://fbrk.kz/articles/{slug}"
        fixes.append({"slug": slug, "new_source": guessed})
    if apply and fixes:
        for f in fixes:
            con.execute(
                "UPDATE articles SET source=?, updated_at=CURRENT_TIMESTAMP WHERE slug=?",
                (f["new_source"], f["slug"]),
            )
        con.commit()
    return {"count": len(fixes), "samples": fixes[:5]}


def step_regen_sections(con, apply: bool) -> dict:
    """
    Regenerate sections_json from body_json using the same logic as ingester.
    Only updates rows where the regenerated version differs.
    """
    sys.path.insert(0, "/opt/fbrk-admin")
    try:
        from app.editorjs import editorjs_to_sections
    except Exception as e:
        return {"error": f"cannot import editorjs_to_sections: {e}"}

    rows = con.execute(
        "SELECT slug, body_json, sections_json FROM articles"
    ).fetchall()
    diffs = []
    for r in rows:
        try:
            body = json.loads(r["body_json"]) if r["body_json"] else {"blocks": []}
            new_sections = editorjs_to_sections(body)
            new_json = json.dumps(new_sections, ensure_ascii=False)
        except Exception as e:
            diffs.append({"slug": r["slug"], "error": str(e)})
            continue
        if new_json != r["sections_json"]:
            diffs.append({"slug": r["slug"], "old_len": len(r["sections_json"] or ""), "new_len": len(new_json)})
    if apply and diffs:
        # Re-fetch and update only differing ones
        for d in diffs:
            if "error" in d:
                continue
            row = con.execute("SELECT body_json FROM articles WHERE slug=?", (d["slug"],)).fetchone()
            body = json.loads(row["body_json"])
            new_sections = editorjs_to_sections(body)
            new_json = json.dumps(new_sections, ensure_ascii=False)
            con.execute(
                "UPDATE articles SET sections_json=?, updated_at=CURRENT_TIMESTAMP WHERE slug=?",
                (new_json, d["slug"]),
            )
        con.commit()
    return {"count": len(diffs), "samples": diffs[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually modify DB")
    ap.add_argument("--steps", default="dup,inv,src,sec",
                    help="comma-separated subset of: dup,inv,src,sec")
    args = ap.parse_args()

    if args.apply:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = f"/opt/fbrk-admin/backups/fbrk-{ts}-pre-normalize.db"
        print(f"[backup] {bak}")
        with sqlite3.connect(DB_PATH) as src:
            src.execute(f"VACUUM INTO ?", (bak,))
        print(f"[backup] OK ({Path(bak).stat().st_size / (1024*1024):.1f} MB)")

    con = get_con()
    steps = set(args.steps.split(","))
    out = {"apply": args.apply}

    if "dup" in steps:
        print("\n[step] remove duplicates")
        out["duplicates"] = step_remove_dup(con, args.apply)
        print(f"  -> {len(out['duplicates']['to_remove'])} to remove")
        for d in out["duplicates"]["to_remove"]:
            print(f"     - {d['slug']}")

    if "inv" in steps:
        print("\n[step] promote investigations")
        out["investigations"] = step_promote_investigations(con, args.apply)
        print(f"  -> {out['investigations']['count']} candidates")
        for c in out["investigations"]["samples"]:
            print(f"     - [{c['blocks']}b {c['reason']}] {c['slug']}")

    if "src" in steps:
        print("\n[step] normalize source URLs")
        out["sources"] = step_normalize_source(con, args.apply)
        print(f"  -> {out['sources']['count']} to fix")
        for s in out["sources"]["samples"]:
            print(f"     - {s['slug']} -> {s['new_source']}")

    if "sec" in steps:
        print("\n[step] regenerate sections_json (idempotent)")
        out["sections"] = step_regen_sections(con, args.apply)
        if "error" in out["sections"]:
            print(f"  -> ERROR: {out['sections']['error']}")
        else:
            print(f"  -> {out['sections']['count']} differ from current")

    con.close()
    print(f"\n[done] apply={args.apply}")

    if args.apply:
        print("[next] regenerate data.js")
        sys.path.insert(0, "/opt/fbrk-admin")
        from app.publish import regenerate_data_js
        result = regenerate_data_js()
        print(f"[regen] {result}")


if __name__ == "__main__":
    main()
