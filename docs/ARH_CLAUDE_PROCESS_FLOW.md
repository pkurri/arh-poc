# ARH Claude AgentCore Harness Process Flow

<!--
ARH_CLAUDE_PROCESS_FLOW.md - Step-by-step explanation of the Claude
AgentCore Harness proof-of-concept. This document explains infrastructure
preparation, tool registration, Gateway/Harness setup, runtime invocation,
tool dispatch, approval behavior, observability, and cleanup.
-->

## 1. Purpose

This document explains how the Claude AgentCore Harness PoC processes a case
from input to final response. It follows the same level of detail as the
LangGraph Step Functions explanation, but the orchestration model is different:

```text
Case input
   |
   v
Bedrock AgentCore Harness
   |
   +--> Bedrock Claude model selects next action
   |
   +--> AgentCore Gateway using MCP
           |
           v
       Mock tool target
           |
           v
       Mock DataPower Lambda
   |
   v
Tool result returned to Claude
   |
   v
Next tool selected
   |
   v
create_decision_task
   |
   v
Final response and usage metadata
```

The Claude Harness owns the agent loop. The application code configures the
Harness and invokes it, but it does not implement the model/tool loop itself.

## 2. Main components

| Component | Responsibility |
|---|---|
| Terraform | Creates IAM roles, the mock Lambda, Lambda permissions, and the OpenAPI S3 object |
| `openapi_mock.json` | Describes the available REST operations and their `operationId` tool names |
| `mock_lambda.py` | Implements the canned results for each mock tool |
| AgentCore Gateway | Exposes the tools through the MCP protocol and routes calls to Lambda |
| AgentCore Harness | Runs the managed Claude agent loop and connects Claude to the Gateway |
| Bedrock Claude | Selects the next tool and generates the final natural-language response |
| `setup_agentcore.py` | Creates or reuses the Gateway and Harness configuration |
| `test_harness.py` | Starts a Harness session and streams the response and usage metadata |
| S3 | Stores the OpenAPI schema and generated MCP tool-definition document |
| IAM | Allows the Gateway, Harness, and Lambda services to assume roles and call required APIs |

Relevant implementation files:

```text
terraform/modules/agentcore_harness/main.tf
terraform/files/openapi_mock.json
terraform/files/mock_lambda.py
scripts/setup_agentcore.py
scripts/test_harness.py
```

## 3. Deployment flow

### Step 1: Configure AWS access

The runner uses the standard AWS credential chain. Credentials should be
provided through AWS SSO, an AWS CLI profile, or environment variables. They
are not stored in the repository.

Example using AWS SSO:

```bash
aws sso login --profile <profile>
AWS_PROFILE=<profile> python3 scripts/run_all_pocs.py --scenario claude
```

The orchestration script validates the AWS identity before running Terraform.
It also checks that the active account matches the configured target account
when `AWS_ACCOUNT_ID` is present in the local, ignored `.env` file.

### Step 2: Apply Terraform

The Claude root scenario invokes the shared `agentcore_harness` module:

```text
terraform/scenarios/claude-agentcore-harness/main.tf
  -> terraform/modules/agentcore_harness/main.tf
```

Terraform creates or manages:

1. Harness execution IAM role
2. Gateway service IAM role
3. Mock Lambda execution IAM role
4. Mock DataPower Lambda
5. Lambda permission for AgentCore invocation
6. Gateway and Harness IAM policies
7. OpenAPI schema object in the configured S3 bucket

The actual AgentCore Gateway and Harness are created by
`setup_agentcore.py`, outside Terraform, because those control-plane resources
are configured through the AgentCore API in this PoC.

### Step 3: Read Terraform outputs

`setup_agentcore.py` reads the applied Terraform outputs, including:

- AWS region
- AWS account identifier
- Harness execution role ARN
- Gateway service role ARN
- Mock Lambda ARN
- OpenAPI schema S3 URI
- Bedrock model or inference-profile configuration

These values connect the Terraform-created resources to the AgentCore control
plane.

## 4. Gateway creation or reuse

The setup script stores local AgentCore state here:

```text
~/.arh/claude_agentcore.json
```

When that file exists and setup is run without `--force`, the script reuses the
stored Gateway and Harness identifiers instead of creating another pair. The
orchestration script deliberately never passes `--force`.

If no reusable state is available, the setup flow is:

```text
setup_agentcore.py
   |
   v
Create Gateway
   |
   v
Wait until Gateway is READY
   |
   v
Build and upload tool definitions
   |
   v
Create Gateway target
   |
   v
Wait until target is READY
   |
   v
Create Harness
   |
   v
Wait until Harness is READY
   |
   v
Save local state
```

### Gateway configuration

The Gateway is configured with:

```text
protocolType: MCP
authorizerType: AWS_IAM
roleArn: gateway service role
```

The Gateway is the managed boundary between the Harness and the backend tools.
Claude does not call the Lambda directly.

## 5. Tool-definition flow

The source OpenAPI document is:

```text
terraform/files/openapi_mock.json
```

Each operation contains an `operationId`, which becomes the tool name. The
schema defines these tools:

