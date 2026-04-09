"""Signal: Phantom Reference (PHR).

Detects function calls, attribute accesses, and decorator references that
cannot be resolved against the local file scope or the project-wide symbol
table.  These "phantom references" typically arise when AI code generators
hallucinate helper functions (e.g. ``sanitize_input``, ``validate_token``)
that exist in training data but not in the current project.

Cross-file aware: PHR builds a project-wide export table so it can verify
that imported modules actually expose the names used in calling code.

Deterministic, AST-only, LLM-free.

Decision: ADR-033
"""

from __future__ import annotations

import ast
import builtins
import logging
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import ClassVar, Literal

from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    ParseResult,
    Severity,
    SignalType,
)
from drift.signals._utils import is_test_file
from drift.signals.base import BaseSignal, register_signal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in names that are always available without import
# ---------------------------------------------------------------------------

_BUILTINS: frozenset[str] = frozenset(dir(builtins))

# Common framework globals injected at runtime (not importable from stdlib)
_FRAMEWORK_GLOBALS: frozenset[str] = frozenset({
    # pytest
    "fixture", "mark", "param", "raises", "skip", "xfail",
    # typing extras often used unqualified
    "Optional", "Union", "List", "Dict", "Tuple", "Set",
    "Any", "Callable", "Iterator", "Generator", "Sequence",
    "ClassVar", "Final", "Literal", "TypeVar", "Protocol",
    "TypeAlias", "Self", "Never", "TypeGuard", "Annotated",
    # common re-exports
    "dataclass", "field", "dataclasses",
    "Path",
    # dunder names used as identifiers
    "__name__", "__file__", "__doc__", "__all__",
    "__version__", "__package__", "__spec__",
})

# Minimum function count to flag a file (avoids noise on tiny scripts)
_MIN_CALLS_FOR_FINDING = 1


# ---------------------------------------------------------------------------
# AST helpers — collect used names and locally defined names
# ---------------------------------------------------------------------------


