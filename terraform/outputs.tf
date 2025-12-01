# Elastic Cloud Outputs - Local Environment
output "elastic_local" {
  description = "Local Elastic Cloud deployment (for rule development)"
  value = {
    deployment_id      = ec_deployment.local.id
    deployment_name    = ec_deployment.local.name
    elasticsearch_url  = ec_deployment.local.elasticsearch.https_endpoint
    kibana_url         = ec_deployment.local.kibana.https_endpoint
    elasticsearch_user = ec_deployment.local.elasticsearch_username
    cloud_id           = ec_deployment.local.elasticsearch.cloud_id
    version            = ec_deployment.local.version
  }
  sensitive = false
}

output "elastic_local_password" {
  description = "Local Elastic deployment password (sensitive)"
  value       = ec_deployment.local.elasticsearch_password
  sensitive   = true
}

# Elastic Cloud Outputs - Dev Environment
output "elastic_dev" {
  description = "Development Elastic Cloud deployment (simulates customer environment)"
  value = {
    deployment_id      = ec_deployment.dev.id
    deployment_name    = ec_deployment.dev.name
    elasticsearch_url  = ec_deployment.dev.elasticsearch.https_endpoint
    kibana_url         = ec_deployment.dev.kibana.https_endpoint
    elasticsearch_user = ec_deployment.dev.elasticsearch_username
    cloud_id           = ec_deployment.dev.elasticsearch.cloud_id
    version            = ec_deployment.dev.version
  }
  sensitive = false
}

output "elastic_dev_password" {
  description = "Development Elastic deployment password (sensitive)"
  value       = ec_deployment.dev.elasticsearch_password
  sensitive   = true
}

# GitHub Outputs
output "github_authored_rules_repo" {
  description = "Authored rules repository (custom detection rules)"
  value = var.create_authored_rules_repo ? {
    full_name = data.github_repository.authored_rules[0].full_name
    html_url  = data.github_repository.authored_rules[0].html_url
    clone_url = data.github_repository.authored_rules[0].http_clone_url
    ssh_url   = data.github_repository.authored_rules[0].ssh_clone_url
  } : null
}

output "github_enabled_rules_repo" {
  description = "Enabled rules repository (prebuilt rule enablement)"
  value = var.create_enabled_rules_repo ? {
    full_name = github_repository.enabled_rules[0].full_name
    html_url  = github_repository.enabled_rules[0].html_url
    clone_url = github_repository.enabled_rules[0].http_clone_url
    ssh_url   = github_repository.enabled_rules[0].ssh_clone_url
  } : null
}

# Customer Configuration Output
output "customer_config" {
  description = "Customer configuration for dac CLI"
  value = {
    customer_id         = var.customer_id
    enabled_rules_repo  = var.create_enabled_rules_repo ? "${var.github_owner}/${local.enabled_rules_repo_name}" : null
    authored_rules_repo = var.create_authored_rules_repo ? "${var.github_owner}/${local.authored_rules_repo_name}" : null
    kibana_url          = ec_deployment.dev.kibana.https_endpoint
    elastic_space       = "default"
  }
}

# Quick Start Guide
output "quick_start" {
  description = "Quick start commands for dac demo"
  value       = <<-EOT

    DAC - DETECTIONS AS CODE DEMO
    =============================

    Customer: ${var.customer_id}

    ELASTIC CLOUD DEPLOYMENTS
    -------------------------

    Local (Rule Development):
      Kibana:   ${ec_deployment.local.kibana.https_endpoint}
      User:     ${ec_deployment.local.elasticsearch_username}
      Password: terraform output elastic_local_password

    Dev (Customer Simulation):
      Kibana:   ${ec_deployment.dev.kibana.https_endpoint}
      User:     ${ec_deployment.dev.elasticsearch_username}
      Password: terraform output elastic_dev_password

    GITHUB REPOSITORIES
    -------------------
    ${var.create_enabled_rules_repo ? "Enabled Rules: https://github.com/${var.github_owner}/${local.enabled_rules_repo_name}" : "Enabled Rules: Not created"}
    ${var.create_authored_rules_repo ? "Authored Rules: https://github.com/${var.github_owner}/${local.authored_rules_repo_name}" : "Authored Rules: Not created"}

    NEXT STEPS
    ----------

    1. Update customer config in dac repo:

       # customers/${var.customer_id}/config.yaml
       name: "${var.customer_id}"
       enabled_rules_repo: "${var.github_owner}/${local.enabled_rules_repo_name}"
       authored_rules_repo: "${var.github_owner}/${local.authored_rules_repo_name}"
       kibana_url: "${ec_deployment.dev.kibana.https_endpoint}"
       elastic_space: "default"

    2. Add rules to enable:
       vim customers/${var.customer_id}/in-scope-rules.yaml

    3. Validate and push:
       dac validate --customer ${var.customer_id}
       dac diff --customer ${var.customer_id}
       dac push --customer ${var.customer_id}

    Or sync to GitHub for PR workflow:
       dac sync --customer ${var.customer_id}

  EOT
}
