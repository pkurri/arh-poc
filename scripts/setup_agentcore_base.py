"""
scripts/setup_agentcore_base.py - STAGE 1 of 2: create a bare Bedrock AgentCore Runtime.

What this file does:
  - Reads Terraform outputs from terraform/scenarios/agentcore-base
    (the runtime's IAM role ARN, container URI, model, name).
  - Creates a Bedrock AgentCore Runtime (CreateAgentRuntime) from the
    container image at --container-uri, using the model from the
    Terraform output. No Gateway, no MCP wiring - that's stage 2,
    scripts/configure_agentcore_mcp_agent.py, run after this succeeds.
  - Persists the created identifier to ~/.arh/agentcore_base.json so
    stage 2 (and configure_agentcore_mcp_agent.py) can pick it up via
    --agent-runtime-arn or by reading this file directly.
  - Usage:
      python3 scripts/setup_agentcore_base.py \\
          --terraform-dir terraform/scenarios/agentcore-base
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
import subprocess

import boto3
from botocore.exceptions import ClientError


def _read_terraform_outputs(terraform_dir: str) -> dict:
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=terraform_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"terraform output failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def _wait_for_status(describe_fn, status_path, ready_value="READY", max_attempts=30, sleep=10):
    for _ in range(max_attempts):
        try:
            response = describe_fn()
            status = response
            for key in status_path:
                status = status.get(key, {})
            if isinstance(status, dict):
                status = status.get("status", "")
            if status == ready_value:
                return response
            if status in ("FAILED", "CREATE_FAILED", "UPDATE_FAILED"):
                print(f"resource entered failed state: {status}", file=sys.stderr)
                return response
        except ClientError as e:
            print(f"describe call failed: {e}", file=sys.stderr)
            return None
        time.sleep(sleep)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1: create a bare Bedrock AgentCore Runtime")
    parser.add_argument("--terraform-dir", required=True, help="Directory of the applied agentcore-base scenario")
    parser.add_argument("--force", action="store_true", help="Create a new runtime even if a saved one exists")
    args = parser.parse_args()

    state_file = Path.home() / ".arh" / "agentcore_base.json"
    if not args.force and state_file.exists():
        existing = json.loads(state_file.read_text())
        print(f"Reusing existing runtime from {state_file}:")
        print(f"  runtimeArn={existing.get('runtime_arn')}")
        print("Pass --force to create a new runtime instead.")
        return 0

    outputs = _read_terraform_outputs(args.terraform_dir)
    region = outputs["aws_region"]["value"]
    runtime_role_arn = outputs["runtime_execution_role_arn"]["value"]
    bedrock_model = outputs["bedrock_model"]["value"]
    container_uri = outputs["container_uri"]["value"]
    runtime_name = outputs["runtime_name"]["value"]

    session = boto3.Session(region_name=region)
    control = session.client("bedrock-agentcore-control")

    suffix = uuid.uuid4().hex[:8]
    print(f"Creating agent runtime {runtime_name}-{suffix}...")
    try:
        runtime_resp = control.create_agent_runtime(
            agentRuntimeName=f"{runtime_name}-{suffix}".replace("-", "_"),
            agentRuntimeArtifact={
                "containerConfiguration": {"containerUri": container_uri}
            },
            roleArn=runtime_role_arn,
            protocolConfiguration={"serverProtocol": "HTTP"},
            description=f"Bare ARH AgentCore Runtime, model={bedrock_model}",
        )
    except ClientError as e:
        print(f"create_agent_runtime failed: {e}", file=sys.stderr)
        return 1

    runtime_arn = runtime_resp.get("agentRuntimeArn")
    runtime_id = runtime_resp.get("agentRuntimeId")
    print(f"  agentRuntimeId={runtime_id}, agentRuntimeArn={runtime_arn}")

    ready = _wait_for_status(lambda: control.get_agent_runtime(agentRuntimeId=runtime_id), [])
    if not ready:
        print("Agent runtime did not become READY", file=sys.stderr)
        return 1

    state_dir = Path.home() / ".arh"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "region": region,
        "runtime_id": runtime_id,
        "runtime_arn": runtime_arn,
        "bedrock_model": bedrock_model,
    }, indent=2))
    print(f"Saved state to {state_file}")
    print(f"Next: python3 scripts/configure_agentcore_mcp_agent.py "
          f"--terraform-dir terraform/scenarios/agentcore-mcp-agent --agent-runtime-arn {runtime_arn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
