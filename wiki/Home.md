# Project ARH Wiki

Welcome to the Project ARH wiki. ARH is a proof-of-concept that compares three
AWS agent-runtime architectures for processing small-group insurance maintenance
cases (CONTACTS / REVIEW_QUEUE work group) through a fixed set of 8 tools.

## Three scenarios

| # | Scenario | Runtime | Human-approval enforcement |
|---|---|---|---|
| 1 | Claude Agent SDK | Bedrock AgentCore Harness | Prompt-instructed (behavioral) |
| 2 | Strands Agents | Bedrock AgentCore Harness | Not enforced (model continues autonomously) |
| 3 | LangGraph | AWS Step Functions | `waitForTaskToken` (structural / infrastructure-enforced) |

## Wiki pages

- [[Architecture Overview]] - High-level architecture and shared tool set
- [[Scenario 1 - Claude AgentCore Harness]] - Configuration, run, results
- [[Scenario 2 - Strands AgentCore Harness]] - Configuration, run, results
- [[Scenario 3 - LangGraph Step Functions]] - Configuration, run, results
- [[ARH Step Functions Explanation]] - Detailed state-machine and approval-flow explanation
- [[ARH Claude Process Flow]] - Detailed Claude AgentCore Harness process and tool-calling flow
- [[Harness Comparison]] - Side-by-side comparison of all three runs
- [[File Index]] - Every file in the repo and what it does
- [[AWS Setup and Testing]] - How to deploy and test in an AWS account
- [[Cost Estimate]] - Pre-run estimate and actual Cost Explorer figures
- [[Cleanup Guide]] - How to destroy all AWS resources after testing

## Key findings

1. **Claude** (prompt-controlled): followed the prescribed 5-tool sequence and
   stopped at `create_decision_task` as instructed. The stop was behavioral,
   not structurally enforced.

2. **Strands** (autonomous, no prescribed order): selected `classify_intent` plus
   all 8 tools and **continued past the human-approval boundary** straight through
   `execute_transaction` and `write_audit_record`. This proves a model-driven
   harness does not inherently enforce approval boundaries.

3. **LangGraph** (Step Functions): even with Bedrock-driven tool selection, the
   `waitForTaskToken` state structurally blocks execution until an external
   `SendTaskSuccess` is sent. The model cannot bypass the approval boundary.

## Model used

All three successful runs used `global.anthropic.claude-haiku-4-5-20251001-v1:0`
(Bedrock cross-region inference profile) in `ap-south-1`.
