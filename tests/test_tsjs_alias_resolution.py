from __future__ import annotations

from pathlib import Path

from drift.analyzers.typescript.alias_resolver import resolve_tsconfig_alias_import
from drift.analyzers.typescript.import_graph import build_relative_import_graph


def test_resolve_tsconfig_alias_import_resolves_two_aliases_and_ignores_unknown() -> None:
    repo_path = Path(__file__).parent / "fixtures" / "tsjs_alias_resolution"
    source_path = Path("src/app.ts")

    resolved_core = resolve_tsconfig_alias_import(repo_path, source_path, "@core/logger")
    resolved_shared = resolve_tsconfig_alias_import(repo_path, source_path, "@shared/config")
    unresolved = resolve_tsconfig_alias_import(repo_path, source_path, "@unknown/missing")

    assert resolved_core == Path("src/core/logger.ts")
    assert resolved_shared == Path("src/shared/config.ts")
    assert unresolved is None


def test_build_relative_import_graph_resolves_alias_imports() -> None:
    repo_path = Path(__file__).parent / "fixtures" / "tsjs_alias_resolution"

    graph = build_relative_import_graph(repo_path)

    assert graph["src/app.ts"] == {
        "src/core/logger.ts",
        "src/shared/config.ts",
    }


def test_resolve_tsconfig_alias_import_resolves_recursive_extends_chain() -> None:
    repo_path = Path(__file__).parent / "fixtures" / "tsjs_alias_resolution_extends"
    source_path = Path("src/app.ts")

    resolved_leaf = resolve_tsconfig_alias_import(repo_path, source_path, "@leaf/feature")
    resolved_mid = resolve_tsconfig_alias_import(repo_path, source_path, "@mid/util")
    resolved_base = resolve_tsconfig_alias_import(repo_path, source_path, "@base/logger")
    resolved_override = resolve_tsconfig_alias_import(repo_path, source_path, "@shared/config")

    assert resolved_leaf == Path("src/leaf/feature.ts")
    assert resolved_mid == Path("src/mid/util.ts")
    assert resolved_base == Path("src/base/logger.ts")
    assert resolved_override == Path("src/override/config.ts")
