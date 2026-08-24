# Architecture Overview

## Shared tool set (8 tools)

All three scenarios process the same CONTACTS/REVIEW_QUEUE case and use the same 8 tools,
exposed via a mock DataPower REST API (OpenAPI schema):

| Tool | Purpose |
|---|---|
| `classify_intent` | Classifies the case as CONTACTS, HIGH confidence, REVIEW_QUEUE work group |
| `extract_fields` | Extracts date of birth, address, tax ID from the case document |
| `retrieve_sop` | Returns required validation checks (address, tax_id, duplicate) |
| `run_validations` | Runs address/tax-id/duplicate validation checks |
| `check_similar_cases` / `search_similar_cases` | Searches for similar prior cases |
| `create_decision_task` | Creates a human-approval task in the REVIEW_QUEUE decision queue |
| `execute_transaction` | Posts the approved transaction to the backend case-management system |
| `write_audit_record` | Writes an audit record for the completed case |

## Architecture per scenario

### Scenario 1 & 2: Bedrock AgentCore Harness (Claude / Strands)

```
Case text
  -> Bedrock AgentCore Harness (model: Claude Haiku 4.5)
     -> AgentCore Gateway (AWS_IAM auth, MCP protocol)
        -> Lambda target (mock DataPower)
           -> Returns tool results
     <- Model decides next tool
  -> Harness returns transcript + token usage
```

The harness is a fully managed AWS service that runs the agent loop (model
invocation + tool calling) server-side. The Gateway exposes the mock Lambda's
tools via MCP and the harness calls through it.

### Scenario 3: LangGraph + Step Functions

```
StartExecution (case_id, case_text)
  -> Step Functions: Intake state
     -> Lambda: intake (LangGraph node loop)
        -> Bedrock Converse (selects next tool) [if USE_BEDROCK=true]
        -> Lambda: mock DataPower (executes tool)
        -> DynamoDB: persist graph state
        -> After create_decision_task: store task token, return PENDING
     -> waitForTaskToken (BLOCKS)
  <- External: SendTaskSuccess (decision=Approved)
  -> Step Functions: Execute state
     -> Lambda: execute (execute_transaction + write_audit_record)
  -> SUCCEEDED
```

The agent loop lives inside the intake Lambda. Step Functions enforces the
human-approval boundary via `waitForTaskToken`.

## Key architectural difference

| Aspect | AgentCore Harness | LangGraph + Step Functions |
|---|---|---|
| Agent loop owner | AWS managed harness service | Your Lambda code |
| Tool transport | AgentCore Gateway (MCP) | Lambda Invoke |
| State storage | Harness-managed | DynamoDB |
| Human approval | Prompt-dependent (not enforced) | `waitForTaskToken` (enforced) |
| Model invocation | Harness calls Bedrock | Lambda calls Bedrock Converse |
