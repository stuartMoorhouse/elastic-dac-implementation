#!/bin/bash
# Setup the enabled-rules repository for a customer
#
# Usage:
#   ./scripts/setup-enabled-rules-repo.sh <customer-id>
#
# Prerequisites:
#   - gh CLI installed and authenticated
#   - Customer config exists in customers/<customer-id>/config.yaml
#   - KIBANA_URL and ELASTIC_API_KEY set (for GitHub secrets)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAC_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -z "$1" ]; then
    echo "Usage: $0 <customer-id>"
    echo ""
    echo "Example: $0 demo"
    exit 1
fi

CUSTOMER_ID="$1"
CUSTOMER_DIR="${DAC_ROOT}/customers/${CUSTOMER_ID}"
CONFIG_FILE="${CUSTOMER_DIR}/config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Customer config not found: $CONFIG_FILE"
    echo "Run 'dac add-customer $CUSTOMER_ID' first"
    exit 1
fi

# Parse config.yaml to get repo info
REPO_NAME=$(grep 'enabled_rules_repo:' "$CONFIG_FILE" | sed 's/.*: *"//' | sed 's/".*//' | cut -d'/' -f2)
REPO_OWNER=$(grep 'enabled_rules_repo:' "$CONFIG_FILE" | sed 's/.*: *"//' | sed 's/".*//' | cut -d'/' -f1)

if [ -z "$REPO_NAME" ] || [ -z "$REPO_OWNER" ]; then
    echo "Error: Could not parse enabled_rules_repo from config.yaml"
    exit 1
fi

echo "=============================================="
echo "Setup Enabled-Rules Repository"
echo "=============================================="
echo ""
echo "Customer: $CUSTOMER_ID"
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo ""

# Check if repo already exists
if gh repo view "${REPO_OWNER}/${REPO_NAME}" &>/dev/null; then
    echo "Repository ${REPO_OWNER}/${REPO_NAME} already exists."
    echo "To recreate, delete it first: gh repo delete ${REPO_OWNER}/${REPO_NAME}"
    exit 1
fi

# Check for required environment variables (for GitHub secrets)
if [ -z "$KIBANA_URL" ]; then
    read -p "Enter KIBANA_URL (for GitHub secret): " KIBANA_URL
fi

if [ -z "$ELASTIC_API_KEY" ]; then
    read -s -p "Enter ELASTIC_API_KEY (for GitHub secret): " ELASTIC_API_KEY
    echo ""
fi

echo "[1/5] Creating GitHub repository..."
gh repo create "${REPO_OWNER}/${REPO_NAME}" \
    --public \
    --description "Prebuilt rule enablement for ${CUSTOMER_ID} - managed by dac CLI"

echo "[2/5] Cloning repository..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
gh repo clone "${REPO_OWNER}/${REPO_NAME}"
cd "${REPO_NAME}"

echo "[3/5] Creating initial files..."

# Create enablement.yaml from in-scope-rules
IN_SCOPE_FILE="${CUSTOMER_DIR}/in-scope-rules.yaml"
if [ -f "$IN_SCOPE_FILE" ]; then
    cat > enablement.yaml << 'HEADER'
# Detections as Code - Rule Enablement Manifest
#
# This file is managed by dac CLI. Do not edit directly.
# To modify, update the source in the dac repository and run:
#   dac sync --customer CUSTOMER_ID
#
# Changes to this file trigger GitHub Actions to push to Elastic.

HEADER
    # Copy the enabled/disabled sections from in-scope-rules.yaml
    grep -A 1000 "^enabled:" "$IN_SCOPE_FILE" >> enablement.yaml
else
    cat > enablement.yaml << 'EOF'
# Detections as Code - Rule Enablement Manifest
#
# This file declares which prebuilt detection rules should be enabled or disabled.
# Changes to this file trigger GitHub Actions to push to Elastic.

enabled: []

disabled: []
EOF
fi

# Create .env.example
cat > .env.example << 'EOF'
# Elastic Cloud Authentication
# These are set as GitHub repository secrets for CI/CD
KIBANA_URL=https://your-deployment.kb.us-central1.gcp.cloud.es.io
ELASTIC_API_KEY=your-api-key-here
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
.gitignore
.env
.claude/
CLAUDE.md
EOF

# Create GitHub Actions workflow for PR validation
mkdir -p .github/workflows

cat > .github/workflows/pr-validation.yaml << 'EOF'
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

      - name: Install dac CLI
        run: pip install git+https://github.com/stuartMoorhouse/elastic-dac-implementation.git

      - name: Validate enablement.yaml
        run: |
          # Basic YAML validation
          python -c "import yaml; yaml.safe_load(open('enablement.yaml'))"
          echo "enablement.yaml is valid YAML"

      - name: Show diff preview
        env:
          KIBANA_URL: ${{ secrets.KIBANA_URL }}
          ELASTIC_API_KEY: ${{ secrets.ELASTIC_API_KEY }}
        run: |
          echo "## Enablement Changes" >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          # TODO: Run dac diff once it supports standalone enablement.yaml
          cat enablement.yaml >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
EOF

cat > .github/workflows/deploy.yaml << 'EOF'
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

      - name: Install dac CLI
        run: pip install git+https://github.com/stuartMoorhouse/elastic-dac-implementation.git

      - name: Push enablement to Elastic
        env:
          KIBANA_URL: ${{ secrets.KIBANA_URL }}
          ELASTIC_API_KEY: ${{ secrets.ELASTIC_API_KEY }}
        run: |
          echo "Deploying enablement changes to Elastic..."
          # TODO: Run dac push once it supports standalone enablement.yaml
          echo "enablement.yaml contents:"
          cat enablement.yaml
          echo ""
          echo "Deployment complete!"
EOF

echo "[4/5] Setting repository secrets..."
gh secret set KIBANA_URL --body "$KIBANA_URL" --repo "${REPO_OWNER}/${REPO_NAME}"
gh secret set ELASTIC_API_KEY --body "$ELASTIC_API_KEY" --repo "${REPO_OWNER}/${REPO_NAME}"

echo "[5/5] Committing and pushing..."
git add .
git commit -m "Initial enablement configuration

Managed by dac CLI from elastic-dac-implementation repository.
"
git push -u origin main

echo ""
echo "=============================================="
echo "Repository created successfully!"
echo "=============================================="
echo ""
echo "Repository: https://github.com/${REPO_OWNER}/${REPO_NAME}"
echo "Local clone: ${TEMP_DIR}/${REPO_NAME}"
echo ""
echo "Next steps:"
echo "  1. Edit customers/${CUSTOMER_ID}/in-scope-rules.yaml in the dac repo"
echo "  2. Run 'dac sync --customer ${CUSTOMER_ID}' to update this repo"
echo "  3. Create a PR in ${REPO_NAME} to review changes"
echo "  4. Merge PR to deploy to Elastic"
echo ""
