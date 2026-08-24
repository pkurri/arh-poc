# terraform/modules/agentcore_harness/outputs.tf
#
# What this file does:
#   - Exposes module outputs consumed by setup_agentcore.py:
#     harness execution role ARN, gateway service role ARN, mock Lambda ARN,
#     OpenAPI S3 URI, AWS account ID, region, and the resolved inference profile ID.

output "harness_execution_role_arn" {
  description = "ARN of the IAM role for the Bedrock AgentCore Harness"
  value       = aws_iam_role.harness_execution.arn
}

output "gateway_service_role_arn" {
  description = "ARN of the IAM role for the Bedrock AgentCore Gateway"
  value       = aws_iam_role.gateway_service.arn
}

output "mock_lambda_arn" {
  description = "ARN of the mock DataPower Lambda"
  value       = aws_lambda_function.data_power_mock.arn
}

output "openapi_s3_uri" {
  description = "S3 URI of the OpenAPI schema"
  value       = "s3://${data.aws_s3_bucket.openapi.id}/${aws_s3_object.openapi_schema.key}"
}

output "openapi_s3_bucket" {
  description = "S3 bucket holding the OpenAPI schema"
  value       = data.aws_s3_bucket.openapi.id
}

output "openapi_s3_key" {
  description = "S3 key of the OpenAPI schema"
  value       = aws_s3_object.openapi_schema.key
}

output "aws_region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "inference_profile_id" {
  description = "Bedrock cross-region inference profile ID used by the harness"
  value       = var.inference_profile_id
}
