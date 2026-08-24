# terraform/modules/agentcore_harness/main.tf
#
# What this file does:
#   - Shared Terraform module for the Claude and Strands AgentCore Harness PoCs.
#   - Creates IAM roles for the harness execution and gateway service principals.
#   - Packages and deploys the mock DataPower Lambda (mock_lambda.py).
#   - Uploads the OpenAPI mock schema to the shared S3 bucket (<SHARED_S3_BUCKET>).
#   - Exposes outputs (role ARNs, mock Lambda ARN, OpenAPI S3 URI, account/region)
#     consumed by scripts/setup_agentcore.py to create the AgentCore Gateway + Harness.
#   - The actual AgentCore Gateway and Harness resources are created imperatively
#     by setup_agentcore.py (boto3) because the AWS Terraform provider does not
#     yet support bedrock-agentcore resources.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  prefix     = "arh-${var.flavor}"
  common_tags = merge({
    Project = "ARH"
    Flavor  = var.flavor
  }, var.tags)
  bedrock_model_arn             = "arn:aws:bedrock:${local.region}::foundation-model/${var.model_id}"
  bedrock_inference_profile_arn = "arn:aws:bedrock:${local.region}:${local.account_id}:inference-profile/${var.inference_profile_id}"
}

# Use an existing S3 bucket for the OpenAPI schema; new bucket creation is
# blocked by a service control policy in the target test account.
data "aws_s3_bucket" "openapi" {
  bucket = var.openapi_bucket_name
}

resource "aws_s3_object" "openapi_schema" {
  bucket       = data.aws_s3_bucket.openapi.id
  key          = "openapi/mock-datapower.json"
  content      = file("${path.module}/../../files/openapi_mock.json")
  content_type = "application/json"
  etag         = filemd5("${path.module}/../../files/openapi_mock.json")
}

# Mock DataPower REST API target (invoked by Bedrock AgentCore Gateway)
data "archive_file" "mock_lambda" {
  type        = "zip"
  source_file = "${path.module}/../../files/mock_lambda.py"
  output_path = "${path.module}/.terraform/mock-lambda-${var.flavor}.zip"
}

resource "aws_iam_role" "mock_lambda" {
  name = "${local.prefix}-datapower-mock-role"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "mock_lambda_basic" {
  role       = aws_iam_role.mock_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "data_power_mock" {
  function_name = "${local.prefix}-datapower-mock"
  role          = aws_iam_role.mock_lambda.arn
  handler       = "mock_lambda.handler"
  runtime       = "python3.12"
  filename      = data.archive_file.mock_lambda.output_path
  source_code_hash = data.archive_file.mock_lambda.output_base64sha256
  timeout       = 30
  memory_size   = 256
  tags          = local.common_tags

  environment {
    variables = {
      REVIEW_LINK = "https://example.com/review/TASK-123"
    }
  }
}

# Allow the Bedrock AgentCore service to invoke the mock target
resource "aws_lambda_permission" "agentcore_invoke" {
  statement_id  = "AllowBedrockAgentCore"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_power_mock.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_account = local.account_id
  source_arn    = "arn:aws:bedrock-agentcore:${local.region}:${local.account_id}:harness/*"
}

# Execution role for the Bedrock AgentCore Harness/Runtime
resource "aws_iam_role" "harness_execution" {
  name = "${local.prefix}-harness-execution-role"
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

resource "aws_iam_role_policy" "harness_bedrock" {
  name = "BedrockInvoke"
  role = aws_iam_role.harness_execution.id

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

resource "aws_iam_role_policy" "harness_agentcore" {
  name = "AgentCoreGatewayInvoke"
  role = aws_iam_role.harness_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "bedrock-agentcore:*"
      Resource = "*"
    }]
  })
}

# Service role for the Bedrock AgentCore Gateway so it can read the OpenAPI schema and invoke the mock target
resource "aws_iam_role" "gateway_service" {
  name = "${local.prefix}-gateway-service-role"
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

resource "aws_iam_role_policy" "gateway_service" {
  name = "GatewayOutbound"
  role = aws_iam_role.gateway_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          data.aws_s3_bucket.openapi.arn,
          "${data.aws_s3_bucket.openapi.arn}/*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = [aws_lambda_function.data_power_mock.arn]
      },
    ]
  })
}
