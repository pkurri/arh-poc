# terraform/scenarios/claude-agentcore-harness/outputs.tf
#
# What this file does:
#   - Passes through module outputs (harness execution role ARN, mock Lambda ARN,
#     OpenAPI S3 URI, gateway service role ARN, region, account, model) and
#     prints the setup_agentcore.py command to run after `terraform apply`.

output "harness_execution_role_arn" {
  description = "ARN of the IAM role for the Bedrock AgentCore Harness"
  value       = module.agentcore_harness.harness_execution_role_arn
}

output "mock_lambda_arn" {
  description = "ARN of the mock DataPower Lambda"
  value       = module.agentcore_harness.mock_lambda_arn
}

output "openapi_s3_uri" {
  description = "S3 URI of the OpenAPI schema"
  value       = module.agentcore_harness.openapi_s3_uri
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
  value       = module.agentcore_harness.inference_profile_id
}

output "setup_command" {
  description = "Next command to run after terraform apply"
  value       = "python3 ${path.module}/../../scripts/setup_agentcore.py --flavor claude --terraform-dir ${path.module}"
}
