"""Convert Editor.js output -> {sections:[{h,p}]} used by the public site."""
from __future__ import annotations

import html
import re
from typing import Any


def _strip_html(s: str) -> str:
    # Editor.js inline tools produce <b>/<i>/<a>; the public template wraps
    # paragraphs in <p> verbatim, so we keep the HTML for paragraphs but
    # unescape headings to plain text.
    return re.sub(r"<[^>]+>", "", s or "").strip()


def editorjs_to_sections(data: dict[str, Any] | None) -> list[dict]:
    """Return [{h: str, p: str}] pairs: each H2 starts a section; paragraphs collect until next H2.

    Unsectioned paragraphs at the top get an empty h="".
    """
    if not data:
        return []
    blocks = data.get("blocks", []) or []
    sections: list[dict] = []
    current: dict | None = None

    def flush_para(p: str):
        nonlocal current
        if not p:
            return
        if current is None:
            current = {"h": "", "p": p}
            sections.append(current)
        else:
            # append to the last paragraph with a blank line
            current["p"] = (current["p"] + "\n\n" + p).strip() if current["p"] else p

    for b in blocks:
        t = b.get("type")
        d = b.get("data") or {}
        if t == "header":
            text = _strip_html(d.get("text", ""))
            level = d.get("level", 2)
            if level <= 2:
                current = {"h": text, "p": ""}
                sections.append(current)
            else:
                # H3+ inline as bold paragraph
                flush_para(f"<strong>{html.escape(text)}</strong>")
        elif t == "paragraph":
            flush_para((d.get("text") or "").strip())
        elif t == "quote":
            text = (d.get("text") or "").strip()
            caption = (d.get("caption") or "").strip()
            q = f"<blockquote>{text}{f' — <em>{caption}</em>' if caption else ''}</blockquote>"
            flush_para(q)
        elif t == "list":
            style = d.get("style", "unordered")
            tag = "ol" if style == "ordered" else "ul"
            items = "".join(f"<li>{i}</li>" for i in (d.get("items") or []))
            flush_para(f"<{tag}>{items}</{tag}>")
        elif t == "image":
            url = (d.get("file") or {}).get("url") or d.get("url")
            caption = d.get("caption", "")
            if url:
                flush_para(f'<img src="{html.escape(url)}" alt="{html.escape(_strip_html(caption))}"/>')
        elif t == "delimiter":
            flush_para("<hr/>")
        else:
            # unknown block: try .text
            text = d.get("text")
            if text:
                flush_para(text)

    # Drop empty sections
    return [s for s in sections if s["h"] or s["p"]]


def sections_to_editorjs(sections: list[dict]) -> dict:
    """Reverse: load a sections list back into an Editor.js document so that
    opening a legacy article in the editor yields a sensible starting state."""
    blocks = []
    for s in sections or []:
        h = (s.get("h") or "").strip()
        p = (s.get("p") or "").strip()
        if h:
            blocks.append({"type": "header", "data": {"text": h, "level": 2}})
        if p:
            # split double-newlines -> separate paragraphs
            for part in [x.strip() for x in p.split("\n\n") if x.strip()]:
                blocks.append({"type": "paragraph", "data": {"text": part}})
    return {"time": 0, "blocks": blocks, "version": "2.30.0"}
