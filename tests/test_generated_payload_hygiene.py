from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_generated_payload_hygiene.py"


def write_payload(path: Path, prefix: str, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{prefix} {json.dumps(payload, ensure_ascii=False)};\n", encoding="utf-8")


def run_check(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--skip-origin-check"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_generated_payload_hygiene_passes_without_optional_caches(tmp_path: Path) -> None:
    write_payload(
        tmp_path / "js" / "data.js",
        "const FBRK_DATA =",
        {
            "totalCount": 125,
            "articles": [{"id": "a1"}, {"id": "a2"}],
        },
    )

    result = run_check(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "OK data.js recent=2 total=125" in result.stdout
    assert "SKIP data-archive.js missing" in result.stdout
    assert "SKIP article-full.js missing" in result.stdout
    assert "STATUS=ok" in result.stdout


def test_generated_payload_hygiene_rejects_truncated_optional_cache(tmp_path: Path) -> None:
    write_payload(
        tmp_path / "js" / "data.js",
        "const FBRK_DATA =",
        {
            "totalCount": 125,
            "articles": [{"id": "a1"}, {"id": "a2"}],
        },
    )
    (tmp_path / "js" / "article-full.js").write_text("window.ARTICLE_FULL = {};\n", encoding="utf-8")

    result = run_check(tmp_path)

    assert result.returncode != 0
    assert "FAIL article-full.js is suspiciously small" in result.stderr
