"""
scripts/setup_agentcore.py - Create (or reuse) a Bedrock AgentCore Gateway + Harness.

What this file does:
  - Reads Terraform outputs (mock Lambda ARN, IAM role ARNs, OpenAPI S3 URI,
    model/inference-profile ID) for the chosen flavor (`claude` or `strands`).
  - Reuses an existing AgentCore Gateway + Harness stored in ~/.arh/<flavor>_agentcore.json
    when present and valid; otherwise creates new ones.
  - Uploads the tool-definition JSON to S3 and creates a Bedrock AgentCore Gateway
    with an AWS_LAMBDA target pointing at the mock DataPower Lambda.
  - Creates a Bedrock AgentCore Harness configured with the system prompt,
    model (inference profile), and the gateway as the tool source.
  - Persists the created gateway/harness identifiers to ~/.arh/<flavor>_agentcore.json
    so test_harness.py and subsequent runs can reuse them.
  - Usage: `python3 scripts/setup_agentcore.py --flavor claude --terraform-dir terraform/scenarios/claude-agentcore-harness`
"""

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


SYSTEM_PROMPTS = {
    "claude": (
        "You are a small-group insurance maintenance agent. "
        "Process the incoming CONTACTS case for work group REVIEW_QUEUE. "
        "Use the available tools in this order: extract_fields, retrieve_sop, "
        "run_validations, check_similar_cases, then create_decision_task. "
        "Report the final status and stop after creating the decision task."
    ),
    # Strands: no prescribed tool order, to observe how the harness/model
    # sequences the available tools on its own.
    "strands": (
        "You are a small-group insurance maintenance agent. "
        "Process the incoming CONTACTS case for work group REVIEW_QUEUE using the tools "
        "available to you. Decide which tools to call and in what order based on "
        "the case. Report the final status once you have made a decision on the case."
    ),
}


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


