# terraform/modules/langgraph_stepfunctions/main.tf
#
# What this file does:
#   - Terraform module for the LangGraph + Step Functions PoC.
#   - Creates a DynamoDB table (arh-langgraph-checkpoints) for graph state
#     and waitForTaskToken token storage.
#   - Packages and deploys three Lambdas: intake (langgraph_lambda.py),
#     execute (same file, different handler), and the mock DataPower target.
#   - Creates IAM roles for each Lambda and for Step Functions.
#   - Renders the Step Functions state machine definition from
#     state_machine.json.tmpl and creates the state machine with CloudWatch
#     logging enabled (ALL level).
#   - Passes USE_BEDROCK and BEDROCK_MODEL env vars to the intake Lambda so
#     the graph can run in deterministic or Bedrock-driven routing mode.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  prefix     = "arh-langgraph"
  common_tags = {
    Project = "ARH"
    Flavor  = "langgraph"
  }
}

# DynamoDB stores LangGraph checkpoints and Step Functions task tokens
resource "aws_dynamodb_table" "checkpoints" {
  name         = "${local.prefix}-checkpoints"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "case_id"
  range_key    = "sk"
  tags         = local.common_tags

  attribute {
    name = "case_id"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }
}

# Shared mock DataPower REST API for the LangGraph tools node
data "archive_file" "mock_lambda" {
  type        = "zip"
  source_file = "${path.module}/../../files/mock_lambda.py"
  output_path = "${path.module}/.terraform/mock-lambda-langgraph.zip"
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

# LangGraph intake/execute Lambda package
data "archive_file" "langgraph" {
  type        = "zip"
  source_file = "${path.module}/../../files/langgraph_lambda.py"
  output_path = "${path.module}/.terraform/langgraph.zip"
}

resource "aws_iam_role" "langgraph_lambda" {
  name = "${local.prefix}-lambda-role"
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

resource "aws_iam_role_policy_attachment" "langgraph_lambda_basic" {
  role       = aws_iam_role.langgraph_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "langgraph_lambda" {
  name = "${local.prefix}-lambda-policy"
  role = aws_iam_role.langgraph_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
        ]
        Resource = aws_dynamodb_table.checkpoints.arn
      },
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.data_power_mock.arn
      },
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/anthropic.*",
          "arn:aws:bedrock:${local.region}:${local.account_id}:inference-profile/*",
        ]
      },
    ]
  })
}

resource "aws_lambda_function" "intake" {
  function_name = "${local.prefix}-intake"
  role          = aws_iam_role.langgraph_lambda.arn
  handler       = "langgraph_lambda.intake_handler"
  runtime       = "python3.12"
  filename      = data.archive_file.langgraph.output_path
  source_code_hash = data.archive_file.langgraph.output_base64sha256
  timeout       = 60
  memory_size   = 512
  tags          = local.common_tags

  environment {
    variables = {
      CHECKPOINT_TABLE = aws_dynamodb_table.checkpoints.name
      MOCK_LAMBDA_ARN  = aws_lambda_function.data_power_mock.arn
      USE_BEDROCK      = var.use_bedrock ? "true" : "false"
      BEDROCK_MODEL    = var.bedrock_model
    }
  }
}

resource "aws_lambda_function" "execute" {
  function_name = "${local.prefix}-execute"
  role          = aws_iam_role.langgraph_lambda.arn
  handler       = "langgraph_lambda.execute_handler"
  runtime       = "python3.12"
  filename      = data.archive_file.langgraph.output_path
  source_code_hash = data.archive_file.langgraph.output_base64sha256
  timeout       = 60
  memory_size   = 512
  tags          = local.common_tags

  environment {
    variables = {
      CHECKPOINT_TABLE = aws_dynamodb_table.checkpoints.name
      MOCK_LAMBDA_ARN  = aws_lambda_function.data_power_mock.arn
    }
  }
}

# Step Functions execution role
resource "aws_iam_role" "sfn" {
  name = "${local.prefix}-sfn-role"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "sfn" {
  name = "${local.prefix}-sfn-policy"
  role = aws_iam_role.sfn.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          aws_lambda_function.intake.arn,
          aws_lambda_function.execute.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/states/${local.prefix}"
  retention_in_days = 7
  tags              = local.common_tags
}

resource "aws_sfn_state_machine" "main" {
  name     = "${local.prefix}-state-machine"
  role_arn = aws_iam_role.sfn.arn
  type     = "STANDARD"
  tags     = local.common_tags

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = false
    level                  = "ALL"
  }

  definition = templatefile("${path.module}/state_machine.json.tmpl", {
    intake_arn  = aws_lambda_function.intake.arn
    execute_arn = aws_lambda_function.execute.arn
  })
}
