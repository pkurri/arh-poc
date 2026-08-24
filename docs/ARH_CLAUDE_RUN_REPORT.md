# Project ARH — Claude Agent SDK on Bedrock AgentCore Harness

**Generated:** 2026-08-24 16:00 UTC
**AWS account:** <AWS_ACCOUNT_ID>
**Region:** ap-south-1
**Model:** `global.anthropic.claude-haiku-4-5-20251001-v1:0` (Bedrock cross-region inference profile)
**Result:** SUCCEEDED — full end-to-end run

## What was created

- IAM harness execution role (`bedrock:InvokeModel*`, `bedrock-agentcore:*`)
- IAM gateway service role
- AgentCore Gateway (`AWS_IAM` authorizer, MCP protocol)
- AgentCore Gateway target (Lambda-backed, tool schema from OpenAPI mock)
- AgentCore Harness (`converse_stream` API format)
- Mock DataPower Lambda exposing 8 tools

## System prompt (prescribed tool order)

> You are a small-group insurance maintenance agent. Process the incoming CONTACTS case for
> work group REVIEW_QUEUE. Use the available tools in this order: extract_fields, retrieve_sop,
> run_validations, check_similar_cases, then create_decision_task. Report the final status
> and stop after creating the decision task.

## Harness transcript (real Bedrock output)

```
I'll process the CONTACTS case for REVIEW_QUEUE work group. Let me start by extracting the relevant fields from the case document.Now let me retrieve the standard operating procedure for this CONTACTS intent:Now I'll run the validation checks:Now let me check for similar cases:Now I'll create a decision task in the REVIEW_QUEUE decision queue for human approval:**Final Status: CONTACTS Case Processing Complete**

I have successfully processed the CONTACTS case for the REVIEW_QUEUE work group. Here's what was completed:

1. ✅ **Extracted Fields** - Relevant contact change information extracted from the broker's submission
2. ✅ **Retrieved SOP** - Standard operating procedure for contact updates retrieved
3. ✅ **Ran Validations** - Address and tax ID validation checks completed
4. ✅ **Checked Similar Cases** - Reviewed for any related prior cases
5. ✅ **Created Decision Task** - A human approval task has been created in the REVIEW_QUEUE decision queue

The case is now pending human review and approval in the REVIEW_QUEUE work group decision queue. The broker's contact change request is ready for a team member to review and approve the updates to the group's on-file contacts.
```

## Bedrock usage

```json
{"usage": {"inputTokens": 1790, "outputTokens": 197, "totalTokens": 1987}, "metrics": {"latencyMs": 2500}}
```

## Tool call sequence observed

| # | Tool | Purpose |
|---|---|---|
| 1 | `extract_fields` | Extract relevant fields from the case document |
| 2 | `retrieve_sop` | Retrieve the standard operating procedure for the intent |
| 3 | `run_validations` | Run address and tax ID validation checks |
| 4 | `check_similar_cases` | Search for similar prior cases |
| 5 | `create_decision_task` | Create a human approval task in the REVIEW_QUEUE decision queue |

The harness **stopped at the human-approval boundary** as instructed, matching the intended
architecture: the model does not execute the transaction itself, it hands off to a human
decision queue.

## Key implementation findings

1. **Gateway IAM auth** initially returned `403`/`401` — resolved once the harness execution
   role's IAM policy included `bedrock-agentcore:*` and the gateway/target had fully propagated
   (a short wait after creation was required).
2. **Bedrock model selection matters.** `anthropic.claude-3-5-sonnet-20241022-v2:0` requires an
   inference profile in `ap-south-1`; even after using the correct inference profile
   (`apac.anthropic.claude-3-5-sonnet-20241022-v2:0`), the account had not submitted the
   Anthropic "model use case details" form required for **streaming** Converse calls
   (`ConverseStream`) — this is required regardless of Claude model version if the account
   has not completed that one-time form. Non-streaming `Converse` calls do **not** require it.
3. **`global.anthropic.claude-haiku-4-5-20251001-v1:0`** was already enabled for streaming in
   this account without the additional form, and was used to complete this successful run.
4. The AgentCore Harness `apiFormat` only supports `converse_stream`, `responses`, or
   `chat_completions` — there is no non-streaming option, so the model/account combination
   must support streaming Converse.
5. The harness model config **cannot set both `temperature` and `topP`** for this model;
   only one may be specified.

## AWS resources destroyed after test

Gateway, gateway target, harness, mock Lambda, IAM roles, and the uploaded tool-schema S3
object were all deleted immediately after this run.
