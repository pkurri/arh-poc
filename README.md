# Project ARH — AWS Bedrock AgentCore / LangGraph PoC

This repository contains the source documents, searchable PDFs, Terraform infrastructure, and test scripts for three ARH runtime harness proof-of-concepts:

1. **Claude Agent SDK on Bedrock AgentCore Runtime**
2. **LangGraph + AWS Step Functions Runtime**
3. **Strands Agents on Bedrock AgentCore Runtime**

## Repository layout

```
.
├── proper_pdfs/                       # OCR-searchable copies of the three source PDFs
├── terraform/
│   ├── files/                         # Shared Lambda code and OpenAPI schema
│   ├── modules/
│   │   ├── agentcore_harness/         # Shared base for Claude and Strands AgentCore PoCs
│   │   └── langgraph_stepfunctions/   # LangGraph + Step Functions PoC
│   └── scenarios/
│       ├── claude-agentcore-harness/
│       ├── strands-agentcore-harness/
│       └── langgraph-stepfunctions/
├── scripts/
│   ├── setup_agentcore.py             # Create AgentCore Gateway + Harness after Terraform apply
│   ├── test_harness.py                # Invoke a Bedrock AgentCore Harness
│   └── test_langgraph.py              # Start and resume a Step Functions execution
├── docs/                              # Markdown source for the run reports and comparison
├── wiki/                              # DeepWiki / GitHub wiki pages
├── cost_estimate.py                   # Generate a cost estimate for the PoC test run
├── .env.example                       # Template for environment-specific values (copy to .env)
└── requirements.txt
```

## Prerequisites

- AWS CLI v2 and valid credentials with enough privilege to create IAM, Lambda, S3, DynamoDB, Step Functions, and Bedrock resources.
- Terraform >= 1.5.0.
- Python 3.9+ and `boto3 >= 1.35.0`.
- Access to **Amazon Bedrock** and, if you run the AgentCore scenarios, the **Bedrock AgentCore** control/data planes in the target account/region.
- An existing S3 bucket for the OpenAPI schema upload (the test account's SCP blocks new bucket creation).

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Environment setup

Environment-specific values (AWS account ID, S3 bucket name, region, model) are
stored in a `.env` file that is **not** committed to git. Copy the template and
fill in your values:

```bash
cp .env.example .env
# Edit .env with your AWS account ID, S3 bucket name, region, and model
```

For Terraform scenarios, each scenario directory has a `terraform.tfvars.example`
file. Copy it to `terraform.tfvars` and fill in your values (the `.tfvars` file
is also gitignored).

## Cost estimate

Run the cost estimator (detailed assumptions are inside the script):

```bash
python3 cost_estimate.py --runs 1 --use-bedrock --output COST_ESTIMATE.md
```

The script produces an itemised markdown table. Bedrock model usage dominates the cost when enabled.

## 1. Claude Agent SDK (Bedrock AgentCore Harness)

```bash
cd terraform/scenarios/claude-agentcore-harness
terraform init
terraform plan
terraform apply

# After apply, create the AgentCore Gateway and Harness
python3 ../../scripts/setup_agentcore.py --flavor claude --terraform-dir .

# Invoke the harness
python3 ../../scripts/test_harness.py --flavor claude
```

## 2. Strands Agents (Bedrock AgentCore Harness)

```bash
cd terraform/scenarios/strands-agentcore-harness
terraform init
terraform plan
terraform apply

python3 ../../scripts/setup_agentcore.py --flavor strands --terraform-dir .
python3 ../../scripts/test_harness.py --flavor strands
```

## 3. LangGraph + Step Functions

```bash
cd terraform/scenarios/langgraph-stepfunctions
terraform init
terraform plan
terraform apply

# Start and resume the workflow
python3 ../../scripts/test_langgraph.py \
  --state-machine-arn $(terraform output -raw state_machine_arn) \
  --dynamodb-table $(terraform output -raw dynamodb_table)
```

## Cleaning up

Each scenario can be destroyed with:

```bash
terraform destroy
```

For the AgentCore scenarios, the `setup_agentcore.py` created Bedrock AgentCore resources (gateway, target, harness). They must be deleted with the console or with `aws bedrock-agentcore-control delete-harness`, `delete-gateway-target`, and `delete-gateway` before `terraform destroy` if you want to keep the Terraform state consistent.

## Important notes

- The mock DataPower REST targets are implemented as AWS Lambda functions. The AgentCore Gateway wraps them as tools for the two AgentCore harnesses.
- The OpenAPI schema lives in S3 and is referenced by `create-gateway-target`.
- The LangGraph PoC uses AWS Step Functions `waitForTaskToken` to pause for a human decision. The test script reads the token from DynamoDB and resumes with `Approved`/`Denied`.
- Default AWS region is `us-east-1` and default model is `anthropic.claude-3-5-sonnet-20241022-v2:0`. Override in each scenario's `terraform.tfvars` or with `-var`.
