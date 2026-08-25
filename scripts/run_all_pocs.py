"""
scripts/run_all_pocs.py - Orchestrate the three ARH AWS PoC scenarios.

What this file does:
  - Loads optional local environment values from .env without printing secrets.
  - Validates AWS credentials with STS and checks required local commands.
  - Applies Terraform for the selected scenarios.
  - Reuses existing AgentCore Gateway/Harness state by calling setup_agentcore.py
    without --force.
  - Invokes the Claude and Strands harness tests.
  - Starts the LangGraph test, stopping at manual approval unless --approve is set.
  - Runs Terraform cleanup only when --cleanup is explicitly supplied.
  - Never stores credentials in the repository or prints credential values.

Credential setup examples:
  aws sso login --profile <profile>
  AWS_PROFILE=<profile> python3 scripts/run_all_pocs.py

  export AWS_ACCESS_KEY_ID=...
  export AWS_SECRET_ACCESS_KEY=...
  export AWS_SESSION_TOKEN=...
  python3 scripts/run_all_pocs.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_ROOT = ROOT / "terraform" / "scenarios"
DEFAULT_REGION = "ap-south-1"
DEFAULT_MODEL = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
PYTHON_EXECUTABLE = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else sys.executable
AWS_CREDENTIAL_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)


class POCError(RuntimeError):
    """Raised when a PoC orchestration step fails."""


def _load_dotenv(env: dict[str, str]) -> None:
    """Load simple KEY=VALUE entries without overriding exported variables."""
    dotenv = ROOT / ".env"
    if not dotenv.exists():
        return

    for raw_line in dotenv.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in env:
            env[key] = value


def _build_env(profile: str | None, region: str) -> dict[str, str]:
    env = os.environ.copy()
    _load_dotenv(env)
    if profile:
        env["AWS_PROFILE"] = profile
        for key in AWS_CREDENTIAL_KEYS:
            env.pop(key, None)
    env["AWS_REGION"] = region
    env["AWS_DEFAULT_REGION"] = region
    return env


def _display_command(command: list[str]) -> str:
    """Render a command without exposing environment-specific values."""
    safe_args = [
        "-var=openapi_bucket_name=<redacted>" if arg.startswith("-var=openapi_bucket_name=") else arg
        for arg in command
    ]
    return " ".join(safe_args)


def _run(label: str, command: list[str], cwd: Path, env: dict[str, str]) -> str:
    """Run a command with inherited output and return stdout."""
    print(f"\n=== {label} ===")
    print(f"Working directory: {cwd}")
    print(f"Command: {_display_command(command)}")
    result = subprocess.run(command, cwd=cwd, env=env, text=True)
    if result.returncode != 0:
        raise POCError(f"{label} failed with exit code {result.returncode}")
    return ""


def _capture(label: str, command: list[str], cwd: Path, env: dict[str, str]) -> str:
    """Run a command while capturing output for use by a later step."""
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise POCError(f"{label} failed: {detail}")
    return result.stdout.strip()


def _validate_environment(env: dict[str, str]) -> None:
    for command in ("aws", "terraform", "python3"):
        if shutil.which(command) is None:
            raise POCError(f"Required command not found: {command}")

    dependency_check = subprocess.run(
        [PYTHON_EXECUTABLE, "-c", "import boto3"],
        env=env,
        text=True,
        capture_output=True,
    )
    if dependency_check.returncode != 0:
        raise POCError(
            f"boto3 is not installed for {PYTHON_EXECUTABLE}; "
            "run `python3 -m pip install -r requirements.txt`"
        )

    identity = _capture(
        "AWS credential validation",
        ["aws", "sts", "get-caller-identity", "--output", "json"],
        ROOT,
        env,
    )
    try:
        account = json.loads(identity).get("Account", "unknown")
    except json.JSONDecodeError as exc:
        raise POCError("AWS identity response was not valid JSON") from exc
    expected_account = env.get("AWS_ACCOUNT_ID")
    if expected_account and account != expected_account:
        raise POCError(
            "Active AWS credentials do not match the configured ARH target account; "
            "select the correct AWS profile or export the intended credentials."
        )
    print("AWS credentials validated for the configured target account")


def _terraform_vars(args: argparse.Namespace) -> list[str]:
    return [
        f"-var=aws_region={args.region}",
        f"-var=bedrock_model={args.bedrock_model}",
    ]


def _apply_terraform(name: str, args: argparse.Namespace, env: dict[str, str]) -> None:
    scenario_dir = TERRAFORM_ROOT / name
    _run(f"{name}: terraform init", ["terraform", "init", "-input=false"], scenario_dir, env)

    variables = _terraform_vars(args)
    if name == "langgraph-stepfunctions":
        variables.extend(
            [
                f"-var=use_bedrock={'true' if args.use_bedrock else 'false'}",
                f"-var=state_machine_name={args.state_machine_name}",
            ]
        )
    else:
        bucket = env.get("SHARED_S3_BUCKET") or env.get("TF_VAR_openapi_bucket_name")
        if not bucket:
            raise POCError(
                "AgentCore scenarios require SHARED_S3_BUCKET in .env or "
                "TF_VAR_openapi_bucket_name in the environment"
            )
        variables.append(f"-var=openapi_bucket_name={bucket}")

    env["TF_VAR_openapi_bucket_name"] = env.get("SHARED_S3_BUCKET", env.get("TF_VAR_openapi_bucket_name", ""))
    _run(
        f"{name}: terraform apply",
        ["terraform", "apply", "-input=false", "-auto-approve", *variables],
        scenario_dir,
        env,
    )


def _destroy_terraform(name: str, args: argparse.Namespace, env: dict[str, str]) -> None:
    scenario_dir = TERRAFORM_ROOT / name
    variables = _terraform_vars(args)
    if name == "langgraph-stepfunctions":
        variables.extend(
            [
                f"-var=use_bedrock={'true' if args.use_bedrock else 'false'}",
                f"-var=state_machine_name={args.state_machine_name}",
            ]
        )
    else:
        bucket = env.get("SHARED_S3_BUCKET") or env.get("TF_VAR_openapi_bucket_name")
        if bucket:
            variables.append(f"-var=openapi_bucket_name={bucket}")
    _run(
        f"{name}: terraform destroy",
        ["terraform", "destroy", "-input=false", "-auto-approve", *variables],
        scenario_dir,
        env,
    )


def _run_agentcore(flavor: str, args: argparse.Namespace, env: dict[str, str]) -> None:
    scenario = f"{flavor}-agentcore-harness"
    scenario_dir = TERRAFORM_ROOT / scenario
    _run(
        f"{flavor}: setup or reuse AgentCore resources",
        [
            PYTHON_EXECUTABLE,
            str(ROOT / "scripts" / "setup_agentcore.py"),
            "--flavor",
            flavor,
            "--terraform-dir",
            str(scenario_dir),
            "--region",
            args.region,
            "--bedrock-model",
            args.bedrock_model,
        ],
        ROOT,
        env,
    )
    _run(
        f"{flavor}: invoke harness",
        [
            PYTHON_EXECUTABLE,
            str(ROOT / "scripts" / "test_harness.py"),
            "--flavor",
            flavor,
        ],
        ROOT,
        env,
    )


def _run_langgraph(args: argparse.Namespace, env: dict[str, str]) -> None:
    scenario_dir = TERRAFORM_ROOT / "langgraph-stepfunctions"
    state_machine_arn = _capture(
        "LangGraph state-machine ARN",
        ["terraform", "output", "-raw", "state_machine_arn"],
        scenario_dir,
        env,
    )
    dynamodb_table = _capture(
        "LangGraph DynamoDB table",
        ["terraform", "output", "-raw", "dynamodb_table"],
        scenario_dir,
        env,
    )
    command = [
        PYTHON_EXECUTABLE,
        str(ROOT / "scripts" / "test_langgraph.py"),
        "--state-machine-arn",
        state_machine_arn,
        "--dynamodb-table",
        dynamodb_table,
        "--case-id",
        args.case_id,
        "--case-text",
        args.case_text,
        "--region",
        args.region,
    ]
    if not args.approve:
        command.append("--wait-for-approval")
    _run("langgraph: execute workflow", command, ROOT, env)


def _selected_scenarios(selection: str) -> list[str]:
    if selection == "all":
        return ["claude", "strands", "langgraph"]
    return [selection]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the ARH Claude, Strands, and LangGraph AWS PoCs"
    )
    parser.add_argument("--scenario", choices=["all", "claude", "strands", "langgraph"], default="all")
    parser.add_argument("--profile", help="AWS CLI profile; otherwise use the standard credential chain")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", DEFAULT_REGION))
    parser.add_argument("--bedrock-model", default=os.environ.get("BEDROCK_MODEL", DEFAULT_MODEL))
    parser.add_argument("--use-bedrock", dest="use_bedrock", action="store_true", default=True)
    parser.add_argument("--deterministic", dest="use_bedrock", action="store_false", help="Use deterministic LangGraph routing")
    parser.add_argument("--approve", action="store_true", help="Approve the LangGraph task automatically")
    parser.add_argument("--cleanup", action="store_true", help="Destroy Terraform-managed resources after the run")
    parser.add_argument("--keep-resources", action="store_true", help="Explicitly keep resources; overrides --cleanup")
    parser.add_argument("--validate-only", action="store_true", help="Validate tools, dependencies, and AWS credentials without changing resources")
    parser.add_argument("--state-machine-name", default="arh-langgraph-state-machine")
    parser.add_argument("--case-id", default="CASE-ORCHESTRATOR-001")
    parser.add_argument("--case-text", default="A request was submitted to update group contacts.")
    args = parser.parse_args()

    if args.cleanup and args.keep_resources:
        parser.error("--cleanup and --keep-resources cannot be used together")
    if args.validate_only and args.cleanup:
        parser.error("--validate-only and --cleanup cannot be used together")
    if args.cleanup and "langgraph" in _selected_scenarios(args.scenario) and not args.approve:
        parser.error("--cleanup with LangGraph requires --approve so a waiting execution is not destroyed")

    env = _build_env(args.profile, args.region)
    selected = _selected_scenarios(args.scenario)
    completed: list[str] = []

    try:
        _validate_environment(env)
        if args.validate_only:
            print("Validation passed; no AWS resources were changed.")
            return 0
        if "claude" in selected:
            _apply_terraform("claude-agentcore-harness", args, env)
            _run_agentcore("claude", args, env)
            completed.append("claude")
        if "strands" in selected:
            _apply_terraform("strands-agentcore-harness", args, env)
            _run_agentcore("strands", args, env)
            completed.append("strands")
        if "langgraph" in selected:
            _apply_terraform("langgraph-stepfunctions", args, env)
            _run_langgraph(args, env)
            completed.append("langgraph")
    except POCError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if args.cleanup and not args.keep_resources and not args.validate_only:
            for scenario in reversed(selected):
                terraform_name = f"{scenario}-agentcore-harness" if scenario in {"claude", "strands"} else "langgraph-stepfunctions"
                try:
                    _destroy_terraform(terraform_name, args, env)
                except POCError as exc:
                    print(f"Cleanup warning: {exc}", file=sys.stderr)

    print(f"\nCompleted scenarios: {', '.join(completed) or 'none'}")
    if args.cleanup:
        print("Terraform cleanup was requested. AgentCore Gateway/Harness resources are reused/managed by setup_agentcore.py and may require separate AgentCore deletion.")
    elif "langgraph" in selected and not args.approve:
        print("LangGraph is waiting for manual approval. Re-run with --approve for an automatic approval, or approve through your external callback flow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
