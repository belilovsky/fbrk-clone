import re
import subprocess
from pathlib import Path

from admin.app.seo import _hero_dek, _sections_to_html


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
    ROOT / "regions.html",
    ROOT / "resonance.html",
    ROOT / "search.html",
    ROOT / "series.html",
    ROOT / "sitemap.html",
    ROOT / "topics.html",
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


def test_home_shell_uses_absolute_asset_paths() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'href="/css/style.css?v=' in html
    assert 'src="/js/runtime-config.js?v=' in html
    assert 'src="/js/data.js?v=' in html
    assert 'src="/js/app.js?v=' in html


def test_public_shells_do_not_use_relative_core_asset_paths() -> None:
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert 'href="css/style.css' not in html, path
        assert 'src="js/' not in html, path


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
        assert 'class="site-footer__version">AV DS 4</span>' in html, path
        assert "<!-- AV DS" not in html, path


def test_public_shells_link_editorial_policy() -> None:
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert '<a href="/editorial-policy.html">Редакционная политика</a>' in html, path


def test_public_shells_do_not_use_inline_style_attributes() -> None:
    for path in STATIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        assert 'style="' not in html, path


def test_public_script_references_are_available_or_generated() -> None:
    generated = {"data.js", "data-archive.js", "article-full.js", "search-index.js"}
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        for raw_src in re.findall(r'<script src="([^"]+)"', html):
            src = raw_src.split("?", 1)[0].lstrip("/")
            if not src.startswith("js/"):
                continue
            script_name = Path(src).name
            assert script_name in generated or (ROOT / src).exists(), (path, raw_src)


def test_public_font_stylesheet_exists_for_local_preview() -> None:
    css = ROOT / "fonts" / "avds" / "avds-fonts.css"
    assert css.exists()
    assert "https://fbrk.qdev.run/fonts/avds/" in css.read_text(encoding="utf-8")


def test_public_asset_versions_are_busted_consistently() -> None:
    versions: set[str] = set()
    for path in PUBLIC_SHELLS:
        html = path.read_text(encoding="utf-8")
        versions.update(re.findall(r"\?v=(\d+)", html))

    assert versions
    assert len(versions) == 1
    assert all(len(version) == 14 for version in versions)
    assert "3" not in versions


def test_frontend_css_keeps_article_spacing_readable() -> None:
    css = (ROOT / "css" / "style.css").read_text(encoding="utf-8")
    js = (ROOT / "js" / "app.js").read_text(encoding="utf-8")

    assert not re.search(r"letter-spacing:\s*-", css)
    assert "console.log" not in js
    assert re.search(r"\.ad-block:empty\s*\{\s*display:\s*none;", css)
    assert re.search(r"\.site-header__nav\s*\{[\s\S]*max-height:\s*calc\(100dvh - 84px\);", css)
    assert re.search(r"\.site-header__nav\s*\{[\s\S]*border-radius:\s*20px;", css)
    assert ".article__cover.image-kind-ai::after" in css
    assert ".lead__media.image-kind-ai::after" not in css
    assert ".card__media.image-kind-ai::after" not in css
    assert "ИЛЛЮСТРАЦИЯ ФБРК · ИИ" not in css
    assert "ИИ-изображение. Не является фотоматериалом" in js
    assert re.search(r"\.article__body\s*\{[\s\S]*margin-top:\s*var\(--space-8\);", css)
    assert ".article__body figure {" in css


def test_ssr_article_wraps_plain_section_text_into_paragraphs() -> None:
    html = _sections_to_html(
        [{"h": "Что произошло", "p": "Первый абзац.\n\nВторой абзац с <b>выделением</b>."}],
        "https://fbrk.qdev.run",
    )

    assert "<h2>Что произошло</h2>" in html
    assert "<p>Первый абзац.</p>" in html
    assert "<p>Второй абзац с <b>выделением</b>.</p>" in html


def test_ssr_article_hides_summary_when_it_repeats_first_section() -> None:
    assert _hero_dek(
        "",
        "В апреле этого года СМИ активно писали о разрушении канала К-30 в Жетысайском районе Туркестанской области.",
        [
            {
                "h": "",
                "p": "В апреле этого года СМИ активно писали о разрушении <b>канала К-30</b> в Жетысайском районе Туркестанской области. Далее идёт основной текст.",
            }
        ],
    ) == ""


def test_ssr_article_hides_near_duplicate_editorial_lead_with_punctuation_drift() -> None:
    assert _hero_dek(
        "В апреле этого года СМИ активно писали о разрушении канала К-30 в Жетысайском районе Туркестанской области, от которого зависит орошение 1700 га сельхозугодий. Берега сооружения обваливались, пропускная способность падала.",
        "",
        [
            {
                "h": "",
                "p": "В апреле этого года СМИ активно писали о разрушении <b>канала К-30</b> в Жетысайском районе Туркестанской области, от которого зависит орошение 1700 га сельхозугодий. Берега сооружения обваливались, пропускная способность падала, а аграрии сёл рисковали остаться без воды.",
            }
        ],
    ) == ""


def test_home_shell_exposes_editorial_homepage_sections() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'data-home-resonance-section' in html
    assert 'data-home-regions-section' in html
    assert 'data-home-block-title="resonance"' in html
    assert 'data-home-block-title="regions"' in html


def test_archive_and_search_shells_expose_polish_hooks() -> None:
    archive_html = (ROOT / "archive.html").read_text(encoding="utf-8")
    search_html = (ROOT / "search.html").read_text(encoding="utf-8")

    assert 'data-archive-active' in archive_html
    assert 'data-archive-active-list' in archive_html
    assert 'data-archive-empty-message' in archive_html
    assert 'data-search-empty-message' in search_html


def test_trust_pages_use_editorial_copy_and_consistent_contact_labels() -> None:
    about_html = (ROOT / "about.html").read_text(encoding="utf-8")
    contacts_html = (ROOT / "contacts.html").read_text(encoding="utf-8")
    privacy_html = (ROOT / "privacy.html").read_text(encoding="utf-8")
    policy_html = (ROOT / "editorial-policy.html").read_text(encoding="utf-8")

    assert "<h2>Что такое ФБРК</h2>" in about_html
    assert "<h2>Как передать информацию</h2>" in about_html
    assert "Главный редактор:" not in contacts_html
    assert "Для читателей и информаторов" in contacts_html
    assert "Для комментариев, интервью, перепечаток и партнёрских запросов." in contacts_html
    assert "не использует их для рекламного профилирования" in privacy_html
    assert "краткая публичная версия этого стандарта" in policy_html
    assert "Если вопрос касается конкретной публикации" in policy_html


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
