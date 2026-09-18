# terraform/scenarios/agentcore-mcp-agent/main.tf
#
# STAGE 2 of 2 - "configuring MCP and the agent in AgentCore".
#
# What this file does:
#   - Creates only the IAM role the Bedrock AgentCore Gateway (the MCP
#     server that exposes tools over the MCP protocol) needs to run.
#   - Depends on Stage 1 (../agentcore-base) already existing: the
#     `agent_runtime_arn` variable ties this gateway's description/tags
#     back to that runtime so it's traceable in the console.
#   - The AWS Terraform provider does not yet support bedrockagentcore
#     resources (verified against provider v5.100.0), so the actual
#     Gateway, its MCP target, and the agent-to-gateway wiring are created
#     imperatively by scripts/configure_agentcore_mcp_agent.py (boto3),
#     consuming this file's outputs together with Stage 1's outputs.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
  common_tags = merge({ Project = "ARH", Stage = "agentcore-mcp-agent" }, var.tags)
}

# Service role for the AgentCore Gateway (the MCP server exposing tools).
resource "aws_iam_role" "gateway_service" {
  name = "arh-agentcore-gateway-role"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "bedrock-agentcore.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = local.account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "gateway_agentcore" {
  name = "AgentCoreGatewayOperations"
  role = aws_iam_role.gateway_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "bedrock-agentcore:*"
      Resource = "*"
    }]
  })
}
