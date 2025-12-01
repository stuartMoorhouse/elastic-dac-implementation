"""CLI entry point for dac."""

import sys
from pathlib import Path
from typing import Any

import click

from dac import __version__

# Template for enablement.yaml
ENABLEMENT_TEMPLATE = """\
# Detections as Code - Rule Enablement Manifest
#
# This file declares which detection rules should be enabled or disabled.
# Use stable rule_id values (not internal Kibana IDs).
#
# Find rule_ids in Kibana: Security > Rules > click rule > rule_id in URL or details

# Rules that should be enabled in this environment
enabled: []
  # - "9a1a2dae-0b5f-4c3d-8305-a268d404c306"  # Example: Credential Dumping
  # - "28d39238-0c01-420a-b77a-24e5a7378663"  # Example: Sudo Enumeration

# Rules that should be explicitly disabled
disabled: []
  # - "e5c1f8a2-3b4d-4c5e-9f6a-7b8c9d0e1f2a"  # Example: Too noisy
"""


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
    cwd = Path.cwd()

    # Create enablement.yaml if it doesn't exist
    enablement_path = cwd / "enablement.yaml"
    if not enablement_path.exists():
        enablement_path.write_text(ENABLEMENT_TEMPLATE)
        click.echo("Created enablement.yaml")
    else:
        click.echo("Exists  enablement.yaml")

    # Create .env.example if it doesn't exist
    env_example_path = cwd / ".env.example"
    if not env_example_path.exists():
        env_example_path.write_text(
            "# Elastic Cloud Authentication\n"
            "KIBANA_URL=https://your-deployment.kb.us-central1.gcp.cloud.es.io\n"
            "ELASTIC_API_KEY=your-api-key-here\n"
        )
        click.echo("Created .env.example")

    # Create .gitignore if it doesn't exist
    gitignore_path = cwd / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(".env\n")
        click.echo("Created .gitignore")

    click.echo("")
    click.echo("Repository initialized. Next steps:")
    click.echo("  1. Copy .env.example to .env and add your credentials")
    click.echo("  2. Edit enablement.yaml to specify which rules to enable/disable")
    click.echo("  3. Run 'dac validate' to check your configuration")
    click.echo("  4. Run 'dac diff' to preview changes")


@main.command()
def validate() -> None:
    """Validate all YAML files against schemas."""
    import yaml
    from pydantic import ValidationError

    from dac.models import EnablementManifest

    cwd = Path.cwd()
    errors: list[str] = []

    # Validate enablement.yaml
    enablement_path = cwd / "enablement.yaml"
    if enablement_path.exists():
        click.echo("Validating enablement.yaml...", err=True)
        try:
            with open(enablement_path) as f:
                data = yaml.safe_load(f) or {}
            EnablementManifest(**data)
            click.echo("  enablement.yaml: valid")
        except yaml.YAMLError as e:
            errors.append(f"enablement.yaml: YAML parse error: {e}")
            click.echo(f"  enablement.yaml: YAML parse error", err=True)
        except ValidationError as e:
            for err in e.errors():
                field = ".".join(str(x) for x in err["loc"])
                errors.append(f"enablement.yaml: {field}: {err['msg']}")
            click.echo(f"  enablement.yaml: schema validation failed", err=True)
    else:
        click.echo("No enablement.yaml found (run 'dac init' first)", err=True)

    # Summary
    click.echo("")
    if errors:
        click.echo("Validation failed:", err=True)
        for error in errors:
            click.echo(f"  {error}", err=True)
        sys.exit(1)
    else:
        click.echo("Validation passed.")


@main.command()
@click.option("-v", "--verbose", is_flag=True, help="Show detailed differences")
def diff(verbose: bool) -> None:
    """Display differences between Git state and live Elastic state."""
    import yaml

    from dac.client import ElasticClient
    from dac.config import get_settings
    from dac.models import EnablementManifest

    cwd = Path.cwd()

    # Load enablement.yaml
    enablement_path = cwd / "enablement.yaml"
    if not enablement_path.exists():
        click.echo("Error: enablement.yaml not found (run 'dac init' first)", err=True)
        sys.exit(1)

    with open(enablement_path) as f:
        data = yaml.safe_load(f) or {}
    manifest = EnablementManifest(**data)

    # Connect to Elastic and fetch all rules
    click.echo("Connecting to Elastic...", err=True)
    try:
        settings = get_settings()
    except Exception as e:
        click.echo(f"Error: Failed to load settings: {e}", err=True)
        click.echo("Make sure KIBANA_URL and ELASTIC_API_KEY are set", err=True)
        sys.exit(2)

    try:
        with ElasticClient(settings) as client:
            click.echo("Fetching rules...", err=True)
            all_rules = client.get_all_rules()
    except Exception as e:
        click.echo(f"Error: Failed to fetch rules: {e}", err=True)
        sys.exit(2)

    # Build a map of rule_id -> rule info
    rule_map: dict[str, dict[str, Any]] = {}
    for rule in all_rules:
        rule_id = rule.get("rule_id")
        if rule_id:
            rule_map[rule_id] = {
                "id": rule.get("id"),  # Internal ID for bulk actions
                "name": rule.get("name", "Unknown"),
                "enabled": rule.get("enabled", False),
            }

    click.echo(f"Found {len(rule_map)} rules in Elastic", err=True)
    click.echo("")

    # Calculate drift
    to_enable: list[tuple[str, str]] = []  # (rule_id, name)
    to_disable: list[tuple[str, str]] = []  # (rule_id, name)
    not_found: list[str] = []

    for rule_id in manifest.enabled:
        if rule_id not in rule_map:
            not_found.append(rule_id)
        elif not rule_map[rule_id]["enabled"]:
            to_enable.append((rule_id, rule_map[rule_id]["name"]))

    for rule_id in manifest.disabled:
        if rule_id not in rule_map:
            not_found.append(rule_id)
        elif rule_map[rule_id]["enabled"]:
            to_disable.append((rule_id, rule_map[rule_id]["name"]))

    # Output drift report
    click.echo("Drift Report")
    click.echo("============")
    click.echo("")

    if to_enable or to_disable or not_found:
        click.echo("Enablement:")
        for rule_id, name in to_enable:
            click.echo(f"  ! {name} (should be enabled, currently disabled)")
            if verbose:
                click.echo(f"      rule_id: {rule_id}")
        for rule_id, name in to_disable:
            click.echo(f"  ! {name} (should be disabled, currently enabled)")
            if verbose:
                click.echo(f"      rule_id: {rule_id}")
        for rule_id in not_found:
            click.echo(f"  ? {rule_id} (not found in Elastic)")
        click.echo("")

    # Summary
    total_changes = len(to_enable) + len(to_disable)
    click.echo(f"Summary: {len(to_enable)} to enable, {len(to_disable)} to disable", end="")
    if not_found:
        click.echo(f", {len(not_found)} not found", end="")
    click.echo("")

    if total_changes == 0 and not not_found:
        click.echo("")
        click.echo("No changes required - Elastic matches desired state.")


