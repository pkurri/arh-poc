output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  value = data.aws_region.current.name
}

output "runtime_execution_role_arn" {
  value = aws_iam_role.runtime_execution.arn
}

output "bedrock_model" {
  value = var.bedrock_model
}

output "container_uri" {
  value = var.container_uri
}

output "runtime_name" {
  value = var.runtime_name
}
