# terraform/modules/agentcore_harness/versions.tf
#
# What this file does:
#   - Pins the Terraform version (>= 1.5.0) and required provider versions
#     (aws ~> 5.0, archive ~> 2.0, random ~> 3.0) for the agentcore_harness module.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
