"""AI-enrichment worker for FBRK articles.

Reads unprocessed articles from SQLite, calls OpenAI chat completions with a
strict JSON schema prompt, and writes results to `article_meta`.

Usage:
    # Full run (all pending)
    OPENAI_API_KEY=sk-... python3 /opt/fbrk-admin/enrich.py

    # Small batch for testing
    python3 /opt/fbrk-admin/enrich.py --limit 5

    # Re-run failed rows
    python3 /opt/fbrk-admin/enrich.py --retry-errors

    # Single article by id
    python3 /opt/fbrk-admin/enrich.py --only <article_id>

Model defaults to gpt-4o-mini (cheap, good enough for RU). Override with
FBRK_ENRICH_MODEL or --model.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Make the app package importable when run as script from /opt/fbrk-admin
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import db, row_to_article
from app.meta_schema import ensure_meta_schema


DEFAULT_MODEL = os.environ.get("FBRK_ENRICH_MODEL", "gemini-2.0-flash")
FALLBACK_MODEL = os.environ.get("FBRK_ENRICH_FALLBACK_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Max characters from the article body to send to the model (token budget guard)
MAX_INPUT_CHARS = 9000


SYSTEM_PROMPT = """Ты — редактор независимого казахстанского издания ФБРК. Тебе нужно обогатить карточку статьи для SEO/Schema.org/AEO.

Строго верни ОДИН JSON-объект без пояснений. Схема:
{
  "summary_short": "Одно предложение, до 180 символов, по-русски, суть статьи.",
  "summary_tts": "2-4 предложения, гладкий разговорный русский — это зачитается голосом.",
  "key_points": ["3-5 коротких буллета, каждый <= 140 символов"],
  "importance": 1-5,   // 1 = проходная заметка, 3 = средняя новость, 5 = крупное расследование/скандал
  "sentiment": "positive" | "negative" | "neutral" | "mixed",
  "entities": [
    {"name": "Назарбаев", "type": "person"},
    {"name": "КНБ", "type": "org"},
    {"name": "Атырауская область", "type": "place"}
  ],
  // допустимые type: person, org, gov, place, law, case, money, other
  "region": "Астана" | "Алматы" | "Атырауская область" | ... | "",  // главный географический контекст в РК
  "category_auto": "news" | "investigation" | "analysis" | "opinion",
  "tags_auto": ["до 6 тегов на русском, заглавные буквы, короткие"]
}

