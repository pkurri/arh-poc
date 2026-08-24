# Cost Estimate

## Pre-run estimate (from cost_estimate.py)

Assumptions: 1 run per scenario; Bedrock model costs included.

| Scenario | Bedrock | Lambda | Step Functions | DynamoDB | AgentCore | Total |
|---|---|---|---|---|---|---|
| Claude AgentCore | ~$0.006 | ~$0.001 | - | - | ~$0.017 | ~$0.024 |
| Strands AgentCore | ~$0.007 | ~$0.001 | - | - | ~$0.017 | ~$0.025 |
| LangGraph + SFN | ~$0.006 | ~$0.001 | ~$0.0001 | ~$0.0001 | - | ~$0.007 |
| **Total** | | | | | | **~$0.056** |

## Actual Cost Explorer figures

Cost Explorer data is delayed ~24 hours. Figures below are from the test period
(account <AWS_ACCOUNT_ID>, ap-south-1).

### ARH-attributable costs

| Service | Amount | Notes |
|---|---|---|
| Amazon Bedrock AgentCore | ~$0.0174 | Harness usage during Claude/Strands runs |
| Amazon DynamoDB | ~$0.00001 | Checkpoint table reads/writes |
| Amazon S3 | ~$0.0005 | OpenAPI + tool definition uploads |
| Amazon Bedrock (Haiku inference) | ~$0.01-0.02 | Model calls across all three runs |
| **ARH total** | **~$0.03-0.04** | |

### Account baseline (not ARH-attributable)

| Service | Daily cost | Notes |
|---|---|---|
| CloudWatch | ~$1.22/day | Shared monitoring infrastructure |
| RDS | ~$2.44/day | Unrelated databases |
| ECS | ~$1.74/day | Unrelated containers |
| EC2 / ELB / VPC | ~$3.66/day | Unrelated compute/networking |
| KMS / Config / Security Hub | ~$1.23/day | Shared security/compliance |

The ARH PoC cost is negligible (~$0.03-0.04) compared to the account's
pre-existing baseline (~$10+/day from shared infrastructure).

## How to check costs

```bash
# Last 3 days, grouped by service
aws ce get-cost-and-usage \
  --time-period Start=2026-08-22,End=2026-08-25 \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by "Type=DIMENSION,Key=SERVICE" \
  --output table
```
