#!/usr/bin/env python3
"""Generate blind annotation sheets for independent precision validation.

Creates a randomised sample of findings WITHOUT scores, so that human
reviewers classify TP/FP/Disputed based solely on the source-code context.
This breaks the circular validation where the tool's own score determines
ground truth.

Usage:
    python scripts/generate_annotation_sheet.py [--n 50] [--seed 42]
    python scripts/generate_annotation_sheet.py --evaluate annotated.json

Outputs:
    benchmark_results/annotation_sheet.json   — for reviewers (no scores)
    benchmark_results/annotation_key.json     — answer key (with scores, hidden)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "benchmark_results"


def _load_all_findings() -> list[dict]:
    """Load findings from all *_full.json benchmark files."""
    findings: list[dict] = []
    for full_file in sorted(RESULTS_DIR.glob("*_full.json")):
        repo = full_file.stem.replace("_full", "")
        try:
            data = json.loads(full_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for f in data.get("findings", []):
            f["_repo"] = repo
            findings.append(f)
    return findings


def _uniform_stratified_sample(
    findings: list[dict], n: int, rng: random.Random
) -> list[dict]:
    """Uniform-random stratified sample (equal per signal), NOT score-weighted."""
    by_signal: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        by_signal[f.get("signal", "unknown")].append(f)

    per_signal = max(1, n // len(by_signal)) if by_signal else n
    sample: list[dict] = []

    for _sig, items in sorted(by_signal.items()):
        rng.shuffle(items)
        sample.extend(items[:per_signal])

    # Fill remaining quota from all findings
    remaining = n - len(sample)
    if remaining > 0:
        pool = [f for f in findings if f not in sample]
        rng.shuffle(pool)
        sample.extend(pool[:remaining])

    rng.shuffle(sample)
    return sample[:n]


def generate(n: int = 50, seed: int = 42) -> None:
    """Generate annotation sheet and answer key."""
    findings = _load_all_findings()
    if not findings:
        print("No findings found in benchmark_results/*_full.json", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    sample = _uniform_stratified_sample(findings, n, rng)

    # Annotation sheet: what reviewers see (NO score, NO severity)
    sheet: list[dict] = []
    key: list[dict] = []

    for idx, f in enumerate(sample, 1):
        item_id = f"F{idx:03d}"

        sheet.append({
            "id": item_id,
            "signal": f.get("signal", ""),
            "repo": f.get("_repo", ""),
            "title": f.get("title", ""),
            "description": f.get("description", ""),
            "file": f.get("file", f.get("affected_file", "")),
            "label": "",  # reviewer fills this: TP / FP / Disputed
            "reviewer_notes": "",  # free-text justification
        })

        key.append({
            "id": item_id,
            "signal": f.get("signal", ""),
            "repo": f.get("_repo", ""),
            "title": f.get("title", ""),
            "score": f.get("score", 0),
            "severity": f.get("severity", ""),
        })

    sheet_path = RESULTS_DIR / "annotation_sheet.json"
    key_path = RESULTS_DIR / "annotation_key.json"

    sheet_path.write_text(json.dumps(sheet, indent=2, ensure_ascii=False), encoding="utf-8")
    key_path.write_text(json.dumps(key, indent=2, ensure_ascii=False), encoding="utf-8")

    # Signal distribution in sample
    dist: dict[str, int] = defaultdict(int)
    for f in sample:
        dist[f.get("signal", "unknown")] += 1

    print(f"Generated annotation sheet: {sheet_path}")
    print(f"Answer key (do NOT share with reviewers): {key_path}")
    print(f"\nSample: {len(sample)} findings from {len(set(f['_repo'] for f in sample))} repos")
    print(f"Sampling: uniform-random stratified (seed={seed})")
    print("\nSignal distribution:")
    for sig, count in sorted(dist.items()):
        print(f"  {sig:<30s} {count:>3d}")

    print("\n--- Instructions for reviewers ---")
    print("1. Open annotation_sheet.json")
    print("2. For each finding, inspect the source code at the given file path")
    print("3. Set 'label' to TP, FP, or Disputed")
    print("4. Add a brief justification in 'reviewer_notes'")
    print("5. Do NOT look at scores or the answer key")


def evaluate(annotated_path: str) -> None:
    """Compute inter-rater agreement and precision from annotated sheet."""
    data = json.loads(Path(annotated_path).read_text(encoding="utf-8"))

    by_signal: dict[str, dict[str, int]] = defaultdict(
        lambda: {"TP": 0, "FP": 0, "Disputed": 0, "unlabeled": 0, "total": 0}
    )
    total_tp = total_fp = total_disp = total_n = 0

    for item in data:
        sig = item.get("signal", "unknown")
        label = item.get("label", "").strip().upper()
        if label in ("TP", "FP", "DISPUTED"):
            if label == "DISPUTED":
                label = "Disputed"
            by_signal[sig][label] += 1
            by_signal[sig]["total"] += 1
            if label == "TP":
                total_tp += 1
            elif label == "FP":
                total_fp += 1
            else:
                total_disp += 1
            total_n += 1
        else:
            by_signal[sig]["unlabeled"] += 1

    print("=" * 72)
    print("INDEPENDENT ANNOTATION RESULTS")
    print("=" * 72)
    hdr = (
        f"{'Signal':<28s} {'n':>4s} {'TP':>4s} {'FP':>4s} {'Disp':>5s} "
        f"{'Prec(strict)':>13s} {'Prec(lenient)':>14s}"
    )
    print(hdr)
    print("-" * 72)

    for sig in sorted(by_signal):
        s = by_signal[sig]
        n = s["total"]
        tp, fp, disp = s["TP"], s["FP"], s["Disputed"]
        if n > 0:
            ps = tp / n
            pl = (tp + disp) / n
            print(
                f"{sig:<28s} {n:>4d} {tp:>4d} {fp:>4d} {disp:>5d} "
                f"{ps:>12.1%} {pl:>13.1%}"
            )

    if total_n > 0:
        print("-" * 72)
        ps = total_tp / total_n
        pl = (total_tp + total_disp) / total_n
        print(
            f"{'TOTAL':<28s} {total_n:>4d} {total_tp:>4d} {total_fp:>4d} "
            f"{total_disp:>5d} {ps:>12.1%} {pl:>13.1%}"
        )
    else:
        print("\nNo labeled findings found. Did the reviewer fill in the 'label' field?")


def main() -> None:
    parser = argparse.ArgumentParser(description="Blind annotation tooling")
    parser.add_argument("--n", type=int, default=50, help="Sample size (default: 50)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--evaluate", type=str, default=None,
        help="Path to annotated JSON file for evaluation",
    )
    args = parser.parse_args()

    if args.evaluate:
        evaluate(args.evaluate)
    else:
        generate(n=args.n, seed=args.seed)


if __name__ == "__main__":
    main()