ВАЖНО:
- Пиши только на русском.
- НЕ придумывай факты — бери только то, что есть в тексте.
- Если не уверен в значении — ставь "" или пустой массив.
- JSON должен быть валидным, без markdown-обёртки."""


def _strip(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _build_article_text(a: dict) -> str:
    parts = [a.get("title") or ""]
    if a.get("dek"):
        parts.append(_strip(a["dek"]))
    for s in a.get("sections") or []:
        if not isinstance(s, dict):
            continue
        if s.get("h"):
            parts.append(str(s["h"]))
        if s.get("p"):
            parts.append(_strip(str(s["p"])))
    text = "\n\n".join(p for p in parts if p)
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + "…"
    return text


def _call_openai(text: str, model: str) -> dict:
    """Call OpenAI Chat Completions and return parsed JSON."""
    import urllib.request
    import urllib.error

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    req = urllib.request.Request(
        f"{OPENAI_BASE}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"openai {e.code}: {msg[:500]}") from e

    data = json.loads(body)
    content = data["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except Exception as e:
        raise RuntimeError(f"bad JSON from model: {e}; head={content[:200]}") from e


def _call_gemini(text: str, model: str) -> dict:
    """Call Google Gemini generateContent endpoint, strict JSON response."""
    import urllib.request
    import urllib.error

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "response_mime_type": "application/json",
            "maxOutputTokens": 8192,
            # Disable thinking for 2.5-flash — we want output tokens, not reasoning.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"gemini {e.code}: {msg[:500]}") from e

    data = json.loads(body)
    try:
        parts = data["candidates"][0]["content"]["parts"]
        content = "".join(p.get("text", "") for p in parts)
    except Exception as e:
        raise RuntimeError(f"bad gemini response: {str(data)[:300]}") from e
    try:
        return json.loads(content)
    except Exception as e:
        raise RuntimeError(f"bad JSON from model: {e}; head={content[:200]}") from e


def _call_model(text: str, model: str) -> dict:
    """Route to the right provider based on model id prefix."""
    m = (model or "").lower()
    if m.startswith("gemini"):
        return _call_gemini(text, model)
    return _call_openai(text, model)


def _should_fallback_from_gemini(model: str, error_msg: str) -> bool:
    """Retry with OpenAI when Gemini is unavailable/quota-blocked."""
    if not OPENAI_API_KEY:
        return False
    if not (model or "").lower().startswith("gemini"):
        return False
    em = (error_msg or "").lower()
    triggers = (
        "gemini 403",
        "gemini 429",
        "gemini 503",
        "denied access",
        "quota",
        "resource_exhausted",
        "unavailable",
        "high demand",
    )
    return any(t in em for t in triggers)


def _sanitize_result(raw: dict) -> dict:
    def _str(x, maxlen=500):
        if not isinstance(x, str):
            return ""
        return x.strip()[:maxlen]

    def _list_str(x, maxlen=200, cap=10):
        if not isinstance(x, list):
            return []
        out = []
        for item in x[:cap]:
            if isinstance(item, str) and item.strip():
                out.append(item.strip()[:maxlen])
        return out

    entities_in = raw.get("entities") if isinstance(raw.get("entities"), list) else []
    entities: list[dict] = []
    for e in entities_in[:20]:
        if not isinstance(e, dict):
            continue
        name = _str(e.get("name"), 120)
        etype = _str(e.get("type"), 30).lower() or "other"
        if etype not in {"person", "org", "gov", "place", "law", "case", "money", "other"}:
            etype = "other"
        if name:
            entities.append({
                "name": name,
                "type": etype,
                "wikidata": _str(e.get("wikidata"), 20) or None,
                "wiki_url": _str(e.get("wiki_url"), 300) or None,
            })

    importance = raw.get("importance")
    try:
        importance = int(importance)
    except Exception:
        importance = 0
    importance = max(0, min(5, importance))

    sentiment = _str(raw.get("sentiment"), 20).lower()
    if sentiment not in {"positive", "negative", "neutral", "mixed"}:
        sentiment = ""

    category_auto = _str(raw.get("category_auto"), 30).lower()
    if category_auto not in {"news", "investigation", "analysis", "opinion"}:
        category_auto = ""

    return {
        "summary_short": _str(raw.get("summary_short"), 220),
        "summary_tts": _str(raw.get("summary_tts"), 600),
        "key_points": _list_str(raw.get("key_points"), 160, 5),
        "importance": importance,
        "sentiment": sentiment,
        "entities": entities,
        "region": _str(raw.get("region"), 80),
        "category_auto": category_auto,
        "tags_auto": _list_str(raw.get("tags_auto"), 60, 6),
    }


def _fallback_result(a: dict) -> dict:
    """Deterministic fallback when model providers are unavailable."""
    title = (a.get("title") or "").strip()
    dek = _strip(a.get("dek") or "")

    paragraphs: list[str] = []
    for s in a.get("sections") or []:
        if isinstance(s, dict) and s.get("p"):
            p = _strip(str(s.get("p")))
            if p:
                paragraphs.append(p)

    lead = dek or (paragraphs[0] if paragraphs else "")
    summary_short = (lead or title)[:220]
    summary_tts = " ".join(x for x in [dek, paragraphs[0] if paragraphs else ""] if x).strip()
    if not summary_tts:
        summary_tts = summary_short
    summary_tts = summary_tts[:600]

    key_points: list[str] = []
    for chunk in [dek, *paragraphs[:6]]:
        for sent in re.split(r"(?<=[.!?])\s+", chunk or ""):
            s = _strip(sent).strip(" .")
            if len(s) < 40:
                continue
            s = s[:160]
            if s and s not in key_points:
                key_points.append(s)
            if len(key_points) >= 5:
                break
        if len(key_points) >= 5:
            break
    if not key_points and summary_short:
        key_points = [summary_short[:160]]

    entities: list[dict] = []
    seen: set[str] = set()
    for t in a.get("tags") or []:
        if not isinstance(t, str):
            continue
        name = t.strip()[:120]
        if not name:
            continue
        lk = name.lower()
        if lk in seen:
            continue
        seen.add(lk)
        entities.append({"name": name, "type": "other", "wikidata": None, "wiki_url": None})
        if len(entities) >= 12:
            break

    blob = " ".join(x for x in [title, dek] if x)
    for m in re.finditer(
        r"\b[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9-]{2,}(?:\s+[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9-]{2,}){0,2}\b",
        blob,
    ):
        name = m.group(0).strip()[:120]
        lk = name.lower()
        if lk in seen:
            continue
        if lk in {"новости", "расследование", "казахстан", "республика"}:
            continue
        seen.add(lk)
        entities.append({"name": name, "type": "other", "wikidata": None, "wiki_url": None})
        if len(entities) >= 12:
            break

    category_auto = (a.get("category") or "").strip().lower()
    if category_auto not in {"news", "investigation"}:
        category_auto = "news"

    importance = 3 if category_auto == "investigation" else 2

    tags_auto = []
    for t in a.get("tags") or []:
        if isinstance(t, str) and t.strip():
            tags_auto.append(t.strip()[:60])
        if len(tags_auto) >= 6:
            break

    return {
        "summary_short": summary_short,
        "summary_tts": summary_tts,
        "key_points": key_points[:5],
        "importance": importance,
        "sentiment": "neutral",
        "entities": entities,
        "region": "",
        "category_auto": category_auto,
        "tags_auto": tags_auto,
    }


def _select_pending(limit: int | None, only_id: str | None, retry_errors: bool) -> list[dict]:
    with db() as conn:
        if only_id:
            rows = conn.execute(
                "SELECT * FROM articles WHERE id = ? OR slug = ? LIMIT 1",
                (only_id, only_id),
            ).fetchall()
        elif retry_errors:
            q = (
                "SELECT a.* FROM articles a "
                "JOIN article_meta m ON a.id = m.article_id "
                "WHERE a.published=1 AND m.error <> '' "
                "ORDER BY a.date_iso DESC"
            )
            if limit:
                q += f" LIMIT {int(limit)}"
            rows = conn.execute(q).fetchall()
        else:
            q = (
                "SELECT a.* FROM articles a "
                "LEFT JOIN article_meta m ON a.id = m.article_id "
                "WHERE a.published=1 AND (m.article_id IS NULL OR m.error <> '') "
                "ORDER BY a.date_iso DESC"
            )
            if limit:
                q += f" LIMIT {int(limit)}"
            rows = conn.execute(q).fetchall()
    return [row_to_article(r) for r in rows]


def _upsert_meta(aid: str, result: dict, model: str, input_chars: int, error: str = "") -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO article_meta
                (article_id, summary_short, summary_tts, key_points, importance,
                 sentiment, entities_json, region, category_auto, tags_auto,
                 model, input_chars, processed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_id) DO UPDATE SET
                summary_short=excluded.summary_short,
                summary_tts=excluded.summary_tts,
                key_points=excluded.key_points,
                importance=excluded.importance,
                sentiment=excluded.sentiment,
                entities_json=excluded.entities_json,
                region=excluded.region,
                category_auto=excluded.category_auto,
                tags_auto=excluded.tags_auto,
                model=excluded.model,
                input_chars=excluded.input_chars,
                processed_at=excluded.processed_at,
                error=excluded.error
            """,
            (
                aid,
                result.get("summary_short", ""),
                result.get("summary_tts", ""),
                json.dumps(result.get("key_points", []), ensure_ascii=False),
                int(result.get("importance") or 0),
                result.get("sentiment", ""),
                json.dumps(result.get("entities", []), ensure_ascii=False),
                result.get("region", ""),
                result.get("category_auto", ""),
                json.dumps(result.get("tags_auto", []), ensure_ascii=False),
                model,
                input_chars,
                datetime.utcnow().isoformat(timespec="seconds"),
                error,
            ),
        )


