# Trust and Evidence

This page is the shortest path to the evidence behind drift.

It is designed for teams that need to answer a practical question before rollout: what can we trust today, what should we verify locally, and where is the raw material?

## Public claims safe to repeat

- drift uses 6 scoring signals in the composite score, plus 4 report-only signals (DIA, BEM, TPD, GCD)
- DIA, BEM, TPD, and GCD remain report-only with weight 0.00 until extraction precision improves
- the current study corpus covers 15 real-world repositories
- all analysis is deterministic and does not use an LLM in the detector pipeline

## Benchmark evidence

- 80% strict precision on a score-weighted sample of 291 findings across 5 repositories (automated heuristic classification; upper-bound estimate — independent multi-rater validation pending)
- 0 confirmed false positives for the 6 active scoring signals (n=202); all FPs from DIA (weight 0.00)
- 86% detection rate on a controlled mutation benchmark of 14 author-designed synthetic patterns (not a population recall estimate)
- self-analysis of drift reports a score of 0.442 (MEDIUM)

These numbers are summarized from [Benchmark Study](study.md) and should be interpreted together with the limitations below.

## What the evidence means

The strongest current claim is not that every finding is equally reliable.

The strongest current claim is that drift provides a deterministic and inspectable process, with benchmarked evidence, for surfacing structural drift patterns that teams can calibrate against their own repository.

## Known limitations to keep visible

- the labeled precision sample is score-weighted and over-represents higher-confidence findings
- recall was measured on a synthetic mutation benchmark, not on every naturally evolving repository shape
- DIA currently has known precision limitations and is excluded from the composite score
- temporal signals depend on repository history quality and clone depth
- the composite score is orientation, not a verdict

## Recommended evaluation posture

1. start with report-only usage
2. inspect findings per signal
3. gate only on high-confidence cases
4. tune based on recurring evidence in your own repo

## Where the detailed material lives

- [Benchmarking and Trust](benchmarking.md)
- [Benchmark Study](study.md)
- [Case Studies](case-studies/index.md)
- [Signal Reference](algorithms/signals.md)

## Repository artifacts

The raw benchmark and audit artifacts live in the repository alongside the docs. That matters because teams can inspect the material instead of relying on a black-box headline metric.

Useful starting points:

- `benchmark_results/all_results.json` for aggregate benchmark output across the corpus
- `benchmark_results/ground_truth_analysis.json` for labeled precision-analysis material
- `benchmark_results/ground_truth_labels.json` for the underlying labels
- `benchmark_results/mutation_benchmark.json` for the controlled recall benchmark
- `benchmark_results/holdout_validation.json` for validation snapshots kept apart from the main analysis narrative
- `benchmark_results/fastapi.json`, `benchmark_results/pydantic.json`, and `benchmark_results/django.json` for case-study-adjacent repository summaries
- `audit_results/cli_audit.md`, `audit_results/requests_audit.md`, `audit_results/arrow_audit.md`, and `audit_results/frappe_audit.md` for focused audit writeups

These artifacts are most useful when read together with [Benchmarking and Trust](benchmarking.md) and [Benchmark Study](study.md), because the methodology and the limits determine how the numbers should be interpreted.

## What to verify locally before making policy decisions

- whether your strongest findings line up with places the team already finds expensive to change
- whether generated or exceptional directories should be excluded
- whether boundary violations reflect real architecture intent or acceptable convenience imports
- whether temporal signals have enough git history to be meaningful in your clone

## Next pages

- [Architecture Drift Detection for Python](use-cases/architecture-drift-python.md)
- [CI Architecture Checks with SARIF](use-cases/ci-architecture-checks-sarif.md)
- [FAQ](faq.md)