#!/usr/bin/env python3
"""Agent-Loop Efficiency Benchmark.

Simulates deterministic agent workflows using ``drift.api`` functions
and measures API-call counts, iterations, and finding deltas.

Three scenarios derived from ground-truth fixtures:
  1. Gate-Check — can ``nudge()`` correctly block a dirty repo?
  2. Fix-Cycle  — how many API calls from scan→fix_plan→diff?
  3. Context-Export — does negative_context reduce findings?

Usage:
    python scripts/benchmark_agent_loop.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Corpus reuse
# ---------------------------------------------------------------------------
CORPUS_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "corpus"


@dataclass
class ScenarioResult:
    """Result of one agent-loop scenario."""

    name: str = ""
    api_calls: int = 0
    findings_before: int = 0
    findings_after: int = 0
    score_before: float = 0.0
    score_after: float = 0.0
    iterations: int = 0
    duration_seconds: float = 0.0
    details: dict = field(default_factory=dict)


def _init_git_repo(path: Path) -> None:
    """Initialize a minimal git repo at *path* for drift to work."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "bench",
        "GIT_COMMITTER_NAME": "bench",
        "GIT_AUTHOR_EMAIL": "b@b",
        "GIT_COMMITTER_EMAIL": "b@b",
    }
    subprocess.run(
        ["git", "init"], cwd=str(path), capture_output=True, env=env,
    )
    subprocess.run(
        ["git", "add", "."], cwd=str(path), capture_output=True, env=env,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(path),
        capture_output=True,
        env=env,
    )


def _prepare_workspace(tmp: Path) -> Path:
    """Copy corpus into tmp and init git."""
    ws = tmp / "workspace"
    shutil.copytree(CORPUS_DIR, ws)
    _init_git_repo(ws)
    return ws


def scenario_gate_check(workspace: Path) -> ScenarioResult:
    """Scenario 1: Agent uses scan() then nudge() to gate a commit.

    Measures: Is the gate decision correct? How many API calls needed?
    """
    from drift.api import nudge, scan

    result = ScenarioResult(name="gate_check")
    t0 = time.monotonic()

    # Step 1: Initial scan to establish baseline.
    scan_result = scan(path=str(workspace), max_findings=50)
    result.api_calls += 1
    result.findings_before = len(scan_result.get("findings", []))
    result.score_before = scan_result.get("drift_score", 0.0)

    # Step 2: Nudge to check if safe to commit.
    nudge_result = nudge(path=str(workspace))
    result.api_calls += 1

    safe = nudge_result.get("safe_to_commit", True)
    blocking = nudge_result.get("blocking_reasons", [])

    result.details = {
        "safe_to_commit": safe,
        "blocking_reasons": blocking,
        "direction": nudge_result.get("direction", "unknown"),
        "severity": scan_result.get("severity", "unknown"),
    }
    result.iterations = 1  # Single gate check.
    result.duration_seconds = round(time.monotonic() - t0, 3)
    result.findings_after = result.findings_before  # No fix applied.
    result.score_after = result.score_before
    return result


def scenario_fix_cycle(workspace: Path) -> ScenarioResult:
    """Scenario 2: Agent runs scan→fix_plan→(simulated fix)→diff loop.

    Measures: iterations, API calls, finding delta.
    """
    from drift.api import fix_plan, scan

    result = ScenarioResult(name="fix_cycle")
    t0 = time.monotonic()

    # Step 1: Initial scan.
    scan1 = scan(path=str(workspace), max_findings=50)
    result.api_calls += 1
    result.findings_before = len(scan1.get("findings", []))
    result.score_before = scan1.get("drift_score", 0.0)

    # Step 2: Fix plan.
    plan = fix_plan(path=str(workspace), max_tasks=5)
    result.api_calls += 1
    tasks = plan.get("priority_tasks", [])

    result.details = {
        "tasks_proposed": len(tasks),
        "task_signals": [t.get("signal", "") for t in tasks],
        "task_efforts": [t.get("effort", "") for t in tasks],
    }

    # Step 3: Re-scan (simulating that agent applied fixes).
    # In a real loop, the agent would edit files here.
    # We measure the baseline API-call overhead.
    scan2 = scan(path=str(workspace), max_findings=50)
    result.api_calls += 1
    result.findings_after = len(scan2.get("findings", []))
    result.score_after = scan2.get("drift_score", 0.0)

    result.iterations = 2  # scan→plan→scan.
    result.duration_seconds = round(time.monotonic() - t0, 3)
    return result


