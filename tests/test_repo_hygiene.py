from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_repo_hygiene.py"


def load_repo_hygiene_module():
    spec = importlib.util.spec_from_file_location("check_repo_hygiene", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tracked_root_entries_extracts_unique_top_level_names():
    module = load_repo_hygiene_module()

    files = [
        "README.md",
        "docs/STUDY.md",
        "src/drift/analyzer.py",
        "src/drift/config.py",
        "docs-site/index.md",
    ]

    assert module.tracked_root_entries(files) == ["README.md", "docs", "docs-site", "src"]


def test_find_root_violations_flags_unexpected_root_entries():
    module = load_repo_hygiene_module()

    violations = module.find_root_violations(
        ["README.md", "docs", "scratch.txt", "src"],
        ["README.md", "docs", "src"],
    )

    assert violations == [("scratch.txt", "<no allowlist match>")]


def test_find_root_violations_supports_glob_patterns():
    module = load_repo_hygiene_module()

    violations = module.find_root_violations(
        ["README.md", "docs", "notes.md"],
        ["README.md", "docs", "*.md"],
    )

    assert violations == []
