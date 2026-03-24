# Quick Start

> Repo: `sauremilk/drift` · Package: `drift-analyzer` · Command: `drift`

## 0. Before you try it

```bash
python --version
```

Drift currently requires Python 3.11+. If your shell or CI runner is still on 3.10, fix that first so the first run is a signal test, not an environment failure.

## 1. Install

```bash
pip install drift-analyzer    # requires Python 3.11+
```

## 2. Analyze your repository

```bash
cd /path/to/your/project
drift analyze --repo .
```

## 3. What you'll see

```text
╭─ drift analyze  myproject/ ──────────────────────────────────────────────────╮
│  DRIFT SCORE  0.52  │  87 files  │  412 functions  │  AI: 34%  │  2.1s      │
╰──────────────────────────────────────────────────────────────────────────────╯

┌──┬────────┬───────┬──────────────────────────────────────┬──────────────────────┐
│  │ Signal │ Score │ Title                                │ Location             │
├──┼────────┼───────┼──────────────────────────────────────┼──────────────────────┤
│◉ │ PFS    │  0.85 │ Error handling split 4 ways          │ src/api/routes.py:42 │
│◉ │ AVS    │  0.72 │ DB import in API layer               │ src/api/auth.py:18   │
│○ │ MDS    │  0.61 │ 3 near-identical validators          │ src/utils/valid.py   │
└──┴────────┴───────┴──────────────────────────────────────┴──────────────────────┘
```

## 4. How to read your first findings

- **Score ≥ 0.7** → strong signal, likely a real structural issue worth investigating
- **Score 0.4–0.7** → moderate signal, review when you touch that module
- **Score < 0.4** → weak signal, likely noise in small repos — skip for now

Each finding links to a specific file and line. Start with the highest-scored findings and check if the pattern matches your understanding of the codebase.

Typical first-run decisions:

- **You see repeated pattern variants in one module** → standardize on one implementation shape before adding more features there.
- **You see a boundary violation at a stable layer edge** → add or tighten an architecture rule before it spreads.
- **You mostly see weak findings in a small repo** → keep drift in observation mode and revisit after the codebase grows.

## 5. Verify your installation

Drift can analyze its own codebase — useful to confirm everything works:

```bash
drift self
```

## Next: add to CI

The recommended first step is report-only CI (no build failures):

```bash
drift check --fail-on none    # report findings, never exit 1
```

The GitHub Action now follows the same safe default. Tighten to `high` only after the team has reviewed a few real runs.

See [Team Rollout](team-rollout.md) for the full progressive adoption path.

## Other commands

```bash
# Machine-readable JSON
drift analyze --format json

# GitHub Code Scanning (SARIF)
drift analyze --format sarif

# Track drift score over time
drift trend --last 90

# Root-cause analysis per module
drift timeline --repo . --since 90
```
