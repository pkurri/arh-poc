# AWS Setup and Testing

## Prerequisites

- AWS account with Bedrock model access enabled
- `terraform >= 1.5.0`
- `python3` with `boto3` (`pip install -r requirements.txt`)
- AWS credentials with permissions for IAM, Lambda, DynamoDB, Step Functions,
  Bedrock, Bedrock AgentCore, and S3

## Run all three scenarios with one command

The repository includes `scripts/run_all_pocs.py` to validate credentials, apply
Terraform, reuse existing AgentCore resources, run the Claude/Strands harnesses,
and run LangGraph. Credentials must come from the standard AWS credential chain;
never hardcode them in the script.

```bash
# AWS SSO
aws sso login --profile <profile>
AWS_PROFILE=<profile> python3 scripts/run_all_pocs.py --scenario all --approve

# Or use credentials already exported in the shell
python3 scripts/run_all_pocs.py --scenario all --approve
```

The script reads `SHARED_S3_BUCKET` from the uncommitted `.env` file for the
AgentCore OpenAPI schema upload. Use `--scenario claude`, `--scenario strands`,
or `--scenario langgraph` to run one scenario. By default LangGraph stops at
`waitForTaskToken`; add `--approve` to automatically resume it. Add `--cleanup`
to destroy Terraform-managed resources after a completed run. Resources are
kept by default, and AgentCore resources created outside Terraform may require
separate AgentCore deletion. Use `--validate-only` to verify local tools and AWS
credentials without changing any resources.

## Scenario 1: Claude AgentCore Harness

```bash
# 1. Deploy infrastructure (IAM roles, mock Lambda, OpenAPI upload)
cd terraform/scenarios/claude-agentcore-harness
terraform init
terraform apply -var="aws_region=ap-south-1" \
  -var="bedrock_model=global.anthropic.claude-haiku-4-5-20251001-v1:0"

# 2. Create AgentCore Gateway + Harness
python3 ../../scripts/setup_agentcore.py --flavor claude \
  --terraform-dir .

# 3. Invoke the harness and capture results
python3 ../../scripts/test_harness.py --flavor claude

# 4. Destroy when done
terraform destroy -auto-approve
```

## Scenario 2: Strands AgentCore Harness

```bash
cd terraform/scenarios/strands-agentcore-harness
terraform init
terraform apply -var="aws_region=ap-south-1" \
  -var="bedrock_model=global.anthropic.claude-haiku-4-5-20251001-v1:0"

python3 ../../scripts/setup_agentcore.py --flavor strands --terraform-dir .
python3 ../../scripts/test_harness.py --flavor strands

terraform destroy -auto-approve
```

## Scenario 3: LangGraph + Step Functions

```bash
cd terraform/scenarios/langgraph-stepfunctions
terraform init
terraform apply -var="aws_region=ap-south-1" \
  -var="use_bedrock=true" \
  -var="bedrock_model=global.anthropic.claude-haiku-4-5-20251001-v1:0"

# Start execution, wait for token, send approval, verify result
python3 ../../scripts/test_langgraph.py \
  --state-machine-arn $(terraform output -raw state_machine_arn) \
  --dynamodb-table $(terraform output -raw dynamodb_table)

terraform destroy -auto-approve
```

## Model selection notes

- `ap-south-1` requires cross-region inference profiles for Claude models.
- `anthropic.claude-3-5-sonnet-20241022-v2:0` requires the account to submit the
  Anthropic "model use case details" form for streaming Converse.
- `global.anthropic.claude-haiku-4-5-20251001-v1:0` was already enabled and used
  for all three successful runs.

## Viewing logs in AWS

### AgentCore Harness (Claude / Strands)

```bash
# Mock Lambda logs (tool calls)
aws logs tail /aws/lambda/arh-claude-datapower-mock --since 30m
aws logs tail /aws/lambda/arh-strands-datapower-mock --since 30m

# Harness invocation details
aws bedrock-agentcore get-harness-session --harness-id <id> --session-id <id>
```

### LangGraph (Step Functions)

```bash
# State machine execution history
aws stepfunctions describe-execution --execution-arn <arn>

# Lambda logs
aws logs tail /aws/lambda/arh-langgraph-intake --since 30m
aws logs tail /aws/lambda/arh-langgraph-execute --since 30m

# DynamoDB state
aws dynamodb get-item --table-name arh-langgraph-checkpoints \
  --key '{"case_id":{"S":"CASE-001"},"sk":{"S":"state"}}'
```
