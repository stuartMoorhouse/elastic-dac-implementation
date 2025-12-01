#!/bin/bash
# Setup the authored-rules repository for a customer (clean fork of detection-rules)
#
# Usage:
#   ./scripts/setup-authored-rules-repo.sh <customer-id>
#
# Prerequisites:
#   - gh CLI installed and authenticated
#   - Customer config exists in customers/<customer-id>/config.yaml
#
# This creates a standalone repository (not a GitHub fork) with:
#   - Clean git history (single initial commit)
#   - No original detection-rules commit history
#   - Ready for customer-specific rule development

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
# Look for authored_rules_repo, or construct default name
REPO_LINE=$(grep 'authored_rules_repo:' "$CONFIG_FILE" | grep -v '^#' || true)
if [ -n "$REPO_LINE" ]; then
    REPO_NAME=$(echo "$REPO_LINE" | sed 's/.*: *"//' | sed 's/".*//' | cut -d'/' -f2)
    REPO_OWNER=$(echo "$REPO_LINE" | sed 's/.*: *"//' | sed 's/".*//' | cut -d'/' -f1)
else
    # Default: use same owner as enabled_rules_repo, with -authored-rules suffix
    REPO_OWNER=$(grep 'enabled_rules_repo:' "$CONFIG_FILE" | sed 's/.*: *"//' | sed 's/".*//' | cut -d'/' -f1)
    REPO_NAME="${CUSTOMER_ID}-authored-rules"
fi

if [ -z "$REPO_NAME" ] || [ -z "$REPO_OWNER" ]; then
    echo "Error: Could not determine repository name"
    exit 1
fi

echo "=============================================="
echo "Setup Authored-Rules Repository"
echo "=============================================="
echo ""
echo "Customer: $CUSTOMER_ID"
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo ""
echo "This will create a clean copy of elastic/detection-rules"
echo "with no commit history (for cleaner diffs and smaller size)."
echo ""

# Check if repo already exists
if gh repo view "${REPO_OWNER}/${REPO_NAME}" &>/dev/null; then
    echo "Repository ${REPO_OWNER}/${REPO_NAME} already exists."
    echo "To recreate, delete it first: gh repo delete ${REPO_OWNER}/${REPO_NAME}"
    exit 1
fi

echo "[1/6] Creating GitHub repository..."
gh repo create "${REPO_OWNER}/${REPO_NAME}" \
    --public \
    --description "Custom detection rules for ${CUSTOMER_ID} - based on elastic/detection-rules"

echo "[2/6] Cloning elastic/detection-rules source..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
git clone --depth 1 https://github.com/elastic/detection-rules.git
cd detection-rules

echo "[3/6] Removing upstream remote..."
git remote remove origin

echo "[4/6] Cleaning up unwanted GitHub Actions workflows..."
# Remove workflows that would fail without Elastic's infrastructure
if [ -d ".github/workflows" ]; then
    # Keep only essential workflows, remove CI/CD that requires Elastic secrets
    rm -f .github/workflows/release*.yml 2>/dev/null || true
    rm -f .github/workflows/publish*.yml 2>/dev/null || true
    rm -f .github/workflows/lock*.yml 2>/dev/null || true
fi

echo "[5/6] Creating clean history with orphan branch..."
git checkout --orphan new-main
git add -A
git commit -m "Initial commit from elastic/detection-rules

This repository contains detection rules based on Elastic Security's
detection-rules repository. It is used for custom rule development
for ${CUSTOMER_ID}.

Original source: https://github.com/elastic/detection-rules
Managed independently with clean git history for easier maintenance.

To develop custom rules:
1. Use the detection-rules CLI: python -m detection_rules
2. Create rules in rules/ directory
3. Test with: python -m detection_rules test
4. Export and deploy as needed
"

# Replace main branch
git branch -D main 2>/dev/null || true
git branch -m main

echo "[6/6] Pushing to new repository..."
git remote add origin "https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
git push -f origin main

echo ""
echo "=============================================="
echo "Repository created successfully!"
echo "=============================================="
echo ""
echo "Repository: https://github.com/${REPO_OWNER}/${REPO_NAME}"
echo "Local clone: ${TEMP_DIR}/detection-rules"
echo ""
echo "Next steps:"
echo "  1. Clone the repository: gh repo clone ${REPO_OWNER}/${REPO_NAME}"
echo "  2. Set up Python environment: python -m venv .venv && source .venv/bin/activate"
echo "  3. Install dependencies: pip install -e ."
echo "  4. Develop custom rules using the detection-rules CLI"
echo "  5. See: python -m detection_rules --help"
echo ""
echo "Update customers/${CUSTOMER_ID}/config.yaml with:"
echo "  authored_rules_repo: \"${REPO_OWNER}/${REPO_NAME}\""
echo ""
