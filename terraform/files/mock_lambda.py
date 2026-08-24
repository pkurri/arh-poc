"""
terraform/files/mock_lambda.py - Mock DataPower REST target for all three PoC scenarios.

What this file does:
  - Implements the 8 ARH tools (classify_intent, extract_fields, retrieve_sop,
    run_validations, check_similar_cases/search_similar_cases,
    create_decision_task, execute_transaction, write_audit_record) as a single
    Lambda handler.
  - Each tool returns canned/mock data that mimics a real DataPower + Postgres
    + pgvector + the backend case-management system (e.g. extracted fields, SOP checks,
    validation results, similar cases, decision task ids, transaction status).
  - Used as the AgentCore Gateway Lambda target (Claude/Strands) and as the
    direct invoke target for the LangGraph intake/execute Lambdas.
  - Handler: `mock_lambda.handler` (event: {"tool": "<name>", "case_id": "..."}).
"""

import json
import os
import re


def _tool(tool_name: str, event: dict):
    print(f"[MOCK] invoked tool: {tool_name}")
    print(f"[MOCK] event: {json.dumps(event, default=str)}")
    tools = {
        "classify_intent": {
            "intent": "CONTACTS",
            "confidence": "HIGH",
            "work_group": "REVIEW_QUEUE",
            "auto_processing": False,
        },
        "extract_fields": {
            "extracted_fields": {
                "date_of_birth": "1975-01-01",
                "address": "123 Main St",
                "tax_id": "123-45-6789",
            },
            "gateway_redacted": ["date_of_birth"],
        },
        "retrieve_sop": {
            "required_checks": ["address", "tax_id", "duplicate"],
        },
        "run_validations": {
            "address": "valid",
            "tax_id": "valid",
            "duplicate_check": "skipped",
        },
        "search_similar_cases": {
            "similar_cases": [
                {"case_id": "CASE-1", "outcome": "approved"},
                {"case_id": "CASE-2", "outcome": "approved"},
            ],
        },
        "check_similar_cases": {
            "similar_cases": [
                {"case_id": "CASE-1", "outcome": "approved"},
                {"case_id": "CASE-2", "outcome": "approved"},
            ],
        },
        "create_decision_task": {
            "task_id": "TASK-123",
            "status": "PENDING",
            "review_link": os.environ.get("REVIEW_LINK", "https://example.com/review/TASK-123"),
        },
        "execute_transaction": {
            "status": "APPROVED",
            "message": "contacts updated",
        },
        "write_audit_record": {
            "status": "recorded",
        },
        "get_validation_rules": {
            "required_checks": ["address", "tax_id", "duplicate"],
        },
        "validate_address": {"address": "valid"},
        "validate_taxid": {"tax_id": "valid"},
    }
    return tools.get(tool_name, {"result": "ok", "tool": tool_name})


def _identify_tool(event: dict) -> str:
    for key in ("tool", "toolName", "tool_name", "operationId", "operation"):
        if key in event:
            return str(event[key]).lower()
    path = event.get("path", "")
    if path:
        return path.strip("/").replace("-", "_")
    body = event.get("body", "")
    if body:
        try:
            data = json.loads(body) if isinstance(body, str) else body
            for key in ("tool", "toolName", "tool_name", "operationId", "operation"):
                if key in data:
                    return str(data[key]).lower()
        except Exception:
            pass
    for key in event:
        if re.match(r"^x-agentcore-", key, re.I):
            return str(event[key]).lower()
    return "default"


def _api_gateway_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    print(f"[MOCK] Lambda invoked, event keys: {list(event.keys())}")
    if "httpMethod" in event or "requestContext" in event:
        tool = _identify_tool(event)
        print(f"[MOCK] API Gateway mode, tool: {tool}")
        result = _tool(tool, event)
        print(f"[MOCK] API Gateway response: {json.dumps(result, default=str)}")
        return _api_gateway_response(200, result)
    tool = _identify_tool(event)
    print(f"[MOCK] Direct invoke mode, tool: {tool}")
    result = _tool(tool, event)
    print(f"[MOCK] Returning: {json.dumps(result, default=str)}")
    return result
