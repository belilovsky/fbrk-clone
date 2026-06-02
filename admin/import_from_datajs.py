"""One-shot: import existing js/data.js into the admin SQLite so the dashboard
shows the current 12 articles on first boot."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make app.* importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings  # noqa: E402
from app.db import db, init_db  # noqa: E402
from app.editorjs import sections_to_editorjs  # noqa: E402


def parse_data_js(path: Path) -> dict:
    """Load FBRK_DATA from a JS file via Node require(). Works with either
    legacy (const + optional module.exports) or regenerated (pure JSON) files."""
    import subprocess
    script = f"""
const fs = require('fs');
let code = fs.readFileSync({json.dumps(str(path))}, 'utf8');
if (!code.includes('module.exports')) {{
    // Handle the regenerated file where we emit 'const FBRK_DATA = {{...}};'
    code += '\\nmodule.exports = (typeof FBRK_DATA !== "undefined") ? FBRK_DATA : null;';
}}
const Module = require('module');
const m = new Module('datajs');
m._compile(code, {json.dumps(str(path))});
process.stdout.write(JSON.stringify(m.exports));
"""
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"node parse failed: {r.stderr}")
    return json.loads(r.stdout)


def main() -> None:
    init_db()
    data = parse_data_js(Path(settings.data_js_path))
    articles = data.get("articles", [])
    with db() as conn:
        for a in articles:
            body = sections_to_editorjs(a.get("sections") or [])
            conn.execute(
                """INSERT OR REPLACE INTO articles
                   (id, slug, title, dek, author, date_iso, date_label,
                    category, category_label, image, tags_json, source,
                    body_json, sections_json, featured, published)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a["id"], a.get("slug") or a["id"], a["title"], a.get("dek", ""),
                    a.get("author", "fbrk_news"), a.get("dateIso", ""),
                    a.get("date", ""), a.get("category", "news"),
                    a.get("categoryLabel", "Новости"), a.get("image", ""),
                    json.dumps(a.get("tags") or [], ensure_ascii=False),
                    a.get("source", ""),
                    json.dumps(body, ensure_ascii=False),
                    json.dumps(a.get("sections") or [], ensure_ascii=False),
                    1 if a.get("featured") else 0, 1,
                ),
            )
    print(f"imported {len(articles)} articles")


if __name__ == "__main__":
    main()
