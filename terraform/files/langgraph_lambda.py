"""
terraform/files/langgraph_lambda.py - Lambda implementing the LangGraph node loop
for the LangGraph + Step Functions PoC.

What this file does:
  - Exposes two Lambda handlers: `intake_handler` and `execute_handler`.
  - `intake_handler` runs the LangGraph-style agent loop: at each node it either
    calls Bedrock Converse (USE_BEDROCK=true) to select the next tool, or follows
    a deterministic order (USE_BEDROCK=false). For each selected tool it invokes
    the mock DataPower Lambda, appends the result to the graph state, and persists
    state to DynamoDB. After `create_decision_task` it stores the Step Functions
    task token in DynamoDB and returns status=PENDING, blocking at the
    human-approval boundary.
  - `execute_handler` resumes after approval: calls `execute_transaction` and
    `write_audit_record` via the mock Lambda, then returns status=CLOSED.
  - Graph state and the task token are persisted in DynamoDB
    (arh-langgraph-checkpoints).
"""

import json
import os
import boto3
from botocore.exceptions import ClientError

TABLE = os.environ["CHECKPOINT_TABLE"]
MOCK_LAMBDA_ARN = os.environ["MOCK_LAMBDA_ARN"]
USE_BEDROCK = os.environ.get("USE_BEDROCK", "false").lower() == "true"

_dynamodb = None
_lambda = None
_bedrock_client = None


def _ddb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _lambda_client():
    global _lambda
    if _lambda is None:
        _lambda = boto3.client("lambda")
    return _lambda


def _bedrock():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime")
    return _bedrock_client


def _get_state(case_id: str):
    table = _ddb().Table(TABLE)
    try:
        res = table.get_item(Key={"case_id": case_id, "sk": "state"})
        return res.get("Item", {}).get("data", "{}")
    except ClientError as e:
        print("get_state error:", e)
        return "{}"


def _put_state(case_id: str, state: dict):
    table = _ddb().Table(TABLE)
    table.put_item(Item={"case_id": case_id, "sk": "state", "data": json.dumps(state)})


def _put_token(case_id: str, token: str):
    table = _ddb().Table(TABLE)
    table.put_item(Item={"case_id": case_id, "sk": "token", "token": token})


def _call_tool(tool: str):
    print(f"[LANGGRAPH] _call_tool: {tool}")
    if tool == "classify_intent":
        result = {"intent": "CONTACTS", "confidence": "HIGH", "work_group": "REVIEW_QUEUE"}
        print(f"[LANGGRAPH] _call_tool result (local): {json.dumps(result)}")
        return result
    resp = _lambda_client().invoke(
        FunctionName=MOCK_LAMBDA_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({"tool": tool}).encode(),
    )
    result = json.loads(resp["Payload"].read())
    print(f"[LANGGRAPH] _call_tool result (from mock): {json.dumps(result)}")
    return result


def _bedrock_decide(state: dict) -> str:
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "You are a maintenance agent processing a CONTACTS case. "
                        "Based on the case history, choose the next tool to call from: "
                        "extract_fields, retrieve_sop, run_validations, search_similar_cases, "
                        "create_decision_task, execute_transaction, write_audit_record, or END. "
                        f"History: {json.dumps(state.get('history', []))}. "
                        "Return exactly one tool name and nothing else."
                    )
                }
            ],
        }
    ]
    try:
        model_id = os.environ.get("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        resp = _bedrock().converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={"maxTokens": 64, "temperature": 0.0},
        )
        text = resp["output"]["message"]["content"][0]["text"].strip()
        return text.split()[0]
    except Exception as e:
        print("bedrock decide error:", e)
        return "END"


def _deterministic_decide(turn: int) -> str:
    sequence = [
        "extract_fields",
        "retrieve_sop",
        "run_validations",
        "search_similar_cases",
        "create_decision_task",
    ]
    if turn < len(sequence):
        return sequence[turn]
    return "END"


def _agent(state: dict) -> str:
    next_tool = _bedrock_decide(state) if USE_BEDROCK else _deterministic_decide(len(state.get("history", [])))
    print(f"[LANGGRAPH] _agent decided next tool: {next_tool} (use_bedrock={USE_BEDROCK})")
    return next_tool


def _run_graph(case_id: str, case_text: str, token: str) -> dict:
    print(f"[LANGGRAPH INTAKE] _run_graph starting case_id={case_id} case_text={case_text}")
    state = {"case_id": case_id, "case_text": case_text, "history": []}
    _put_state(case_id, state)

    while True:
        next_tool = _agent(state)
        print(f"[LANGGRAPH INTAKE] current history length: {len(state.get('history', []))}, next_tool: {next_tool}")
        if next_tool == "END":
            break
        if next_tool == "create_decision_task":
            result = _call_tool("create_decision_task")
            state["history"].append({"tool": next_tool, "result": result})
            _put_state(case_id, state)
            _put_token(case_id, token)
            return {
                "case_id": case_id,
                "task_id": result.get("task_id"),
                "status": "PENDING",
            }
        result = _call_tool(next_tool)
        state["history"].append({"tool": next_tool, "result": result})
        _put_state(case_id, state)

    return {"case_id": case_id, "status": "DONE"}


def intake_handler(event, context):
    case_id = event.get("case_id", "CASE-UNKNOWN")
    case_text = event.get("case_text", "")
    task_token = event.get("TaskToken", "")
    print(f"[LANGGRAPH INTAKE] invoked case_id={case_id} task_token_prefix={task_token[:16]}...")
    result = _run_graph(case_id, case_text, task_token)
    print(f"[LANGGRAPH INTAKE] returning: {json.dumps(result)}")
    return result


def execute_handler(event, context):
    case_id = event.get("case_id", "CASE-UNKNOWN")
    decision = event.get("decision", "Denied")
    print(f"[LANGGRAPH EXECUTE] invoked case_id={case_id} decision={decision}")

    state_data = _get_state(case_id)
    state = json.loads(state_data) if state_data else {}

    if decision == "Approved":
        result = _call_tool("execute_transaction")
        state["history"].append({"tool": "execute_transaction", "result": result})
    else:
        state["history"].append({"tool": "execute_transaction", "result": {"status": "DENIED"}})

    audit = _call_tool("write_audit_record")
    state["history"].append({"tool": "write_audit_record", "result": audit})
    state["decision"] = decision
    _put_state(case_id, state)
    result = {"case_id": case_id, "decision": decision, "status": "CLOSED"}
    print(f"[LANGGRAPH EXECUTE] returning: {json.dumps(result)}")
    return result
