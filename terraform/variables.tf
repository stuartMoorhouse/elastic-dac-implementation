# Project Configuration
variable "project_name" {
  description = "Name of the project (used as prefix for resources)"
  type        = string
  default     = "dac-demo"
}

# Customer Configuration
variable "customer_id" {
  description = "Customer identifier (e.g., 'customer-a')"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]{1,30}$", var.customer_id))
    error_message = "customer_id must be lowercase alphanumeric with hyphens (1-30 characters)"
  }
}

# Elastic Cloud Configuration
variable "ec_region" {
  description = "Elastic Cloud region"
  type        = string
  default     = "us-east-1"
}

variable "elastic_version" {
  description = "Elastic Stack version (regex pattern to match latest patch)"
  type        = string
  default     = "8.17.0"
}

variable "deployment_template_id" {
  description = "Elastic Cloud deployment template"
  type        = string
  default     = "aws-storage-optimized"
}

variable "elasticsearch_size" {
  description = "Elasticsearch instance size"
  type        = string
  default     = "4g"
}

variable "elasticsearch_zone_count" {
  description = "Number of availability zones for Elasticsearch"
  type        = number
  default     = 1
}

variable "kibana_size" {
  description = "Kibana instance size"
  type        = string
  default     = "1g"
}

variable "kibana_zone_count" {
  description = "Number of availability zones for Kibana"
  type        = number
  default     = 1
}

variable "integrations_server_size" {
  description = "Integrations server instance size"
  type        = string
  default     = "1g"
}

variable "integrations_server_zone_count" {
  description = "Number of availability zones for Integrations server"
  type        = number
  default     = 1
}

# GitHub Configuration
variable "github_owner" {
  description = "GitHub username or organization"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_-]{1,39}$", var.github_owner))
    error_message = "github_owner must be a valid GitHub username (1-39 characters, alphanumeric, hyphens, underscores)"
  }
}

variable "create_authored_rules_repo" {
  description = "Whether to create the authored-rules repository (clean fork of detection-rules)"
  type        = bool
  default     = true
}

variable "create_enabled_rules_repo" {
  description = "Whether to create the enabled-rules repository"
  type        = bool
  default     = true
}

variable "repo_visibility" {
  description = "Visibility of created repositories (public or private)"
  type        = string
  default     = "public"

  validation {
    condition     = contains(["public", "private"], var.repo_visibility)
    error_message = "repo_visibility must be 'public' or 'private'"
  }
}