def run(limit: int | None = None, only_id: str | None = None,
        retry_errors: bool = False, model: str = DEFAULT_MODEL,
        sleep_between: float = 0.3) -> dict:
    ensure_meta_schema()
    articles = _select_pending(limit, only_id, retry_errors)
    total = len(articles)
    print(f"[enrich] to process: {total} (model={model})", flush=True)
    ok = 0
    err = 0
    t0 = time.time()
    for i, a in enumerate(articles, 1):
        text = _build_article_text(a)
        if len(text) < 80:  # too short to enrich
            _upsert_meta(
                a["id"],
                _fallback_result(a),
                model="fallback-local",
                input_chars=len(text),
            )
            ok += 1
            if i % 20 == 0:
                print(f"[enrich] {i}/{total} ok={ok} err={err} ({(time.time()-t0):.1f}s)", flush=True)
            continue
        try:
            raw = _call_model(text, model)
            result = _sanitize_result(raw)
            _upsert_meta(a["id"], result, model=model, input_chars=len(text))
            ok += 1
        except Exception as e:
            primary_msg = f"{type(e).__name__}: {e}"[:320]
            if _should_fallback_from_gemini(model, primary_msg):
                try:
                    print(
                        f"[enrich] RETRY {a['id']}: {model} failed, fallback={FALLBACK_MODEL}",
                        flush=True,
                    )
                    raw = _call_model(text, FALLBACK_MODEL)
                    result = _sanitize_result(raw)
                    _upsert_meta(a["id"], result, model=FALLBACK_MODEL, input_chars=len(text))
                    ok += 1
                    continue
                except Exception as e2:
                    fallback_msg = f"{type(e2).__name__}: {e2}"[:180]
                    msg = (
                        f"primary[{model}]: {primary_msg}; "
                        f"fallback[{FALLBACK_MODEL}]: {fallback_msg}"
                    )[:500]
            else:
                msg = primary_msg
            err += 1
            print(f"[enrich] FAIL {a['id']}: {msg}", flush=True)
            # Persist deterministic fallback so article pages keep key points/entities.
            _upsert_meta(
                a["id"],
                _fallback_result(a),
                model="fallback-local",
                input_chars=len(text),
                error="",
            )
        if i % 10 == 0:
            elapsed = time.time() - t0
            rate = i / max(elapsed, 1e-3)
            eta = (total - i) / max(rate, 1e-3)
            print(f"[enrich] {i}/{total} ok={ok} err={err} rate={rate:.2f}/s eta={eta:.0f}s",
                  flush=True)
        if sleep_between:
            time.sleep(sleep_between)
    print(f"[enrich] DONE ok={ok} err={err} total={total} elapsed={(time.time()-t0):.1f}s",
          flush=True)
    return {"ok": ok, "err": err, "total": total}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="Max articles to process")
    p.add_argument("--only", type=str, default=None, help="Process a single article id/slug")
    p.add_argument("--retry-errors", action="store_true", help="Only re-run rows with error set")
    p.add_argument("--model", type=str, default=DEFAULT_MODEL, help="OpenAI model id")
    p.add_argument("--sleep", type=float, default=0.3, help="Sleep between calls (s)")
    args = p.parse_args()
    run(limit=args.limit, only_id=args.only, retry_errors=args.retry_errors,
        model=args.model, sleep_between=args.sleep)


if __name__ == "__main__":
    main()
