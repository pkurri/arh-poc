# terraform/modules/langgraph_stepfunctions/variables.tf
#
# What this file does:
#   - Input variables for the langgraph_stepfunctions module.
#   - `region`: AWS region.
#   - `environment`: environment tag.
#   - `use_bedrock`: if true, the intake Lambda calls Bedrock Converse for tool
#     selection; if false, it follows a deterministic tool order.
#   - `bedrock_model`: Bedrock model / inference profile ID (only used when
#     use_bedrock=true).

variable "region" {
  description = "AWS region for the PoC"
  type        = string
  default     = "us-east-1"
}

variable "state_machine_name" {
  description = "Name of the Step Functions state machine; use a unique name if a previous state machine is still deleting"
  type        = string
  default     = "arh-langgraph-state-machine"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}

variable "use_bedrock" {
  description = "If true, the LangGraph agent calls Bedrock Converse; otherwise a deterministic sequence is used"
  type        = bool
  default     = false
}

variable "bedrock_model" {
  description = "Bedrock model ID (only used when use_bedrock=true)"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}
