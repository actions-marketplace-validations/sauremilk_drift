# Benchmark Study

## Summary

The benchmark study covers 15 repositories across 5 corpus categories. Key results:

- **Precision:** 77% strict / 95% lenient (v0.5 baseline, 286 findings, 5 repos, score-weighted sample, single-rater, 51 disputed)
- **Mutation recall:** 88% detection rate (v0.7.1, 17 injected patterns, 10 signal types)
- **Temporal stability:** Django 1.8–6.0 score variation σ = 0.004 across 10 years
- **Per-signal precision range:** PFS 100%, EDS 100%, SMS 100%, MDS 82%, DIA 63%, AVS 30% (n=20), TVS 0% strict (classification-method artifact)

All methodology, per-signal breakdowns, reproducibility commands, and corpus details are in the full study.

## Full study

The full benchmark study (54 KB) with evaluation methodology, ground-truth precision analysis (291 classified findings), controlled mutation benchmark (14 patterns, 86% recall), and tool landscape comparison is available at:

**[STUDY.md on GitHub](https://github.com/mick-gsk/drift/blob/main/docs/STUDY.md)**
