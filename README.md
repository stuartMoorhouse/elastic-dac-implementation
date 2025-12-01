# dac - Detections as Code CLI

A command-line tool for managing Elastic Security detection rules as code.

## Architecture: Separate Repositories

This tool is designed with a **two-repository model**:

```
elastic-dac-implementation/          # This repo - the dac CLI tool
├── src/dac/                         # CLI source code
├── tests/                           # Tests
└── pyproject.toml                   # Package definition

detection-rules-<customer>/          # Separate repo per customer/environment
├── enablement.yaml                  # Which prebuilt rules to enable/disable
├── .github/workflows/deploy.yaml    # CI/CD to apply changes
└── .env.example                     # Environment template
```

**Why separate repos?**
- The `dac` CLI is a tool - install it once, use it everywhere
- Each customer/environment gets its own detection rules repo
- Changes to rules go through that repo's PR process
- Credentials stay in each environment's repo secrets

## Use Case 1: GitOps Enablement of Prebuilt Rules

**Goal**: Declaratively manage which Elastic prebuilt detection rules are enabled in your environment, with Git as the source of truth.

Elastic Security ships with hundreds of prebuilt rules, but there's no built-in way to:
- Define in Git which rules should be enabled for a specific environment
- Detect drift when someone manually changes rules in Kibana
- Enforce desired state via CI/CD

The `dac` CLI solves this with `enablement.yaml`.

### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Developer Workstation                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Edit enablement.yaml                                                    │
│     - Add rule_ids to 'enabled' list                                        │
│     - Add rule_ids to 'disabled' list                                       │
│                                                                             │
│  2. dac validate                                                            │
│     - Validates YAML syntax and schema                                      │
│                                                                             │
│  3. dac diff                                                                │
│     - Shows which rules will be enabled/disabled                            │
│     - Preview changes before committing                                     │
│                                                                             │
│  4. git commit && git push && create PR                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GitHub Actions                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  On Pull Request:                                                           │
│    - dac validate (ensure YAML is valid)                                    │
│    - dac diff (comment drift report on PR)                                  │
│                                                                             │
│  On Merge to Main:                                                          │
│    - dac push (apply enablement changes to Elastic)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Elastic Security                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Rules are now enabled/disabled as declared in enablement.yaml              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Example enablement.yaml

```yaml
# Prebuilt rules to enable for this environment
enabled:
  - "9a1a2dae-0b5f-4c3d-8305-a268d404c306"  # Credential Dumping - LSASS Memory
  - "f44fa4b6-524c-4e87-8d9e-8c6a45a3a8d9"  # Suspicious PowerShell Execution
  - "28d39238-0c01-420a-b77a-24e5a7378663"  # Sudo Command Enumeration Detected

# Prebuilt rules to explicitly disable
disabled:
  - "e5c1f8a2-3b4d-4c5e-9f6a-7b8c9d0e1f2a"  # Too noisy for this environment
```

### Finding Rule IDs

To find a prebuilt rule's `rule_id`:
1. In Kibana, go to **Security > Rules**
2. Click on a rule
3. The `rule_id` is shown in the rule details (or in the URL)

### Demo Steps

1. **Create a new detection rules repo** for your environment
2. **Install dac**: `pip install dac` or `uv tool install dac`
3. **Initialize**: `dac init` (creates `enablement.yaml`)
4. **Configure**: Set `KIBANA_URL` and `ELASTIC_API_KEY` in `.env`
5. **Edit enablement.yaml**: Add rule IDs to enable
6. **Validate**: `dac validate`
7. **Preview**: `dac diff`
8. **Commit and push**: Create a Pull Request
9. **Review**: GitHub Action comments with drift report
10. **Merge**: GitHub Action runs `dac push`
11. **Verify**: Check Kibana - rules are now enabled

## Installation

### As a CLI tool (recommended)

```bash
# Using uv
uv tool install git+https://github.com/stuartMoorhouse/elastic-dac-implementation.git

# Using pip
pip install git+https://github.com/stuartMoorhouse/elastic-dac-implementation.git
```

### For development

```bash
git clone https://github.com/stuartMoorhouse/elastic-dac-implementation.git
cd elastic-dac-implementation
uv sync
uv run dac --help
```

## Configuration

The CLI reads configuration from environment variables (supports `.env` files):

| Variable | Required | Description |
|----------|----------|-------------|
| `KIBANA_URL` | Yes | Full URL to Kibana instance |
| `ELASTIC_API_KEY` | Yes | API key for authentication |
| `ELASTIC_SPACE` | No | Kibana space (default: "default") |

## Commands

| Command | Description |
|---------|-------------|
| `dac init` | Initialize repository with `enablement.yaml` template |
| `dac validate` | Validate YAML files against schemas |
| `dac diff` | Show enablement drift between Git and Elastic |
| `dac push` | Apply enablement changes to Elastic |
| `dac push --dry-run` | Preview changes without applying |

## Setting Up a Customer Repository

Create a new repo for each customer/environment:

```bash
mkdir detection-rules-acme-corp
cd detection-rules-acme-corp
git init

# Initialize with dac
dac init

# Copy GitHub Actions workflows
mkdir -p .github/workflows
# Copy from examples/github-workflows/ in this repo:
#   - pr-validation.yaml  (validates on PR)
#   - deploy.yaml         (pushes on merge)

# Configure credentials (add to .gitignore!)
cp .env.example .env
# Edit .env with your KIBANA_URL and ELASTIC_API_KEY

# Edit enablement.yaml with your desired rules
# Then validate and preview
dac validate
dac diff

# Commit and push
git add enablement.yaml .github/
git commit -m "Initial rule enablement configuration"
git push
```

### GitHub Repository Secrets

Add these secrets to your customer repository (Settings > Secrets > Actions):

| Secret | Description |
|--------|-------------|
| `KIBANA_URL` | Full URL to Kibana instance |
| `ELASTIC_API_KEY` | API key for authentication |

## Future Use Cases

- **Custom rule management**: Create and deploy custom detection rules
- **OOTB rule overrides**: Modify severity, risk score, tags on prebuilt rules
- **Exception management**: Manage exception lists and items as code
