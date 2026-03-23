"""Resilience tests for disk-backed parse cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from drift.cache import ParseCache
from drift.models import ParseResult


def test_get_corrupted_cache_entry_returns_none_and_deletes_file(tmp_path: Path) -> None:
    cache = ParseCache(tmp_path)
    content_hash = "deadbeefdeadbeef"
    cache_file = tmp_path / "parse" / f"{content_hash}.json"
    cache_file.write_text("{not-valid-json", encoding="utf-8")

    result = cache.get(content_hash)

    assert result is None
    assert not cache_file.exists()


def test_put_swallows_oserror_on_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache = ParseCache(tmp_path)
    parse_result = ParseResult(file_path=Path("a.py"), language="python")

    def _raise_oserror(*_args: object, **_kwargs: object) -> str:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _raise_oserror)  # type: ignore[attr-defined]

    # Cache failures must never crash analysis.
    cache.put("cafebabecafebabe", parse_result)
