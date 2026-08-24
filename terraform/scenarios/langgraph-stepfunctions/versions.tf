# terraform/scenarios/langgraph-stepfunctions/versions.tf
#
# What this file does:
#   - Pins Terraform version (>= 1.5.0) and the AWS provider (~> 5.0) for the
#     LangGraph + Step Functions scenario.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
