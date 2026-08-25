# terraform/scenarios/strands-agentcore-harness/main.tf
#
# What this file does:
#   - Root Terraform scenario for the Strands Agents on Bedrock AgentCore Harness PoC.
#   - Configures the AWS provider and invokes the shared agentcore_harness module
#     with flavor="strands" and the selected Bedrock model.
#   - Exposes outputs and the setup_agentcore.py command to run after apply.

provider "aws" {
  region = var.aws_region
}

module "agentcore_harness" {
  source              = "../../modules/agentcore_harness"
  flavor              = "strands"
  region              = var.aws_region
  model_id            = var.bedrock_model
  openapi_bucket_name = var.openapi_bucket_name
}

output "harness_execution_role_arn" {
  value = module.agentcore_harness.harness_execution_role_arn
}

output "mock_lambda_arn" {
  value = module.agentcore_harness.mock_lambda_arn
}

output "openapi_s3_uri" {
  value = module.agentcore_harness.openapi_s3_uri
}

output "gateway_service_role_arn" {
  description = "ARN of the IAM role for the Bedrock AgentCore Gateway"
  value       = module.agentcore_harness.gateway_service_role_arn
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = module.agentcore_harness.aws_account_id
}

output "bedrock_model" {
  description = "Bedrock model used"
  value       = var.bedrock_model
}

output "setup_command" {
  description = "Next command to run after terraform apply"
  value       = "python3 ${path.module}/../../scripts/setup_agentcore.py --flavor strands --terraform-dir ${path.module}"
}
