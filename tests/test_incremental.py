"""Tests for Phase 2 incremental analysis foundation.

Covers ``SignalCache.content_hash_for_file`` and ``BaselineSnapshot``.
"""

from __future__ import annotations

import time

import pytest

from drift.cache import SignalCache
from drift.incremental import BaselineSnapshot  # noqa: I001

# ---------------------------------------------------------------------------
# SignalCache.content_hash_for_file
# ---------------------------------------------------------------------------


class TestContentHashForFile:
    def test_returns_file_hash_unchanged(self) -> None:
        file_hash = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        assert SignalCache.content_hash_for_file(file_hash) == file_hash

    def test_different_hashes_produce_different_keys(self) -> None:
        h1 = "aaaa" * 8
        h2 = "bbbb" * 8
        assert SignalCache.content_hash_for_file(h1) != SignalCache.content_hash_for_file(h2)


# ---------------------------------------------------------------------------
# BaselineSnapshot
# ---------------------------------------------------------------------------


class TestBaselineSnapshot:
    @pytest.fixture()
    def baseline_hashes(self) -> dict[str, str]:
        return {
            "src/a.py": "aaa1",
            "src/b.py": "bbb2",
            "src/c.py": "ccc3",
        }

    def test_is_valid_within_ttl(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(file_hashes=baseline_hashes, ttl_seconds=60)
        assert snap.is_valid()

    def test_is_valid_expired(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(
            file_hashes=baseline_hashes,
            created_at=time.time() - 1000,
            ttl_seconds=60,
        )
        assert not snap.is_valid()

    def test_changed_files_no_changes(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(file_hashes=baseline_hashes)
        added, removed, modified = snap.changed_files(baseline_hashes)
        assert added == set()
        assert removed == set()
        assert modified == set()

    def test_changed_files_added(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(file_hashes=baseline_hashes)
        current = {**baseline_hashes, "src/d.py": "ddd4"}
        added, removed, modified = snap.changed_files(current)
        assert added == {"src/d.py"}
        assert removed == set()
        assert modified == set()

    def test_changed_files_removed(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(file_hashes=baseline_hashes)
        current = {"src/a.py": "aaa1", "src/b.py": "bbb2"}
        added, removed, modified = snap.changed_files(current)
        assert added == set()
        assert removed == {"src/c.py"}
        assert modified == set()

    def test_changed_files_modified(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(file_hashes=baseline_hashes)
        current = {**baseline_hashes, "src/b.py": "xxx9"}
        added, removed, modified = snap.changed_files(current)
        assert added == set()
        assert removed == set()
        assert modified == {"src/b.py"}

    def test_changed_files_mixed(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(file_hashes=baseline_hashes)
        current = {
            "src/a.py": "aaa1",  # unchanged
            # src/b.py removed
            "src/c.py": "zzz0",  # modified
            "src/new.py": "nnn1",  # added
        }
        added, removed, modified = snap.changed_files(current)
        assert added == {"src/new.py"}
        assert removed == {"src/b.py"}
        assert modified == {"src/c.py"}

    def test_all_changed_union(self, baseline_hashes: dict[str, str]) -> None:
        snap = BaselineSnapshot(file_hashes=baseline_hashes)
        current = {
            "src/a.py": "aaa1",
            "src/c.py": "zzz0",
            "src/new.py": "nnn1",
        }
        result = snap.all_changed(current)
        assert result == {"src/b.py", "src/c.py", "src/new.py"}

    def test_stores_score(self) -> None:
        snap = BaselineSnapshot(file_hashes={}, score=0.42)
        assert snap.score == 0.42

    def test_default_ttl(self) -> None:
        snap = BaselineSnapshot(file_hashes={})
        assert snap.ttl_seconds == 900

    def test_empty_baseline_vs_populated_current(self) -> None:
        snap = BaselineSnapshot(file_hashes={})
        current = {"a.py": "hash1", "b.py": "hash2"}
        added, removed, modified = snap.changed_files(current)
        assert added == {"a.py", "b.py"}
        assert removed == set()
        assert modified == set()
