# Signal Reference

Drift measures 6 active detection signals, each targeting a different dimension of architectural erosion, plus 4 report-only signals that surface consistency patterns without affecting the composite score.

## Active Signals

### Pattern Fragmentation (PFS)

**What it detects:** Same category of pattern implemented N different ways within one module.

**Example:** Error handling split across try/except, bare except, logging-only, and re-raise patterns in the same API module.

**Score:** `1 - (1 / num_variants)` — 4 variants → 0.75 (HIGH)

### Architecture Violations (AVS)

**What it detects:** Imports that cross layer boundaries or create circular dependencies.

**Example:** A database model importing from an API route handler.

**Techniques:** Import graph analysis, layer inference, hub dampening, Tarjan SCC.

### Mutant Duplicates (MDS)

**What it detects:** Near-identical functions that diverge in subtle ways.

**Example:** `validate_user()` and `validate_admin()` sharing 90% identical AST structure.

**Techniques:** AST n-gram Jaccard similarity, LOC bucketing, optional FAISS embeddings.

### Explainability Deficit (EDS)

**What it detects:** Complex functions lacking docstrings, tests, or type annotations.

**Focus:** Especially flags AI-attributed functions (from git blame heuristics).

### Temporal Volatility (TVS)

**What it detects:** Files with anomalous change frequency, author diversity, or defect correlation.

**Techniques:** Statistical z-score on commit frequency, author entropy.

### System Misalignment (SMS)

**What it detects:** Recently introduced imports or patterns foreign to their target module.

**Example:** A utility module suddenly importing from an HTTP client library.

## Phase 2 Signals (Report-Only)

### Doc-Implementation Drift (DIA)

**What it detects:** Documented architecture that no longer matches actual code.

**Status:** Reported by default, but excluded from the composite score (weight 0.0) until extraction precision improves.

### Broad Exception Monoculture (BEM)

**What it detects:** Modules where exception handling is uniformly broad (bare except, catch-all Exception) with high swallowing ratios.

**Status:** Report-only (weight 0.0). See [ADR-007](https://github.com/sauremilk/drift/blob/main/docs/adr/007-consistency-proxy-signals.md).

### Test Polarity Deficit (TPD)

**What it detects:** Test suites with near-zero negative assertions — only happy-path testing, no failure-path coverage.

**Status:** Report-only (weight 0.0). See [ADR-007](https://github.com/sauremilk/drift/blob/main/docs/adr/007-consistency-proxy-signals.md).

### Guard Clause Deficit (GCD)

**What it detects:** Modules where public functions uniformly lack early guard clauses (parameter validation, precondition checks).

**Status:** Report-only (weight 0.0). See [ADR-007](https://github.com/sauremilk/drift/blob/main/docs/adr/007-consistency-proxy-signals.md).
