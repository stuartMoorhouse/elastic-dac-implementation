#!/bin/bash
# Setup a test customer repository for dac demo
#
# Usage:
#   ./scripts/setup-test-repo.sh
#
# Prerequisites:
#   - gh CLI installed and authenticated
#   - KIBANA_URL and ELASTIC_API_KEY set in environment (or will prompt)

set -e

REPO_NAME="detection-rules-demo"
REPO_OWNER=$(gh api user --jq '.login')

echo "=============================================="
echo "Setup Test Customer Repository"
echo "=============================================="
echo ""
echo "This script will create: ${REPO_OWNER}/${REPO_NAME}"
echo ""

# Check if repo already exists
if gh repo view "${REPO_OWNER}/${REPO_NAME}" &>/dev/null; then
    echo "Repository ${REPO_OWNER}/${REPO_NAME} already exists."
    echo "Run ./scripts/teardown-test-repo.sh first to remove it."
    exit 1
fi

# Check for required environment variables
if [ -z "$KIBANA_URL" ]; then
    read -p "Enter KIBANA_URL: " KIBANA_URL
fi

if [ -z "$ELASTIC_API_KEY" ]; then
    read -s -p "Enter ELASTIC_API_KEY: " ELASTIC_API_KEY
    echo ""
fi

echo "[1/6] Creating GitHub repository..."
gh repo create "${REPO_NAME}" --public --description "Test repository for dac (Detections as Code) demo"

echo "[2/6] Cloning repository..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
gh repo clone "${REPO_OWNER}/${REPO_NAME}"
cd "${REPO_NAME}"

echo "[3/6] Initializing with dac..."
# Use the local dac CLI
DAC_CLI="/Users/stuart/Documents/code/working/elastic-dac-implementation/.venv/bin/dac"
$DAC_CLI init

echo "[4/6] Copying GitHub Actions workflows..."
mkdir -p .github/workflows
cp /Users/stuart/Documents/code/working/elastic-dac-implementation/examples/github-workflows/pr-validation.yaml .github/workflows/
cp /Users/stuart/Documents/code/working/elastic-dac-implementation/examples/github-workflows/deploy.yaml .github/workflows/

echo "[5/6] Setting repository secrets..."
gh secret set KIBANA_URL --body "$KIBANA_URL"
gh secret set ELASTIC_API_KEY --body "$ELASTIC_API_KEY"

echo "[6/6] Committing and pushing..."
git add .
git commit -m "Initial dac repository setup"
git push -u origin main

echo ""
echo "=============================================="
echo "Test repository created successfully!"
echo "=============================================="
echo ""
echo "Repository: https://github.com/${REPO_OWNER}/${REPO_NAME}"
echo "Local clone: ${TEMP_DIR}/${REPO_NAME}"
echo ""
echo "Next steps:"
echo "  1. cd ${TEMP_DIR}/${REPO_NAME}"
echo "  2. Edit enablement.yaml to add rule IDs"
echo "  3. git add enablement.yaml && git commit -m 'Enable rules'"
echo "  4. git push (or create a PR)"
echo ""
echo "To tear down: ./scripts/teardown-test-repo.sh"
