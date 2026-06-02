from __future__ import annotations

import html
import re


_INLINE_ATTR_RE = re.compile(
    r"(<(?P<tag>img|a)\b[^>]*\b(?P<attr>src|href)\s*=\s*)(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE,
)


def _abs_site_url(value: str, site_url: str) -> str:
    raw = html.unescape(str(value or "").strip())
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.startswith(("http://", "https://", "data:", "mailto:", "tel:", "#")):
        return raw
    if raw.startswith("/"):
        return f"{site_url}{raw}"
    return f"{site_url}/{raw}"


def normalize_inline_asset_url(value: str, site_url: str, *, attr: str) -> str:
    raw = html.unescape(str(value or "").strip())
    if not raw:
        return ""
    if attr == "href" and raw.lower().startswith("javascript:"):
        return ""
    return _abs_site_url(raw, site_url)


def normalize_inline_html_assets(raw: str, site_url: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        quote = match.group("quote")
        attr = match.group("attr").lower()
        normalized = normalize_inline_asset_url(match.group("value"), site_url, attr=attr)
        if not normalized:
            return prefix
        return f"{prefix}{quote}{html.escape(normalized, quote=True)}{quote}"

    return _INLINE_ATTR_RE.sub(_replace, str(raw or ""))
