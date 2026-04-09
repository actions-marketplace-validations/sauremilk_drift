"""Feedback event model and JSONL persistence for calibration evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class FeedbackEvent:
    """A single calibration evidence data point.

    Each event records whether a specific finding was a true positive,
    false positive, or false negative, along with the source of the
    evidence and optional context.
    """

    signal_type: str
    file_path: str
    verdict: Literal["tp", "fp", "fn"]
    source: Literal["user", "inline_suppress", "inline_confirm", "git_correlation", "github_api"]
    timestamp: str = ""
    finding_id: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()
        if not self.finding_id:
            self.finding_id = _compute_finding_id(
                self.signal_type, self.file_path
            )


def _compute_finding_id(signal_type: str, file_path: str) -> str:
    """Compute a stable finding identifier from signal + file."""
    raw = f"{signal_type}:{file_path}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def finding_id_for(signal_type: str, file_path: str, start_line: int | None = None) -> str:
    """Compute a stable finding identifier for external use."""
    raw = f"{signal_type}:{file_path}"
    if start_line is not None:
        raw += f":{start_line}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def record_feedback(
    feedback_path: Path,
    event: FeedbackEvent,
) -> None:
    """Append a feedback event to the JSONL file.

    Creates the parent directory and file if they don't exist.
    """
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(event), ensure_ascii=False, sort_keys=True)
    with feedback_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_feedback(feedback_path: Path) -> list[FeedbackEvent]:
    """Load all feedback events from a JSONL file.

    Returns an empty list if the file does not exist.
    Silently skips malformed lines.
    """
    if not feedback_path.exists():
        return []

    events: list[FeedbackEvent] = []
    for line in feedback_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            events.append(FeedbackEvent(**data))
        except (json.JSONDecodeError, TypeError):
            continue
    return events


def feedback_summary(events: list[FeedbackEvent]) -> dict[str, dict[str, int]]:
    """Aggregate feedback events into per-signal TP/FP/FN counts.

    Returns::

        {
            "pattern_fragmentation": {"tp": 5, "fp": 2, "fn": 1},
            "architecture_violation": {"tp": 3, "fp": 0, "fn": 0},
            ...
        }
    """
    summary: dict[str, dict[str, int]] = {}
    for event in events:
        if event.signal_type not in summary:
            summary[event.signal_type] = {"tp": 0, "fp": 0, "fn": 0}
        summary[event.signal_type][event.verdict] += 1
    return summary
