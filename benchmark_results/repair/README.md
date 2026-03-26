# Repair Benchmark

Deterministic Translation + Verification benchmark for
`drift analyze --format agent-tasks`.

Proves that Drift can generate structurally valid repair tasks,
verify correct repairs via measurable score reduction,
and reject incorrect repairs.  This is **not** a full autonomous
agent-repair benchmark — see [Claim Boundary](#claim-boundary).

## What This Proves

| Property | Evidence |
|----------|----------|
| **Task Correctness** | All generated tasks have valid schema, sequential priorities, non-empty success criteria, signal-prefixed IDs |
| **Causality** | Applying a correct repair measurably reduces the drift score for that signal (per-signal delta tracked) |
| **Verification Sharpness** | Incorrect repairs (3 cases across MDS, DIA, EDS) are correctly rejected — FAR = 0%, FRR = 0% |
| **Reproducibility** | 3× repeated analysis on identical input produces identical scores, findings, and task counts |
| **Effort Visibility** | Diff size (files changed, lines) tracked per repair intervention |

## Claim Boundary

### Strongly proven

- Drift produces deterministic, schema-complete repair tasks from analysis findings
- Controlled repairs on synthetic repos reduce drift scores measurably
- Incorrect repairs are not falsely accepted (verification is sharp)
- Task generation is stable on real benchmark data (flask, httpx)
- Repeated runs on identical input are deterministic

### Not yet proven

- Real coding agents executing these tasks autonomously in production repos
- Multi-step repair orchestration across dependent findings
- Comparative advantage over unguided agent repair (no control group yet)
- TVS/SMS signal repair coverage (only observed as side-effects)

### Known limitations

- **TVS side-effects**: Repair commits create `temporal_volatility` findings as a side effect.  Phase C cascade test confirms these stabilize (no divergence), but sequential agents must account for transient TVS spikes.
- **Sample sizes**: n=5 correct, n=3 incorrect.  FAR/FRR are directionally valid but not yet statistically robust (need n≥10 per class for formal significance).
- **EDS residual findings**: EDS repair reduces score significantly but may leave a residual finding (e.g. high parameter count).  The `targeted_finding_resolved` field tracks this precisely; see D14 in decisions.md.

This distinction is intentional.  A precise narrow claim is stronger
than an overpromised broad one.

## Verification Metrics

| Metric | Definition | Value |
|--------|-----------|-------|
| **True Positive Rate (TPR)** | Correct repairs verified / attempted | 5/5 = 100% |
| **True Negative Rate (TNR)** | Incorrect repairs detected / attempted | 3/3 = 100% |
| **False Acceptance Rate (FAR)** | Incorrect repairs falsely accepted | 0/3 = 0% |
| **False Rejection Rate (FRR)** | Correct repairs falsely rejected | 0/5 = 0% |
| **Signal Coverage** | Signals with verified repairs | MDS, EDS, DIA, PFS (4/6 recommender signals) |
| **Determinism** | N runs → identical output | 3/3 runs per repo |
| **TVS Cascade** | Sequential repairs → TVS stabilizes | Phase C: stable (no divergence) |

## Methodology

### Phase A — Controlled Repair (synthetic repos)

Two synthetic repos with injected drift patterns modeled after real
findings in `flask_full.json` and `httpx_full.json`:

**webapp** (Flask-like):
- MDS: Exact duplicate `_make_timedelta` in two modules (mirrors Flask's real finding)
- PFS: 4 inconsistent error handling patterns in `handlers/`

**datalib** (httpx-like):
- MDS: Duplicate `flush()` methods across decoder classes (mirrors httpx's DeflateDecoder/GZipDecoder)
- EDS: Complex undocumented `transform_records` function (CC≥12, 6 params, no docstring)
- SMS: Module using system-level deps (`ctypes`, `mmap`, `struct`)

For each repo:
1. Create synthetic repo with known issues → `git init`
2. Run `drift analyze` → baseline scores
3. Generate `agent-tasks` → validate task quality
4. Apply targeted repair → re-analyze → verify score drop
5. (webapp only) Apply **incorrect** repair → verify drift rejects it

### Phase B — Real Data Validation

Loads existing `flask_full.json` and `httpx_full.json`, reconstructs
Finding objects, generates agent-tasks, and validates:
- Schema completeness (all required fields present)
- ID uniqueness and signal prefix format
- Sequential priority ordering
- Non-empty success criteria, actions, expected effects

## Repair Interventions

| Repo | Signal | Repair | Type | Result |
|------|--------|--------|------|--------|
| webapp | MDS | Consolidate `_make_timedelta` into `utils/timedelta.py` | correct | finding removed, score ↓ |
| webapp | DIA | Fix README phantom directory references | correct | phantom refs removed, score ↓ |
| webapp | PFS | Standardize error handling to custom-exception pattern | correct | variant count reduced, score ↓ |
| webapp | MDS | Rename to `_convert_to_timedelta` (body unchanged) | incorrect | finding persists — **expected** |
| webapp | DIA | Replace old phantom refs with new phantom refs | incorrect | DIA still fires — **expected** |
| datalib | MDS | Extract `flush()` into `BaseDecoder` | correct | finding removed, score ↓ |
| datalib | EDS | Add docstrings, split into `_coerce`/`_passes`/`_aggregate` | correct | score ↓ significantly |
| datalib | EDS | Add trivial docstring, keep complexity | incorrect | EDS persists — **expected** |

## Failure Case

**webapp MDS incorrect repair**: Renaming a duplicate function without
consolidating the body does not resolve the MDS finding.  Drift detects
structural duplication via function body hashes, not names.  The
identical body in both files still triggers detection.  This proves
that verification is not trivially satisfiable.

## Reproduction

```bash
# From repo root, with drift installed:
python scripts/repair_benchmark.py --json

# Output: benchmark_results/repair/summary.json
```

No network access required — all repos are created synthetically.
Deterministic: same drift version → same results.

## Output Format

`summary.json` follows the repository's benchmark conventions:

```json
{
  "_metadata": { "drift_version": "...", "generated_at": "...", ... },
  "repos": {
    "webapp": {
      "baseline": { "drift_score": 0.195, "signal_breakdown": {...}, ... },
      "task_quality": { "quality_score": 1.0, ... },
      "task_complexity": { "distribution": {"moderate": 3, ...}, ... },
      "determinism": { "runs": 3, "identical": true, ... },
      "repairs": [ {
        "verification": "PASS", "drift_score_delta": -0.029,
        "diff_stats": { "files_changed": 3, "total_diff_lines": 28 },
        "per_signal_deltas": { "mutant_duplicate": { "score_delta": -0.05, ... } }
      } ],
      "failure_cases": [ { "verification": "PASS", "failure_analysis": "..." } ]
    }
  },
  "summary": {
    "verification_metrics": { "false_acceptance_rate": 0, "false_rejection_rate": 0, ... },
    "signal_coverage": { "mutant_duplicate": {...}, "explainability_deficit": {...} },
    "determinism": { "all_repos_deterministic": true, "runs_per_repo": 3 },
    "effort_metrics": { "median_diff_lines": 28, ... },
    "claim_boundary": { "proven": [...], "not_yet_proven": [...] }
  }
}
```

## Next Steps (highest ROI)

1. **Real-world verified repairs**: Run tasks on 2–3 OSS targets, not just task generation
2. **Control group**: Same tasks + agent, with vs. without Drift verification
3. **Signal coverage**: Add verified repairs for AVS, TVS, SMS (3 remaining)
4. **Increase sample size**: n≥10 per class for statistically robust FAR/FRR

## Files

| File | Purpose |
|------|---------|
| `scripts/repair_benchmark.py` | Main benchmark + reproduction script |
| `scripts/_repair_repos.py` | Synthetic repo builders and repair functions |
| `benchmark_results/repair/summary.json` | Full results |
| `benchmark_results/repair/README.md` | This file |
| `benchmark_results/repair/decisions.md` | Design decisions |