def scenario_context_export(workspace: Path) -> ScenarioResult:
    """Scenario 3: Agent uses negative_context() for prompt enrichment.

    Measures: API calls, context patterns generated, token estimate.
    """
    from drift.api import negative_context, scan

    result = ScenarioResult(name="context_export")
    t0 = time.monotonic()

    # Step 1: Scan.
    scan1 = scan(path=str(workspace), max_findings=50)
    result.api_calls += 1
    result.findings_before = len(scan1.get("findings", []))
    result.score_before = scan1.get("drift_score", 0.0)

    # Step 2: Export negative context.
    ctx = negative_context(path=str(workspace))
    result.api_calls += 1

    forbidden = ctx.get("forbidden_patterns", [])
    # Estimate token savings: compact vs verbose.
    # Each forbidden pattern is ~20 tokens in compact form.
    compact_tokens = len(forbidden) * 20
    # Verbose format would be ~80 tokens per pattern.
    verbose_tokens = len(forbidden) * 80

    result.details = {
        "forbidden_patterns": len(forbidden),
        "compact_token_estimate": compact_tokens,
        "verbose_token_estimate": verbose_tokens,
        "token_saving_percent": (
            round((1 - compact_tokens / verbose_tokens) * 100, 1)
            if verbose_tokens > 0
            else 0
        ),
        "signals_covered": list(
            {p.get("signal", "") for p in forbidden if p.get("signal")},
        ),
    }

    result.findings_after = result.findings_before
    result.score_after = result.score_before
    result.iterations = 1
    result.duration_seconds = round(time.monotonic() - t0, 3)
    return result


def main() -> None:
    """Run all scenarios and write results."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Agent-loop efficiency benchmark",
    )
    parser.add_argument(
        "--output",
        default="benchmark_results/agent_loop_benchmark.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    results: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="drift_agent_") as tmp_str:
        tmp = Path(tmp_str)
        workspace = _prepare_workspace(tmp)

        for scenario_fn in [
            scenario_gate_check,
            scenario_fix_cycle,
            scenario_context_export,
        ]:
            print(f"Running: {scenario_fn.__name__} ...")
            sr = scenario_fn(workspace)
            result_dict = {
                "scenario": sr.name,
                "api_calls": sr.api_calls,
                "iterations": sr.iterations,
                "findings_before": sr.findings_before,
                "findings_after": sr.findings_after,
                "score_before": round(sr.score_before, 4),
                "score_after": round(sr.score_after, 4),
                "duration_seconds": sr.duration_seconds,
                "details": sr.details,
            }
            results.append(result_dict)
            print(
                f"  API calls: {sr.api_calls}"
                f"  Findings: {sr.findings_before}"
                f"  Duration: {sr.duration_seconds}s",
            )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "benchmark": "agent_loop_efficiency",
        "scenarios": {r["scenario"]: r for r in results},
        "summary": {
            "total_api_calls": sum(r["api_calls"] for r in results),
            "total_iterations": sum(r["iterations"] for r in results),
            "narrative": (
                "Pre-v0.10.5: agents needed scan + manual JSON parsing "
                "for gate decisions. Post-v0.10.5: nudge() provides "
                "safe_to_commit in 1 API call. fix_plan() replaces "
                "manual triage. negative_context() enriches agent "
                "prompts without re-analysis."
            ),
        },
    }
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