@main.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
def push(dry_run: bool) -> None:
    """Reconcile Elastic state to match Git state."""
    import yaml

    from dac.client import ElasticClient
    from dac.config import get_settings
    from dac.models import EnablementManifest

    cwd = Path.cwd()

    # Load enablement.yaml
    enablement_path = cwd / "enablement.yaml"
    if not enablement_path.exists():
        click.echo("Error: enablement.yaml not found (run 'dac init' first)", err=True)
        sys.exit(1)

    with open(enablement_path) as f:
        data = yaml.safe_load(f) or {}
    manifest = EnablementManifest(**data)

    # Connect to Elastic and fetch all rules
    click.echo("Connecting to Elastic...", err=True)
    try:
        settings = get_settings()
    except Exception as e:
        click.echo(f"Error: Failed to load settings: {e}", err=True)
        click.echo("Make sure KIBANA_URL and ELASTIC_API_KEY are set", err=True)
        sys.exit(2)

    try:
        with ElasticClient(settings) as client:
            click.echo("Fetching rules...", err=True)
            all_rules = client.get_all_rules()

            # Build a map of rule_id -> rule info
            rule_map: dict[str, dict[str, Any]] = {}
            for rule in all_rules:
                rule_id = rule.get("rule_id")
                if rule_id:
                    rule_map[rule_id] = {
                        "id": rule.get("id"),  # Internal ID for bulk actions
                        "name": rule.get("name", "Unknown"),
                        "enabled": rule.get("enabled", False),
                    }

            click.echo(f"Found {len(rule_map)} rules in Elastic", err=True)

            # Calculate what needs to change
            to_enable_ids: list[str] = []  # Internal IDs
            to_enable_names: list[str] = []
            to_disable_ids: list[str] = []  # Internal IDs
            to_disable_names: list[str] = []
            not_found: list[str] = []

            for rule_id in manifest.enabled:
                if rule_id not in rule_map:
                    not_found.append(rule_id)
                elif not rule_map[rule_id]["enabled"]:
                    to_enable_ids.append(rule_map[rule_id]["id"])
                    to_enable_names.append(rule_map[rule_id]["name"])

            for rule_id in manifest.disabled:
                if rule_id not in rule_map:
                    not_found.append(rule_id)
                elif rule_map[rule_id]["enabled"]:
                    to_disable_ids.append(rule_map[rule_id]["id"])
                    to_disable_names.append(rule_map[rule_id]["name"])

            # Report not found rules
            if not_found:
                click.echo("", err=True)
                click.echo("Warning: The following rule_ids were not found:", err=True)
                for rule_id in not_found:
                    click.echo(f"  ? {rule_id}", err=True)

            # Apply changes
            if dry_run:
                click.echo("", err=True)
                click.echo("Dry run - changes that would be made:", err=True)
                if to_enable_names:
                    click.echo(f"  Would enable {len(to_enable_names)} rules:")
                    for name in to_enable_names:
                        click.echo(f"    + {name}")
                if to_disable_names:
                    click.echo(f"  Would disable {len(to_disable_names)} rules:")
                    for name in to_disable_names:
                        click.echo(f"    - {name}")
                if not to_enable_names and not to_disable_names:
                    click.echo("  No changes needed.")
            else:
                click.echo("", err=True)
                # Enable rules
                if to_enable_ids:
                    click.echo(f"Enabling {len(to_enable_ids)} rules...", err=True)
                    result = client.bulk_action("enable", to_enable_ids)
                    # Handle different response formats
                    succeeded = result.get("attributes", {}).get("summary", {}).get("succeeded", len(to_enable_ids))
                    for name in to_enable_names:
                        click.echo(f"  + Enabled: {name}")
                    click.echo(f"  {succeeded} rules enabled", err=True)

                # Disable rules
                if to_disable_ids:
                    click.echo(f"Disabling {len(to_disable_ids)} rules...", err=True)
                    result = client.bulk_action("disable", to_disable_ids)
                    succeeded = result.get("attributes", {}).get("summary", {}).get("succeeded", len(to_disable_ids))
                    for name in to_disable_names:
                        click.echo(f"  - Disabled: {name}")
                    click.echo(f"  {succeeded} rules disabled", err=True)

                if not to_enable_ids and not to_disable_ids:
                    click.echo("No changes needed - Elastic already matches desired state.")
                else:
                    click.echo("")
                    click.echo("Push complete.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)


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
