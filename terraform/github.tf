# Local variables for repository names
locals {
  authored_rules_repo_name = "${var.customer_id}-authored-rules"
  enabled_rules_repo_name  = "${var.customer_id}-enabled-rules"
}

# =============================================================================
# AUTHORED-RULES REPOSITORY (Clean fork of detection-rules)
# =============================================================================

resource "null_resource" "create_authored_rules_repo" {
  count = var.create_authored_rules_repo ? 1 : 0

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "Creating ${local.authored_rules_repo_name} repository..."

      # Check if repository already exists
      if gh repo view "${var.github_owner}/${local.authored_rules_repo_name}" &>/dev/null; then
        echo "Repository ${local.authored_rules_repo_name} already exists"
      else
        echo "Creating new repository..."
        gh repo create "${var.github_owner}/${local.authored_rules_repo_name}" \
          --${var.repo_visibility} \
          --description "Custom detection rules for ${var.customer_id} - based on elastic/detection-rules" \
          --clone=false

        echo "Cloning elastic/detection-rules source..."
        TEMP_DIR=$(mktemp -d)
        cd "$TEMP_DIR"
        git clone --depth 1 https://github.com/elastic/detection-rules.git
        cd detection-rules

        echo "Removing upstream remote..."
        git remote remove origin

        echo "Cleaning up unwanted GitHub Actions workflows..."
        # Remove workflows that would fail without Elastic's infrastructure
        rm -f .github/workflows/release*.yml 2>/dev/null || true
        rm -f .github/workflows/publish*.yml 2>/dev/null || true
        rm -f .github/workflows/lock*.yml 2>/dev/null || true

        echo "Creating clean history with orphan branch..."
        git checkout --orphan new-main
        git add -A
        git commit -m "Initial commit from elastic/detection-rules

This repository contains detection rules based on Elastic Security's
detection-rules repository for ${var.customer_id}.

Original source: https://github.com/elastic/detection-rules
Managed independently with clean git history."

        # Replace main branch
        git branch -D main 2>/dev/null || true
        git branch -m main

        echo "Pushing to new repository..."
        git remote add origin "https://github.com/${var.github_owner}/${local.authored_rules_repo_name}.git"
        git push -f origin main

        echo "Cleaning up..."
        cd ../..
        rm -rf "$TEMP_DIR"

        echo "Created ${local.authored_rules_repo_name} successfully"
      fi
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      echo "Note: GitHub repository not automatically deleted"
      echo "To delete manually: gh repo delete ${self.triggers.github_owner}/${self.triggers.repo_name}"
      exit 0
    EOT
  }

  triggers = {
    github_owner = var.github_owner
    repo_name    = local.authored_rules_repo_name
  }
}

# Data source for authored-rules repo
data "github_repository" "authored_rules" {
  count     = var.create_authored_rules_repo ? 1 : 0
  full_name = "${var.github_owner}/${local.authored_rules_repo_name}"

  depends_on = [null_resource.create_authored_rules_repo]
}

# =============================================================================
# ENABLED-RULES REPOSITORY (Prebuilt rule enablement)
# =============================================================================

resource "github_repository" "enabled_rules" {
  count = var.create_enabled_rules_repo ? 1 : 0

  name        = local.enabled_rules_repo_name
  description = "Prebuilt rule enablement for ${var.customer_id} - managed by dac CLI"
  visibility  = var.repo_visibility

  auto_init = true

  # Allow merge commits for cleaner PR history
  allow_merge_commit = true
  allow_squash_merge = true
  allow_rebase_merge = false

  # Delete head branches after merge
  delete_branch_on_merge = true
}

# Create enablement.yaml file
resource "github_repository_file" "enablement_yaml" {
  count = var.create_enabled_rules_repo ? 1 : 0

  repository          = github_repository.enabled_rules[0].name
  branch              = "main"
  file                = "enablement.yaml"
  commit_message      = "Initial enablement configuration"
  overwrite_on_create = true

  content = <<-EOT
# Detections as Code - Rule Enablement Manifest
#
# This file is managed by dac CLI. Do not edit directly.
# To modify, update the source in the dac repository and run:
#   dac sync --customer ${var.customer_id}
#
# Changes to this file trigger GitHub Actions to push to Elastic.

# Prebuilt rules that should be enabled
enabled: []

# Prebuilt rules that should be disabled
disabled: []
EOT
}

# Create .env.example file
resource "github_repository_file" "env_example" {
  count = var.create_enabled_rules_repo ? 1 : 0

  repository          = github_repository.enabled_rules[0].name
  branch              = "main"
  file                = ".env.example"
  commit_message      = "Add environment template"
  overwrite_on_create = true

  content = <<-EOT
# Elastic Cloud Authentication
# These are set as GitHub repository secrets for CI/CD
KIBANA_URL=https://your-deployment.kb.us-central1.gcp.cloud.es.io
ELASTIC_API_KEY=your-api-key-here
EOT

  depends_on = [github_repository_file.enablement_yaml]
}

