# terraform/modules/langgraph_stepfunctions/outputs.tf
#
# What this file does:
#   - Exposes module outputs: state machine ARN/name, DynamoDB table name,
#     intake/execute/mock Lambda ARNs, and a ready-to-run start-execution
#     CLI command for quick testing.

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.main.arn
}

output "state_machine_name" {
  description = "Name of the Step Functions state machine"
  value       = aws_sfn_state_machine.main.name
}

output "dynamodb_table" {
  description = "DynamoDB table used for checkpoints"
  value       = aws_dynamodb_table.checkpoints.name
}

output "intake_lambda_arn" {
  description = "ARN of the intake Lambda"
  value       = aws_lambda_function.intake.arn
}

output "execute_lambda_arn" {
  description = "ARN of the execute Lambda"
  value       = aws_lambda_function.execute.arn
}

output "mock_lambda_arn" {
  description = "ARN of the mock DataPower Lambda"
  value       = aws_lambda_function.data_power_mock.arn
}

output "start_execution_command" {
  description = "AWS CLI command to start a test execution"
  value       = "aws stepfunctions start-execution --state-machine-arn ${aws_sfn_state_machine.main.arn} --input '{\"case_id\":\"CASE-TEST-001\",\"case_text\":\"A broker emailed a change to the group contacts.\"}'"
}
