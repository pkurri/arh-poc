# terraform/scenarios/claude-agentcore-harness/variables.tf
#
# What this file does:
#   - Input variables for the Claude AgentCore Harness scenario.
#   - `aws_region`: AWS region (default us-east-1; overridden to ap-south-1 in testing).
#   - `bedrock_model`: Bedrock model / inference profile ID
#     (default global.anthropic.claude-haiku-4-5-20251001-v1:0).

variable "aws_region" {
  description = "AWS region for the PoC"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_model" {
  description = "Bedrock model ID (must be enabled in the account/region)"
  type        = string
  default     = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "openapi_bucket_name" {
  description = "Existing S3 bucket used for the OpenAPI tool schema"
  type        = string
}
