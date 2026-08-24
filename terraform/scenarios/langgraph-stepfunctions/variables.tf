# terraform/scenarios/langgraph-stepfunctions/variables.tf
#
# What this file does:
#   - Input variables for the LangGraph + Step Functions scenario.
#   - `aws_region`: AWS region (default us-east-1; overridden to ap-south-1 in testing).
#   - `use_bedrock`: if true, the intake Lambda calls Bedrock Converse for tool
#     selection; if false, deterministic routing (default true).
#   - `bedrock_model`: Bedrock model / inference profile ID
#     (default global.anthropic.claude-haiku-4-5-20251001-v1:0).

variable "aws_region" {
  description = "AWS region for the PoC"
  type        = string
  default     = "us-east-1"
}

variable "use_bedrock" {
  description = "If true, the LangGraph agent calls Bedrock Converse"
  type        = bool
  default     = true
}

variable "bedrock_model" {
  description = "Bedrock model ID (only used when use_bedrock=true)"
  type        = string
  default     = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
}
