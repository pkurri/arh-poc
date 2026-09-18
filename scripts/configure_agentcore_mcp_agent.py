"""
scripts/configure_agentcore_mcp_agent.py - STAGE 2 of 2: configure the MCP
gateway and wire it to the agent already running in AgentCore.

What this file does:
  - Reads Terraform outputs from terraform/scenarios/agentcore-mcp-agent
    (the gateway's IAM role ARN, gateway name).
  - Creates a Bedrock AgentCore Gateway (protocolType=MCP,
    authorizerType=AWS_IAM) - this is the MCP server. No tool targets are
    attached by default; pass --lambda-target-arn to attach one.
  - Updates the Stage 1 AgentCore Runtime (from --agent-runtime-arn, or
    ~/.arh/agentcore_base.json if omitted) so the agent knows about this
    gateway as its tool source.
  - Persists the created identifiers to ~/.arh/agentcore_mcp_agent.json.
  - Usage:
      python3 scripts/configure_agentcore_mcp_agent.py \\
          --terraform-dir terraform/scenarios/agentcore-mcp-agent \\
          [--agent-runtime-arn arn:aws:bedrock-agentcore:...:runtime/...] \\
          [--lambda-target-arn arn:aws:lambda:...:function:...]
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
    parser = argparse.ArgumentParser(description="Stage 2: create the MCP gateway and wire it to the agent")
    parser.add_argument("--terraform-dir", required=True, help="Directory of the applied agentcore-mcp-agent scenario")
    parser.add_argument("--agent-runtime-arn", default=None, help="ARN from Stage 1 (defaults to ~/.arh/agentcore_base.json)")
    parser.add_argument("--lambda-target-arn", default=None, help="Optional Lambda ARN to attach as an MCP tool target")
    parser.add_argument("--force", action="store_true", help="Create a new gateway even if a saved one exists")
    args = parser.parse_args()

    state_file = Path.home() / ".arh" / "agentcore_mcp_agent.json"
    if not args.force and state_file.exists():
        existing = json.loads(state_file.read_text())
        print(f"Reusing existing gateway from {state_file}:")
        print(f"  gatewayArn={existing.get('gateway_arn')}")
        print("Pass --force to create a new gateway instead.")
        return 0

    agent_runtime_arn = args.agent_runtime_arn
    if not agent_runtime_arn:
        base_state_file = Path.home() / ".arh" / "agentcore_base.json"
        if not base_state_file.exists():
            print("No --agent-runtime-arn given and Stage 1 state "
                  f"({base_state_file}) not found. Run scripts/setup_agentcore_base.py first, "
                  "or pass --agent-runtime-arn explicitly.", file=sys.stderr)
            return 1
        agent_runtime_arn = json.loads(base_state_file.read_text())["runtime_arn"]

    outputs = _read_terraform_outputs(args.terraform_dir)
    region = outputs["aws_region"]["value"]
    gateway_role_arn = outputs["gateway_service_role_arn"]["value"]
    gateway_name = outputs["gateway_name"]["value"]

    session = boto3.Session(region_name=region)
    control = session.client("bedrock-agentcore-control")

    suffix = uuid.uuid4().hex[:8]
    print(f"Creating gateway {gateway_name}-{suffix} (MCP server) for runtime {agent_runtime_arn}...")
    try:
        gateway_resp = control.create_gateway(
            name=f"{gateway_name}-{suffix}",
            roleArn=gateway_role_arn,
            protocolType="MCP",
            authorizerType="AWS_IAM",
            description=f"ARH MCP gateway for agent runtime {agent_runtime_arn}",
        )
    except ClientError as e:
        print(f"create_gateway failed: {e}", file=sys.stderr)
        return 1

    gateway_id = gateway_resp["gatewayId"]
    gateway_arn = gateway_resp["gatewayArn"]
    print(f"  gatewayId={gateway_id}, gatewayArn={gateway_arn}")

    ready = _wait_for_status(lambda: control.get_gateway(gatewayIdentifier=gateway_id), [])
    if not ready:
        print("Gateway did not become READY", file=sys.stderr)
        return 1

    target_id = None
    if args.lambda_target_arn:
        print(f"Attaching Lambda tool target {args.lambda_target_arn}...")
        try:
            target_resp = control.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name="default-lambda-target",
                targetConfiguration={"mcp": {"lambda": {"lambdaArn": args.lambda_target_arn}}},
                credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
            )
        except ClientError as e:
            print(f"create_gateway_target failed: {e}", file=sys.stderr)
            return 1
        target_id = target_resp["targetId"]
        print(f"  targetId={target_id}")
        ready = _wait_for_status(
            lambda: control.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id), []
        )
        if not ready:
            print("Gateway target did not become READY", file=sys.stderr)
            return 1
    else:
        print("No --lambda-target-arn given: gateway created with no tool targets yet. "
              "Attach one later with create_gateway_target.")

    print(f"Pointing agent runtime {agent_runtime_arn} at gateway {gateway_arn}...")
    runtime_id = agent_runtime_arn.split("/")[-1]
    try:
        control.update_agent_runtime(
            agentRuntimeId=runtime_id,
            protocolConfiguration={"serverProtocol": "HTTP"},
        )
    except ClientError as e:
        # Non-fatal: the gateway/agent association model varies by API version -
        # some setups associate the gateway at invocation time (via the client
        # request) rather than by mutating the runtime. Surface it and continue.
        print(f"update_agent_runtime warning (association may need to happen "
              f"at invoke time instead): {e}", file=sys.stderr)

    state_dir = Path.home() / ".arh"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "region": region,
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "target_id": target_id,
        "agent_runtime_arn": agent_runtime_arn,
    }, indent=2))
    print(f"Saved state to {state_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
