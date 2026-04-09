"""drift feedback — record TP/FP/FN evidence for signal calibration."""

from __future__ import annotations

from pathlib import Path

import click

from drift.commands import console


@click.group()
def feedback() -> None:
    """Record calibration feedback for signal weight tuning."""


@feedback.command()
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the repository root.",
)
@click.option(
    "--mark",
    "-m",
    type=click.Choice(["tp", "fp", "fn"]),
    required=True,
    help="Verdict: true positive, false positive, or false negative.",
)
@click.option(
    "--signal",
    "-s",
    required=True,
    help="Signal type or abbreviation (e.g. PFS, architecture_violation).",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    help="File path the finding relates to.",
)
@click.option(
    "--reason",
    default=None,
    help="Optional reason for the verdict.",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default=None,
    help="Config file path.",
)
def mark(
    repo: Path,
    mark: str,
    signal: str,
    file_path: str,
    reason: str | None,
    config: Path | None,
) -> None:
    """Record a single feedback verdict for a finding."""
    from drift.calibration.feedback import FeedbackEvent, record_feedback
    from drift.config import SIGNAL_ABBREV, DriftConfig

    cfg = DriftConfig.load(repo, config)

    # Resolve signal abbreviation to full name
    resolved_signal = SIGNAL_ABBREV.get(signal.upper(), signal)

    feedback_path = repo / cfg.calibration.feedback_path
    event = FeedbackEvent(
        signal_type=resolved_signal,
        file_path=file_path,
        verdict=mark,  # type: ignore[arg-type]
        source="user",
        evidence={"reason": reason} if reason else {},
    )

    record_feedback(feedback_path, event)
    console.print(
        f"[green]Recorded[/green] {mark.upper()} for "
        f"[bold]{resolved_signal}[/bold] in {file_path}"
    )


@feedback.command()
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the repository root.",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default=None,
    help="Config file path.",
)
def summary(repo: Path, config: Path | None) -> None:
    """Show aggregated feedback counts per signal."""
    from drift.calibration.feedback import feedback_summary, load_feedback
    from drift.config import DriftConfig

    cfg = DriftConfig.load(repo, config)
    feedback_path = repo / cfg.calibration.feedback_path
    events = load_feedback(feedback_path)

    if not events:
        console.print("[dim]No feedback recorded yet.[/dim]")
        return

    stats = feedback_summary(events)
    console.print(f"\n[bold]Feedback Summary[/bold] ({len(events)} events)\n")
    console.print(f"{'Signal':<30} {'TP':>5} {'FP':>5} {'FN':>5}")
    console.print("-" * 50)
    for signal_type in sorted(stats):
        counts = stats[signal_type]
        console.print(
            f"{signal_type:<30} {counts['tp']:>5} {counts['fp']:>5} {counts['fn']:>5}"
        )


@feedback.command(name="import")
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the repository root.",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default=None,
    help="Config file path.",
)
@click.argument(
    "source_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def import_feedback(repo: Path, config: Path | None, source_file: Path) -> None:
    """Import feedback events from an external JSONL file."""
    from drift.calibration.feedback import load_feedback, record_feedback
    from drift.config import DriftConfig

    cfg = DriftConfig.load(repo, config)
    feedback_path = repo / cfg.calibration.feedback_path

    events = load_feedback(source_file)
    if not events:
        console.print("[yellow]No valid events found in source file.[/yellow]")
        return

    for event in events:
        record_feedback(feedback_path, event)

    console.print(f"[green]Imported {len(events)} events[/green] into {feedback_path}")
