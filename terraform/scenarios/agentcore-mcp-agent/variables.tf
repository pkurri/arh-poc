# terraform/scenarios/agentcore-mcp-agent/variables.tf
#
# STAGE 2 of 2. Creates the IAM role for the Bedrock AgentCore Gateway
# (the MCP server exposing tools) and points it at the Runtime that Stage 1
# (../agentcore-base) already created. Apply Stage 1 first.

variable "aws_region" {
  description = "AWS region for the AgentCore Gateway (must match Stage 1)"
  type        = string
  default     = "us-east-1"
}

variable "agent_runtime_arn" {
  description = "ARN of the AgentCore Runtime created by Stage 1 (agentcore-base) - `terraform output runtime_execution_role_arn`/agentcore console after running scripts/setup_agentcore_base.py"
  type        = string
}

variable "gateway_name" {
  description = "Name for the AgentCore Gateway (MCP server)"
  type        = string
  default     = "arh-agentcore-gateway"
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
