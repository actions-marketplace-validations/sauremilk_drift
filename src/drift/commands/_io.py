"""Shared I/O helpers for CLI commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from drift.errors import DriftConfigError


def _is_non_tty_stdout() -> bool:
    """Return True when stdout is a real non-TTY (pipe, redirect, agent).

    Returns False for CliRunner/StringIO test streams (no file descriptor)
    so auto-progress doesn't trigger during unit tests.
    """
    try:
        return not os.isatty(sys.stdout.fileno())
    except (ValueError, OSError, AttributeError):
        return False


def _write_output_file(content: str, destination: Path) -> None:
    try:
        destination.write_text(content + "\n", encoding="utf-8")
    except OSError as exc:
        raise DriftConfigError(
            "DRIFT-2003",
            path=str(destination),
            reason=str(exc),
        ) from exc
