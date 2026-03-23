"""Tests for the ``drift badge`` command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from drift.cli import main


class TestBadgeCommand:
    """Test the ``drift badge`` command."""

    def test_badge_outputs_shields_url(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo)])
        assert result.exit_code == 0
        assert "img.shields.io" in result.output

    def test_badge_outputs_markdown_snippet(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo)])
        assert result.exit_code == 0
        assert "[![Drift Score]" in result.output

    def test_badge_write_to_file(self, tmp_repo: Path) -> None:
        out_file = tmp_repo / "badge.txt"
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo), "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        url = out_file.read_text(encoding="utf-8")
        assert "img.shields.io" in url

    def test_badge_style_option(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo), "--style", "for-the-badge"])
        assert result.exit_code == 0
        assert "for-the-badge" in result.output

    def test_badge_color_green_for_low_score(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo)])
        assert result.exit_code == 0
        # An empty repo should have low drift → brightgreen
        assert "brightgreen" in result.output
