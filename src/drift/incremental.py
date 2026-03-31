"""Incremental analysis foundation for Drift.

Provides ``BaselineSnapshot`` — a lightweight checkpoint of analysis state
that enables efficient re-analysis of only changed files between full scans.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class BaselineSnapshot:
    """Immutable snapshot of file hashes captured after a full scan.

    The snapshot tracks which files existed and their content hashes so
    that a subsequent incremental run can determine the minimal set of
    files that actually changed.

    Parameters
    ----------
    file_hashes:
        Mapping of ``file_path`` (posix string) → content SHA-256 prefix
        as produced by ``ParseCache.file_hash``.
    score:
        Composite drift score at the time the baseline was captured.
    created_at:
        Unix timestamp of snapshot creation (defaults to ``time.time()``).
    ttl_seconds:
        Time-to-live in seconds.  ``is_valid()`` returns ``False`` after
        this period to force a full re-scan.
    """

    file_hashes: dict[str, str]
    score: float = 0.0
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 900  # 15 minutes

    # -- queries -------------------------------------------------------------

    def is_valid(self) -> bool:
        """Return ``True`` if the snapshot has not expired."""
        return (time.time() - self.created_at) < self.ttl_seconds

    def changed_files(
        self,
        current_hashes: dict[str, str],
    ) -> tuple[set[str], set[str], set[str]]:
        """Compare *current_hashes* against the baseline.

        Returns
        -------
        (added, removed, modified)
            Three disjoint sets of file paths (posix strings).
        """
        baseline_keys = set(self.file_hashes)
        current_keys = set(current_hashes)

        added = current_keys - baseline_keys
        removed = baseline_keys - current_keys
        modified = {
            p
            for p in baseline_keys & current_keys
            if self.file_hashes[p] != current_hashes[p]
        }
        return added, removed, modified

    def all_changed(self, current_hashes: dict[str, str]) -> set[str]:
        """Return the union of added, removed, and modified file paths."""
        added, removed, modified = self.changed_files(current_hashes)
        return added | removed | modified
