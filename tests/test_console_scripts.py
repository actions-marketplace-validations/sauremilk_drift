from __future__ import annotations

import tomllib
from pathlib import Path


def test_console_scripts_include_package_and_short_alias() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    scripts = data["project"]["scripts"]
    assert scripts["drift"] == "drift.cli:safe_main"
    assert scripts["drift-analyzer"] == "drift.cli:safe_main"