# Create GitHub Actions workflow for PR validation
resource "github_repository_file" "pr_validation_workflow" {
  count = var.create_enabled_rules_repo ? 1 : 0

  repository          = github_repository.enabled_rules[0].name
  branch              = "main"
  file                = ".github/workflows/pr-validation.yaml"
  commit_message      = "Add PR validation workflow"
  overwrite_on_create = true

  content = <<-EOT
name: PR Validation

on:
  pull_request:
    branches: [main]
    paths:
      - 'enablement.yaml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Validate enablement.yaml
        run: |
          python -c "import yaml; yaml.safe_load(open('enablement.yaml'))"
          echo "enablement.yaml is valid YAML"

      - name: Show changes
        run: |
          echo "## Enablement Changes" >> $$GITHUB_STEP_SUMMARY
          echo '```yaml' >> $$GITHUB_STEP_SUMMARY
          cat enablement.yaml >> $$GITHUB_STEP_SUMMARY
          echo '```' >> $$GITHUB_STEP_SUMMARY
EOT

  depends_on = [github_repository_file.env_example]
}

# Create GitHub Actions workflow for deployment
resource "github_repository_file" "deploy_workflow" {
  count = var.create_enabled_rules_repo ? 1 : 0

  repository          = github_repository.enabled_rules[0].name
  branch              = "main"
  file                = ".github/workflows/deploy.yaml"
  commit_message      = "Add deployment workflow"
  overwrite_on_create = true

  content = <<-EOT
name: Deploy to Elastic

on:
  push:
    branches: [main]
    paths:
      - 'enablement.yaml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pyyaml httpx

      - name: Deploy enablement to Elastic
        env:
          KIBANA_URL: $${{ secrets.KIBANA_URL }}
          ELASTIC_API_KEY: $${{ secrets.ELASTIC_API_KEY }}
        run: |
          python << 'PYTHON_SCRIPT'
import os
import yaml
import httpx

kibana_url = os.environ['KIBANA_URL'].rstrip('/')
api_key = os.environ['ELASTIC_API_KEY']

with open('enablement.yaml') as f:
    config = yaml.safe_load(f)

headers = {
    'Authorization': f'ApiKey {api_key}',
    'kbn-xsrf': 'true',
    'Content-Type': 'application/json'
}

# Fetch all rules to build rule_id -> id mapping
print("Fetching rules from Elastic...")
rules = []
page = 1
while True:
    resp = httpx.get(
        f'{kibana_url}/api/detection_engine/rules/_find',
        headers=headers,
        params={'page': page, 'per_page': 1000}
    )
    resp.raise_for_status()
    data = resp.json()
    rules.extend(data.get('data', []))
    if len(rules) >= data.get('total', 0):
        break
    page += 1

rule_map = {r['rule_id']: r for r in rules}
print(f"Found {len(rule_map)} rules")

# Process enabled rules
to_enable = []
for rule_id in config.get('enabled', []):
    if rule_id in rule_map and not rule_map[rule_id].get('enabled'):
        to_enable.append(rule_map[rule_id]['id'])

# Process disabled rules
to_disable = []
for rule_id in config.get('disabled', []):
    if rule_id in rule_map and rule_map[rule_id].get('enabled'):
        to_disable.append(rule_map[rule_id]['id'])

# Enable rules
if to_enable:
    print(f"Enabling {len(to_enable)} rules...")
    resp = httpx.post(
        f'{kibana_url}/api/detection_engine/rules/_bulk_action',
        headers=headers,
        json={'action': 'enable', 'ids': to_enable}
    )
    resp.raise_for_status()
    print(f"Enabled {len(to_enable)} rules")

# Disable rules
if to_disable:
    print(f"Disabling {len(to_disable)} rules...")
    resp = httpx.post(
        f'{kibana_url}/api/detection_engine/rules/_bulk_action',
        headers=headers,
        json={'action': 'disable', 'ids': to_disable}
    )
    resp.raise_for_status()
    print(f"Disabled {len(to_disable)} rules")

if not to_enable and not to_disable:
    print("No changes needed")
else:
    print("Deployment complete!")
PYTHON_SCRIPT
EOT

  depends_on = [github_repository_file.pr_validation_workflow]
}

# Set repository secrets for enabled-rules repo
resource "github_actions_secret" "kibana_url" {
  count = var.create_enabled_rules_repo ? 1 : 0

  repository      = github_repository.enabled_rules[0].name
  secret_name     = "KIBANA_URL"
  plaintext_value = ec_deployment.dev.kibana.https_endpoint
}

resource "github_actions_secret" "elastic_api_key" {
  count = var.create_enabled_rules_repo ? 1 : 0

  repository      = github_repository.enabled_rules[0].name
  secret_name     = "ELASTIC_API_KEY"
  plaintext_value = ec_deployment.dev.elasticsearch_password

  # Note: Using password for now. In production, create a proper API key.
  # The deployment password works for basic auth but API key is preferred.
}
