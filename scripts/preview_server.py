#!/usr/bin/env python3
"""Local preview server with FBRK article-route fallback.

Serves the static repo root and rewrites pretty article URLs used in production:
    /a/<slug> -> /article.html?id=<slug>&spa=1
"""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class PreviewHandler(SimpleHTTPRequestHandler):
    def _article_redirect(self) -> str | None:
        parts = urlsplit(self.path)
        clean_path = parts.path
        if not clean_path.startswith("/a/"):
            return None
        slug = clean_path[len("/a/") :].strip("/")
        if not slug:
            return None
        return f"/article.html?id={quote(slug)}&spa=1"

    def do_GET(self) -> None:  # noqa: N802
        redirect = self._article_redirect()
        if redirect is not None:
            self.send_response(302)
            self.send_header("Location", redirect)
            self.end_headers()
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        redirect = self._article_redirect()
        if redirect is not None:
            self.send_response(302)
            self.send_header("Location", redirect)
            self.end_headers()
            return
        super().do_HEAD()

    def translate_path(self, path: str) -> str:
        parts = urlsplit(path)
        return super().translate_path(parts.path)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        # Keep the preview server output compact during local smoke runs.
        print(f"[preview] {self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve local FBRK preview with article route fallback")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4175)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), lambda *a, **kw: PreviewHandler(*a, directory=str(ROOT), **kw))
    print(f"Serving FBRK preview on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping FBRK preview server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
