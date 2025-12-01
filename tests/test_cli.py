"""Tests for CLI commands."""

from click.testing import CliRunner

from dac.cli import main


def test_version() -> None:
    """Test --version flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help() -> None:
    """Test --help flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Detections as Code CLI" in result.output


def test_init_command() -> None:
    """Test init command runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0


def test_validate_command() -> None:
    """Test validate command runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate"])
    assert result.exit_code == 0
