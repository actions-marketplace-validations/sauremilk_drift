# Workflows overview

This repository currently uses multiple focused workflows instead of one monolithic pipeline.
The table below documents purpose and when to look at each workflow.

| Workflow | Primary purpose | Typical trigger |
|---|---|---|
| ci.yml | Core quality gate (lint, types, tests, drift self-check) | push, pull_request |
| release.yml | Semantic release automation and PyPI publish | push to main, manual dispatch |
| docs.yml | Documentation build/deploy checks | docs-related updates |
| codeql.yml | Code scanning and security analysis | scheduled / push / pull_request |
| dependency-review.yml | Dependency risk review on PRs | pull_request |
| security-hygiene.yml | Security hygiene checks | scheduled / manual |
| validate-release.yml | Release metadata/process validation | release-related changes |
| publish.yml | Manual/auxiliary publish path | manual dispatch |
| install-smoke.yml | Package install smoke test | scheduled / manual |
| package-kpis.yml | Package-level KPI generation | scheduled |
| repo-guard.yml | Repository policy/guardrail checks | push, pull_request |
| workflow-sanity.yml | Validate workflow consistency | workflow file changes |
| welcome.yml | First-time contributor greeting | issues, pull requests |
| stale.yml | Mark stale issues and pull requests | scheduled |
| labeler.yml | Auto-label pull requests | pull_request_target |

## Why not collapse immediately?

Several workflows have different permissions, schedules, and trust boundaries.
A direct merge into 3-5 files can accidentally weaken security boundaries or break release reliability.

## Consolidation path

If consolidation is desired, do it in phases:
1. Merge low-risk maintenance workflows first (for example repo-guard + workflow-sanity).
2. Keep release/publish and security workflows isolated.
3. Re-measure runtime and failure modes before further merges.
