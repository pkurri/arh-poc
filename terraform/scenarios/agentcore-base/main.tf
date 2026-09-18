# terraform/scenarios/agentcore-base/main.tf
#
# STAGE 1 of 2 - "create AgentCore separately, alone".
#
# What this file does:
#   - Creates only what a Bedrock AgentCore Runtime (the agent's compute)
#     needs to exist: its IAM execution role and that role's policies.
#   - Nothing MCP-related lives here - no Gateway, no Gateway role, no
#     tool wiring. That is stage 2, in ../agentcore-mcp-agent, which
#     consumes this stage's `runtime_execution_role_arn` output.
#   - The AWS Terraform provider does not yet support bedrockagentcore
#     resources (verified against provider v5.100.0), so the actual
#     AgentCore Runtime is created imperatively by
#     scripts/setup_agentcore_base.py (boto3), consuming this file's
#     outputs - same pattern as scripts/setup_agentcore.py.
#
# Apply order: this stage first, then terraform/scenarios/agentcore-mcp-agent.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
  common_tags = merge({ Project = "ARH", Stage = "agentcore-base" }, var.tags)
}

# Execution role for the AgentCore Runtime (the agent itself).
resource "aws_iam_role" "runtime_execution" {
  name = "arh-agentcore-runtime-role"
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

resource "aws_iam_role_policy" "runtime_bedrock_invoke" {
  name = "BedrockInvoke"
  role = aws_iam_role.runtime_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
      Resource = [
        "arn:aws:bedrock:*::foundation-model/anthropic.*",
        "arn:aws:bedrock:${local.region}:${local.account_id}:inference-profile/*",
      ]
    }]
  })
}

resource "aws_iam_role_policy" "runtime_agentcore" {
  name = "AgentCoreOperations"
  role = aws_iam_role.runtime_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "bedrock-agentcore:*"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy" "runtime_ecr_pull" {
  name = "PullContainerImage"
  role = aws_iam_role.runtime_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
        ]
        Resource = "arn:aws:ecr:${local.region}:${local.account_id}:repository/*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "runtime_logs" {
  name = "AgentCoreLogs"
  role = aws_iam_role.runtime_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
      ]
      Resource = "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/bedrock-agentcore/*"
    }]
  })
}
