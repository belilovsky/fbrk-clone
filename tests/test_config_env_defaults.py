from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "admin"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))


def load_config_module():
    script = ADMIN_ROOT / "app" / "config.py"
    spec = importlib.util.spec_from_file_location("app_config_for_test", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_env_defaults_populates_missing_settings_from_file(tmp_path: Path, monkeypatch) -> None:
    config = load_config_module()
    env_file = tmp_path / "fbrk-admin.env"
    env_file.write_text(
        'FBRK_PUBLIC_ROOT="/srv/fbrk-site"\n'
        'FBRK_DATA_JS="/srv/fbrk-site/js/data.js"\n'
        "FBRK_API_KEY=test-from-file\n",
        encoding="utf-8",
    )

    for name in ("FBRK_PUBLIC_ROOT", "FBRK_DATA_JS", "FBRK_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    config._load_env_defaults((env_file,))
    settings = config.Settings()

    assert settings.public_root == "/srv/fbrk-site"
    assert settings.data_js_path == "/srv/fbrk-site/js/data.js"
    assert settings.api_key == "test-from-file"


def test_load_env_defaults_does_not_override_explicit_environment(tmp_path: Path, monkeypatch) -> None:
    config = load_config_module()
    env_file = tmp_path / "fbrk-admin.env"
    env_file.write_text(
        "export FBRK_DATA_JS=/srv/fbrk-site/js/data.js\n"
        "FBRK_PUBLIC_ROOT=/srv/fbrk-site\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("FBRK_DATA_JS", "/already-set/data.js")
    monkeypatch.setenv("FBRK_PUBLIC_ROOT", "/already-set/public")

    config._load_env_defaults((env_file,))
    settings = config.Settings()

    assert settings.data_js_path == "/already-set/data.js"
    assert settings.public_root == "/already-set/public"


def test_clean_env_value_strips_matching_quotes() -> None:
    config = load_config_module()

    assert config._clean_env_value('"quoted"') == "quoted"
    assert config._clean_env_value("'quoted'") == "quoted"
    assert config._clean_env_value("plain") == "plain"
