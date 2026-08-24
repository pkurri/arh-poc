# terraform/modules/agentcore_harness/variables.tf
#
# What this file does:
#   - Input variables for the shared agentcore_harness module.
#   - `flavor`: "claude" or "strands" (drives resource naming and prompt selection).
#   - `region`: AWS region for the PoC.
#   - `model_id`: Bedrock model / inference profile ID to use.
#   - `s3_bucket`: Existing shared S3 bucket for the OpenAPI schema upload.
#   - `mock_lambda_source_file`: Path to mock_lambda.py.
#   - `openapi_source_file`: Path to openapi_mock.json.

variable "flavor" {
  description = "Scenario flavor: claude or strands"
  type        = string
}

variable "region" {
  description = "AWS region for the PoC"
  type        = string
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}

variable "openapi_bucket_name" {
  description = "Existing S3 bucket for the OpenAPI schema (new-bucket creation is blocked by SCP in the test account). Set via TF_VAR_openapi_bucket_name or terraform.tfvars."
  type        = string
}

variable "model_id" {
  description = "Bedrock model ID for the harness (must be enabled in the target account/region)"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "inference_profile_id" {
  description = "Bedrock cross-region inference profile ID to invoke (only used if model_id requires one)"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
