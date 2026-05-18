from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_shells_expose_header_search_button() -> None:
    shells = [
        ROOT / "index.html",
        ROOT / "archive.html",
        ROOT / "article.html",
        ROOT / "about.html",
        ROOT / "404.html",
        ROOT / "admin" / "templates" / "article_ssr.html",
    ]

    for path in shells:
        html = path.read_text(encoding="utf-8")
        assert html.count("data-search-open") == 1, path
        assert 'aria-label="Открыть поиск"' in html, path
