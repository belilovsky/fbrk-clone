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