| OpenAPI path | `operationId` | Purpose |
|---|---|---|
| `/classify-intent` | `classify_intent` | Classify the incoming case |
| `/extract-fields` | `extract_fields` | Extract relevant case fields |
| `/retrieve-sop` | `retrieve_sop` | Retrieve required checks |
| `/run-validations` | `run_validations` | Run validation checks |
| `/check-similar-cases` | `check_similar_cases` | Search prior cases |
| `/create-decision-task` | `create_decision_task` | Create a human decision task |
| `/execute-transaction` | `execute_transaction` | Execute an approved change |
| `/write-audit-record` | `write_audit_record` | Record the audit result |

`setup_agentcore.py` reads the OpenAPI `paths` object and creates a simplified
MCP tool-definition document containing:

```json
{
  "name": "extract_fields",
  "description": "Extract relevant fields from the case document",
  "inputSchema": {"type": "object", "properties": {}},
  "outputSchema": {"type": "object"}
}
```

The generated document is uploaded under a flavor-specific tools key in the
configured S3 bucket. The Gateway target references that S3 document as its
Lambda tool schema.

## 6. Gateway target configuration

The target connects the Gateway to the mock Lambda:

```text
AgentCore Gateway
   |
   | MCP tool call
   v
Gateway target
   |
   | Lambda ARN + S3 tool schema
   v
mock_lambda.handler
```

The target configuration contains:

```json
{
  "targetConfiguration": {
    "mcp": {
      "lambda": {
        "lambdaArn": "<mock-lambda-arn>",
        "toolSchema": {
          "s3": {
            "uri": "s3://<shared-bucket>/tools/arh-claude-tools.json",
            "bucketOwnerAccountId": "<aws-account-id>"
          }
        }
      }
    }
  }
}
```

The Gateway uses its IAM role to access the target and the Harness uses its
execution role to invoke the Gateway. The Lambda has an explicit permission
allowing AgentCore to invoke it.

## 7. Harness creation

The Harness is created with:

```text
Model: global.anthropic.claude-haiku-4-5-20251001-v1:0
API format: converse_stream
Maximum iterations: 25
Maximum output tokens: 4096
Timeout: 300 seconds
Tool source: AgentCore Gateway
```

The model configuration is supplied through `bedrockModelConfig`:

```json
{
  "model": {
    "bedrockModelConfig": {
      "modelId": "<bedrock-model-or-inference-profile>",
      "maxTokens": 4096,
      "temperature": 0.7,
      "apiFormat": "converse_stream"
    }
  }
}
```

The Harness is also given the Gateway as its tool source:

```json
{
  "type": "agentcore_gateway",
  "config": {
    "agentCoreGateway": {
      "gatewayArn": "<gateway-arn>"
    }
  }
}
```

There is no separate Claude skill package in this PoC. The Harness response
contains `skills: []`; the available capabilities are the Gateway tools and
its `allowedTools` configuration.

## 8. Claude system prompt

The Claude scenario uses a prompt-controlled sequence:

```text
You are a maintenance agent. Process the incoming CONTACTS case. Use the
available tools in this order: extract_fields, retrieve_sop, run_validations,
check_similar_cases, then create_decision_task. Report the final status and
stop after creating the decision task.
```

This prompt performs two jobs:

1. It describes the role and case context.
2. It requests a specific sequence and asks Claude to stop at the decision task.

The prompt is defined in:

```text
scripts/setup_agentcore.py -> SYSTEM_PROMPTS["claude"]
```

The sequence is behavioral. It is not a Step Functions-style infrastructure
pause.

## 9. Runtime invocation flow

`test_harness.py` loads the saved state and creates a runtime session:

```text
1. Load ~/.arh/claude_agentcore.json
2. Read region, Harness ARN, and model metadata
3. Create the bedrock-agentcore client
4. Generate a runtime session ID
5. Call invoke_harness
6. Stream response events
7. Print final text and metadata
```

The invocation request has this shape:

```json
{
  "harnessArn": "<harness-arn>",
  "runtimeSessionId": "<new-session-id>",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "text": "Process the CONTACTS case from the submitted request."
        }
      ]
    }
  ]
}
```

The Harness then runs the managed agent loop. The client receives streamed
`contentBlockDelta` events and final metadata.

## 10. Runtime tool-calling loop

The detailed runtime sequence is:

```text
1. test_harness.py sends the case message to the Harness.
2. The Harness sends the system prompt and available tool metadata to Claude.
3. Claude selects the next tool.
4. The Harness sends the tool call to the AgentCore Gateway.
5. The Gateway authenticates and routes the MCP call to the Gateway target.
6. The target invokes mock_lambda.handler.
7. The mock Lambda returns a JSON result.
8. The Gateway returns the tool result to the Harness.
9. The Harness adds the tool result to the conversation.
10. Claude selects the next tool.
11. Steps 3-10 repeat until Claude stops or reaches its iteration limit.
12. The Harness streams Claude's final response to test_harness.py.
```

In short:

```text
Claude -> Harness -> Gateway -> Lambda -> Gateway -> Harness -> Claude
```

The application does not invoke the mock Lambda directly in the AgentCore
scenario. The Gateway performs that dispatch.

