#!/usr/bin/env python3
"""Compute inter-rater agreement (Fleiss' kappa / Cohen's kappa).

Used by community studies S7 (Multi-Rater PFS Validation) and S8
(Deliberate Polymorphism Taxonomy) to measure how consistently
independent raters classify drift findings.

Usage:
    # Compute kappa from a rating matrix file:
    python scripts/study_rater_agreement.py ratings.json

    # Run self-test with known reference values:
    python scripts/study_rater_agreement.py --test

Input format (JSON):
    {
      "categories": ["TP", "FP", "Unclear"],
      "ratings": [
        {"finding_id": "F-001", "raters": ["TP", "TP", "FP"]},
        {"finding_id": "F-002", "raters": ["FP", "FP", "FP"]},
        ...
      ]
    }

Output: kappa value, per-finding agreement, disagreement analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def fleiss_kappa(ratings: list[list[str]], categories: list[str]) -> float:
    """Compute Fleiss' kappa for multiple raters.

    Args:
        ratings: List of findings, each containing a list of rater judgments.
        categories: List of possible category labels.
    Returns:
        Fleiss' kappa coefficient (-1.0 to 1.0).
    """
    n_subjects = len(ratings)
    if n_subjects == 0:
        return 0.0
    n_raters = len(ratings[0])
    if n_raters < 2:
        return 0.0

    # Build the n_subjects x n_categories count matrix
    cat_index = {c: i for i, c in enumerate(categories)}
    n_cat = len(categories)
    matrix = []
    for finding_ratings in ratings:
        row = [0] * n_cat
        for r in finding_ratings:
            if r in cat_index:
                row[cat_index[r]] += 1
        matrix.append(row)

    # P_i for each subject
    p_values = []
    for row in matrix:
        total = sum(row)
        if total <= 1:
            p_values.append(0.0)
            continue
        p_i = (sum(x * x for x in row) - total) / (total * (total - 1))
        p_values.append(p_i)

    p_bar = sum(p_values) / n_subjects

    # P_j for each category (proportion across all ratings)
    total_ratings = n_subjects * n_raters
    p_j = []
    for j in range(n_cat):
        col_sum = sum(matrix[i][j] for i in range(n_subjects))
        p_j.append(col_sum / total_ratings)

    p_e = sum(pj * pj for pj in p_j)

    if abs(1.0 - p_e) < 1e-10:
        return 1.0 if abs(1.0 - p_bar) < 1e-10 else 0.0

    return (p_bar - p_e) / (1.0 - p_e)


def cohen_kappa(rater_a: list[str], rater_b: list[str], categories: list[str]) -> float:
    """Compute Cohen's kappa for two raters.

    Args:
        rater_a: Judgments from rater A.
        rater_b: Judgments from rater B.
        categories: List of possible category labels.
    Returns:
        Cohen's kappa coefficient (-1.0 to 1.0).
    """
    n = len(rater_a)
    if n == 0:
        return 0.0

    cat_index = {c: i for i, c in enumerate(categories)}
    n_cat = len(categories)

    # Confusion matrix
    confusion = [[0] * n_cat for _ in range(n_cat)]
    for a, b in zip(rater_a, rater_b, strict=True):
        if a in cat_index and b in cat_index:
            confusion[cat_index[a]][cat_index[b]] += 1

    p_o = sum(confusion[i][i] for i in range(n_cat)) / n

    p_e = 0.0
    for i in range(n_cat):
        row_sum = sum(confusion[i])
        col_sum = sum(confusion[j][i] for j in range(n_cat))
        p_e += (row_sum / n) * (col_sum / n)

    if abs(1.0 - p_e) < 1e-10:
        return 1.0 if abs(1.0 - p_o) < 1e-10 else 0.0

    return (p_o - p_e) / (1.0 - p_e)


def per_finding_agreement(ratings: list[list[str]]) -> list[dict]:
    """Compute agreement rate per finding."""
    results = []
    for i, finding_ratings in enumerate(ratings):
        counts = Counter(finding_ratings)
        total = len(finding_ratings)
        majority_label, majority_count = counts.most_common(1)[0]
        agreement = majority_count / total if total > 0 else 0.0
        results.append({
            "finding_index": i,
            "majority_label": majority_label,
            "agreement_rate": round(agreement, 3),
            "distribution": dict(counts),
        })
    return results


def analyze_file(path: Path) -> dict:
    """Load a rating matrix from JSON and compute all metrics."""
    data = json.loads(path.read_text(encoding="utf-8"))
    categories = data["categories"]
    raw_ratings = data["ratings"]

    ratings_matrix = [entry["raters"] for entry in raw_ratings]
    finding_ids = [entry.get("finding_id", f"F-{i:03d}") for i, entry in enumerate(raw_ratings)]

    n_raters = len(ratings_matrix[0]) if ratings_matrix else 0

    if n_raters == 2:
        rater_a = [r[0] for r in ratings_matrix]
        rater_b = [r[1] for r in ratings_matrix]
        kappa = cohen_kappa(rater_a, rater_b, categories)
        kappa_type = "cohen"
    else:
        kappa = fleiss_kappa(ratings_matrix, categories)
        kappa_type = "fleiss"

    per_finding = per_finding_agreement(ratings_matrix)
    for pf, fid in zip(per_finding, finding_ids, strict=True):
        pf["finding_id"] = fid

    mean_agreement = (
        sum(pf["agreement_rate"] for pf in per_finding) / len(per_finding)
        if per_finding else 0.0
    )

    # Disagreement cluster: findings with agreement < 0.67
    disagreements = [pf for pf in per_finding if pf["agreement_rate"] < 0.67]

    return {
        "kappa_type": kappa_type,
        "kappa": round(kappa, 4),
        "n_findings": len(ratings_matrix),
        "n_raters": n_raters,
        "n_categories": len(categories),
        "categories": categories,
        "mean_agreement": round(mean_agreement, 3),
        "n_disagreements": len(disagreements),
        "per_finding": per_finding,
        "disagreements": disagreements,
    }


def run_self_test() -> bool:
    """Run self-test with known reference values. Returns True if all pass."""
    passed = True

    # Test 1: Perfect agreement → κ = 1.0
    ratings_perfect = [["TP", "TP", "TP"]] * 10
    k = fleiss_kappa(ratings_perfect, ["TP", "FP", "Unclear"])
    if abs(k - 1.0) > 0.01:
        print(f"FAIL: Perfect agreement expected κ=1.0, got κ={k:.4f}")
        passed = False
    else:
        print(f"PASS: Perfect agreement κ={k:.4f}")

    # Test 2: Known Fleiss reference (Fleiss 1971 example, adapted)
    # 10 findings, 3 raters, 3 categories
    # Moderate agreement expected: κ ≈ 0.29
    ratings_moderate = [
        ["TP", "TP", "FP"],
        ["FP", "FP", "FP"],
        ["TP", "FP", "TP"],
        ["TP", "TP", "TP"],
        ["FP", "FP", "Unclear"],
        ["Unclear", "TP", "Unclear"],
        ["TP", "TP", "TP"],
        ["FP", "FP", "FP"],
        ["TP", "FP", "TP"],
        ["Unclear", "Unclear", "FP"],
    ]
    k = fleiss_kappa(ratings_moderate, ["TP", "FP", "Unclear"])
    if not (0.15 < k < 0.50):
        print(f"FAIL: Moderate agreement expected κ ∈ [0.15, 0.50], got κ={k:.4f}")
        passed = False
    else:
        print(f"PASS: Moderate agreement κ={k:.4f}")

    # Test 3: Cohen's κ perfect agreement
    k = cohen_kappa(["TP"] * 10, ["TP"] * 10, ["TP", "FP"])
    if abs(k - 1.0) > 0.01:
        print(f"FAIL: Cohen perfect expected κ=1.0, got κ={k:.4f}")
        passed = False
    else:
        print(f"PASS: Cohen perfect agreement κ={k:.4f}")

    # Test 4: Cohen's κ no agreement beyond chance
    rater_a = ["TP", "FP"] * 5
    rater_b = ["FP", "TP"] * 5
    k = cohen_kappa(rater_a, rater_b, ["TP", "FP"])
    if k > 0.01:
        print(f"FAIL: No agreement expected κ≤0, got κ={k:.4f}")
        passed = False
    else:
        print(f"PASS: No agreement κ={k:.4f}")

    return passed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute inter-rater agreement (Fleiss'/Cohen's kappa)"
    )
    parser.add_argument("input", nargs="?", help="Path to rating matrix JSON file")
    parser.add_argument("--test", action="store_true", help="Run self-test with known values")
    parser.add_argument(
        "--output", "-o", help="Output path for results JSON (default: stdout)"
    )
    args = parser.parse_args()

    if args.test:
        ok = run_self_test()
        sys.exit(0 if ok else 1)

    if not args.input:
        parser.error("Either provide an input file or use --test")

    result = analyze_file(Path(args.input))

    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")
        print(f"Results written to {args.output}")
    else:
        print(output_json)

    # Summary to stderr
    print(
        f"\n{'Fleiss' if result['kappa_type'] == 'fleiss' else 'Cohen'}'s κ = {result['kappa']}"
        f"  (n={result['n_findings']} findings, {result['n_raters']} raters)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
