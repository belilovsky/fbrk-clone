#!/usr/bin/env python3
"""Guard against stale local generated payload caches before deploy work."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path


DEFAULT_BACKEND_ORIGIN = "https://fbrk.qdev.run"
MIN_OPTIONAL_BYTES = 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument(
        "--backend-origin",
        default=os.environ.get("BACKEND_ORIGIN", DEFAULT_BACKEND_ORIGIN),
        help="Origin used to compare optional local caches against live backend payloads.",
    )
    parser.add_argument(
        "--skip-origin-check",
        action="store_true",
        help="Skip backend hash comparison for optional local caches.",
    )
    return parser.parse_args()


def load_js_object(path: Path, marker: str) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    idx = raw.find(marker)
    if idx < 0:
        raise ValueError(f"marker missing: {marker}")
    payload = raw[idx + len(marker):].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    js_root = root / "js"

    data_path = js_root / "data.js"
    if not data_path.exists():
        return fail(f"missing required payload: {data_path}")

    try:
        data_payload = load_js_object(data_path, "const FBRK_DATA =")
    except Exception as exc:  # pragma: no cover - surfaced in tests via stderr
        return fail(f"{data_path.name} is not parseable: {exc}")

    recent_articles = data_payload.get("articles") or []
    recent_count = len(recent_articles)
    total_count = int(data_payload.get("totalCount") or recent_count)
    if recent_count <= 0:
        return fail("data.js has no recent articles")
    if total_count < recent_count:
        return fail(f"data.js totalCount={total_count} is smaller than recent_count={recent_count}")

    print(f"OK data.js recent={recent_count} total={total_count}")

    optional_specs = [
        ("data-archive.js", "window.ARTICLES_ARCHIVE ="),
        ("article-full.js", "window.ARTICLE_FULL ="),
    ]
    backend_origin = str(args.backend_origin or "").rstrip("/")

    for filename, marker in optional_specs:
        path = js_root / filename
        if not path.exists():
            print(f"SKIP {filename} missing (optional backend-owned cache)")
            continue
        size = path.stat().st_size
        if size < MIN_OPTIONAL_BYTES:
            return fail(
                f"{filename} is suspiciously small ({size} bytes); remove or refresh the local cache"
            )
        try:
            payload = load_js_object(path, marker)
        except Exception as exc:  # pragma: no cover - surfaced in tests via stderr
            return fail(f"{filename} is not parseable: {exc}")
        article_count = len(payload.get("articles") or [])
        if article_count < recent_count:
            return fail(
                f"{filename} contains only {article_count} articles, smaller than data.js recent_count={recent_count}"
            )
        print(f"OK {filename} articles={article_count}")

        if args.skip_origin_check or not backend_origin:
            continue

        local_sha = sha256_bytes(path.read_bytes())
        remote_url = f"{backend_origin}/js/{filename}"
        try:
            remote_sha = sha256_bytes(fetch_bytes(remote_url))
        except Exception as exc:  # pragma: no cover - network dependent
            return fail(f"{filename} backend fetch failed from {remote_url}: {exc}")
        if local_sha != remote_sha:
            return fail(
                f"{filename} local sha differs from backend copy; delete or refresh the local cache before any manual sync"
            )
        print(f"OK {filename} sha={local_sha}")

    print("STATUS=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
