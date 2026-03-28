"""Tests for stable rule_id on Finding and its propagation to JSON/SARIF."""

from __future__ import annotations

import datetime
from pathlib import Path

from drift.models import Finding, Severity, SignalType


class TestRuleIdField:
    """rule_id defaults to signal_type.value and can be overridden."""

    def test_default_rule_id_from_signal_type(self) -> None:
        f = Finding(
            signal_type=SignalType.PATTERN_FRAGMENTATION,
            severity=Severity.HIGH,
            score=0.8,
            title="test",
            description="d",
        )
        assert f.rule_id == "pattern_fragmentation"

    def test_custom_rule_id_preserved(self) -> None:
        f = Finding(
            signal_type=SignalType.ARCHITECTURE_VIOLATION,
            severity=Severity.HIGH,
            score=0.7,
            title="test",
            description="d",
            rule_id="circular-dependency",
        )
        assert f.rule_id == "circular-dependency"

    def test_all_signal_types_produce_rule_id(self) -> None:
        for sig in SignalType:
            f = Finding(
                signal_type=sig,
                severity=Severity.MEDIUM,
                score=0.5,
                title="t",
                description="d",
            )
            assert f.rule_id == sig.value
            assert isinstance(f.rule_id, str)
            assert len(f.rule_id) > 0

    def test_rule_ids_are_unique_per_signal(self) -> None:
        ids = set()
        for sig in SignalType:
            f = Finding(
                signal_type=sig,
                severity=Severity.MEDIUM,
                score=0.5,
                title="t",
                description="d",
            )
            ids.add(f.rule_id)
        assert len(ids) == len(SignalType)


class TestRuleIdInJson:
    """JSON output includes rule_id field."""

    def test_json_contains_rule_id(self) -> None:
        import json

        from drift.models import RepoAnalysis, TrendContext
        from drift.output.json_output import analysis_to_json

        analysis = RepoAnalysis(
            repo_path=Path("."),
            analyzed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            drift_score=0.5,
            findings=[
                Finding(
                    signal_type=SignalType.PATTERN_FRAGMENTATION,
                    severity=Severity.HIGH,
                    score=0.8,
                    title="test finding",
                    description="test desc",
                    file_path=Path("src/foo.py"),
                )
            ],
            module_scores=[],
            total_files=1,
            total_functions=1,
            trend=TrendContext(
                previous_score=None,
                delta=None,
                direction="baseline",
                recent_scores=[],
                history_depth=0,
                transition_ratio=0.0,
            ),
        )
        data = json.loads(analysis_to_json(analysis))
        finding = data["findings"][0]
        assert "rule_id" in finding
        assert finding["rule_id"] == "pattern_fragmentation"

    def test_json_custom_rule_id(self) -> None:
        import json

        from drift.models import RepoAnalysis, TrendContext
        from drift.output.json_output import analysis_to_json

        analysis = RepoAnalysis(
            repo_path=Path("."),
            analyzed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            drift_score=0.5,
            findings=[
                Finding(
                    signal_type=SignalType.ARCHITECTURE_VIOLATION,
                    severity=Severity.HIGH,
                    score=0.7,
                    title="test",
                    description="d",
                    file_path=Path("a.py"),
                    rule_id="boundary-violation",
                )
            ],
            module_scores=[],
            total_files=1,
            total_functions=1,
            trend=TrendContext(
                previous_score=None,
                delta=None,
                direction="baseline",
                recent_scores=[],
                history_depth=0,
                transition_ratio=0.0,
            ),
        )
        data = json.loads(analysis_to_json(analysis))
        assert data["findings"][0]["rule_id"] == "boundary-violation"


class TestRuleIdInSarif:
    """SARIF output uses rule_id for rule identification."""

    def test_sarif_rule_id_default(self) -> None:
        import json

        from drift.models import RepoAnalysis, TrendContext
        from drift.output.json_output import findings_to_sarif

        analysis = RepoAnalysis(
            repo_path=Path("."),
            analyzed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            drift_score=0.5,
            findings=[
                Finding(
                    signal_type=SignalType.MUTANT_DUPLICATE,
                    severity=Severity.MEDIUM,
                    score=0.6,
                    title="dupes",
                    description="d",
                    file_path=Path("a.py"),
                )
            ],
            module_scores=[],
            total_files=1,
            total_functions=1,
            trend=TrendContext(
                previous_score=None,
                delta=None,
                direction="baseline",
                recent_scores=[],
                history_depth=0,
                transition_ratio=0.0,
            ),
        )
        sarif = json.loads(findings_to_sarif(analysis))
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert rules[0]["id"] == "mutant_duplicate"

    def test_sarif_custom_rule_id(self) -> None:
        import json

        from drift.models import RepoAnalysis, TrendContext
        from drift.output.json_output import findings_to_sarif

        analysis = RepoAnalysis(
            repo_path=Path("."),
            analyzed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            drift_score=0.5,
            findings=[
                Finding(
                    signal_type=SignalType.ARCHITECTURE_VIOLATION,
                    severity=Severity.HIGH,
                    score=0.7,
                    title="circ",
                    description="d",
                    file_path=Path("a.py"),
                    rule_id="circular-dependency",
                )
            ],
            module_scores=[],
            total_files=1,
            total_functions=1,
            trend=TrendContext(
                previous_score=None,
                delta=None,
                direction="baseline",
                recent_scores=[],
                history_depth=0,
                transition_ratio=0.0,
            ),
        )
        sarif = json.loads(findings_to_sarif(analysis))
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        results = sarif["runs"][0]["results"]
        assert rules[0]["id"] == "circular-dependency"
        assert results[0]["ruleId"] == "circular-dependency"
