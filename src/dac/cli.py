"""CLI entry point for dac."""

import sys

import click

from dac import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Detections as Code CLI for Elastic Security.

    Manage detection rules, exceptions, and rule enablement as code.
    """
    pass


@main.command()
def init() -> None:
    """Initialize a new detection rules repository."""
    click.echo("Initializing repository structure...")
    # TODO: Create directory structure
    click.echo("Repository initialized.")


@main.command()
def validate() -> None:
    """Validate all YAML files against schemas."""
    click.echo("Validating YAML files...")
    # TODO: Implement validation
    click.echo("Validation complete.")


@main.command()
@click.option("-v", "--verbose", is_flag=True, help="Show detailed differences")
def diff(verbose: bool) -> None:
    """Display differences between Git state and live Elastic state."""
    click.echo("Comparing local state to Elastic...", err=True)
    # TODO: Implement diff
    click.echo("No differences found.")


@main.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
def push(dry_run: bool) -> None:
    """Reconcile Elastic state to match Git state."""
    if dry_run:
        click.echo("Dry run mode - no changes will be made", err=True)
    click.echo("Pushing changes to Elastic...", err=True)
    # TODO: Implement push
    click.echo("Push complete.")


@main.command()
def pull() -> None:
    """Export current Elastic state to local YAML files."""
    click.echo("Pulling state from Elastic...", err=True)
    # TODO: Implement pull
    click.echo("Pull complete.")


@main.command("export-rule")
@click.argument("rule_id")
def export_rule(rule_id: str) -> None:
    """Export a single rule from Elastic to stdout."""
    try:
        from dac.client import ElasticClient
        from dac.config import get_settings

        import yaml

        settings = get_settings()
        with ElasticClient(settings) as client:
            rule = client.get_rule(rule_id)
            click.echo(yaml.dump(rule, default_flow_style=False, sort_keys=False))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
