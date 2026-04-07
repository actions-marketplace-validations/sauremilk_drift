---
name: drift-commit-push
description: "Drift-specific git commit and push workflow. Use when preparing commits, choosing conventional commit messages, checking pre-push gates, or deciding whether a push to main is allowed. Keywords: commit, push, git push, conventional commit, pre-push, changelog, risk audit, hooks."
argument-hint: "Describe what changed and whether you need commit help, push readiness, or both."
---

# Drift Commit And Push Skill

Use this skill for repository-safe commit and push workflows in Drift.

## When To Use

- Prepare a commit after code changes
- Choose the correct conventional commit type
- Check whether a push is allowed
- Verify pre-push gates before pushing to `main`
- Decide which supporting artifacts must be updated with the code change

## Core Rules

1. **Do not push autonomously.** A push requires explicit maintainer approval.
2. **Never commit blocked paths.** Anything under `tagesplanung/` is excluded from pushes.
3. **Use conventional commits.** Release automation depends on `feat:`, `fix:`, and `BREAKING:` semantics.
4. **Run validation before commit and again before push when relevant.**
5. **Do not bypass hooks by default.** Environment-variable bypasses are emergency-only and must be justified.

## Step 1: Classify The Change

Choose the commit type from the actual impact:

- `fix:` for bug fixes and regressions
- `feat:` for new user-visible capabilities
- `refactor:` for internal restructuring without behavior change
- `docs:` for documentation-only changes
- `test:` for tests-only changes
- `chore:` for maintenance work
- `BREAKING:` or a `BREAKING CHANGE:` footer for incompatible changes

If the change touches signals, scoring, output formats, or architecture boundaries, stop and verify whether an ADR and risk-audit updates are required before committing.

## Step 2: Inspect The Working Tree

Review exactly what will be committed:

```bash
git status --short
git diff --stat
git diff
```

Check for unrelated files and leave them out of the commit.

## Step 3: Satisfy Change-Coupled Requirements

Apply the repository gates before pushing, and usually before committing if they affect the same logical change:

- `src/drift/signals/`, `src/drift/ingestion/`, or `src/drift/output/` changed:
  update at least one required audit artifact in `audit_results/`, and keep all four audit files present.
- `feat:` commit planned:
  include tests, a versioned evidence file in `benchmark_results/`, and update `docs/STUDY.md` if it exists.
- `feat:` or `fix:` commit planned:
  include a `CHANGELOG.md` update in the same push.
- `pyproject.toml` changed:
  ensure `uv.lock` is updated too.
- New public function under `src/drift/`:
  add a docstring in the same diff.

## Step 4: Run Validation

Minimum expectation before commit:

```bash
make test-fast
```

Before push, the repository standard is:

```bash
make check
```

If the change is narrowly scoped and a faster targeted check is used first, do not treat that as a substitute for the required pre-push validation.

## Step 5: Create The Commit

Stage only the intended files:

```bash
git add <paths>
git commit -m "fix: concise summary"
```

Good commit subjects are:

- specific
- outcome-oriented
- scoped to one logical change

Examples:

```text
fix: prevent detached release tag lineage regressions
feat: add evidence gate for feature pushes
docs: clarify pre-push audit requirements
```

## Step 6: Evaluate Push Readiness

Before any push, confirm all of the following:

- explicit maintainer approval to push exists
- no blocked paths are included
- the relevant pre-push gates are satisfied
- `make check` is green
- the branch and target are intentional

Useful checks:

```bash
git diff --name-only origin/main HEAD
git log --oneline origin/main..HEAD
```

## Step 7: Push Only With Approval

If and only if approval exists:

```bash
git push origin main
```

Do not use bypasses like `DRIFT_SKIP_HOOKS=1` unless the maintainer explicitly requests an emergency override and the reason is documented.

## Review Checklist

- [ ] Commit type matches actual change impact
- [ ] Only intended files are staged
- [ ] Drift Policy Gate was satisfied for the underlying task
- [ ] Required artifacts changed together with the code
- [ ] Validation was run at the appropriate level
- [ ] Push approval was explicitly granted before pushing

## References

- `.github/copilot-instructions.md`
- `.github/instructions/drift-policy.instructions.md`
- `.github/instructions/drift-push-gates.instructions.md`
- `.github/instructions/drift-quality-workflow.instructions.md`