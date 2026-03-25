# Scoring Model

## Composite Drift Score

Individual signal scores are combined into a weighted composite:

$$\text{Score} = \frac{\sum (\text{signal\_weight} \times \text{signal\_score})}{\sum \text{weights}}$$

## Count Dampening

Logarithmic dampening prevents signals with many low-confidence findings from dominating:

$$\text{signal\_score} = \overline{s} \times \min\!\left(1,\; \frac{\ln(1 + n)}{\ln(1 + k)}\right)$$

- $\overline{s}$ = mean finding score
- $n$ = finding count
- $k$ = dampening constant (default: 10)

**Effect:** 1 finding at 0.5 → dampened to 0.27. 15 findings at 0.5 → full 0.5.

## Default Weights

| Signal | Weight | Rationale |
|---|---|---|
| Pattern Fragmentation (PFS) | 0.22 | Highest ablation-study impact on F1 |
| Architecture Violation (AVS) | 0.22 | Critical for maintainability |
| Mutant Duplicate (MDS) | 0.17 | Common AI pattern |
| Temporal Volatility (TVS) | 0.17 | Predictive of future bugs |
| Explainability Deficit (EDS) | 0.12 | Important but noisy |
| System Misalignment (SMS) | 0.10 | Newest signal, still calibrating |

Weights are calibrated via ablation study: remove each signal, measure F1 delta, assign proportional weight. See [ADR-003](https://github.com/sauremilk/drift/blob/master/docs/adr/003-composite-scoring-model.md).

## Report-Only Signals (Weight 0.00)

| Signal | Weight | Status |
|---|---|---|
| Doc-Implementation Drift (DIA) | 0.00 | Report-only |
| Broad Exception Monoculture (BEM) | 0.00 | Report-only |
| Test Polarity Deficit (TPD) | 0.00 | Report-only |
| Guard Clause Deficit (GCD) | 0.00 | Report-only |

These signals appear in analysis output but do not affect the composite score. See [ADR-007](https://github.com/sauremilk/drift/blob/master/docs/adr/007-consistency-proxy-signals.md) for BEM/TPD/GCD rationale.

## Severity Mapping

| Score Range | Severity |
|---|---|
| ≥ 0.70 | CRITICAL |
| 0.50–0.70 | HIGH |
| 0.30–0.50 | MEDIUM |
| < 0.30 | LOW |

## Module-Level Scoring

Findings are grouped by module path. Each module receives:

- Per-signal scores
- Composite score
- AI attribution ratio (% findings from AI-generated code)
- Top signal identifier
