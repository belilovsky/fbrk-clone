import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC_SHELLS = [
    ROOT / "404.html",
    ROOT / "about.html",
    ROOT / "archive.html",
    ROOT / "article.html",
    ROOT / "contacts.html",
    ROOT / "editorial-policy.html",
    ROOT / "index.html",
    ROOT / "privacy.html",
    ROOT / "search.html",
    ROOT / "sitemap.html",
]
PUBLIC_SHELLS = STATIC_SHELLS + [ROOT / "admin" / "templates" / "article_ssr.html"]


def extract_block(html: str, block_name: str, path: Path) -> str:
    match = re.search(rf'[ \t]*<{block_name} class="site-{block_name}"[\s\S]*?</{block_name}>', html)
    assert match, path
    return match.group(0)


def test_public_shells_expose_header_search_button() -> None:
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert html.count("data-search-open") == 1, path
        assert 'aria-label="Открыть поиск"' in html, path


def test_public_shells_define_early_theme_init() -> None:
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert "localStorage.getItem('theme')" in html or 'localStorage.getItem("theme")' in html, path
        assert "document.documentElement.dataset.theme" in html, path


def test_static_pages_share_canonical_shell_markup() -> None:
    canonical = (ROOT / "index.html").read_text(encoding="utf-8")
    canonical_header = extract_block(canonical, "header", ROOT / "index.html")
    canonical_footer = extract_block(canonical, "footer", ROOT / "index.html")

    for path in STATIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert extract_block(html, "header", path) == canonical_header, path
        assert extract_block(html, "footer", path) == canonical_footer, path


def test_public_shells_expose_visible_avds_version() -> None:
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert 'class="site-footer__version">AV DS 3.7.1</span>' in html, path
        assert "<!-- AV DS" not in html, path


def test_public_shells_link_editorial_policy() -> None:
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert '<a href="/editorial-policy.html">Редакционная политика</a>' in html, path


def test_public_asset_versions_are_busted_consistently() -> None:
    versions: set[str] = set()
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        versions.update(re.findall(r"\?v=(\d+)", html))

    assert versions
    assert all(len(version) == 14 for version in versions)
    assert "3" not in versions


def test_frontend_css_keeps_article_spacing_readable() -> None:
    css = (ROOT / "css" / "style.css").read_text(encoding="utf-8")

    assert not re.search(r"letter-spacing:\s*-", css)
    assert re.search(r"\.ad-block:empty\s*\{\s*display:\s*none;", css)
    assert re.search(r"\.site-header__nav\s*\{[\s\S]*min-height:\s*100dvh;", css)


def test_ssr_article_keeps_summary_and_share_below_body() -> None:
    html = (ROOT / "admin" / "templates" / "article_ssr.html").read_text(encoding="utf-8")

    body_idx = html.index('class="article__body"')
    tldr_idx = html.index('class="article__tldr"')
    mentions_idx = html.index('class="entity-chips"')
    share_idx = html.index('class="article__share"')

    assert body_idx < tldr_idx < mentions_idx < share_idx


def test_public_shell_sync_script_has_no_drift() -> None:
    subprocess.run(
        ["python3", "admin/scripts/sync_public_shell.py", "--check"],
        cwd=ROOT,
        check=True,
    )
