# Changelog

All notable changes to drift-analyzer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] – 2026-03-19

### Changed

- **DIA signal**: Replaced regex-based Markdown parsing with mistune AST parser. Link URLs are now skipped entirely, eliminating false positives from GitHub badges, CI links, and package registry URLs. Added URL-segment blacklist (~80 entries). Strict precision improved from 48% → 59% (+12pp), false positives reduced from 31 → 6 (−81%).
- **AVS signal**: Added Omnilayer recognition for cross-cutting directories (config/, utils/, types/, common/, shared/, etc.) — these no longer generate layer-violation findings. Hub-module dampening via NetworkX in-degree centrality (90th percentile cutoff, ×0.3 score dampening). Optional embedding-based layer inference for ambiguous modules.
- **MDS signal**: Hybrid similarity scoring (0.6 × AST Jaccard + 0.4 × cosine embedding similarity). Phase 3 semantic duplicate search via FAISS index catches renamed-variable duplicates that structural comparison alone misses.
- **Overall precision**: 80% → 85% strict (+5pp) across 269 classified findings on 5 repositories.

### Added

- `drift.embeddings` module: Central embedding service with lazy model loading (all-MiniLM-L6-v2), cosine similarity, FAISS index builder, disk-backed `EmbeddingCache`. Fully optional — all signals degrade gracefully without embedding dependencies.
- CLI flags: `--no-embeddings` (disable embedding features), `--embedding-model` (override model name). Available on both `analyze` and `check` commands.
- Config fields: `embeddings_enabled`, `embedding_model`, `embedding_batch_size`, `allowed_cross_layer` (policy patterns for AVS).
- Optional dependency group `[markdown]` for `mistune>=3.0`. DIA signal falls back to regex extraction when mistune is not installed.
- 36 new unit tests: `test_embeddings.py` (10), `test_avs_enhanced.py` (13), `test_dia_enhanced.py` (13).

### Fixed

- DIA: Badge/CI URL fragments (e.g., `actions/`, `workflows/`, `blob/`) no longer reported as missing directories.
- AVS: Findings below score 0.15 filtered out (reduces noise from ambiguous cross-layer references).
- Embedding cosine similarity: Normalized with L2 norm (was using raw dot product).

## [0.1.0] – 2026-02-15

Initial release with 7 detection signals: PFS, AVS, MDS, EDS, TVS, SMS, DIA.

- 80% strict precision on 291 classified findings across 5 repositories
- 86% recall on 14 controlled mutations
- CLI commands: `analyze`, `check`, `self`, `trend`, `timeline`, `patterns`, `badge`
- Output formats: rich (terminal), JSON, SARIF (GitHub Code Scanning)
- GitHub Actions integration via `drift-check.yml` template
