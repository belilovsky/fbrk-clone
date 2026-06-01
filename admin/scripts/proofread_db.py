#!/usr/bin/env python3
"""
DeepSeek proofreading for legacy FBRK article copy.

Default mode is dry-run: it only lists candidate articles and shows heading
examples. With ``--apply`` it updates ``dek``, ``sections_json`` and
``body_json`` in SQLite, then regenerates public payloads.

Typical VPS run:
  cd /opt/fbrk-admin && set -a && . /etc/fbrk-admin/fbrk-admin.env && . ./.env && set +a \
    && python3 ./scripts/proofread_db.py --limit 25 --apply
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db import connect, row_to_article
from app.editorjs import normalize_section_heading, sections_to_editorjs
from app.publish import regenerate_data_js


DEFAULT_MODEL = os.environ.get("FBRK_PROOFREAD_MODEL", "deepseek-chat")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

SYSTEM_PROMPT = """Ты — литературный редактор ФБРК. Твоя задача — аккуратно вычитать текст статьи.

Верни строго ОДИН JSON-объект без пояснений:
{
  "dek": "исправленный лид",
  "sections": [
    {"h": "исправленный подзаголовок", "p": "исправленный текст секции"}
  ]
}

Правила:
- Не добавляй новые факты и не меняй смысл.
- Исправляй только базовую грамматику, пунктуацию, синтаксис, опечатки и шероховатости.
- Если исходный `dek` пустой, совпадает с заголовком или состоит только из служебной пометки вроде даты/источника, создай новый короткий лид на 1-2 предложения строго по содержанию статьи.
- Подзаголовки из КАПСЛОКА переводи в обычный регистр, но сохраняй аббревиатуры вроде МВД, КНБ, РК, ДТП, АЭС.
- Сохраняй количество секций, их порядок и общую структуру.
- Если в параграфе уже есть inline HTML (<a>, <strong>, <em>, <blockquote>, <ul>, <ol>, <li>, <br>, <img>, <hr>), постарайся его сохранить.
- Не сокращай текст агрессивно и не переписывай стиль заново.
- Если правка не нужна, верни исходный текст."""

SOURCE_HINT_RE = re.compile(r"(?:источник|источники|source)\s*:", re.IGNORECASE)
DATE_PREFIX_RE = re.compile(r"^\(?\s*\d{1,2}\s+[A-Za-zА-Яа-яЁё]+")
LEAD_HARD_CAP = 240


def _is_caps_heading(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    letters = [ch for ch in value if ch.isalpha()]
    if len(letters) < 4:
        return False
    upper = sum(1 for ch in value if ch.isupper())
    lower = sum(1 for ch in value if ch.islower())
    return lower == 0 and upper / max(len(letters), 1) >= 0.72


def _plain_text(text: str) -> str:
    value = re.sub(r"<[^>]+>", " ", str(text or ""))
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _is_metadata_only_dek(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    lower = value.casefold()
    if SOURCE_HINT_RE.search(value):
        return True
    if value.startswith("(") and value.endswith(")") and (DATE_PREFIX_RE.match(value) or "|" in value or "•" in value):
        return True
    return lower.startswith("источник:") or lower.startswith("источники:")


def _needs_lead_generation(article: dict) -> bool:
    dek = _plain_text(article.get("dek") or "")
    title = _plain_text(article.get("title") or "")
    if not dek:
        return True
    if _is_metadata_only_dek(dek):
        return True
    return bool(title and dek == title)


def _candidate_reasons(article: dict) -> list[str]:
    reasons: list[str] = []
    sections = article.get("sections") or []
    if any(_is_caps_heading((section or {}).get("h", "")) for section in sections if isinstance(section, dict)):
        reasons.append("caps_headings")
    if _needs_lead_generation(article):
        reasons.append("lead")
    return reasons


def _needs_proofread(article: dict) -> bool:
    return bool(_candidate_reasons(article))


def _article_input(article: dict) -> dict:
    return {
        "title": str(article.get("title") or "").strip(),
        "dek": str(article.get("dek") or "").strip(),
        "needs_lead_generation": _needs_lead_generation(article),
        "sections": [
            {
                "h": str((section or {}).get("h") or "").strip(),
                "p": str((section or {}).get("p") or "").strip(),
            }
            for section in (article.get("sections") or [])
            if isinstance(section, dict)
        ],
    }


def _call_deepseek(payload: dict, model: str) -> dict:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")

    request_payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(
        f"{DEEPSEEK_BASE.rstrip('/')}/chat/completions",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"deepseek {exc.code}: {detail[:400]}") from exc

    data = json.loads(body)
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def _sanitize_result(article: dict, result: dict) -> tuple[str, list[dict]]:
    original_dek = _plain_text(article.get("dek") or "")
    title = _plain_text(article.get("title") or "")
    original_sections = [
        {
            "h": str((section or {}).get("h") or "").strip(),
            "p": str((section or {}).get("p") or "").strip(),
        }
        for section in (article.get("sections") or [])
        if isinstance(section, dict)
    ]
    context = " ".join(filter(None, [str(article.get("title") or "").strip(), original_dek]))

    new_dek = _plain_text(result.get("dek") or "") or original_dek
    if _needs_lead_generation(article) and (not new_dek or _is_metadata_only_dek(new_dek) or (title and new_dek == title)):
        new_dek = _fallback_lead(article, fallback=original_dek or title)
    if len(new_dek) > LEAD_HARD_CAP:
        new_dek = _trim_lead(new_dek, LEAD_HARD_CAP)
    sections_in = result.get("sections") if isinstance(result.get("sections"), list) else []
    if len(sections_in) != len(original_sections):
      sections_in = original_sections

    cleaned_sections: list[dict] = []
    for original, updated in zip(original_sections, sections_in):
        updated = updated if isinstance(updated, dict) else {}
        heading = normalize_section_heading(updated.get("h") or original["h"], context=context)
        paragraph = str(updated.get("p") or original["p"]).strip() or original["p"]
        if original["p"]:
            ratio = len(paragraph) / max(len(original["p"]), 1)
            if ratio < 0.55 or ratio > 1.8:
                paragraph = original["p"]
        cleaned_sections.append({"h": heading, "p": paragraph})

    return new_dek, cleaned_sections


def _trim_lead(text: str, maxlen: int = LEAD_HARD_CAP) -> str:
    value = _plain_text(text)
    if len(value) <= maxlen:
        return value
    sentences = re.split(r"(?<=[.!?])\s+", value)
    acc = []
    current = 0
    for sentence in sentences:
        if not sentence:
            continue
        extra = len(sentence) + (1 if acc else 0)
        if current + extra > maxlen and acc:
            break
        acc.append(sentence)
        current += extra
        if current >= 120:
            break
    if acc:
        return " ".join(acc).strip()
    cut = value[:maxlen].rsplit(" ", 1)[0].strip()
    return (cut or value[:maxlen]).rstrip(" ,;:-—")


def _fallback_lead(article: dict, fallback: str = "") -> str:
    title = _plain_text(article.get("title") or "")
    if fallback and not _is_metadata_only_dek(fallback) and fallback != title:
        return _trim_lead(fallback)
    paragraphs: list[str] = []
    for section in article.get("sections") or []:
        if not isinstance(section, dict):
            continue
        text = _plain_text(section.get("p") or "")
        if text:
            paragraphs.append(text)
    if paragraphs:
        lead = _trim_lead(paragraphs[0])
        if lead:
            return lead
    return _trim_lead(title)


def _backup_db() -> Path:
    db_path = Path(settings.db_path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = db_path.with_name(f"{db_path.stem}-proofread-{stamp}{db_path.suffix}")
    with sqlite3.connect(str(db_path)) as src:
        src.execute("VACUUM INTO ?", (str(backup),))
    return backup


def _load_articles(limit: int, only: str | None) -> list[dict]:
    with connect() as conn:
        if only:
            rows = conn.execute(
                "SELECT * FROM articles WHERE id = ? OR slug = ? ORDER BY date_iso DESC",
                (only, only),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM articles WHERE published = 1 ORDER BY date_iso DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [row_to_article(row) for row in rows]


def _apply_article(article: dict, dek: str, sections: list[dict]) -> None:
    body = sections_to_editorjs(sections)
    with connect() as conn:
        conn.execute(
            """
            UPDATE articles
               SET dek = ?,
                   body_json = ?,
                   sections_json = ?,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
            """,
            (
                dek,
                json.dumps(body, ensure_ascii=False),
                json.dumps(sections, ensure_ascii=False),
                article["id"],
            ),
        )
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes into SQLite and regenerate public JS payloads")
    parser.add_argument("--limit", type=int, default=20, help="max published articles to inspect in dry-run mode")
    parser.add_argument("--only", help="proofread a single article by id or slug")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="DeepSeek model id")
    parser.add_argument("--sleep", type=float, default=0.15, help="sleep between API calls when applying")
    args = parser.parse_args()

    articles = _load_articles(args.limit, args.only)
    candidates = [article for article in articles if args.only or _needs_proofread(article)]

    if not candidates:
        print("No proofreading candidates found.")
        return 0

    print(f"Candidates: {len(candidates)}")
    reason_counts = Counter()
    for article in candidates:
        for reason in _candidate_reasons(article):
            reason_counts[reason] += 1
    if reason_counts:
        print("Reasons: " + ", ".join(f"{key}={reason_counts[key]}" for key in sorted(reason_counts)))
    for article in candidates[:10]:
        headings = [
            str((section or {}).get("h") or "").strip()
            for section in (article.get("sections") or [])
            if isinstance(section, dict) and str((section or {}).get("h") or "").strip()
        ]
        print(f"- {article['slug']}: reasons={','.join(_candidate_reasons(article)) or '-'} headings={headings[:3]}")

    if not args.apply:
        print("Dry-run only. Re-run with --apply to update the DB.")
        return 0

    backup = _backup_db()
    print(f"Backup: {backup}")

    changed = 0
    failed = 0
    for idx, article in enumerate(candidates, 1):
        try:
            payload = _article_input(article)
            result = _call_deepseek(payload, args.model)
            dek, sections = _sanitize_result(article, result)
            if dek == _plain_text(article.get("dek") or "") and sections == (article.get("sections") or []):
                continue
            _apply_article(article, dek, sections)
            changed += 1
            print(f"updated: {article['slug']}")
        except Exception as exc:
            failed += 1
            print(f"failed: {article['slug']}: {type(exc).__name__}: {exc}")
        if args.sleep and idx < len(candidates):
            time.sleep(args.sleep)

    regen = regenerate_data_js()
    print(f"Proofread changes applied: {changed}")
    print(f"Proofread errors: {failed}")
    print(f"Public payload regenerated: {regen}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
