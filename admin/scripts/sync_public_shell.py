#!/usr/bin/env python3
"""Keep public static header/footer markup in sync with index.html."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SHELL = ROOT / "index.html"
STATIC_SHELL_FILES = (
    "404.html",
    "about.html",
    "archive.html",
    "article.html",
    "contacts.html",
    "editorial-policy.html",
    "privacy.html",
    "regions.html",
    "resonance.html",
    "search.html",
    "series.html",
    "sitemap.html",
    "topics.html",
)

BLOCK_PATTERNS = {
    "header": re.compile(r"(?P<block>[ \t]*<header class=\"site-header\"[\s\S]*?</header>)"),
    "footer": re.compile(r"(?P<block>[ \t]*<footer class=\"site-footer\"[\s\S]*?</footer>)"),
}


def extract_block(html: str, block_name: str, source: Path) -> str:
    match = BLOCK_PATTERNS[block_name].search(html)
    if not match:
        raise ValueError(f"{source}: missing site {block_name}")
    return match.group("block")


def replace_block(html: str, block_name: str, replacement: str, source: Path) -> str:
    pattern = BLOCK_PATTERNS[block_name]
    if not pattern.search(html):
        raise ValueError(f"{source}: missing site {block_name}")
    return pattern.sub(replacement, html, count=1)


def sync_file(path: Path, canonical_header: str, canonical_footer: str) -> bool:
    html = path.read_text(encoding="utf-8")
    updated = replace_block(html, "header", canonical_header, path)
    updated = replace_block(updated, "footer", canonical_footer, path)
    if updated == html:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def check_file(path: Path, canonical_header: str, canonical_footer: str) -> list[str]:
    html = path.read_text(encoding="utf-8")
    problems: list[str] = []
    if extract_block(html, "header", path) != canonical_header:
        problems.append("header")
    if extract_block(html, "footer", path) != canonical_footer:
        problems.append("footer")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify files without rewriting them")
    args = parser.parse_args()

    canonical_html = CANONICAL_SHELL.read_text(encoding="utf-8")
    canonical_header = extract_block(canonical_html, "header", CANONICAL_SHELL)
    canonical_footer = extract_block(canonical_html, "footer", CANONICAL_SHELL)

    changed: list[Path] = []
    drift: list[str] = []
    for name in STATIC_SHELL_FILES:
        path = ROOT / name
        try:
            if args.check:
                problems = check_file(path, canonical_header, canonical_footer)
                if problems:
                    drift.append(f"{path.relative_to(ROOT)}: {', '.join(problems)}")
            elif sync_file(path, canonical_header, canonical_footer):
                changed.append(path)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.check and drift:
        print("Public shell drift detected:", file=sys.stderr)
        for item in drift:
            print(f"  {item}", file=sys.stderr)
        return 1

    if changed:
        for path in changed:
            print(f"synced {path.relative_to(ROOT)}")
    else:
        print("public shell ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
