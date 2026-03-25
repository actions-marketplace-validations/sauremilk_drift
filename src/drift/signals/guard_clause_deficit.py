"""Signal 10: Guard Clause Deficit (GCD).

Detects modules where public, non-trivial functions uniformly lack
guard clauses — isinstance checks, assert statements, if-raise/return
patterns that validate inputs early.

This is a proxy for *consistent wrongness* (EPISTEMICS §2): when every
function blindly trusts its inputs, the codebase is structurally
vulnerable to a single incorrect assumption propagating everywhere.
"""

from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath

from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    FunctionInfo,
    ParseResult,
    Severity,
    SignalType,
)
from drift.signals.base import BaseSignal, register_signal


def _is_test_file(file_path: Path) -> bool:
    """Return True if *file_path* looks like a test file (by filename only)."""
    name = file_path.name.lower()
    return name.startswith("test_") or name.endswith("_test.py")


def _has_guard(stmt: ast.stmt, param_names: set[str]) -> bool:
    """Return True if *stmt* is a guard clause referencing a parameter."""
    # isinstance(param, ...)
    if (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Name)
        and stmt.value.func.id == "isinstance"
        and stmt.value.args
        and isinstance(stmt.value.args[0], ast.Name)
    ):
        return stmt.value.args[0].id in param_names
    # assert <param> ...
    if isinstance(stmt, ast.Assert):
        return _references_param(stmt.test, param_names)
    # if <cond>: raise/return (single-branch guard)
    if (
        isinstance(stmt, ast.If)
        and not stmt.orelse
        and any(isinstance(s, ast.Raise | ast.Return) for s in stmt.body)
    ):
        return _references_param(stmt.test, param_names)
    return False


def _references_param(node: ast.expr, param_names: set[str]) -> bool:
    """Return True if the expression references at least one parameter name."""
    return any(
        isinstance(child, ast.Name) and child.id in param_names
        for child in ast.walk(node)
    )


def _function_is_guarded(source: str, func_info: FunctionInfo, param_names: set[str]) -> bool:
    """Parse function body and check first 30% of statements for guards."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True  # benefit of doubt

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = node.body
        if not body:
            return True
        check_count = max(1, len(body) * 30 // 100)
        return any(_has_guard(stmt, param_names) for stmt in body[:check_count])
    return True  # no function found — benefit of doubt


@register_signal
class GuardClauseDeficitSignal(BaseSignal):
    """Detect modules with uniformly unguarded public functions."""

    @property
    def signal_type(self) -> SignalType:
        return SignalType.GUARD_CLAUSE_DEFICIT

    @property
    def name(self) -> str:
        return "Guard Clause Deficit"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        min_public = config.thresholds.gcd_min_public_functions

        # Group qualifying functions by module directory
        module_funcs: dict[str, list[tuple[FunctionInfo, ParseResult]]] = {}

        for pr in parse_results:
            if pr.language != "python":
                continue
            if _is_test_file(pr.file_path):
                continue
            if pr.file_path.name == "__init__.py":
                continue

            for fn in pr.functions:
                if fn.name.startswith("_"):
                    continue
                if len(fn.parameters) < 2:
                    continue
                if fn.complexity < 5:
                    continue

                module_key = PurePosixPath(pr.file_path.parent).as_posix()
                module_funcs.setdefault(module_key, []).append((fn, pr))

        findings: list[Finding] = []

        for module_key, func_list in module_funcs.items():
            if len(func_list) < min_public:
                continue

            guarded = 0
            total_complexity = 0

            for fn, pr in func_list:
                param_names = set(fn.parameters)
                # Read source for the specific function
                source = _read_function_source(pr.file_path, fn, self._repo_path)
                if source is None:
                    guarded += 1  # benefit of doubt
                    continue

                if _function_is_guarded(source, fn, param_names):
                    guarded += 1
                else:
                    total_complexity += fn.complexity

            total = len(func_list)
            guarded_ratio = guarded / total

            if guarded_ratio >= 0.15:
                continue

            unguarded = total - guarded
            mean_complexity = total_complexity / max(1, unguarded)
            score = round(min(1.0, (1.0 - guarded_ratio) * mean_complexity / 20), 3)

            severity = Severity.HIGH if score >= 0.7 else Severity.MEDIUM

            findings.append(
                Finding(
                    signal_type=self.signal_type,
                    severity=severity,
                    score=score,
                    title=f"Guard clause deficit in {module_key}/",
                    description=(
                        f"{unguarded}/{total} public functions lack guard "
                        f"clauses (guarded ratio {guarded_ratio:.1%}, "
                        f"mean unguarded complexity {mean_complexity:.1f})."
                    ),
                    file_path=Path(module_key),
                    fix=(
                        f"Add guard clauses to {unguarded}/{total} unguarded functions in "
                        f"{module_key}/ (mean complexity {mean_complexity:.1f}): "
                        f"isinstance checks, None guards, or assert statements."
                    ),
                    metadata={
                        "total_qualifying": total,
                        "guarded_count": guarded,
                        "guarded_ratio": guarded_ratio,
                        "mean_unguarded_complexity": mean_complexity,
                    },
                )
            )

        return findings


def _read_function_source(
    file_path: Path, fn: FunctionInfo, repo_path: Path | None = None
) -> str | None:
    """Read source lines for a single function."""
    try:
        target = file_path
        if repo_path and not file_path.is_absolute():
            target = repo_path / file_path
        lines = target.read_text(encoding="utf-8").splitlines()
        start = fn.start_line - 1
        end = fn.end_line
        return "\n".join(lines[start:end])
    except (OSError, UnicodeDecodeError, AttributeError):
        return None
