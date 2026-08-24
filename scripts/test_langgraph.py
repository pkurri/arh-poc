"""
scripts/test_langgraph.py - End-to-end test driver for the LangGraph + Step Functions PoC.

What this file does:
  - Starts a Step Functions execution with a CONTACTS case id and case text.
  - Polls DynamoDB for the waitForTaskToken token written by the intake Lambda.
  - Sends SendTaskSuccess with an Approved decision to resume the execution
    past the human-approval boundary.
  - Waits for the execution to reach SUCCEEDED/FAILED and prints the final
    output, status, and timing.
  - Usage: `python3 scripts/test_langgraph.py --state-machine-arn <arn> --dynamodb-table <table>`
"""

import argparse
import json
import sys
import time
import uuid

import boto3
from botocore.exceptions import ClientError


def _wait_for_token(ddb_table, case_id, timeout=120):
    client = boto3.resource("dynamodb")
    table = client.Table(ddb_table)
    for _ in range(timeout // 2):
        try:
            item = table.get_item(Key={"case_id": case_id, "sk": "token"})
            token = item.get("Item", {}).get("token")
            if token:
                return token
        except ClientError as e:
            print(f"dynamodb get failed: {e}", file=sys.stderr)
            return None
        time.sleep(2)
    return None


def _wait_for_execution(sfn, execution_arn, timeout=120):
    for _ in range(timeout // 5):
        resp = sfn.describe_execution(executionArn=execution_arn)
        status = resp["status"]
        if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
            return resp
        time.sleep(5)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the ARH LangGraph + Step Functions PoC")
    parser.add_argument("--state-machine-arn", required=True)
    parser.add_argument("--dynamodb-table", required=True)
    parser.add_argument("--case-id", default=f"CASE-{uuid.uuid4().hex[:8].upper()}")
    parser.add_argument("--case-text", default="A broker emailed a change to the group on-file contacts.")
    parser.add_argument("--decision", default="Approved", choices=["Approved", "Denied"])
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    region = args.region
    sfn = boto3.client("stepfunctions", region_name=region)

    print(f"Starting execution for case {args.case_id}...")
    try:
        start = sfn.start_execution(
            stateMachineArn=args.state_machine_arn,
            name=f"test-{args.case_id}",
            input=json.dumps({"case_id": args.case_id, "case_text": args.case_text}),
        )
    except ClientError as e:
        print(f"start_execution failed: {e}", file=sys.stderr)
        return 1

    execution_arn = start["executionArn"]
    print(f"  executionArn={execution_arn}")

    token = _wait_for_token(args.dynamodb_table, args.case_id)
    if not token:
        print("Timed out waiting for decision task token", file=sys.stderr)
        return 1

    print(f"Resuming execution with decision={args.decision}...")
    try:
        sfn.send_task_success(
            taskToken=token,
            output=json.dumps({"case_id": args.case_id, "decision": args.decision}),
        )
    except ClientError as e:
        print(f"send_task_success failed: {e}", file=sys.stderr)
        return 1

    result = _wait_for_execution(sfn, execution_arn)
    if not result:
        print("Timed out waiting for execution", file=sys.stderr)
        return 1

    print(f"Execution status: {result['status']}")
    print(f"Output: {result.get('output', '{}')}")
    return 0 if result["status"] == "SUCCEEDED" else 1


if __name__ == "__main__":
    sys.exit(main())
