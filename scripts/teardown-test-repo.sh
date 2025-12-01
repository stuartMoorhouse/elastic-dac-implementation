#!/bin/bash
# Teardown the test customer repository
#
# Usage:
#   ./scripts/teardown-test-repo.sh
#
# Prerequisites:
#   - gh CLI installed and authenticated

set -e

REPO_NAME="detection-rules-demo"
REPO_OWNER=$(gh api user --jq '.login')

echo "=============================================="
echo "Teardown Test Customer Repository"
echo "=============================================="
echo ""
echo "This will DELETE: ${REPO_OWNER}/${REPO_NAME}"
echo ""

# Check if repo exists
if ! gh repo view "${REPO_OWNER}/${REPO_NAME}" &>/dev/null; then
    echo "Repository ${REPO_OWNER}/${REPO_NAME} does not exist."
    exit 0
fi

read -p "Are you sure you want to delete this repository? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Deleting repository..."
gh repo delete "${REPO_OWNER}/${REPO_NAME}" --yes

echo ""
echo "=============================================="
echo "Repository deleted successfully!"
echo "=============================================="
