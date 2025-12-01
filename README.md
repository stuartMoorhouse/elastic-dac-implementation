# dac - Detections as Code CLI

A command-line tool for managing Elastic Security prebuilt rule enablement as code.

## Architecture: Three-Repository Model

This tool uses a **three-repository model** that cleanly separates concerns:

```
elastic-dac-implementation/              # This repo - dac CLI + customer configs
├── src/dac/                             # CLI source code
├── customers/                           # Customer configurations (source of truth)
│   └── <customer>/
│       ├── config.yaml                  # Customer settings (repos, Kibana URL)
│       └── in-scope-rules.yaml          # Master list of rules to enable
├── scripts/                             # Setup scripts
└── pyproject.toml                       # Package definition

<customer>-enabled-rules/                # Per-customer: prebuilt rule enablement
├── enablement.yaml                      # Synced from in-scope-rules.yaml
├── .github/workflows/                   # CI/CD to push to Elastic
└── .env.example                         # Environment template

<customer>-authored-rules/               # Per-customer: custom rules (optional)
├── rules/                               # Custom TOML rules
├── detection_rules/                     # Elastic's detection-rules CLI
└── ...                                  # Standard detection-rules structure
```

### Why This Architecture?

| Repository | Purpose | Managed By |
|------------|---------|------------|
| `elastic-dac-implementation` | CLI tool + master rule lists per customer | `dac` CLI |
| `<customer>-enabled-rules` | Which prebuilt rules are ON/OFF | `dac` CLI |
| `<customer>-authored-rules` | Custom detection rules | `detection-rules` CLI (Elastic) |

**Key benefits:**
- Clear separation between prebuilt rule management and custom rule authoring
- The `dac` CLI focuses on ONE thing: prebuilt rule enablement
- Custom rules use Elastic's official `detection-rules` CLI (no duplication)
- Customer configs in this repo serve as the source of truth
- Changes flow through PR review in the customer's enabled-rules repo

## Quick Start

### 1. Install dac CLI

```bash
# Using uv (recommended)
uv tool install git+https://github.com/stuartMoorhouse/elastic-dac-implementation.git

# Using pip
pip install git+https://github.com/stuartMoorhouse/elastic-dac-implementation.git
```

### 2. Add a Customer

```bash
# Clone this repo for development
git clone https://github.com/stuartMoorhouse/elastic-dac-implementation.git
cd elastic-dac-implementation

# Add a new customer
dac add-customer customer-a --github-owner your-github-username
```

This creates:
- `customers/customer-a/config.yaml` - Customer settings
- `customers/customer-a/in-scope-rules.yaml` - Rules to enable (edit this!)

### 3. Set Up Customer Repositories

```bash
# Set environment variables
export KIBANA_URL="https://your-deployment.kb.us-central1.gcp.cloud.es.io"
export ELASTIC_API_KEY="your-api-key"

# Create the enabled-rules repo
./scripts/setup-enabled-rules-repo.sh customer-a

# Optionally, create the authored-rules repo (clean fork of detection-rules)
./scripts/setup-authored-rules-repo.sh customer-a
```

### 4. Manage Rules

```bash
# Edit the master rule list
vim customers/customer-a/in-scope-rules.yaml

# Validate configuration
dac validate --customer customer-a

# Preview what will change in Elastic
dac diff --customer customer-a

# Push changes directly to Elastic
dac push --customer customer-a

# Or sync to the customer's enabled-rules repo (for PR workflow)
dac sync --customer customer-a
```

## Commands

| Command | Description |
|---------|-------------|
| `dac add-customer <id>` | Add a new customer configuration |
| `dac list` | List all configured customers |
| `dac validate --customer <id>` | Validate customer config and rules |
| `dac diff --customer <id>` | Show drift between config and Elastic |
| `dac push --customer <id>` | Push enablement changes to Elastic |
| `dac push --customer <id> --dry-run` | Preview changes without applying |
| `dac sync --customer <id>` | Sync rules to customer's enabled-rules repo |
| `dac setup-repos --customer <id>` | Show commands to create customer repos |

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KIBANA_URL` | Yes | Full URL to Kibana instance |
| `ELASTIC_API_KEY` | Yes | API key for authentication |
| `ELASTIC_SPACE` | No | Kibana space (default: "default") |

### Customer Config (customers/<id>/config.yaml)

```yaml
name: "Customer A"
enabled_rules_repo: "your-org/customer-a-enabled-rules"
authored_rules_repo: "your-org/customer-a-authored-rules"  # optional
kibana_url: "https://customer-a.kb.us-central1.gcp.cloud.es.io"  # optional override
elastic_space: "default"
```

### In-Scope Rules (customers/<id>/in-scope-rules.yaml)

```yaml
# Prebuilt rules to enable
enabled:
  - "28d39238-0c01-420a-b77a-24e5a7378663"  # Sudo Command Enumeration Detected
  - "ff10d4d8-fea7-422d-afb1-e5a2702369a9"  # Cron Job Created or Modified

# Prebuilt rules to explicitly disable
disabled: []
```

## Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    This Repo (elastic-dac-implementation)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Edit customers/<customer>/in-scope-rules.yaml                           │
│     - Add/remove rule_ids from 'enabled' list                               │
│                                                                             │
│  2. dac validate --customer <customer>                                      │
│     - Validates YAML syntax and schema                                      │
│                                                                             │
│  3. dac diff --customer <customer>                                          │
│     - Shows which rules will be enabled/disabled                            │
│                                                                             │
│  4. dac sync --customer <customer>                                          │
│     - Syncs to customer's enabled-rules repo                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Customer's enabled-rules Repository                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  5. Create Pull Request with updated enablement.yaml                        │
│     - GitHub Action validates the changes                                   │
│                                                                             │
│  6. Merge Pull Request                                                      │
│     - GitHub Action runs 'dac push' to apply to Elastic                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Elastic Security                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Rules are now enabled/disabled as declared                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Finding Rule IDs

To find a prebuilt rule's `rule_id`:

1. In Kibana, go to **Security > Rules**
2. Click on a rule
3. The `rule_id` is shown in the rule details (or in the URL)

**Example rule IDs:**
- `28d39238-0c01-420a-b77a-24e5a7378663` - Sudo Command Enumeration Detected
- `ff10d4d8-fea7-422d-afb1-e5a2702369a9` - Cron Job Created or Modified

## Custom Rules (Optional)

For custom detection rules, use the `<customer>-authored-rules` repository:

```bash
# Create the authored-rules repo (clean fork of detection-rules)
./scripts/setup-authored-rules-repo.sh customer-a

# Clone and set up
gh repo clone your-org/customer-a-authored-rules
cd customer-a-authored-rules
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Use Elastic's detection-rules CLI
python -m detection_rules --help
```

This keeps custom rule development completely separate from prebuilt rule management.

## Development

```bash
# Clone this repo
git clone https://github.com/stuartMoorhouse/elastic-dac-implementation.git
cd elastic-dac-implementation

# Set up development environment
uv sync

# Run CLI
uv run dac --help

# Run tests
uv run pytest
```
