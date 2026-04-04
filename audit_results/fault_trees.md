# Fault Tree Analysis

## 2026-04-04 - MCP stdio deadlock hardening on Windows

### FT-1: Tool call blocks on subprocess stdin inheritance
- Top event: MCP tool call does not return when child process is spawned.
- Branch A: Tool path invokes `subprocess.run(...)` without explicit stdin handling.
- Branch B: Child process inherits stdio handle from MCP server transport.
- Branch C: Windows IOCP path enters blocking state and call never completes.
- Mitigation implemented: Explicit `stdin=subprocess.DEVNULL` in affected subprocess paths plus regression test to prevent omissions.

### FT-2: Threaded first import deadlock with C-extension modules
- Top event: MCP request hangs during `asyncio.to_thread` execution.
- Branch A: Heavy module import (for example numpy/torch/faiss) occurs first time inside worker thread.
- Branch B: Event loop already owns IOCP resources.
- Branch C: DLL loader lock contention causes deadlock.
- Mitigation implemented: `_eager_imports()` called before `mcp.run()` so heavy imports happen before threaded tool execution.

## 2026-04-03 - PFS/NBV low-actionability output paths (Issue #125)

### FT-1: PFS remediation cannot be applied directly
- Top event: Agent receives PFS finding but cannot perform a targeted refactor.
- Branch A: Dominant pattern named but not exemplified.
- Branch B: Deviating locations do not include stable line-level anchors.
- Branch C: Context window does not include the relevant source bodies.
- Mitigation implemented: PFS fix embeds canonical exemplar `file:line` and concrete deviation refs.

### FT-2: NBV remediation path is ambiguous
- Top event: Agent applies wrong fix (rename vs behavior) for naming-contract finding.
- Branch A: Rule semantics (`validate_`, `ensure_`, `is_`) not reflected in suggestion.
- Branch B: No concrete location anchor to patch first.
- Branch C: Generic wording interpreted inconsistently by different agents.
- Mitigation implemented: NBV fix uses prefix-specific suggestion plus `file:line` location.

## 2026-07-18 - Security audit: test-file FP in PFS/AVS/MDS

### FT-1: False Positive from test files bypassing exclude patterns
- Top event: PFS/AVS/MDS produce findings on test files when user overrides default exclude.
- Branch A: User removes `**/tests/**` from exclude list in drift.yaml.
- Branch B: Signals iterate all parse_results without checking is_test_file().
- Branch C: Test file patterns/imports/duplicates generate false findings.
- Mitigation implemented: Defense-in-depth is_test_file() check in each signal's analyze() method.

### FT-2: File discovery crash on broken FS entries
- Top event: discover_files() raises unhandled OSError on inaccessible paths.
- Branch A: glob() encounters permission-denied or broken symlink targets.
- Branch B: stat() fails on locked/deleted file between enumeration and access.
- Mitigation implemented: try/except OSError around glob(), is_file()/is_symlink(), and stat() calls.

## 2026-04-03 - DIA FP cluster for markdown slash tokens (Issue #121)

### FT-1: False Positive escalation in Doc-Implementation Drift
- Top event: README/ADR missing-directory findings are noisy and misleading.
- Branch A: Directory-like token extracted from plain prose.
- Branch B: Token has no structural context (not backticked, no directory/folder/path semantics nearby).
- Branch C: Repository has no corresponding directory, causing DIA finding emission.
- Mitigation implemented: Gate extraction by structural context and preserve explicit code-span path mentions.

### FT-2: False Negative risk after FP mitigation
- Top event: Legitimate plain-prose directory mention is ignored.
- Branch A: Mention not backticked.
- Branch B: Structural cue absent from local context window.
- Mitigation implemented: Add keyword-based structural context and targeted tests for positive prose context.
