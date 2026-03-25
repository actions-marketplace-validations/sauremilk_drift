"""Signal 9: Test Polarity Deficit (TPD).

Detects test suites that contain only positive / happy-path assertions
and lack negative tests (``pytest.raises``, ``assertRaises``, ``assertFalse``,
boundary/edge-case function names).

This is a proxy for *consistent wrongness* (EPISTEMICS §2): when every
test confirms "works as expected" but none checks "fails as expected",
the test suite provides a false sense of correctness.
"""

from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath

from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    ParseResult,
    Severity,
    SignalType,
)
from drift.signals.base import BaseSignal, register_signal

_NEGATIVE_METHODS: frozenset[str] = frozenset({
    "assertRaises",
    "assertFalse",
    "assertNotIn",
    "assertIsNone",
    "assertNotEqual",
    "assertNotIsInstance",
    "assertRaisesRegex",
    "assertWarns",
    "assertWarnsRegex",
    "assertLogs",
})

_POSITIVE_METHODS: frozenset[str] = frozenset({
    "assertTrue",
    "assertEqual",
    "assertIn",
    "assertIs",
    "assertIsNotNone",
    "assertIsInstance",
    "assertGreater",
    "assertGreaterEqual",
    "assertLess",
    "assertLessEqual",
    "assertAlmostEqual",
    "assertCountEqual",
    "assertSequenceEqual",
    "assertListEqual",
    "assertDictEqual",
    "assertSetEqual",
    "assertTupleEqual",
    "assertRegex",
    "assertMultiLineEqual",
})

_BOUNDARY_KEYWORDS: frozenset[str] = frozenset({
    "boundary", "edge", "limit", "zero", "empty",
    "null", "none", "negative", "invalid", "error",
    "fail", "overflow", "underflow", "corrupt",
})


def _is_test_file(file_path: Path) -> bool:
    """Return True if *file_path* looks like a test file (by filename only)."""
    name = file_path.name.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.tsx")
    )


class _AssertionCounter(ast.NodeVisitor):
    """Walk a test-file AST and count positive vs negative assertions."""

    def __init__(self) -> None:
        self.positive = 0
        self.negative = 0
        self.test_functions = 0
        self.boundary_functions = 0

    # --- function-level ---------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        if node.name.startswith("test_") or node.name.startswith("test"):
            self.test_functions += 1
            lower = node.name.lower()
            if any(kw in lower for kw in _BOUNDARY_KEYWORDS):
                self.boundary_functions += 1
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]  # noqa: N815

    # --- assertion counting -----------------------------------------------

    def visit_Assert(self, node: ast.Assert) -> None:  # noqa: N802
        self.positive += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:  # noqa: N802
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                call = item.context_expr
                func_name = _call_name(call)
                if func_name in ("pytest.raises", "raises", "assertRaises"):
                    self.negative += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = _call_name(node)
        if name in _NEGATIVE_METHODS or name.split(".")[-1] in _NEGATIVE_METHODS:
            self.negative += 1
        elif name in _POSITIVE_METHODS or name.split(".")[-1] in _POSITIVE_METHODS:
            self.positive += 1
        self.generic_visit(node)


def _call_name(node: ast.Call) -> str:
    """Extract a dotted name from an ast.Call node."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return func.attr
    return ""


@register_signal
class TestPolarityDeficitSignal(BaseSignal):
    """Detect test suites dominated by positive / happy-path assertions."""

    __test__ = False  # prevent pytest collection

    @property
    def signal_type(self) -> SignalType:
        return SignalType.TEST_POLARITY_DEFICIT

    @property
    def name(self) -> str:
        return "Test Polarity Deficit"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        min_test_functions = config.thresholds.tpd_min_test_functions

        # Group test files by module directory
        module_counters: dict[str, _AssertionCounter] = {}

        for pr in parse_results:
            if pr.language != "python" and pr.language not in (
                "typescript", "tsx", "javascript", "jsx",
            ):
                continue
            if not _is_test_file(pr.file_path):
                continue
            # Only Python files can be AST-parsed here
            if pr.language != "python":
                continue

            source = _read_source(pr.file_path, self._repo_path)
            if source is None:
                continue

            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            module_key = PurePosixPath(pr.file_path.parent).as_posix()
            counter = module_counters.setdefault(module_key, _AssertionCounter())
            counter.visit(tree)

        findings: list[Finding] = []

        for module_key, c in module_counters.items():
            if c.test_functions < min_test_functions:
                continue
            total_assertions = c.positive + c.negative
            if total_assertions < 10:
                continue

            negative_ratio = c.negative / max(1, total_assertions)

            if negative_ratio >= 0.10:
                continue

            score = round(
                min(1.0, (1.0 - negative_ratio) * min(1.0, c.test_functions / 10)),
                3,
            )

            severity = Severity.HIGH if score >= 0.7 else Severity.MEDIUM

            findings.append(
                Finding(
                    signal_type=self.signal_type,
                    severity=severity,
                    score=score,
                    title=f"Happy-path-only test suite in {module_key}/",
                    description=(
                        f"{c.test_functions} test functions with "
                        f"{c.positive} positive / {c.negative} negative assertions "
                        f"(negative ratio {negative_ratio:.1%}). "
                        f"{c.boundary_functions} boundary-named tests."
                    ),
                    file_path=Path(module_key),
                    fix=(
                        f"Add negative tests to {module_key}/ "
                        f"({c.test_functions} test functions, only "
                        f"{c.negative} negative assertions): "
                        f"use pytest.raises for expected exceptions, "
                        f"test edge cases (empty, None, invalid input)."
                    ),
                    metadata={
                        "test_functions": c.test_functions,
                        "positive_assertions": c.positive,
                        "negative_assertions": c.negative,
                        "negative_ratio": negative_ratio,
                        "boundary_functions": c.boundary_functions,
                    },
                )
            )

        return findings


def _read_source(file_path: Path, repo_path: Path | None = None) -> str | None:
    """Read source code, returning None on failure."""
    try:
        target = file_path
        if repo_path and not file_path.is_absolute():
            target = repo_path / file_path
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
