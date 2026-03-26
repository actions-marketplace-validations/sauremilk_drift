# Stability and Release Status

This page explains why drift still presents itself as Alpha in package metadata even though parts of the product are already stable enough for real use.

The short version: the core Python path is stronger than the broadest product surface. The release label should reflect that difference instead of hiding it.

## Current release posture

Drift currently keeps the PyPI classifier:

`Development Status :: 3 - Alpha`

This is intentional.

It signals that users should expect mixed maturity across the total surface area, even though the primary path is already much more stable than the label alone might suggest.

## Stability matrix

| Area | Status | Interpretation |
|---|---|---|
| Core Python analysis | Stable | This is the primary product path. It has the strongest validation, the clearest CLI workflow, and the most credible production-adjacent use today. |
| CI and SARIF workflow | Stable | Teams can adopt drift safely in report-only mode and then tighten enforcement gradually. |
| TypeScript support | Experimental | Useful for early adoption and exploration, but not yet positioned as equally mature with Python support. |
| Embeddings-based parts | Optional / experimental | These are outside the deterministic core path and should not be treated as baseline functionality. |
| Benchmark methodology | Evolving | Public, reproducible, and good enough to support conservative claims, but still improving in replication depth, sampling, and interpretation rigor. |

## Why Alpha is still the honest label

Alpha does not mean "nothing works." In drift's case it means:

- the core workflow is ahead of the broadest feature envelope
- some optional or secondary surfaces are still experimental
- benchmark interpretation should remain conservative and signal-specific
- the project would rather under-claim than over-claim

That is a credibility choice, not an apology.

## What users can rely on today

Users can treat these areas as the most production-near parts of drift:

- deterministic core analysis for Python repositories
- local CLI usage
- report-only CI rollout
- SARIF and JSON outputs for review workflows
- signal-by-signal interpretation backed by public artifacts

Users should treat these areas more cautiously:

- TypeScript support beyond early adoption scenarios
- embeddings-based or optional advanced paths
- broad benchmark conclusions applied unchanged to every repository shape

## What would justify a move toward Beta

Moving toward Beta should follow evidence, not tone. A Beta classifier becomes justified when the project can defend these claims simultaneously:

1. the primary Python path remains consistently reliable across more repositories and over time
2. the user-facing workflow is stable enough that rollout guidance changes little between releases
3. optional and experimental areas are clearly separated from the baseline experience
4. benchmark methodology has stronger replication and clearer confidence communication

Until then, Alpha with an explicit stability matrix is the more credible posture.

## Related pages

- [Trust and Evidence](trust-evidence.md)
- [Benchmarking and Trust](benchmarking.md)
- [FAQ](faq.md)