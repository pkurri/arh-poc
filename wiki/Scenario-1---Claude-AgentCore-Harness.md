# Scenario 1 - Claude AgentCore Harness

## Configuration

- **Runtime:** Bedrock AgentCore Harness (managed)
- **Model:** `global.anthropic.claude-haiku-4-5-20251001-v1:0`
- **API format:** `converse_stream`
- **Gateway auth:** AWS_IAM
- **System prompt:** Prescribed tool order (extract_fields -> retrieve_sop ->
  run_validations -> check_similar_cases -> create_decision_task), instructed
  to stop after create_decision_task.

## Run result

- **Status:** SUCCEEDED
- **Input tokens:** 1790
- **Output tokens:** 197
- **Total tokens:** 1987
- **Latency:** 2500 ms

## Tool call sequence

| # | Tool | Purpose |
|---|---|---|
| 1 | `extract_fields` | Extract relevant fields from the case document |
| 2 | `retrieve_sop` | Retrieve the standard operating procedure |
| 3 | `run_validations` | Run address and tax ID validation checks |
| 4 | `check_similar_cases` | Search for similar prior cases |
| 5 | `create_decision_task` | Create a human approval task in the REVIEW_QUEUE queue |

The harness **stopped at the human-approval boundary** as instructed. The stop
was behavioral (prompt-driven), not structurally enforced.

## Key implementation notes

- `anthropic.claude-3-5-sonnet-20241022-v2:0` requires a cross-region inference
  profile in `ap-south-1` and the account must submit the Anthropic "model use
  case details" form for streaming Converse. Haiku 4.5 was already enabled.
- The harness model config cannot set both `temperature` and `topP`; only one
  may be specified.
- Gateway IAM auth initially returned 403/401; resolved after IAM propagation
  and adding `bedrock-agentcore:*` to the harness execution role.

## Files

- `terraform/scenarios/claude-agentcore-harness/` - Terraform scenario
- `terraform/modules/agentcore_harness/` - Shared module
- `scripts/setup_agentcore.py` - Creates the Gateway + Harness
- `scripts/test_harness.py` - Invokes the Harness and captures output
- `docs/ARH_CLAUDE_RUN_REPORT.md` - Full run report
- `proper_pdfs/ARH_CLAUDE_RUN_REPORT.pdf` - PDF version
