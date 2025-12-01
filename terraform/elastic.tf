# Retrieve the latest Elastic Stack version
data "ec_stack" "latest" {
  version_regex = var.elastic_version
  region        = var.ec_region
}

# Local Elastic Cloud deployment (for rule development and testing)
resource "ec_deployment" "local" {
  name                   = "${var.project_name}-${var.customer_id}-local"
  region                 = var.ec_region
  version                = data.ec_stack.latest.version
  deployment_template_id = var.deployment_template_id

  elasticsearch = {
    hot = {
      size        = var.elasticsearch_size
      zone_count  = var.elasticsearch_zone_count
      autoscaling = {}
    }
  }

  kibana = {
    size       = var.kibana_size
    zone_count = var.kibana_zone_count
  }

  integrations_server = {
    size       = var.integrations_server_size
    zone_count = var.integrations_server_zone_count
  }

  tags = {
    environment = "local"
    purpose     = "rule-development"
    project     = var.project_name
    customer    = var.customer_id
  }
}

# Development Elastic Cloud deployment (simulates customer production)
resource "ec_deployment" "dev" {
  name                   = "${var.project_name}-${var.customer_id}-dev"
  region                 = var.ec_region
  version                = data.ec_stack.latest.version
  deployment_template_id = var.deployment_template_id

  elasticsearch = {
    hot = {
      size        = var.elasticsearch_size
      zone_count  = var.elasticsearch_zone_count
      autoscaling = {}
    }
  }

  kibana = {
    size       = var.kibana_size
    zone_count = var.kibana_zone_count
  }

  integrations_server = {
    size       = var.integrations_server_size
    zone_count = var.integrations_server_zone_count
  }

  tags = {
    environment = "development"
    purpose     = "customer-simulation"
    project     = var.project_name
    customer    = var.customer_id
  }
}

# Install prebuilt rules on the dev deployment
resource "null_resource" "install_prebuilt_rules" {
  depends_on = [ec_deployment.dev]

  triggers = {
    deployment_id = ec_deployment.dev.id
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Installing prebuilt detection rules on dev deployment..."

      # Wait for Kibana to be ready
      sleep 30

      # Install prebuilt rules
      curl -s -u "elastic:${ec_deployment.dev.elasticsearch_password}" \
        -X PUT "${ec_deployment.dev.kibana.https_endpoint}/api/detection_engine/rules/prepackaged" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json"

      echo "Prebuilt rules installed successfully"
    EOT
  }
}

# Ingest test data into the local deployment
resource "null_resource" "ingest_test_data" {
  depends_on = [ec_deployment.local]

  triggers = {
    deployment_id = ec_deployment.local.id
  }

  provisioner "local-exec" {
    command     = "../scripts/ingest-test-data.sh"
    working_dir = path.module

    environment = {
      LOCAL_ELASTICSEARCH_URL      = ec_deployment.local.elasticsearch.https_endpoint
      LOCAL_ELASTICSEARCH_PASSWORD = ec_deployment.local.elasticsearch_password
    }
  }
}
