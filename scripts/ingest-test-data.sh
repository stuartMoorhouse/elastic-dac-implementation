#!/bin/bash

################################################################################
# Ingest Test Data into Local Elasticsearch
#
# This script ingests true-positive.json and true-negative.json test data
# into the Local Elasticsearch instance for testing detection rules.
#
# Usage:
#   ./scripts/ingest-test-data.sh
#
# Or called by Terraform with environment variables:
#   LOCAL_ELASTICSEARCH_URL, LOCAL_ELASTICSEARCH_PASSWORD
################################################################################

set -e

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo "=========================================="
echo "Ingest Test Data to Local Elasticsearch"
echo "=========================================="
echo ""

# Determine project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if test data files exist
if [ ! -f "${PROJECT_ROOT}/data/true-positive.json" ] || [ ! -f "${PROJECT_ROOT}/data/true-negative.json" ]; then
    print_error "Test data files not found in ${PROJECT_ROOT}/data/"
    exit 1
fi

# Get Elasticsearch credentials - either from environment (Terraform) or from terraform output
if [ -n "$LOCAL_ELASTICSEARCH_URL" ] && [ -n "$LOCAL_ELASTICSEARCH_PASSWORD" ]; then
    print_info "Using credentials from environment variables"
    ES_ENDPOINT="$LOCAL_ELASTICSEARCH_URL"
    ES_PASSWORD="$LOCAL_ELASTICSEARCH_PASSWORD"
else
    print_info "Getting Elasticsearch credentials from Terraform..."

    TERRAFORM_DIR="${PROJECT_ROOT}/terraform"
    if [ ! -d "$TERRAFORM_DIR" ]; then
        print_error "Terraform directory not found at $TERRAFORM_DIR"
        exit 1
    fi

    cd "$TERRAFORM_DIR"

    if [ ! -f "state/terraform.tfstate" ]; then
        print_error "Terraform state not found. Have you run 'terraform apply'?"
        exit 1
    fi

    ES_ENDPOINT=$(terraform output -json elastic_local 2>/dev/null | jq -r '.elasticsearch_url')
    ES_PASSWORD=$(terraform output -raw elastic_local_password 2>/dev/null)

    cd "$PROJECT_ROOT"
fi

if [ -z "$ES_ENDPOINT" ] || [ "$ES_ENDPOINT" = "null" ] || [ -z "$ES_PASSWORD" ]; then
    print_error "Could not retrieve Elasticsearch credentials."
    print_error "Please ensure 'terraform apply' has completed successfully."
    exit 1
fi

print_info "Elasticsearch endpoint: $ES_ENDPOINT"
print_info "Using elastic user credentials"
echo ""

# Target index - matches the data_stream in the test documents
INDEX_NAME="logs-endpoint.events.process-default"

# Function to ingest a document
ingest_document() {
    local file=$1
    local description=$2

    print_info "Ingesting $description..."

    response=$(curl -s -w "\n%{http_code}" -u "elastic:${ES_PASSWORD}" \
        -X POST "${ES_ENDPOINT}/${INDEX_NAME}/_doc" \
        -H 'Content-Type: application/json' \
        -d @"${file}")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq 201 ] || [ "$http_code" -eq 200 ]; then
        doc_id=$(echo "$body" | jq -r '._id')
        print_info "Success! Document ID: $doc_id"
        return 0
    else
        print_error "Failed with HTTP $http_code"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        return 1
    fi
}

# Wait for Elasticsearch to be ready
print_info "Waiting for Elasticsearch to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s -u "elastic:${ES_PASSWORD}" "${ES_ENDPOINT}/_cluster/health" > /dev/null 2>&1; then
        print_info "Elasticsearch is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    print_error "Elasticsearch did not become ready in time"
    exit 1
fi

echo ""

# Create index with proper mappings (if it doesn't exist)
print_info "Checking if index exists..."
index_exists=$(curl -s -u "elastic:${ES_PASSWORD}" \
    -o /dev/null -w "%{http_code}" \
    "${ES_ENDPOINT}/${INDEX_NAME}")

if [ "$index_exists" -eq 404 ]; then
    print_warn "Index does not exist, creating it..."

    curl -s -u "elastic:${ES_PASSWORD}" \
        -X PUT "${ES_ENDPOINT}/${INDEX_NAME}" \
        -H 'Content-Type: application/json' \
        -d '{
          "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
          },
          "mappings": {
            "properties": {
              "@timestamp": { "type": "date" },
              "event.action": { "type": "keyword" },
              "event.type": { "type": "keyword" },
              "event.category": { "type": "keyword" },
              "process.name": { "type": "keyword" },
              "process.executable": { "type": "keyword" },
              "process.command_line": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
              "process.args": { "type": "keyword" },
              "process.parent.name": { "type": "keyword" },
              "process.parent.executable": { "type": "keyword" },
              "process.parent.command_line": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
              "process.parent.args": { "type": "keyword" },
              "host.name": { "type": "keyword" },
              "user.name": { "type": "keyword" },
              "labels.detection_expected_result": { "type": "keyword" },
              "labels.detection_rule": { "type": "keyword" }
            }
          }
        }' | jq '.' || true

    print_info "Index created"
else
    print_info "Index already exists"
fi

echo ""

# Ingest test documents
print_info "Ingesting test data..."
echo ""

success_count=0
fail_count=0

if ingest_document "${PROJECT_ROOT}/data/true-positive.json" "True Positive (curl piped to bash)"; then
    ((success_count++))
else
    ((fail_count++))
fi

echo ""

if ingest_document "${PROJECT_ROOT}/data/true-negative.json" "True Negative (normal curl download)"; then
    ((success_count++))
else
    ((fail_count++))
fi

echo ""
echo "=========================================="
echo "Ingestion Summary"
echo "=========================================="
echo "Successfully ingested: $success_count documents"
echo "Failed: $fail_count documents"
echo ""

if [ $fail_count -eq 0 ]; then
    print_info "All test data ingested successfully!"
    echo ""
    print_info "Next steps:"
    echo "  1. Open Local Kibana and navigate to Security > Rules"
    echo "  2. Create the 'curl pipe to shell' detection rule using data/rule.esql"
    echo "  3. Run the rule to test against ingested data"
    echo ""
    print_info "To verify ingestion:"
    echo "  curl -u elastic:PASSWORD '${ES_ENDPOINT}/${INDEX_NAME}/_search?pretty&q=labels.detection_rule:curl-pipe-to-shell'"
    exit 0
else
    print_error "Some documents failed to ingest. Please check the errors above."
    exit 1
fi
