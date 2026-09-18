# terraform/scenarios/agentcore-base/variables.tf
#
# STAGE 1 of 2. Only the IAM role a bare Bedrock AgentCore Runtime needs
# to run - no Gateway, no MCP wiring. See ../agentcore-mcp-agent for stage 2.

variable "aws_region" {
  description = "AWS region for the AgentCore Runtime + Gateway"
  type        = string
  default     = "us-east-1"
}

variable "container_uri" {
  description = <<-EOT
    ECR image URI for the AgentCore Runtime's agent code
    (e.g. "<account-id>.dkr.ecr.<region>.amazonaws.com/my-agent:latest").
    Build and push this yourself (e.g. with `agentcore launch` or a plain
    docker build/push) before applying - this module does not create an
    ECR repository or build an image, to avoid any dependency on bucket
    or registry creation permissions.
  EOT
  type        = string
}

variable "bedrock_model" {
  description = "Bedrock model ID the runtime's execution role is allowed to invoke"
  type        = string
  default     = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "runtime_name" {
  description = "Name for the AgentCore Runtime"
  type        = string
  default     = "arh-agentcore-runtime"
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
