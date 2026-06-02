from __future__ import annotations

from pathlib import Path


def test_new_fbrk_public_host_blocks_admin_and_api() -> None:
    conf = Path("admin/deploy/nginx-new-fbrk.conf").read_text(encoding="utf-8")

    assert "location = /admin { return 404; }" in conf
    assert "location ^~ /admin/ { return 404; }" in conf
    assert "location = /api { return 404; }" in conf
    assert "location ^~ /api/ { return 404; }" in conf


def test_new_fbrk_public_host_keeps_public_dynamic_routes() -> None:
    conf = Path("admin/deploy/nginx-new-fbrk.conf").read_text(encoding="utf-8")

    assert "location ^~ /a/" in conf
    assert "location = /sitemap.xml" in conf
    assert "location = /robots.txt" in conf
    assert "location = /feed.xml" in conf
    assert 'Cache-Control "no-cache, no-store, must-revalidate"' in conf
