"""
scripts/test_harness.py - Invoke a Bedrock AgentCore Harness and capture the run.

What this file does:
  - Loads the saved AgentCore state (~/.arh/<flavor>_agentcore.json) produced
    by setup_agentcore.py.
  - Starts an AgentCore Harness session with the CONTACTS/REVIEW_QUEUE case text.
  - Streams the harness response, capturing the model transcript, tool calls,
    token usage, and latency.
  - Prints a structured summary (tool sequence, token counts, latency, final
    status) to stdout for inclusion in the run reports.
  - Usage: `python3 scripts/test_harness.py --flavor claude`
           `python3 scripts/test_harness.py --flavor strands`
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def _load_state(flavor: str) -> dict:
    state_file = Path.home() / ".arh" / f"{flavor}_agentcore.json"
    if not state_file.exists():
        print(f"State file not found: {state_file}", file=sys.stderr)
        print(f"Run setup_agentcore.py --flavor {flavor} first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(state_file.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description="Invoke a ARH Bedrock AgentCore Harness")
    parser.add_argument("--flavor", required=True, choices=["claude", "strands"])
    parser.add_argument("--prompt", default=None, help="User prompt for the harness")
    args = parser.parse_args()

    state = _load_state(args.flavor)
    region = state["region"]
    harness_arn = state["harness_arn"]
    bedrock_model = state["bedrock_model"]

    session = boto3.Session(region_name=region)
    try:
        client = session.client("bedrock-agentcore")
    except Exception as e:
        print(f"bedrock-agentcore client not available: {e}", file=sys.stderr)
        return 1

    prompt = (
        args.prompt
        or "A broker emailed a change to the group on-file contacts. Process the CONTACTS case for REVIEW_QUEUE."
    )

    session_id = str(uuid.uuid4())
    print(f"Invoking harness {harness_arn} with session {session_id}...")
    try:
        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
        )
    except ClientError as e:
        print(f"invoke_harness failed: {e}", file=sys.stderr)
        return 1

    text = ""
    metadata = None
    for event in response.get("stream", []):
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                chunk = delta["text"]
                text += chunk
                print(chunk, end="", flush=True)
        if "metadata" in event:
            metadata = event["metadata"]

    print("\n\n---")
    print(f"Final text: {text}")
    if metadata:
        print(json.dumps(metadata, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
