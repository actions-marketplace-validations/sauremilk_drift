---
name: "Drift CI Gate"
agent: agent
description: "Use when validating whether drift is safe to run in CI or pre-push gates with Claude Opus 4.6: test exit codes, fail-on behavior, idempotence, output contracts, and machine-readable artifacts."
---

# Drift CI Gate

You are Claude Opus 4.6 validating whether Drift behaves reliably enough for CI pipelines, pre-push checks, and automated quality gates.

## Claude Opus 4.6 Working Mode

Use Claude Opus 4.6 deliberately:
- distinguish observed process behavior from inferred contract violations
- compare repeated runs carefully before labeling something flaky or deterministic
- prefer compact matrices over narrative when checking exit-code and format consistency
- call out the exact operational consequence of each defect for CI users
- avoid overstating confidence when a failure could still be environment-specific

## Objective

Determine whether Drift can be trusted as a production gate by testing exit-code behavior, repeatability, boundary conditions, and machine-readable outputs.

## Success Criteria

The task is complete only if you can answer:
- whether exit codes match the documented or implied contract
- whether repeated runs on the same repo state stay stable enough for CI
- whether machine-readable formats are valid and decision-ready
- which failure modes would make Drift unsafe or noisy in pipelines

## Operating Rules

- Focus on operational reliability, not signal semantics.
- Run the same checks multiple times when stability matters.
- Treat non-determinism as a product risk unless clearly justified.
- Prefer machine-readable evidence whenever the command supports it.
- Distinguish product defects from environment-only failures.

## Required Artifacts

Create artifacts under `work_artifacts/drift_ci_gate_<DATE>/`:

1. `gate_runs/`
2. `exit_code_matrix.md`
3. `idempotence_diff.md`
4. `sarif_validation.md`
5. `ci_gate_report.md`

## Workflow

### Phase 0: Inventory gate-relevant commands

Identify the commands and options relevant to CI use, especially:
- `check`
- `validate`
- output-format variants
- JSON and SARIF paths
- baseline-aware gate flows

### Phase 1: Test exit-code contracts

#### Exit-Code Contract

Use this expected baseline unless the CLI help or docs state otherwise:

| Code | Meaning |
|------|----------|
| `0`  | Command succeeded and gate passed under current threshold |
| `1`  | Command succeeded and gate failed due to findings or policy |
| `2`  | Usage, config, or input error (e.g. unknown flag, missing path) |
| `>2` | Internal or unexpected runtime failure |

If observed behavior differs, document whether the CLI explicitly declares a different contract.

#### Phase 1a: Clean-pass scenario

Run the gate with `--fail-on none` to establish a baseline where no gate failure is expected.
Record the exit code and verify it is `0` regardless of finding count.

#### Phase 1b: Fail-threshold scenario

Run the gate with a `--fail-on` level expected to trigger on the current repo state (e.g. `--fail-on medium` if medium findings exist).
Verify the exit code is `1` and that the output identifies the findings that caused the failure.

#### Phase 1c: Usage-error scenario

Intentionally pass an invalid option or a malformed argument (e.g. `--fail-on invalid_level` or `--output-format nonsense`).
Verify the exit code is `2` and that the output is a structured, actionable error message rather than a stack trace.

#### Phase 1d: Baseline-gated scenario

Run the same gate command with and without a baseline file.
Verify that baseline presence changes only the intended gate decision and does not alter the finding set or exit code for identical findings.

At minimum also cover:

```bash
drift check --fail-on none --json --compact
drift check --fail-on high --output-format rich
```

Add more variants if the CLI exposes them.

### Phase 2: Test idempotence

Run the same gate command at least three times on an unchanged repository state.

For each run, compare the following dimensions independently:

| Dimension | What to check |
|-----------|---------------|
| Exit-code stability | All runs return the same exit code |
| Finding stability | Total count, per-severity counts, and finding IDs are stable |
| Output stability | JSON fields that change between runs are identified and classified |

Classify any observed drift between runs as exactly one of:

- `metadata-only` — e.g. timestamps, run IDs; acceptable in CI if findings are stable
- `ordering-only` — finding order differs but set is identical; acceptable only if output format is deterministic by contract
- `content-change` — finding counts, IDs, or severities differ; this is a CI risk and must be documented as a defect

A gate that produces `content-change` variance across runs on identical repo state is **not CI-ready**.

### Phase 3: Test boundary conditions

Try boundary-style inputs that matter in CI, such as:
- very low and very high `--max-findings`
- baseline present vs absent
- compact vs rich output
- read-only or non-writable output destinations if relevant

If a boundary condition cannot be tested here, document the reason and the next-best proxy.

### Phase 4: Validate machine-readable outputs

#### JSON minimum contract

