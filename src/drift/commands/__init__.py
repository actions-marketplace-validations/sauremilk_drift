"""Drift CLI subcommands — each file registers one Click command."""

from __future__ import annotations

import sys

from rich.console import Console

# On Windows, Rich uses a legacy renderer that encodes via cp1252 when
# stdout is a standard stream.  This crashes on Unicode box-drawing chars.
# Reconfigure both streams to UTF-8 before any Console is created.
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

console = Console()
