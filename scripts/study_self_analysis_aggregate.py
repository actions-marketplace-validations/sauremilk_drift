#!/usr/bin/env python3
"""Aggregate self-analysis reports from community study S5 / S13.

Reads structured JSON reports (exported from GitHub Issues or manually
created) and computes summary statistics for the Community Self-Analysis
Evidence Base (STUDY.md §16.2) and Actionability Assessment (§17.3).

Usage:
    python scripts/study_self_analysis_aggregate.py [REPORT_DIR]

    # Default: reads from benchmark_results/study_reports/
    python scripts/study_self_analysis_aggregate.py

    # Custom directory:
    python scripts/study_self_analysis_aggregate.py path/to/reports/

Input format (one JSON file per participant):
    {
      "participant_id": "anon-001",
      "drift_version": "1.2.0",
      "repo_description": "Django web app, ~15k LOC",
      "experience_months": 24,
      "findings": [
        {
          "signal": "PFS",
          "severity": "HIGH",
          "known": false,
          "real_problem": true,
          "will_fix": true,
          "surprise": 4,
          "actionability": {
            "understandable": 4,
            "actionable": 3,
            "prioritizable": 5
          }
        }
      ],
      "most_surprising_finding": "PFS detected 3 different error-handling patterns...",
      "followup_30d": {
        "completed": false,
        "findings_fixed": 0,
        "findings_promised": 3
      }
    }

Output: summary statistics as JSON to stdout or file.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


def _load_reports(report_dir: Path) -> list[dict]:
    """Load all JSON reports from a directory."""
    reports = []
    for p in sorted(report_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if "findings" in data:
                reports.append(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"Warning: skipping invalid file {p}", file=sys.stderr)
    return reports


def aggregate(reports: list[dict]) -> dict:
    """Compute aggregate statistics across all reports."""
    if not reports:
        return {"error": "No reports found", "n_reports": 0}

    all_findings = []
    for r in reports:
        for f in r.get("findings", []):
            f["_participant"] = r.get("participant_id", "unknown")
            all_findings.append(f)

    # Discovery rate: findings that were unknown AND real problems
    n_unknown_real = sum(
        1 for f in all_findings
        if not f.get("known", True) and f.get("real_problem", False)
    )
    n_total = len(all_findings)
    discovery_rate = n_unknown_real / n_total if n_total > 0 else 0.0

    # Surprise by signal
    surprise_by_signal: dict[str, list[int]] = defaultdict(list)
    for f in all_findings:
        if "surprise" in f and f["surprise"] is not None:
            surprise_by_signal[f.get("signal", "UNKNOWN")].append(f["surprise"])

    surprise_summary = {
        signal: {
            "mean": round(mean(values), 2),
            "median": round(median(values), 2),
            "n": len(values),
        }
        for signal, values in sorted(surprise_by_signal.items())
    }

    # Actionability by signal (S13)
    actionability_by_signal: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for f in all_findings:
        act = f.get("actionability")
        if act:
            signal = f.get("signal", "UNKNOWN")
            for dim in ("understandable", "actionable", "prioritizable"):
                if dim in act and act[dim] is not None:
                    actionability_by_signal[signal][dim].append(act[dim])

    actionability_summary = {}
    for signal, dims in sorted(actionability_by_signal.items()):
        actionability_summary[signal] = {
            dim: {
                "median": round(median(values), 2),
                "mean": round(mean(values), 2),
                "n": len(values),
                "pct_gte_4": round(
                    sum(1 for v in values if v >= 4) / len(values) * 100, 1
                ),
            }
            for dim, values in sorted(dims.items())
        }

    # TP/FP distribution
    tp_count = sum(1 for f in all_findings if f.get("real_problem") is True)
    fp_count = sum(1 for f in all_findings if f.get("real_problem") is False)
    unsure_count = sum(1 for f in all_findings if f.get("real_problem") is None)

    # Will-fix rate
    n_will_fix = sum(1 for f in all_findings if f.get("will_fix") is True)
    will_fix_rate = n_will_fix / n_total if n_total > 0 else 0.0

    # 30-day follow-up (only for reports that have it)
    followups = [r["followup_30d"] for r in reports if r.get("followup_30d", {}).get("completed")]
    fix_rate_30d = None
    if followups:
        total_promised = sum(f.get("findings_promised", 0) for f in followups)
        total_fixed = sum(f.get("findings_fixed", 0) for f in followups)
        fix_rate_30d = total_fixed / total_promised if total_promised > 0 else 0.0

    return {
        "n_reports": len(reports),
        "n_findings_total": n_total,
        "discovery_rate": round(discovery_rate, 3),
        "tp_count": tp_count,
        "fp_count": fp_count,
        "unsure_count": unsure_count,
        "perceived_precision": round(tp_count / (tp_count + fp_count), 3)
        if (tp_count + fp_count) > 0 else None,
        "will_fix_rate": round(will_fix_rate, 3),
        "fix_rate_30d": round(fix_rate_30d, 3) if fix_rate_30d is not None else None,
        "surprise_by_signal": surprise_summary,
        "actionability_by_signal": actionability_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate self-analysis reports from community study S5/S13"
    )
    parser.add_argument(
        "report_dir",
        nargs="?",
        default="benchmark_results/study_reports",
        help="Directory containing JSON report files (default: benchmark_results/study_reports/)",
    )
    parser.add_argument("--output", "-o", help="Output path for results JSON")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    if not report_dir.is_dir():
        print(f"Error: {report_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    reports = _load_reports(report_dir)
    result = aggregate(reports)

    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")
        print(f"Results written to {args.output}")
    else:
        print(output_json)

    print(
        f"\nAggregated {result['n_reports']} reports, "
        f"{result['n_findings_total']} findings, "
        f"discovery rate = {result['discovery_rate']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
