# Harness Comparison

## Side-by-side comparison

| | Claude AgentCore | Strands AgentCore | LangGraph + SFN |
|---|---|---|---|
| **Agent loop owner** | Bedrock AgentCore Harness | Bedrock AgentCore Harness | Lambda (langgraph_lambda.py) |
| **AWS orchestrator** | Bedrock AgentCore Runtime | Bedrock AgentCore Harness | AWS Step Functions |
| **Human decision point** | Prompt-instructed stop | Not enforced | `waitForTaskToken` (structural) |
| **State storage** | Harness-managed | Harness-managed | DynamoDB |
| **Tool transport** | AgentCore Gateway (MCP) | AgentCore Gateway (MCP) | Lambda Invoke |
| **Model used** | Haiku 4.5 (global profile) | Haiku 4.5 (global profile) | Haiku 4.5 (global profile) |
| **Token usage** | 1987 total | 2275 total | Not captured in Lambda logs |
| **Latency** | 2500 ms | 3106 ms | ~6894 ms intake + ~1021 ms execute |
| **Tools called** | 5 | 8 | 7 (5 intake + 2 execute) |
| **Stopped at approval?** | Yes (prompt-driven) | No (continued autonomously) | Yes (structurally enforced) |
| **Final status** | Pending human review | Completed autonomously | CLOSED (after approval) |

## AWS API calls during a run

### Claude / Strands (AgentCore)

1. `s3:PutObject` - OpenAPI schema + tool definitions to S3
2. `iam:CreateRole` - gateway-service, harness-execution, datapower-mock roles
3. `lambda:CreateFunction` - mock DataPower Lambda
4. `bedrock-agentcore:CreateGateway` + `CreateGatewayTarget`
5. `bedrock-agentcore:CreateHarness`
6. `bedrock-agentcore:InvokeHarness` - starts the agent session
7. `bedrock:InvokeModel` (ConverseStream) - model inference (harness-managed)
8. `lambda:InvokeFunction` - tool calls through the gateway

### LangGraph (Step Functions)

1. `dynamodb:CreateTable` - arh-langgraph-checkpoints
2. `iam:CreateRole` - Lambda and Step Functions roles
3. `lambda:CreateFunction` - intake, execute, datapower-mock
4. `states:CreateStateMachine`
5. `states:StartExecution`
6. `lambda:InvokeFunction` - intake Lambda (runs the graph loop)
7. `bedrock:InvokeModel` (Converse) - at each node when USE_BEDROCK=true
8. `lambda:InvokeFunction` - mock DataPower (tool calls)
9. `dynamodb:PutItem` / `GetItem` - state persistence
10. `states:SendTaskSuccess` - resume after approval
11. `lambda:InvokeFunction` - execute Lambda
12. `states:DescribeExecution` - check final status

## Architectural conclusions

1. **AgentCore Harness** is the most managed option: AWS runs the agent loop,
   handles model invocation, tool dispatch, and streaming. You provide the model,
   system prompt, and gateway (tool source). Trade-off: less control over the loop
   and no built-in human-approval enforcement.

2. **LangGraph + Step Functions** gives full control over the agent loop and
   structurally enforces human approval via `waitForTaskToken`. Trade-off: you
   manage the graph logic, state persistence, and model calls yourself.

3. **Prompt-driven approval boundaries are not reliable.** The Strands run proved
   that an unscripted model will continue past a "create decision task" step.
   Always enforce approval at the infrastructure/tool level.

4. **Bedrock-driven routing in LangGraph** combines model-driven tool selection
   with structural approval enforcement - the best of both worlds for cases where
   the tool sequence is not known in advance.
