# Cleanup Guide

All AWS resources should be destroyed after testing to avoid ongoing charges.

## Terraform destroy

```bash
# Claude
cd terraform/scenarios/claude-agentcore-harness
terraform destroy -auto-approve

# Strands
cd ../strands-agentcore-harness
terraform destroy -auto-approve

# LangGraph
cd ../langgraph-stepfunctions
terraform destroy -auto-approve
```

## AgentCore Gateways and Harnesses (created by setup_agentcore.py)

Terraform does not manage these. Delete via boto3 or AWS CLI:

```bash
# List gateways
aws bedrock-agentcore list-gateways

# Delete gateway targets first, then the gateway
aws bedrock-agentcore delete-gateway-target --gateway-id <id> --target-id <id>
aws bedrock-agentcore delete-gateway --gateway-id <id>

# List and delete harnesses
aws bedrock-agentcore list-harnesses
aws bedrock-agentcore delete-harness --harness-id <id>
```

## CloudWatch log groups (not auto-deleted by Terraform)

```bash
for lg in \
  /aws/lambda/arh-claude-datapower-mock \
  /aws/lambda/arh-strands-datapower-mock \
  /aws/lambda/arh-langgraph-intake \
  /aws/lambda/arh-langgraph-execute \
  /aws/lambda/arh-langgraph-datapower-mock; do
  aws logs delete-log-group --log-group-name "$lg"
done
```

## S3 temporary objects

```bash
aws s3 rm s3://<SHARED_S3_BUCKET>/tools/ --recursive
aws s3 rm s3://<SHARED_S3_BUCKET>/openapi/mock-datapower.json
```

## Local state files

```bash
rm -f ~/.arh/claude_agentcore.json
rm -f ~/.arh/strands_agentcore.json
```

## Final verification sweep

```bash
# Verify nothing remains
aws stepfunctions list-state-machines --query "stateMachines[?starts_with(name,'arh-')].name" --output text
aws dynamodb list-tables --query "TableNames[?starts_with(@,'arh-')]" --output text
aws lambda list-functions --query "Functions[?starts_with(FunctionName,'arh-')].FunctionName" --output text
aws iam list-roles --query "Roles[?starts_with(RoleName,'arh-')].RoleName" --output text
aws logs describe-log-groups --query "logGroups[?starts_with(logGroupName,'/aws/lambda/arh-')].logGroupName" --output text
aws s3 ls s3://<SHARED_S3_BUCKET>/tools/
```

All commands should return empty output if cleanup is complete.

## Notes

- Step Functions state machines may remain in `DELETING` status for several
  minutes after deletion; this is AWS asynchronous cleanup and incurs no cost.
- AgentCore harnesses may also remain in `DELETING` briefly.
- Gateway targets must be deleted before the gateway itself.
- Cost Explorer data is delayed ~24 hours; final cost figures may not appear
  until the day after testing.
