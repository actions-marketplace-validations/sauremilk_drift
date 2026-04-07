# Case Study: FastAPI

**Repository:** [fastapi/fastapi](https://github.com/fastapi/fastapi)
**Stats:** 1,118 files, 4,554 functions
**Drift Score:** 0.690 (HIGH) | **Time:** 2.3s

!!! note "Scope note"
    These numbers reflect a full-clone analysis (all branches and test files included). The [Comparisons](../comparisons/index.md) page uses a `src/`-only shallow-clone scope, which reports 664 files, score 0.624, and 13.1 s for the same repository.

## Key Findings

### 499 Near-Duplicate Test Functions (MDS 0.85)

FastAPI's test suite contains hundreds of structurally identical test functions that differ only in the model name: `test_read_items()`, `test_read_users()`, `test_read_events()` share identical assertion structures.

This is the classic "mutant duplicate" pattern — code that was likely copied and minimally adapted rather than abstracted into a parameterized test fixture.

### 4 Error-Handling Patterns in Route Modules (PFS)

The Pattern Fragmentation Signal found 4 distinct approaches to error handling across route modules — try/except with re-raise, bare except with logging, HTTPException wrapping, and direct return.

## Interpretation

Even well-maintained frameworks accumulate structural debt at scale. These findings don't indicate bugs — they indicate inconsistency that makes the codebase harder to modify safely.

**Recommendation:** Parameterized test fixtures (`@pytest.mark.parametrize`) could reduce the test duplication. A shared error-handling utility could unify the route patterns.
