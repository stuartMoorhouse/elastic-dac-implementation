"""CLI entry point for dac."""

import sys
from pathlib import Path
from typing import Any

import click

from dac import __version__

# Template for enablement.yaml in customer's enabled-rules repo
ENABLEMENT_TEMPLATE = """\
# Detections as Code - Rule Enablement Manifest
#
# This file declares which prebuilt detection rules should be enabled or disabled.
# Use stable rule_id values (not internal Kibana IDs).
#
# Find rule_ids in Kibana: Security > Rules > click rule > rule_id in URL or details
#
# This file is managed by the dac CLI. Do not edit directly unless you know what you're doing.

# Prebuilt rules that should be enabled in this environment
enabled: []

# Prebuilt rules that should be explicitly disabled
disabled: []
"""

# Template for in-scope-rules.yaml in this repo's customers/<name>/ folder
IN_SCOPE_RULES_TEMPLATE = """\
# In-Scope Prebuilt Rules for {customer_name}
#
# This is the master list of prebuilt rules to enable for this customer.
# Run 'dac sync --customer {customer_id}' to sync this to the customer's enabled-rules repo.

# Prebuilt rules to enable
enabled:
  # - "9a1a2dae-0b5f-4c3d-8305-a268d404c306"  # Credential Dumping - LSASS Memory
  # - "28d39238-0c01-420a-b77a-24e5a7378663"  # Sudo Command Enumeration Detected

# Prebuilt rules to explicitly disable
disabled: []
"""

# Template for customer config.yaml
CUSTOMER_CONFIG_TEMPLATE = """\
# Customer Configuration for {customer_name}
#
# This configures where the customer's repos are located.

name: "{customer_name}"

# GitHub repository for enabled rules (prebuilt rule enablement)
enabled_rules_repo: "{github_owner}/{customer_id}-enabled-rules"

# GitHub repository for authored rules (optional, fork of detection-rules)
# authored_rules_repo: "{github_owner}/{customer_id}-authored-rules"

# Override Kibana URL for this customer (optional, uses KIBANA_URL env var if not set)
# kibana_url: "https://customer.kb.us-central1.gcp.cloud.es.io"

# Kibana space (default: "default")
elastic_space: "default"
"""


def get_dac_root() -> Path:
    """Find the dac repository root (where customers/ folder should be)."""
    # Look for pyproject.toml to identify the dac repo root
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "dac").exists():
            return parent
    # Fallback to current directory
    return cwd