## 11. Observed Claude run

The successful Claude run used the Bedrock Haiku inference profile and produced
this sequence:

| # | Tool | Result or purpose |
|---|---|---|
| 1 | `extract_fields` | Extracted the relevant contact-change fields |
| 2 | `retrieve_sop` | Retrieved the standard procedure and required checks |
| 3 | `run_validations` | Completed address and tax-ID validations |
| 4 | `check_similar_cases` | Reviewed similar prior cases |
| 5 | `create_decision_task` | Created a pending human decision task |

Observed Bedrock metadata:

```json
{
  "usage": {
    "inputTokens": 1798,
    "outputTokens": 165,
    "totalTokens": 1963
  },
  "metrics": {
    "latencyMs": 2505
  }
}
```

Claude returned a final response stating that the decision task was created and
that the case was pending human review.

## 12. Approval behavior

The Claude Harness was instructed to stop after `create_decision_task`. In the
observed run, Claude followed the instruction and did not call
`execute_transaction`.

However, the stop is prompt-controlled:

```text
Claude prompt says: stop after create_decision_task
```

It is not an infrastructure callback boundary. The Harness itself is not
waiting for a `SendTaskSuccess` token in this scenario.

### Claude versus LangGraph approval

| Area | Claude AgentCore Harness | LangGraph + Step Functions |
|---|---|---|
| Agent loop | Managed by AgentCore Harness | Implemented in Lambda code |
| Model call | Harness-managed ConverseStream | Lambda-managed Converse call |
| Tool transport | AgentCore Gateway and MCP | Lambda Invoke |
| State storage | Harness-managed session state | DynamoDB graph checkpoints |
| Approval stop | Prompt-controlled | `waitForTaskToken` callback |
| Can model behavior bypass stop? | Potentially yes | No, workflow remains paused |
| Resume mechanism | New or continued Harness session | `SendTaskSuccess` or `SendTaskFailure` |
| Approval enforcement | Behavioral | Infrastructure-enforced |

For production, the transaction tool or workflow should enforce approval even
when using an AgentCore Harness. A prompt should not be the only control that
prevents a transaction from executing.

## 13. Logging and observability

The PoC exposes evidence at several layers:

### Harness client output

`test_harness.py` prints:

- Session ID
- Streamed Claude text
- Final response text
- Usage metadata when returned
- Latency metrics when returned

### Mock Lambda logs

`mock_lambda.py` logs the tool name and event before returning the mock result.
These logs show which tools were actually called through the Gateway.

### Infrastructure logs

Terraform configures Lambda logging through the standard Lambda CloudWatch log
groups. The Gateway and Harness control-plane responses also expose resource
status during setup.

### What to correlate

For an architect-facing trace, correlate:

```text
Harness session ID
   + model usage metadata
   + streamed response
   + mock Lambda tool log entries
   + Gateway target status
```

The tool sequence should be taken from observed Lambda logs or the captured
Harness trace rather than inferred only from the system prompt.

## 14. Cleanup flow

Terraform manages the supporting AWS resources:

```text
Terraform destroy
   |
   +--> Mock Lambda
   +--> Lambda permission
   +--> IAM policies and roles
   +--> OpenAPI S3 object
```

AgentCore Gateway and Harness resources are created outside Terraform. Their
cleanup order is:

```text
1. Delete Harness
2. Delete Gateway target
3. Delete Gateway
4. Delete temporary MCP tool-definition S3 object
5. Delete Lambda CloudWatch log group if it remains
6. Run terraform destroy for Terraform-managed resources
7. Verify no ARH resources remain
```

Do not delete a Gateway before deleting its targets. AWS rejects that operation
while targets are attached.

## 15. Common setup issues

### Model throughput

Some foundation model IDs cannot be invoked directly with on-demand
throughput in the target region. Use a supported cross-region inference profile
when required.

### Streaming model access

The AgentCore Harness uses `converse_stream`. The selected model and account
must support streaming Converse access.

### IAM propagation

Immediately after role or Gateway creation, a short propagation delay may be
needed before the Harness can access the Gateway. Initial 401 or 403 responses
can occur during this period.

### Harness model parameters

The Harness model configuration accepts the supported model parameters for the
selected model. Do not configure mutually incompatible parameters such as both
`temperature` and `topP` when the model rejects that combination.

### Reuse behavior

Run setup without `--force` to reuse the saved local AgentCore state. Use
`--force` only when intentionally creating a replacement and cleaning up the
older Gateway, target, Harness, and tool-definition object.

## 16. One-command execution

From the project root:

```bash
python3 scripts/run_all_pocs.py \
  --scenario claude \
  --region ap-south-1 \
  --bedrock-model global.anthropic.claude-haiku-4-5-20251001-v1:0
```

The orchestrator performs:

```text
AWS credential validation
   -> Terraform init/apply
   -> AgentCore Gateway/Harness setup or reuse
   -> Harness invocation
   -> Claude tool-calling run
   -> Usage and result output
```

By default, resources are kept after the run. Add `--cleanup` only when the
run is complete and Terraform-managed resources should be destroyed.