def _wait_for_status(
    describe_fn,
    status_path,
    ready_value="READY",
    max_attempts=30,
    sleep=10,
):
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
    parser = argparse.ArgumentParser(description="Set up Bedrock AgentCore Gateway + Harness for a ARH flavor")
    parser.add_argument("--flavor", required=True, choices=["claude", "strands"])
    parser.add_argument("--terraform-dir", required=True, help="Directory of the applied Terraform scenario")
    parser.add_argument("--region", default=None, help="AWS region (defaults to terraform output)")
    parser.add_argument("--bedrock-model", default=None, help="Bedrock model ID (defaults to terraform output)")
    parser.add_argument("--force", action="store_true", help="Create new gateway/harness even if a saved one exists")
    args = parser.parse_args()

    state_file = Path.home() / ".arh" / f"{args.flavor}_agentcore.json"
    if not args.force and state_file.exists():
        existing = json.loads(state_file.read_text())
        print(f"Reusing existing harness from {state_file}:")
        print(f"  harnessArn={existing.get('harness_arn')}")
        print(f"  gatewayArn={existing.get('gateway_arn')}")
        print("Pass --force to create a new gateway/harness instead.")
        return 0

    outputs = _read_terraform_outputs(args.terraform_dir)
    region = args.region or outputs.get("aws_region", {}).get("value", "us-east-1")
    account_id = outputs.get("aws_account_id", {}).get("value", "")
    bedrock_model = args.bedrock_model or outputs.get("bedrock_model", {}).get("value", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    harness_role_arn = outputs["harness_execution_role_arn"]["value"]
    gateway_role_arn = outputs["gateway_service_role_arn"]["value"]
    mock_lambda_arn = outputs["mock_lambda_arn"]["value"]
    openapi_s3_uri = outputs["openapi_s3_uri"]["value"]

    session = boto3.Session(region_name=region)
    try:
        control = session.client("bedrock-agentcore-control")
    except Exception as e:
        print(f"bedrock-agentcore-control client not available in boto3: {e}", file=sys.stderr)
        print("Install a newer boto3 (>= 1.35.0) or use the AWS CLI.", file=sys.stderr)
        return 1

    suffix = uuid.uuid4().hex[:8]
    gateway_name = f"arh-{args.flavor}-gateway-{suffix}"
    print(f"Creating gateway {gateway_name}...")
    try:
        gateway_resp = control.create_gateway(
            name=gateway_name,
            roleArn=gateway_role_arn,
            protocolType="MCP",
            authorizerType="AWS_IAM",
            description=f"Mock DataPower gateway for ARH {args.flavor} PoC",
        )
    except ClientError as e:
        print(f"create_gateway failed: {e}", file=sys.stderr)
        return 1

    print("gateway response:", json.dumps(gateway_resp, default=str, indent=2))
    gateway_id = gateway_resp["gatewayId"]
    gateway_arn = gateway_resp["gatewayArn"]
    print(f"  gatewayId={gateway_id}, gatewayArn={gateway_arn}")

    ready = _wait_for_status(
        lambda: control.get_gateway(gatewayIdentifier=gateway_id),
        [],
    )
    if not ready:
        print("Gateway did not become READY", file=sys.stderr)
        return 1

    print("Building and uploading MCP tool definitions...")
    openapi_path = Path(args.terraform_dir).parent.parent / "files" / "openapi_mock.json"
    with open(openapi_path) as f:
        spec = json.load(f)
    tools = []
    for path, ops in spec.get("paths", {}).items():
        for method, op in ops.items():
            if not isinstance(op, dict):
                continue
            name = op.get("operationId", path.strip("/").replace("-", "_"))
            tools.append({
                "name": name,
                "description": op.get("summary", op.get("description", name)),
                "inputSchema": {"type": "object", "properties": {}},
                "outputSchema": {"type": "object"},
            })
    bucket = openapi_s3_uri.replace("s3://", "").split("/", 1)[0]
    tools_key = f"tools/arh-{args.flavor}-tools.json"
    s3 = session.client("s3")
    s3.put_object(Bucket=bucket, Key=tools_key, Body=json.dumps(tools, indent=2), ContentType="application/json")
    tools_s3_uri = f"s3://{bucket}/{tools_key}"
    print(f"  tools uploaded to {tools_s3_uri}")

    print("Creating gateway target...")
    try:
        target_resp = control.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name="datapower",
            description="Mock DataPower REST target",
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": mock_lambda_arn,
                        "toolSchema": {
                            "s3": {
                                "uri": tools_s3_uri,
                                "bucketOwnerAccountId": account_id,
                            }
                        },
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
        )
    except ClientError as e:
        print(f"create_gateway_target failed: {e}", file=sys.stderr)
        return 1

    target_id = target_resp["targetId"]
    print(f"  targetId={target_id}")

    ready = _wait_for_status(
        lambda: control.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id),
        [],
    )
    if not ready:
        print("Gateway target did not become READY", file=sys.stderr)
        return 1

    harness_name = f"arh_{args.flavor}_harness_{suffix}"
    print(f"Creating harness {harness_name}...")
    try:
        harness_resp = control.create_harness(
            harnessName=harness_name,
            executionRoleArn=harness_role_arn,
            maxIterations=25,
            maxTokens=4096,
            timeoutSeconds=300,
            model={
                "bedrockModelConfig": {
                    "modelId": bedrock_model,
                    "maxTokens": 4096,
                    "temperature": 0.7,
                    "apiFormat": "converse_stream",
                }
            },
            systemPrompt=[
                {
                    "text": SYSTEM_PROMPTS.get(args.flavor, SYSTEM_PROMPTS["claude"])
                }
            ],
            tools=[
                {
                    "type": "agentcore_gateway",
                    "config": {
                        "agentCoreGateway": {
                            "gatewayArn": gateway_arn,
                        }
                    },
                }
            ],
        )
    except ClientError as e:
        print(f"create_harness failed: {e}", file=sys.stderr)
        return 1

    print("harness response:", json.dumps(harness_resp, default=str, indent=2))
    harness = harness_resp.get("harness") or harness_resp
    harness_arn = harness.get("arn") or harness.get("harnessArn")
    harness_id = harness.get("harnessId") or (harness_arn.split("/")[-1] if harness_arn else None)
    print(f"  harnessId={harness_id}, harnessArn={harness_arn}")

    ready = _wait_for_status(
        lambda: control.get_harness(harnessId=harness_id),
        ["harness"],
    )
    if not ready:
        print("Harness did not become READY", file=sys.stderr)
        return 1

    state_dir = Path.home() / ".arh"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{args.flavor}_agentcore.json"
    state = {
        "region": region,
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "target_id": target_id,
        "harness_id": harness_id,
        "harness_arn": harness_arn,
        "bedrock_model": bedrock_model,
    }
    state_file.write_text(json.dumps(state, indent=2))
    print(f"Saved state to {state_file}")
    print(f"Test with: python3 scripts/test_harness.py --flavor {args.flavor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