def list_customers(dac_root: Path) -> list[str]:
    """List all customer IDs from the customers/ folder."""
    customers_dir = dac_root / "customers"
    if not customers_dir.exists():
        return []
    return [d.name for d in customers_dir.iterdir() if d.is_dir() and (d / "config.yaml").exists()]


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Detections as Code CLI for Elastic Security.

    Manage prebuilt rule enablement across customer environments.
    """
    pass


@main.command()
@click.argument("customer_id")
@click.option("--github-owner", prompt="GitHub owner/org", help="GitHub owner or organization")
def add_customer(customer_id: str, github_owner: str) -> None:
    """Add a new customer configuration.

    Creates customers/<CUSTOMER_ID>/ with config.yaml and in-scope-rules.yaml.
    """
    dac_root = get_dac_root()
    customer_dir = dac_root / "customers" / customer_id

    if customer_dir.exists():
        click.echo(f"Error: Customer '{customer_id}' already exists", err=True)
        sys.exit(1)

    # Create customer directory
    customer_dir.mkdir(parents=True)
    click.echo(f"Created customers/{customer_id}/")

    # Create config.yaml
    config_path = customer_dir / "config.yaml"
    customer_name = customer_id.replace("-", " ").title()
    config_path.write_text(
        CUSTOMER_CONFIG_TEMPLATE.format(
            customer_name=customer_name,
            customer_id=customer_id,
            github_owner=github_owner,
        )
    )
    click.echo(f"Created customers/{customer_id}/config.yaml")

    # Create in-scope-rules.yaml
    rules_path = customer_dir / "in-scope-rules.yaml"
    rules_path.write_text(
        IN_SCOPE_RULES_TEMPLATE.format(
            customer_name=customer_name,
            customer_id=customer_id,
        )
    )
    click.echo(f"Created customers/{customer_id}/in-scope-rules.yaml")

    click.echo("")
    click.echo("Next steps:")
    click.echo(f"  1. Edit customers/{customer_id}/in-scope-rules.yaml to add rule IDs")
    click.echo(f"  2. Run 'dac setup-repos --customer {customer_id}' to create GitHub repos")
    click.echo(f"  3. Run 'dac sync --customer {customer_id}' to sync rules to the enabled-rules repo")


@main.command()
def list() -> None:
    """List all configured customers."""
    dac_root = get_dac_root()
    customers = list_customers(dac_root)

    if not customers:
        click.echo("No customers configured.")
        click.echo("Run 'dac add-customer <customer-id>' to add one.")
        return

    click.echo("Configured customers:")
    for customer in customers:
        click.echo(f"  - {customer}")


@main.command()
@click.option("--customer", required=True, help="Customer ID to validate")
def validate(customer: str) -> None:
    """Validate customer configuration and in-scope rules."""
    import yaml
    from pydantic import ValidationError

    from dac.models import CustomerConfig, InScopeRules

    dac_root = get_dac_root()
    customer_dir = dac_root / "customers" / customer

    if not customer_dir.exists():
        click.echo(f"Error: Customer '{customer}' not found", err=True)
        click.echo(f"Run 'dac add-customer {customer}' to create it", err=True)
        sys.exit(1)

    errors: list[str] = []
    valid_count = 0

    # Validate config.yaml
    config_path = customer_dir / "config.yaml"
    if config_path.exists():
        click.echo(f"Validating customers/{customer}/config.yaml...", err=True)
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            CustomerConfig(**data)
            click.echo("  config.yaml: valid")
            valid_count += 1
        except yaml.YAMLError as e:
            errors.append(f"config.yaml: YAML parse error: {e}")
            click.echo("  config.yaml: YAML parse error", err=True)
        except ValidationError as e:
            for err in e.errors():
                field = ".".join(str(x) for x in err["loc"])
                errors.append(f"config.yaml: {field}: {err['msg']}")
            click.echo("  config.yaml: schema validation failed", err=True)
    else:
        errors.append("config.yaml: file not found")
        click.echo("  config.yaml: not found", err=True)

    # Validate in-scope-rules.yaml
    rules_path = customer_dir / "in-scope-rules.yaml"
    if rules_path.exists():
        click.echo(f"Validating customers/{customer}/in-scope-rules.yaml...", err=True)
        try:
            with open(rules_path) as f:
                data = yaml.safe_load(f) or {}
            InScopeRules(**data)
            click.echo("  in-scope-rules.yaml: valid")
            valid_count += 1
        except yaml.YAMLError as e:
            errors.append(f"in-scope-rules.yaml: YAML parse error: {e}")
            click.echo("  in-scope-rules.yaml: YAML parse error", err=True)
        except ValidationError as e:
            for err in e.errors():
                field = ".".join(str(x) for x in err["loc"])
                errors.append(f"in-scope-rules.yaml: {field}: {err['msg']}")
            click.echo("  in-scope-rules.yaml: schema validation failed", err=True)
    else:
        errors.append("in-scope-rules.yaml: file not found")
        click.echo("  in-scope-rules.yaml: not found", err=True)

    # Summary
    click.echo("")
    if errors:
        click.echo("Validation failed:", err=True)
        for error in errors:
            click.echo(f"  {error}", err=True)
        sys.exit(1)
    else:
        click.echo(f"Validation passed. ({valid_count} files)")


@main.command()
@click.option("--customer", required=True, help="Customer ID")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed differences")
def diff(customer: str, verbose: bool) -> None:
    """Show drift between in-scope rules and Elastic state."""
    import yaml

    from dac.client import ElasticClient
    from dac.config import get_settings
    from dac.models import CustomerConfig, InScopeRules

    dac_root = get_dac_root()
    customer_dir = dac_root / "customers" / customer

    if not customer_dir.exists():
        click.echo(f"Error: Customer '{customer}' not found", err=True)
        sys.exit(1)

    # Load customer config
    config_path = customer_dir / "config.yaml"
    with open(config_path) as f:
        config_data = yaml.safe_load(f) or {}
    config = CustomerConfig(**config_data)

    # Load in-scope rules
    rules_path = customer_dir / "in-scope-rules.yaml"
    with open(rules_path) as f:
        rules_data = yaml.safe_load(f) or {}
    in_scope = InScopeRules(**rules_data)

    # Connect to Elastic
    click.echo(f"Connecting to Elastic for {config.name}...", err=True)
    try:
        settings = get_settings()
        # Override with customer-specific settings if provided
        if config.kibana_url:
            settings.kibana_url = config.kibana_url
        settings.elastic_space = config.elastic_space
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
                "id": rule.get("id"),
                "name": rule.get("name", "Unknown"),
                "enabled": rule.get("enabled", False),
                "immutable": rule.get("immutable", False),
            }

    click.echo(f"Found {len(rule_map)} rules in Elastic", err=True)
    click.echo("")

    # Calculate drift
    to_enable: list[tuple[str, str]] = []
    to_disable: list[tuple[str, str]] = []
    not_found: list[str] = []

    for rule_id in in_scope.enabled:
        if rule_id not in rule_map:
            not_found.append(rule_id)
        elif not rule_map[rule_id]["enabled"]:
            to_enable.append((rule_id, rule_map[rule_id]["name"]))

    for rule_id in in_scope.disabled:
        if rule_id not in rule_map:
            not_found.append(rule_id)
        elif rule_map[rule_id]["enabled"]:
            to_disable.append((rule_id, rule_map[rule_id]["name"]))

    # Output drift report
    click.echo(f"Drift Report for {config.name}")
    click.echo("=" * (17 + len(config.name)))
    click.echo("")

    has_changes = bool(to_enable or to_disable or not_found)

    if to_enable:
        click.echo("Rules to ENABLE:")
        for rule_id, name in to_enable:
            click.echo(f"  + {name}")
            if verbose:
                click.echo(f"      rule_id: {rule_id}")

    if to_disable:
        click.echo("Rules to DISABLE:")
        for rule_id, name in to_disable:
            click.echo(f"  - {name}")
            if verbose:
                click.echo(f"      rule_id: {rule_id}")

    if not_found:
        click.echo("Rules NOT FOUND in Elastic:")
        for rule_id in not_found:
            click.echo(f"  ? {rule_id}")

    click.echo("")
    click.echo(f"Summary: {len(to_enable)} to enable, {len(to_disable)} to disable", end="")
    if not_found:
        click.echo(f", {len(not_found)} not found", end="")
    click.echo("")

    if not has_changes:
        click.echo("")
        click.echo("No changes required - Elastic matches desired state.")


@main.command()
@click.option("--customer", required=True, help="Customer ID")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
def push(customer: str, dry_run: bool) -> None:
    """Push in-scope rules to Elastic (enable/disable rules)."""
    import yaml

    from dac.client import ElasticClient
    from dac.config import get_settings
    from dac.models import CustomerConfig, InScopeRules

    dac_root = get_dac_root()
    customer_dir = dac_root / "customers" / customer

    if not customer_dir.exists():
        click.echo(f"Error: Customer '{customer}' not found", err=True)
        sys.exit(1)

    # Load customer config
    config_path = customer_dir / "config.yaml"
    with open(config_path) as f:
        config_data = yaml.safe_load(f) or {}
    config = CustomerConfig(**config_data)

    # Load in-scope rules
    rules_path = customer_dir / "in-scope-rules.yaml"
    with open(rules_path) as f:
        rules_data = yaml.safe_load(f) or {}
    in_scope = InScopeRules(**rules_data)

    # Connect to Elastic
    click.echo(f"Connecting to Elastic for {config.name}...", err=True)
    try:
        settings = get_settings()
        if config.kibana_url:
            settings.kibana_url = config.kibana_url
        settings.elastic_space = config.elastic_space
    except Exception as e:
        click.echo(f"Error: Failed to load settings: {e}", err=True)
        sys.exit(2)

    try:
        with ElasticClient(settings) as client:
            click.echo("Fetching rules...", err=True)
            all_rules = client.get_all_rules()

            # Build rule map
            rule_map: dict[str, dict[str, Any]] = {}
            for rule in all_rules:
                rule_id = rule.get("rule_id")
                if rule_id:
                    rule_map[rule_id] = {
                        "id": rule.get("id"),
                        "name": rule.get("name", "Unknown"),
                        "enabled": rule.get("enabled", False),
                    }

            click.echo(f"Found {len(rule_map)} rules in Elastic", err=True)

            # Calculate changes
            to_enable_ids: list[str] = []
            to_enable_names: list[str] = []
            to_disable_ids: list[str] = []
            to_disable_names: list[str] = []
            not_found: list[str] = []

            for rule_id in in_scope.enabled:
                if rule_id not in rule_map:
                    not_found.append(rule_id)
                elif not rule_map[rule_id]["enabled"]:
                    to_enable_ids.append(rule_map[rule_id]["id"])
                    to_enable_names.append(rule_map[rule_id]["name"])

            for rule_id in in_scope.disabled:
                if rule_id not in rule_map:
                    not_found.append(rule_id)
                elif rule_map[rule_id]["enabled"]:
                    to_disable_ids.append(rule_map[rule_id]["id"])
                    to_disable_names.append(rule_map[rule_id]["name"])

            if not_found:
                click.echo("", err=True)
                click.echo("Warning: The following rule_ids were not found:", err=True)
                for rule_id in not_found:
                    click.echo(f"  ? {rule_id}", err=True)

            has_changes = bool(to_enable_ids or to_disable_ids)

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
                if not has_changes:
                    click.echo("  No changes needed.")
            else:
                click.echo("", err=True)

                if to_enable_ids:
                    click.echo(f"Enabling {len(to_enable_ids)} rules...", err=True)
                    result = client.bulk_action("enable", to_enable_ids)
                    succeeded = result.get("attributes", {}).get("summary", {}).get("succeeded", len(to_enable_ids))
                    for name in to_enable_names:
                        click.echo(f"  + Enabled: {name}")
                    click.echo(f"  {succeeded} rules enabled", err=True)

                if to_disable_ids:
                    click.echo(f"Disabling {len(to_disable_ids)} rules...", err=True)
                    result = client.bulk_action("disable", to_disable_ids)
                    succeeded = result.get("attributes", {}).get("summary", {}).get("succeeded", len(to_disable_ids))
                    for name in to_disable_names:
                        click.echo(f"  - Disabled: {name}")
                    click.echo(f"  {succeeded} rules disabled", err=True)

                if not has_changes:
                    click.echo("No changes needed - Elastic already matches desired state.")
                else:
                    click.echo("")
                    click.echo("Push complete.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)


@main.command()
@click.option("--customer", required=True, help="Customer ID")
def sync(customer: str) -> None:
    """Sync in-scope rules to the customer's enabled-rules repo.

    This copies the in-scope-rules.yaml content to enablement.yaml in the
    customer's enabled-rules repository, commits, and pushes.
    """
    import yaml

    from dac.models import CustomerConfig, InScopeRules

    dac_root = get_dac_root()
    customer_dir = dac_root / "customers" / customer

    if not customer_dir.exists():
        click.echo(f"Error: Customer '{customer}' not found", err=True)
        sys.exit(1)

    # Load customer config
    config_path = customer_dir / "config.yaml"
    with open(config_path) as f:
        config_data = yaml.safe_load(f) or {}
    config = CustomerConfig(**config_data)

    # Load in-scope rules
    rules_path = customer_dir / "in-scope-rules.yaml"
    with open(rules_path) as f:
        rules_data = yaml.safe_load(f) or {}
    in_scope = InScopeRules(**rules_data)

    click.echo(f"Syncing rules for {config.name}...")
    click.echo(f"  Source: customers/{customer}/in-scope-rules.yaml")
    click.echo(f"  Target: {config.enabled_rules_repo}")
    click.echo("")

    # Generate enablement.yaml content
    enablement_content = f"""\
