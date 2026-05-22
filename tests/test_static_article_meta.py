import importlib.util
import json
from pathlib import Path


def load_sync_module():
    script = Path(__file__).resolve().parents[1] / "admin" / "scripts" / "sync_new_frontend_to_plesk.py"
    spec = importlib.util.spec_from_file_location("sync_new_frontend_to_plesk", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_static_article_shell_gets_specific_metadata(tmp_path):
    sync = load_sync_module()
    (tmp_path / "js").mkdir()
    (tmp_path / "article.html").write_text(
        """
        <html><head>
          <title data-article-title>Материал — ФБРК</title>
          <meta name="description" content="generic" data-article-desc />
          <link rel="canonical" href="https://fbrk.qdev.run/article.html" data-article-canonical />
          <link rel="alternate" hreflang="ru" href="https://fbrk.qdev.run/" data-article-hreflang />
          <meta property="og:title" content="generic" data-article-og-title />
          <meta property="og:description" content="generic" data-article-og-desc />
          <meta property="og:image" content="generic" data-article-og-image />
          <meta property="og:url" content="generic" data-article-og-url />
          <meta name="twitter:title" content="generic" data-article-tw-title />
          <meta name="twitter:description" content="generic" data-article-tw-desc />
          <meta name="twitter:image" content="generic" data-article-tw-image />
        </head><body><main id="main" data-article></main></body></html>
        """,
        encoding="utf-8",
    )
    payload = {
        "articles": [
            {
                "slug": "test-slug",
                "title": "Тест <заголовок>",
                "dek": "Описание & лид",
                "dateIso": "2026-05-18",
                "categoryLabel": "Новости",
                "image": "/img/test.png",
            }
        ]
    }
    (tmp_path / "js" / "article-full.js").write_text(
        f"window.ARTICLE_FULL = {json.dumps(payload, ensure_ascii=False)};",
        encoding="utf-8",
    )

    generated = sync.generate_static_article_shells(tmp_path, "https://new.fbrk.kz")

    assert [path.relative_to(tmp_path).as_posix() for path in generated] == ["a/test-slug/index.html"]
    html = generated[0].read_text(encoding="utf-8")
    assert "<title data-article-title>Тест &lt;заголовок&gt; — ФБРК</title>" in html
    assert '<link rel="canonical" href="https://new.fbrk.kz/a/test-slug" data-article-canonical />' in html
    assert '<meta property="og:url" content="https://new.fbrk.kz/a/test-slug" data-article-og-url />' in html
    assert "Описание &amp; лид" in html
    assert "data-static-article-jsonld" in html


def test_split_frontend_package_includes_video_data(tmp_path, monkeypatch):
    sync = load_sync_module()
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "data").mkdir()
    (web_root / "data" / "videos.json").write_text('[{"id":"demo"}]', encoding="utf-8")
    for name in sync.ROOT_FILES:
        (web_root / name).write_text("<html><head></head><body></body></html>", encoding="utf-8")

    def fake_fetch_bytes(url, *, timeout=45, cache_bust=False):
        if url.endswith("/js/article-full.js"):
            return b'window.ARTICLE_FULL = {"articles":[]};'
        if url.endswith("/js/data.js"):
            return b"const FBRK_DATA = {\"articles\":[]};"
        if url.endswith("/js/data-archive.js"):
            return b"const FBRK_ARCHIVE = {\"articles\":[]};"
        if url.endswith("/js/search-index.js"):
            return b"const FBRK_SEARCH_INDEX = {\"items\":[]};"
        if url.endswith("/robots.txt"):
            return b"User-agent: *\nAllow: /\n"
        if url.endswith("/sitemap.xml"):
            return b"<?xml version=\"1.0\"?><urlset></urlset>"
        if url.endswith("/feed.xml"):
            return b"<?xml version=\"1.0\"?><rss></rss>"
        raise AssertionError(url)

    monkeypatch.setattr(sync, "fetch_bytes", fake_fetch_bytes)

    out_dir = tmp_path / "package"
    uploaded = sync.build_package(
        out_dir,
        public_origin="https://new.fbrk.kz",
        backend_origin="https://fbrk.qdev.run",
        web_root=web_root,
        asset_version="20260518180000",
        include_static=False,
        generate_article_pages=False,
    )

    rel_paths = {path.relative_to(out_dir).as_posix() for path in uploaded}
    assert "data/videos.json" in rel_paths
    assert "js/search-index.js" in rel_paths
    assert (out_dir / "data" / "videos.json").read_text(encoding="utf-8") == '[{"id":"demo"}]'
