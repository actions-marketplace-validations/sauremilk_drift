from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from drift.cli import main


def test_validate_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--help"])
    assert result.exit_code == 0
    assert "Validate drift config and environment" in result.output


def test_scan_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "response-detail" in result.output


def test_fix_plan_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["fix-plan", "--help"])
    assert result.exit_code == 0
    assert "automation-fit-min" in result.output
    assert "--target-path" in result.output


def test_validate_outputs_json(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--repo", str(tmp_path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "2.0"
    assert "valid" in payload
    assert "git_available" in payload


def test_scan_outputs_json(monkeypatch, tmp_path: Path) -> None:
    import drift.commands.scan as scan_command

    monkeypatch.setattr(
        scan_command,
        "api_scan",
        lambda *args, **kwargs: {
            "schema_version": "2.0",
            "accept_change": True,
            "blocking_reasons": [],
        },
    )

    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--repo", str(tmp_path), "--max-findings", "1"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "2.0"
    assert "accept_change" in payload
    assert "blocking_reasons" in payload


def test_scan_accepts_signals_alias(monkeypatch, tmp_path: Path) -> None:
    import drift.commands.scan as scan_command

    captured: dict[str, object] = {}

    def _fake_scan(*args, **kwargs):
        captured.update(kwargs)
        return {
            "schema_version": "2.0",
            "accept_change": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(scan_command, "api_scan", _fake_scan)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "scan",
            "--repo",
            str(tmp_path),
            "--signals",
            "PFS,AVS",
            "--max-findings",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert captured.get("signals") == ["PFS", "AVS"]


# ---------------------------------------------------------------------------
# Unit tests for improved agent-native API helpers
# ---------------------------------------------------------------------------


def test_diff_next_actions_in_scope_accept_true() -> None:
    """When out_of_scope_diff_noise is the only blocker, hint at in_scope_accept."""
    from drift.api import _diff_next_actions

    actions = _diff_next_actions(
        [],
        "stable",
        ["out_of_scope_diff_noise"],
        in_scope_accept=True,
    )
    assert any("in_scope_accept" in a and "true" in a for a in actions)


def test_diff_next_actions_in_scope_accept_false() -> None:
    """When in_scope is also blocking, hint to check in_scope_accept but not claim true."""
    from drift.api import _diff_next_actions

    actions = _diff_next_actions(
        [],
        "stable",
        ["new_high_or_critical_findings", "out_of_scope_diff_noise"],
        in_scope_accept=False,
    )
    combined = " ".join(actions)
    assert "in_scope_accept" in combined
    # Should NOT claim in_scope_accept is true
    assert "in_scope_accept (true)" not in combined


def test_scan_next_actions_baseline_hint_many_findings() -> None:
    """When many high/critical findings exist, recommend baseline workflow."""
    from unittest.mock import MagicMock

    from drift.api import _scan_next_actions

    analysis = MagicMock()
    # Create >20 high severity findings
    finding = MagicMock()
    finding.severity.value = "high"
    analysis.findings = [finding] * 30
    analysis.trend = None

    actions = _scan_next_actions(analysis)
    assert any("baseline" in a.lower() for a in actions)


def test_scan_next_actions_no_baseline_hint_few_findings() -> None:
    """When few findings, no baseline hint."""
    from unittest.mock import MagicMock

    from drift.api import _scan_next_actions

    analysis = MagicMock()
    finding = MagicMock()
    finding.severity.value = "high"
    analysis.findings = [finding] * 5
    analysis.trend = None

    actions = _scan_next_actions(analysis)
    assert not any("baseline" in a.lower() for a in actions)


def test_fix_plan_target_path_filters(monkeypatch) -> None:
    """fix-plan CLI passes --target-path through to the API."""
    import drift.commands.fix_plan as fp_module

    captured: dict = {}

    def fake_fix_plan(*args, **kwargs):
        captured.update(kwargs)
        return {"schema_version": "2.0", "tasks": [], "task_count": 0}

    monkeypatch.setattr(fp_module, "api_fix_plan", fake_fix_plan)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["fix-plan", "--repo", ".", "--target-path", "src/drift", "--max-tasks", "3"],
    )
    assert result.exit_code == 0
    assert captured.get("target_path") == "src/drift"