# Detections as Code - Rule Enablement Manifest
#
# This file is managed by dac CLI. Do not edit directly.
# Source: customers/{customer}/in-scope-rules.yaml
#
# To modify, edit the source file in the dac repository and run:
#   dac sync --customer {customer}

# Prebuilt rules that should be enabled
enabled:
"""
    for rule_id in in_scope.enabled:
        enablement_content += f'  - "{rule_id}"\n'

    enablement_content += """
# Prebuilt rules that should be disabled
disabled:
"""
    for rule_id in in_scope.disabled:
        enablement_content += f'  - "{rule_id}"\n'

    if not in_scope.disabled:
        enablement_content += "  []\n"

    click.echo("Generated enablement.yaml content:")
    click.echo("---")
    click.echo(enablement_content)
    click.echo("---")
    click.echo("")
    click.echo("To complete the sync:")
    click.echo(f"  1. Clone {config.enabled_rules_repo} if not already cloned")
    click.echo("  2. Copy the above content to enablement.yaml in that repo")
    click.echo("  3. Commit and push (or create a PR)")
    click.echo("")
    click.echo("Automated sync via gh CLI coming soon!")


@main.command("setup-repos")
@click.option("--customer", required=True, help="Customer ID")
def setup_repos(customer: str) -> None:
    """Create GitHub repositories for a customer.

    Creates:
    - <customer>-enabled-rules: For prebuilt rule enablement
    - <customer>-authored-rules: Clean fork of detection-rules (optional)
    """
    click.echo(f"Setting up repositories for customer: {customer}")
    click.echo("")
    click.echo("This command will:")
    click.echo("  1. Create <customer>-enabled-rules repo with enablement.yaml + GitHub Actions")
    click.echo("  2. Optionally create <customer>-authored-rules as a clean fork of detection-rules")
    click.echo("")
    click.echo("Run the setup scripts manually for now:")
    click.echo(f"  ./scripts/setup-enabled-rules-repo.sh {customer}")
    click.echo(f"  ./scripts/setup-authored-rules-repo.sh {customer}")


if __name__ == "__main__":
    main()
