# terraform/scenarios/claude-agentcore-harness/main.tf
#
# What this file does:
#   - Root Terraform scenario for the Claude Agent SDK on Bedrock AgentCore Harness PoC.
#   - Configures the AWS provider for the target region.
#   - Invokes the shared agentcore_harness module with flavor="claude" and the
#     selected Bedrock model.
#   - Exposes outputs (role ARNs, mock Lambda ARN, OpenAPI S3 URI, setup command)
#     used by scripts/setup_agentcore.py to create the AgentCore Gateway + Harness.

provider "aws" {
  region = var.aws_region
}

module "agentcore_harness" {
  source   = "../../modules/agentcore_harness"
  flavor   = "claude"
  region   = var.aws_region
  model_id = var.bedrock_model
}
