# Scenario 3 - LangGraph Step Functions

## Configuration

- **Runtime:** AWS Step Functions standard state machine
- **Model:** `global.anthropic.claude-haiku-4-5-20251001-v1:0` (when `USE_BEDROCK=true`)
- **Routing mode:** Bedrock-driven (LLM selects each next tool via Bedrock Converse)
- **State storage:** DynamoDB (`arh-langgraph-checkpoints`)
- **Human approval:** `waitForTaskToken` (structurally enforced)

## Two routing modes

1. **Deterministic** (`USE_BEDROCK=false`): hardcoded tool order, no model invoked.
2. **Bedrock-enabled** (`USE_BEDROCK=true`): Lambda calls Bedrock Converse at each
   node to select the next tool. This is the mode used in the final successful run.

## Run result (Bedrock-enabled, CASE-BEDROCK-002)

- **Status:** SUCCEEDED
- **Execution:** `bedrock-1787583767`
- **Start:** 2026-08-24T11:02:48
- **Stop:** 2026-08-24T11:08:58
- **Final output:** `{"case_id":"CASE-BEDROCK-002","decision":"Approved","status":"CLOSED"}`

## Bedrock-selected tool sequence (intake phase)

| # | Tool selected by Bedrock | Mock result |
|---|---|---|
| 1 | `extract_fields` | Redacted DOB; extracted address and tax ID |
| 2 | `retrieve_sop` | Required checks: address, tax ID, duplicate |
| 3 | `run_validations` | Address valid; tax ID valid; duplicate check skipped |
| 4 | `search_similar_cases` | Two approved similar cases returned |
| 5 | `create_decision_task` | task_id: TASK-123, status: PENDING |

After `create_decision_task`, the Lambda stored the task token in DynamoDB and
returned `PENDING`. The execution paused at `waitForTaskToken`.

## Approval and resume (execute phase)

`SendTaskSuccess` was called with `{"decision":"Approved"}`. The state machine
resumed and the execute Lambda called:

| # | Tool | Mock result |
|---|---|---|
| 6 | `execute_transaction` | `{"status": "APPROVED", "message": "contacts updated"}` |
| 7 | `write_audit_record` | `{"status": "recorded"}` |

Execution reached `SUCCEEDED` with `status: CLOSED`.

## Key implementation notes

- **Bedrock client cache collision:** first Bedrock-enabled attempt failed with
  `'function' object has no attribute 'converse'` because the module-level cache
  variable and the factory function were both named `_bedrock`. Fixed by renaming.
- **`waitForTaskToken` is intentionally blocking:** the execution pauses at Intake
  until an external `SendTaskSuccess`/`SendTaskFailure` is made. This cannot be
  bypassed by the model, even with Bedrock-driven routing.
- **Model naming:** Bedrock selected `search_similar_cases` (matching the prompt's
  tool name) rather than `check_similar_cases` (the mock's internal name). The mock
  doesn't strictly validate tool names. Production systems should enforce exact matching.

## Comparison: deterministic vs Bedrock-enabled

| Aspect | Deterministic | Bedrock-enabled |
|---|---|---|
| Tool selection | Hardcoded order | LLM chooses via Bedrock Converse |
| Model invoked | No | Yes (Haiku 4.5) |
| Human approval | `waitForTaskToken` | `waitForTaskToken` |
| Cost | Lambda + SFN only | Lambda + SFN + Bedrock inference |
| Latency | Lower | Higher (one Bedrock call per node) |

## Files

- `terraform/scenarios/langgraph-stepfunctions/` - Terraform scenario
- `terraform/modules/langgraph_stepfunctions/` - Module (DynamoDB, Lambdas, SFN)
- `terraform/files/langgraph_lambda.py` - Lambda implementing the graph node loop
- `terraform/files/mock_lambda.py` - Mock DataPower target
- `scripts/test_langgraph.py` - End-to-end test driver
- `docs/ARH_LANGGRAPH_RUN_REPORT.md` - Full run report
- `proper_pdfs/ARH_LANGGRAPH_RUN_REPORT.pdf` - PDF version
