# terraform/scenarios/langgraph-stepfunctions/main.tf
#
# What this file does:
#   - Root Terraform scenario for the LangGraph + AWS Step Functions PoC.
#   - Configures the AWS provider and invokes the langgraph_stepfunctions module
#     with use_bedrock and bedrock_model variables.
#   - Exposes outputs: state machine ARN/name, DynamoDB table name, and the
#     test_langgraph.py resume command to run after apply.

provider "aws" {
  region = var.aws_region
}

module "langgraph" {
  source        = "../../modules/langgraph_stepfunctions"
  region        = var.aws_region
  use_bedrock   = var.use_bedrock
  bedrock_model = var.bedrock_model
}

output "state_machine_arn" {
  value = module.langgraph.state_machine_arn
}

output "state_machine_name" {
  value = module.langgraph.state_machine_name
}

output "dynamodb_table" {
  value = module.langgraph.dynamodb_table
}

output "test_start_command" {
  value = module.langgraph.start_execution_command
}

output "test_resume_command" {
  value = "python3 ${path.module}/../../scripts/test_langgraph.py --state-machine-arn ${module.langgraph.state_machine_arn} --dynamodb-table ${module.langgraph.dynamodb_table}"
}