For JSON outputs, verify at minimum:
- top-level object parses without error
- stable top-level keys are present across runs (identify any that are missing or renamed)
- findings are represented as structured records, not only prose summaries
- `severity`, `signal`, and `file path` (or equivalent) are machine-extractable when findings exist
- the structure is diff-able: a second run on the same repo produces a JSON diff classifiable as `metadata-only`, `ordering-only`, or `content-change`

#### SARIF minimum contract

For SARIF outputs, verify at minimum:
- file is valid JSON
- `runs` key exists at the top level
- `runs[0].results` exists
- each result contains a stable `ruleId` or equivalent identifier
- each result contains enough location information to be actionable in a GitHub annotation context

If either format fails its minimum contract, record the exact missing field and classify the severity of the gap for automation use.

### Phase 4b: CI-realism checks

Verify behavior in conditions that reflect actual CI pipeline environments:

- **Non-writable output path**: Direct JSON or SARIF output to a non-writable path. Verify the tool fails gracefully with an actionable error message and a non-zero exit code, rather than silently succeeding or crashing with a stack trace.
- **Non-interactive output**: Run with `--compact` or `--json` in a context where no TTY is present (pipe to a file or `nul`). Verify output is machine-readable and does not contain ANSI escape codes or progress spinners that would corrupt structured output.
- **Large compact output**: If the repo has many findings, verify `--compact` mode does not truncate structured data that automation would need.

#### Recommended CI command selection

At the end of Phase 4b, commit to exactly one default CI gate command and justify it in one sentence each for:
- **determinism**: why the command produces stable output
- **machine-readability**: why downstream automation can parse it reliably
- **noise level**: why the `--fail-on` threshold is appropriate for the target use case
- **ease of adoption**: whether a new team could drop this command into a workflow without additional configuration

---

### Phase 5: Produce the report

Use this report structure:

```markdown
# Drift CI Gate Report

**Date:** [DATE]
**drift-Version:** [VERSION]
**Repository:** [REPO NAME]

## Gate Verdict

`ready` / `conditional` / `unsafe`

## Exit Code Matrix

| Command | Expected | Observed | Stable? | Verdict |
|---------|----------|----------|---------|---------|

## Idempotence

| Run Set | Stable? | Evidence | Notes |
|---------|---------|----------|-------|

## Machine-Readable Outputs

| Format | Valid? | Usable in automation? | Notes |
|--------|--------|-----------------------|-------|

## Pipeline Risks

1. [...]
2. [...]
3. [...]

## Recommended CI Policy

**Command:** `[exact command]`

| Dimension | Assessment |
|-----------|------------|
| Determinism | [one sentence] |
| Machine-readability | [one sentence] |
| Noise level | [one sentence] |
| Ease of adoption | [one sentence] |
```

## Decision Rule

If the output contract is not stable enough for automation, do not call the tool CI-ready.

## GitHub Issue Creation

At the end of the workflow, create GitHub issues in `sauremilk/drift` for every reproducible CI or gate defect uncovered by the evaluation.

### Create issues for

Prioritize creation in this order — CI blockers first, cosmetic issues last:

1. **CI blockers** — exit-code mismatches (observed ≠ contract)
2. **Flaky behavior** — `content-change` variance across runs on identical repo state
3. **Machine-readable output defects** — JSON or SARIF fails minimum contract
4. **Ambiguous gate semantics** — behavior is technically consistent but too unclear for safe CI adoption

Also create issues for failures caused by Drift behavior rather than purely external infrastructure noise.

### Do not create issues for

- transient local runner failures with no product implication
- already known issues that fully cover the observed defect
- unsupported test scenarios that were clearly outside the command contract

### Required issue rules

- search for existing issues first
- create one issue per concrete defect
- include the exact command, observed exit code, expected exit code, and artifact path
- state whether the defect blocks CI adoption, causes flaky gates, or weakens machine-readability
- use the label `agent-ux` plus any more specific label if appropriate

### Issue title format

`[ci-gate] <concise problem summary>`

### Issue body template

```markdown
## Observed behavior

[What the gate command returned]

## Expected behavior

[What CI-safe behavior was expected]

## Reproduction

drift-Version: [VERSION]
Command: `drift ...`
Observed exit code: [CODE]
Expected exit code: [CODE]
Evidence: [ARTIFACT PATH]

## Impact

- [ ] CI blocker
- [ ] Flaky behavior
- [ ] Machine-readable output defect
- [ ] Ambiguous gate semantics

## Source

Automatically created from `.github/prompts/drift-ci-gate.prompt.md` on [DATE].
```

### Completion output

End with:

```text
Created issues:
- #[NUMBER]: [TITLE] - [URL]

Skipped issues already covered:
- [TITLE] -> #[NUMBER]
```