class _NameCollector(ast.NodeVisitor):
    """Collect names that are *used* (referenced in Load context) in a module.

    Covers call-targets, bare name references, decorator names, argument
    values, and f-string expressions.  Only the leftmost identifier is
    collected — e.g. ``foo.bar.baz()`` → ``foo``.
    """

    def __init__(self) -> None:
        self.used_names: dict[str, list[int]] = defaultdict(list)  # name → lines
        self._in_type_checking = False
        self._has_star_import = False
        self._has_getattr_module = False
        self._has_exec_eval = False

    def visit_If(self, node: ast.If) -> None:
        """Detect TYPE_CHECKING blocks."""
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            old = self._in_type_checking
            self._in_type_checking = True
            self.generic_visit(node)
            self._in_type_checking = old
            return
        if (
            isinstance(node.test, ast.Attribute)
            and isinstance(node.test.value, ast.Name)
            and node.test.attr == "TYPE_CHECKING"
        ):
            old = self._in_type_checking
            self._in_type_checking = True
            self.generic_visit(node)
            self._in_type_checking = old
            return
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Detect star imports."""
        if node.names and any(alias.name == "*" for alias in node.names):
            self._has_star_import = True
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Detect module-level __getattr__."""
        if node.name == "__getattr__" and self._is_module_level(node):
            self._has_getattr_module = True
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]  # noqa: N815

    def visit_Call(self, node: ast.Call) -> None:
        """Collect call-target names."""
        if self._in_type_checking:
            self.generic_visit(node)
            return

        # Detect exec/eval usage
        if isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval"):
            self._has_exec_eval = True

        name = self._extract_root_name(node.func)
        if name:
            self.used_names[name].append(node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Collect bare name references in Load context (non-TYPE_CHECKING)."""
        if self._in_type_checking:
            self.generic_visit(node)
            return
        if isinstance(node.ctx, ast.Load):
            self.used_names[node.id].append(node.lineno)
        self.generic_visit(node)

    @staticmethod
    def _extract_root_name(node: ast.expr) -> str | None:
        """Extract the leftmost identifier from a call target.

        ``foo()`` → ``foo``
        ``foo.bar()`` → ``foo``
        ``foo.bar.baz()`` → ``foo``
        ``Cls()`` → ``Cls``
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            # Walk to leftmost Name
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                current = current.value
            if isinstance(current, ast.Name):
                return current.id
        return None

    @staticmethod
    def _is_module_level(node: ast.AST) -> bool:
        """Heuristic: node at col_offset 0 is likely module-level."""
        return getattr(node, "col_offset", 1) == 0


class _ScopeCollector(ast.NodeVisitor):
    """Collect all names *defined* in a module's local scope.

    Covers: function defs, class defs, global assignments, for-targets,
    with-as, except-as, comprehension variables, import statements.
    """

    def __init__(self) -> None:
        self.defined_names: set[str] = set()

    def _register_argument_names(self, args: ast.arguments) -> None:
        """Register argument identifiers from function/lambda signatures."""
        for arg in args.args + args.posonlyargs + args.kwonlyargs:
            self.defined_names.add(arg.arg)
        if args.vararg:
            self.defined_names.add(args.vararg.arg)
        if args.kwarg:
            self.defined_names.add(args.kwarg.arg)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Register function name."""
        self.defined_names.add(node.name)
        # Also register parameter names (they are in scope within the function)
        self._register_argument_names(node.args)
        # Register decorator names as used (not defined)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]  # noqa: N815

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Register lambda parameter names."""
        self._register_argument_names(node.args)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Register class name."""
        self.defined_names.add(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Register imported module names."""
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.defined_names.add(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Register from-imported names."""
        for alias in node.names:
            if alias.name == "*":
                continue  # Star imports handled separately
            name = alias.asname or alias.name
            self.defined_names.add(name)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Register assignment targets."""
        for target in node.targets:
            self._collect_target_names(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Register annotated assignment targets."""
        if node.target:
            self._collect_target_names(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Register augmented assignment targets."""
        self._collect_target_names(node.target)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Register for-loop target variables."""
        self._collect_target_names(node.target)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Register with-as variables."""
        for item in node.items:
            if item.optional_vars:
                self._collect_target_names(item.optional_vars)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Register except-as variable."""
        if node.name:
            self.defined_names.add(node.name)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        """Register comprehension / generator iteration variables."""
        self._collect_target_names(node.target)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        """Register walrus operator target."""
        if isinstance(node.target, ast.Name):
            self.defined_names.add(node.target.id)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        """Register global declarations."""
        for name in node.names:
            self.defined_names.add(name)

    def _collect_target_names(self, node: ast.expr) -> None:
        """Extract names from assignment targets (supports tuple unpacking)."""
        if isinstance(node, ast.Name):
            self.defined_names.add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._collect_target_names(elt)
        elif isinstance(node, ast.Starred):
            self._collect_target_names(node.value)


# ---------------------------------------------------------------------------
# Project-wide symbol table construction
# ---------------------------------------------------------------------------


def _build_project_symbols(
    parse_results: list[ParseResult],
) -> set[str]:
    """Build a set of all names exported by the project.

    Includes function names, class names, and top-level assignment targets
    from all Python files (excluding tests).
    """
    symbols: set[str] = set()
    for pr in parse_results:
        if pr.language != "python":
            continue
        for fn in pr.functions:
            symbols.add(fn.name)
        for cls in pr.classes:
            symbols.add(cls.name)
            for method in cls.methods:
                symbols.add(method.name)
    return symbols


def _build_module_exports(
    parse_results: list[ParseResult],
    repo_path: Path | None = None,
) -> dict[str, set[str]]:
    """Map dotted module names to the set of names they export.

    Used to verify that ``from X import Y`` actually finds ``Y`` in X.
    Includes functions, classes, re-exports via imports, and module-level
    assignments (constants, singletons).
    """
    exports: dict[str, set[str]] = defaultdict(set)
    for pr in parse_results:
        if pr.language != "python":
            continue
        mod_name = _path_to_module(pr.file_path)
        if not mod_name:
            continue
        for fn in pr.functions:
            exports[mod_name].add(fn.name)
        for cls in pr.classes:
            exports[mod_name].add(cls.name)
        # Re-exports via imports (e.g. __init__.py re-exporting)
        for imp in pr.imports:
            for name in imp.imported_names:
                if name != "*":
                    exports[mod_name].add(name)
        # Module-level assignments (constants like __version__, console, etc.)
        if repo_path is not None:
            _enrich_exports_from_source(exports[mod_name], pr.file_path, repo_path)
    return dict(exports)


def _path_to_module(file_path: Path) -> str:
    """Convert a file path to a dotted module name.

    Strips common layout prefixes (``src/``, ``lib/``) so that the
    resulting dotted name matches what ``import`` statements use.
    """
    posix = PurePosixPath(file_path)
    parts = list(posix.parts)
    if not parts:
        return ""
    # Strip common source layout prefixes
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _enrich_exports_from_source(
    names: set[str],
    file_path: Path,
    repo_path: Path,
) -> None:
    """Add module-level assignment targets from source code to *names*.

    This captures constants, singletons, and other module-level names
    that are not function/class definitions but are still importable
    (e.g. ``console = Console()``, ``__version__ = "1.0"``).
    """
    full_path = repo_path / file_path
    try:
        source = full_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(
            node.target, ast.Name,
        ):
            names.add(node.target.id)


# ---------------------------------------------------------------------------
# Signal implementation
# ---------------------------------------------------------------------------


@register_signal
class PhantomReferenceSignal(BaseSignal):
    """Detect unresolvable function/class references (AI hallucination indicator).

    Analyses each Python file to find names used in call expressions that
    cannot be resolved via local definitions, imports, builtins, or the
    project-wide symbol table.
    """

    incremental_scope: ClassVar[Literal["cross_file"]] = "cross_file"

    @property
    def signal_type(self) -> SignalType:
        return SignalType.PHANTOM_REFERENCE

    @property
    def name(self) -> str:
        return "Phantom Reference"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        """Run phantom-reference detection across all Python files."""
        project_symbols = _build_project_symbols(parse_results)
        module_exports = _build_module_exports(parse_results, self.repo_path)

        findings: list[Finding] = []

        for pr in parse_results:
            if pr.language != "python":
                continue
            if is_test_file(pr.file_path):
                continue

            file_findings = self._analyze_file(
                pr, project_symbols, module_exports,
            )
            findings.extend(file_findings)

        return findings

    def _analyze_file(
        self,
        pr: ParseResult,
        project_symbols: set[str],
        module_exports: dict[str, set[str]],
    ) -> list[Finding]:
        """Analyse a single file for phantom references."""
        # Re-parse the source to get the full AST
        # (ParseResult only has structured data, not the raw AST)
        source = self._read_source(pr.file_path)
        if source is None:
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        # Collect used names
        name_collector = _NameCollector()
        name_collector.visit(tree)

        # Bail out for files with star imports or module-level __getattr__
        if name_collector._has_star_import:
            return []
        if name_collector._has_getattr_module:
            return []

        # Collect locally defined names
        scope_collector = _ScopeCollector()
        scope_collector.visit(tree)

        # Build the complete available-names set for this file
        available: set[str] = set()
        available.update(scope_collector.defined_names)
        available.update(_BUILTINS)
        available.update(_FRAMEWORK_GLOBALS)
        available.update(project_symbols)

        # Find phantom references (unresolvable names)
        phantoms: list[tuple[str, int]] = []  # (name, first_line)
        for name, lines in name_collector.used_names.items():
            if name in available:
                continue
            # Skip dunder names (protocol methods, magic)
            if name.startswith("__") and name.endswith("__"):
                continue
            # Skip single-character names (loop vars etc.)
            if len(name) <= 1:
                continue
            # Skip private names (likely internal, less likely hallucinated)
            if name.startswith("_"):
                continue
            phantoms.append((name, min(lines)))

        # Find phantom imports: from <project_module> import <name>
        # where <name> does not exist in that module's known exports
        phantom_imports = self._check_import_from_phantoms(
            tree, module_exports,
        )
        phantoms.extend(phantom_imports)

        if not phantoms:
            return []

        # Sort by line number for deterministic output
        phantoms.sort(key=lambda x: x[1])
        phantom_count = len(phantoms)
        phantom_names = [p[0] for p in phantoms[:10]]

        score = round(min(1.0, 0.3 + 0.15 * phantom_count), 3)
        severity = Severity.HIGH if score >= 0.7 else Severity.MEDIUM

        return [
            Finding(
                signal_type=self.signal_type,
                severity=severity,
                score=score,
                title=(
                    f"{phantom_count} unresolvable reference"
                    f"{'s' if phantom_count != 1 else ''} "
                    f"in {pr.file_path.name}"
                ),
                description=(
                    f"{pr.file_path} uses {phantom_count} name"
                    f"{'s' if phantom_count != 1 else ''} that cannot be "
                    f"resolved against local definitions, imports, builtins, "
                    f"or the project symbol table: "
                    f"{', '.join(phantom_names)}"
                    f"{'...' if phantom_count > 10 else ''}. "
                    f"These may be AI-hallucinated references or missing "
                    f"imports."
                ),
                file_path=pr.file_path,
                start_line=phantoms[0][1],
                fix=(
                    f"Verify that {', '.join(phantom_names[:5])} "
                    f"{'exist' if len(phantom_names) > 1 else 'exists'} "
                    f"in the project or add the missing import"
                    f"{'s' if len(phantom_names) > 1 else ''}. "
                    f"If these functions were suggested by an AI assistant, "
                    f"they may need to be implemented first."
                ),
                metadata={
                    "phantom_names": [
                        {"name": p[0], "line": p[1]}
                        for p in phantoms
                    ],
                    "phantom_count": phantom_count,
                },
                rule_id="phantom_reference",
            ),
        ]

    def _read_source(self, file_path: Path) -> str | None:
        """Read source file content, returning None on failure."""
        if self.repo_path is None:
            return None
        full_path = self.repo_path / file_path
        try:
            return full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    @staticmethod
    def _check_import_from_phantoms(
        tree: ast.Module,
        module_exports: dict[str, set[str]],
    ) -> list[tuple[str, int]]:
        """Detect ``from <project_module> import <name>`` where name is absent.

        Only checks modules whose source we have parsed (i.e. project-internal).
        Third-party and stdlib modules are NOT checked.
        """
        phantoms: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            mod_name = node.module or ""
            if mod_name not in module_exports:
                continue
            known = module_exports[mod_name]
            for alias in node.names:
                if alias.name == "*":
                    continue
                real_name = alias.name
                if real_name not in known:
                    # Check parent packages (e.g. drift.signals might
                    # re-export from sub-modules)
                    parts = mod_name.rsplit(".", 1)
                    if len(parts) == 2:
                        parent_mod = parts[0]
                        if (
                            parent_mod in module_exports
                            and real_name in module_exports[parent_mod]
                        ):
                            continue
                    phantoms.append((real_name, node.lineno))
        return phantoms
