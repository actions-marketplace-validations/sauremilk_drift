#!/usr/bin/env python3
"""Compute correlation between drift composite score and tech-debt issue count.

Community study S11: tests the hypothesis that drift score correlates with
the number of tech-debt-labelled GitHub issues (Spearman ρ > 0.4).

Usage:
    # Analyze repos listed in a YAML file:
    python scripts/study_debt_correlation.py repos.yaml

    # Analyze a single repo:
    python scripts/study_debt_correlation.py --repo https://github.com/org/repo

    # Re-analyze from existing results:
    python scripts/study_debt_correlation.py --evaluate results.json

Input YAML format:
    repos:
      - url: https://github.com/org/repo1
        debt_labels: ["tech-debt", "refactoring"]  # optional override
      - url: https://github.com/org/repo2

Default debt labels: tech-debt, technical-debt, refactoring, cleanup,
code-quality, debt
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml

    HAS_YAML = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    HAS_YAML = False

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "benchmark_results"
DEFAULT_DEBT_LABELS = [
    "tech-debt",
    "technical-debt",
    "refactoring",
    "cleanup",
    "code-quality",
    "debt",
]


def _shallow_clone(url: str, dest: Path) -> Path:
    """Clone a repository with depth=1."""
    subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)],
        check=True,
        capture_output=True,
        timeout=300,
    )
    return dest


def _count_loc(repo_path: Path) -> int:
    """Count lines of Python/TypeScript code (simple heuristic)."""
    total = 0
    for ext in ("*.py", "*.ts", "*.js", "*.tsx", "*.jsx"):
        for f in repo_path.rglob(ext):
            if ".git" in f.parts or "node_modules" in f.parts:
                continue
            with contextlib.suppress(OSError):
                total += sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
    return total


def _run_drift(repo_path: Path) -> float | None:
    """Run drift analyze and return composite score."""
    result = subprocess.run(
        ["drift", "analyze", "--repo", str(repo_path), "--format", "json", "--since", "90"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0 and not result.stdout.strip():
        print(f"  drift failed: {result.stderr[:200]}", file=sys.stderr)
        return None
    try:
        data = json.loads(result.stdout)
        return data.get("composite_score", data.get("score"))
    except (json.JSONDecodeError, KeyError):
        return None


def _count_debt_issues(repo_url: str, labels: list[str]) -> int | None:
    """Count tech-debt issues via GitHub CLI ('gh')."""
    # Extract owner/repo from URL
    parts = repo_url.rstrip("/").rstrip(".git").split("/")
    owner_repo = f"{parts[-2]}/{parts[-1]}"

    total = 0
    seen_numbers: set[int] = set()
    for label in labels:
        try:
            result = subprocess.run(
                ["gh", "issue", "list", "--repo", owner_repo, "--label", label,
                 "--state", "all", "--json", "number", "--limit", "1000"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                continue
            issues = json.loads(result.stdout)
            for issue in issues:
                num = issue.get("number")
                if num and num not in seen_numbers:
                    seen_numbers.add(num)
                    total += 1
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            continue

    return total if total > 0 else None


def spearman_rho(x: list[float], y: list[float]) -> tuple[float, int]:
    """Compute Spearman rank correlation (pure Python).

    Returns (rho, n).
    """
    n = len(x)
    if n < 3:
        return 0.0, n

    def _rank(values: list[float]) -> list[float]:
        indexed = sorted(range(n), key=lambda i: values[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and values[indexed[j]] == values[indexed[j + 1]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)

    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry, strict=True))
    rho = 1 - (6 * d_sq) / (n * (n * n - 1))
    return rho, n


def analyze_repos(repos: list[dict]) -> dict:
    """Analyze a list of repos and compute correlation."""
    results = []

    for repo_info in repos:
        url = repo_info["url"]
        labels = repo_info.get("debt_labels", DEFAULT_DEBT_LABELS)
        name = url.rstrip("/").split("/")[-1].replace(".git", "")
        print(f"\nAnalyzing: {name} ({url})", file=sys.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / name
            try:
                _shallow_clone(url, dest)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"  Clone failed: {e}", file=sys.stderr)
                continue

            score = _run_drift(dest)
            loc = _count_loc(dest)

        debt_count = _count_debt_issues(url, labels)

        if score is None or debt_count is None:
            print(f"  Skipped (score={score}, debt={debt_count})", file=sys.stderr)
            continue

        debt_per_10k = (debt_count / loc * 10000) if loc > 0 else 0.0

        entry = {
            "repo": name,
            "url": url,
            "score": round(score, 4),
            "loc": loc,
            "debt_issues": debt_count,
            "debt_per_10kloc": round(debt_per_10k, 2),
        }
        results.append(entry)
        print(f"  score={score:.4f}, LOC={loc}, debt={debt_count}", file=sys.stderr)

    # Compute correlation
    if len(results) >= 3:
        scores = [r["score"] for r in results]
        debts = [r["debt_per_10kloc"] for r in results]
        rho, n = spearman_rho(scores, debts)
    else:
        rho = 0.0

    return {
        "study": "S11-debt-correlation",
        "n_repos": len(results),
        "spearman_rho": round(rho, 4),
        "results": results,
        "hypothesis": "rho > 0.4",
        "debt_labels_used": DEFAULT_DEBT_LABELS,
    }


def evaluate_existing(path: Path) -> None:
    """Re-compute correlation from existing results file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("results", [])
    if len(results) < 3:
        print("Not enough data points for correlation", file=sys.stderr)
        return
    scores = [r["score"] for r in results]
    debts = [r["debt_per_10kloc"] for r in results]
    rho, n = spearman_rho(scores, debts)
    print(f"Spearman ρ = {rho:.4f} (n={n})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute drift score vs. tech-debt issue correlation (study S11)"
    )
    parser.add_argument("input", nargs="?", help="YAML file with repo list")
    parser.add_argument("--repo", help="Single repo URL to analyze")
    parser.add_argument("--evaluate", help="Re-compute from existing results JSON")
    parser.add_argument("--output", "-o", help="Output path (default: benchmark_results/)")
    args = parser.parse_args()

    if args.evaluate:
        evaluate_existing(Path(args.evaluate))
        return

    repos: list[dict] = []
    if args.repo:
        repos.append({"url": args.repo})
    elif args.input:
        if not HAS_YAML or yaml is None:
            print("Error: pyyaml required. Install with: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
        data = yaml.safe_load(Path(args.input).read_text(encoding="utf-8"))
        repos = data.get("repos", [])
    else:
        parser.error("Provide a YAML file, --repo URL, or --evaluate path")

    result = analyze_repos(repos)

    output_path = Path(args.output) if args.output else OUTPUT_DIR / "study_debt_correlation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(out, encoding="utf-8")
    print(f"\nResults written to {output_path}", file=sys.stderr)
    print(f"Spearman ρ = {result['spearman_rho']} (n={result['n_repos']})")


if __name__ == "__main__":
    main()
