# DAC Demo Script

This document describes two use cases demonstrating the Detections as Code workflow.

## Prerequisites

Before running the demo, ensure Terraform has been applied:

```bash
cd terraform
terraform apply
```

This creates:
- **Local** Elastic Cloud cluster (rule development + test data)
- **Dev** Elastic Cloud cluster (simulates customer environment with prebuilt rules)
- **customer-a-authored-rules** GitHub repo (for custom rules)
- **customer-a-enabled-rules** GitHub repo (for prebuilt rule enablement)

## Use Case 1: Custom Rule Development and Deployment

**Goal**: Create a custom detection rule in the Local cluster, test it, then deploy to Dev via Git workflow.

### Step 1: Develop the Rule in Local Cluster

1. Open Local Kibana (get URL from `terraform output elastic_local`)
2. Navigate to **Security > Rules > Detection rules (SIEM)**
3. Click **Create new rule** > **ES|QL**
4. Paste the rule from `data/rule.esql`:

```esql
FROM logs-endpoint.events.process-*
| WHERE event.type == "start"
  AND process.name IN ("bash", "sh", "zsh")
  AND process.parent.name IN ("curl", "wget")
| KEEP @timestamp, host.name, user.name, process.parent.command_line
```

5. Configure rule metadata:
   - Name: "Curl Pipe to Shell Execution"
   - Severity: High
   - Risk Score: 75

6. Run the rule preview - it should match the true-positive document

### Step 2: Export and Commit the Rule

1. Clone the authored-rules repo:
   ```bash
   gh repo clone stuartMoorhouse/customer-a-authored-rules
   cd customer-a-authored-rules
   ```

2. Create a feature branch:
   ```bash
   git checkout -b feature/curl-pipe-to-shell-rule
   ```

3. Create the rule file in TOML format (detection-rules CLI format):
   ```bash
   # Create rule using detection-rules CLI or manually
   vim rules/curl_pipe_to_shell.toml
   ```

4. Commit and push:
   ```bash
   git add rules/curl_pipe_to_shell.toml
   git commit -m "Add curl pipe to shell detection rule"
   git push -u origin feature/curl-pipe-to-shell-rule
   ```

### Step 3: Create Pull Request and Deploy

1. Create PR:
   ```bash
   gh pr create --title "Add curl pipe to shell detection rule" \
     --body "Detects curl/wget piping output to shell - common attack pattern"
   ```

2. Review the PR - GitHub Actions validates the rule

3. Merge the PR - GitHub Actions deploys to Dev cluster

4. Verify in Dev Kibana: **Security > Rules** - rule should be active

---

## Use Case 2: Prebuilt Rule Enablement

**Goal**: Enable 3 specific prebuilt detection rules for the customer via Git workflow.

### Step 1: Identify Rules to Enable

1. Open Dev Kibana (get URL from `terraform output elastic_dev`)
2. Navigate to **Security > Rules > Detection rules (SIEM)**
3. Find prebuilt rules to enable, note their `rule_id` values:
   - `28d39238-0c01-420a-b77a-24e5a7378663` - Sudo Command Enumeration Detected
   - `ff10d4d8-fea7-422d-afb1-e5a2702369a9` - Cron Job Created or Modified
   - `0787daa6-f8c5-453b-a4ec-048037f6c1cd` - Potential Shell via Web Server

### Step 2: Update In-Scope Rules

1. Edit the master rule list in this repo:
   ```bash
   vim customers/customer-a/in-scope-rules.yaml
   ```

2. Add the rule IDs:
   ```yaml
   enabled:
     - "28d39238-0c01-420a-b77a-24e5a7378663"  # Sudo Command Enumeration
     - "ff10d4d8-fea7-422d-afb1-e5a2702369a9"  # Cron Job Created/Modified
     - "0787daa6-f8c5-453b-a4ec-048037f6c1cd"  # Shell via Web Server

   disabled: []
   ```

3. Validate locally:
   ```bash
   dac validate --customer customer-a
   dac diff --customer customer-a
   ```

### Step 3: Sync to Customer Repo via Feature Branch

1. Clone the enabled-rules repo:
   ```bash
   gh repo clone stuartMoorhouse/customer-a-enabled-rules
   cd customer-a-enabled-rules
   ```

2. Create a feature branch:
   ```bash
   git checkout -b feature/enable-initial-rules
   ```

3. Update enablement.yaml with the rules:
   ```yaml
   enabled:
     - "28d39238-0c01-420a-b77a-24e5a7378663"
     - "ff10d4d8-fea7-422d-afb1-e5a2702369a9"
     - "0787daa6-f8c5-453b-a4ec-048037f6c1cd"

   disabled: []
   ```

4. Commit and push:
   ```bash
   git add enablement.yaml
   git commit -m "Enable initial detection rules for customer-a"
   git push -u origin feature/enable-initial-rules
   ```

### Step 4: Create Pull Request and Deploy

1. Create PR:
   ```bash
   gh pr create --title "Enable initial detection rules" \
     --body "Enables 3 prebuilt rules: Sudo enumeration, Cron job changes, Shell via web server"
   ```

2. Review the PR - see the rules that will be enabled

3. Merge the PR - GitHub Actions runs and enables the rules in Dev

4. Verify in Dev Kibana: **Security > Rules** - 3 rules should now be enabled

---

## Summary

| Use Case | Source of Truth | Target Cluster | Workflow |
|----------|-----------------|----------------|----------|
| Custom Rules | customer-a-authored-rules | Dev | detection-rules CLI |
| Prebuilt Enablement | customer-a-enabled-rules | Dev | dac CLI |

Both workflows follow GitOps principles:
- Changes are made in Git (feature branch)
- PRs provide review and validation
- Merge triggers automated deployment
- Git history provides audit trail
