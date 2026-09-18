output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  value = data.aws_region.current.name
}

output "gateway_service_role_arn" {
  value = aws_iam_role.gateway_service.arn
}

output "gateway_name" {
  value = var.gateway_name
}

output "agent_runtime_arn" {
  value = var.agent_runtime_arn
}
