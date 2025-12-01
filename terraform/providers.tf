terraform {
  required_version = ">= 1.0"

  required_providers {
    ec = {
      source  = "elastic/ec"
      version = "~> 0.10"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# Elastic Cloud Provider - uses EC_API_KEY from environment
provider "ec" {}

# GitHub Provider - uses GITHUB_TOKEN from environment
provider "github" {}
