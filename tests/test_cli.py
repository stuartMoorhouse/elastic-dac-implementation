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


def test_list_command() -> None:
    """Test list command runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0


def test_add_customer_command() -> None:
    """Test add-customer command creates customer directory."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create minimal dac repo structure
        import os

        os.makedirs("src/dac")
        with open("pyproject.toml", "w") as f:
            f.write("[project]\nname = 'dac'\n")

        result = runner.invoke(
            main, ["add-customer", "test-customer", "--github-owner", "test-owner"]
        )
        assert result.exit_code == 0
        assert "Created customers/test-customer/" in result.output
        assert os.path.exists("customers/test-customer/config.yaml")
        assert os.path.exists("customers/test-customer/in-scope-rules.yaml")


def test_validate_command_missing_customer() -> None:
    """Test validate command fails without customer."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate"])
    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_validate_command_nonexistent_customer() -> None:
    """Test validate command fails for nonexistent customer."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create minimal dac repo structure
        import os

        os.makedirs("src/dac")
        with open("pyproject.toml", "w") as f:
            f.write("[project]\nname = 'dac'\n")

        result = runner.invoke(main, ["validate", "--customer", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output
