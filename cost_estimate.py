#!/usr/bin/env python3
"""
cost_estimate.py - AWS cost estimator for the three ARH PoC scenarios.

What this file does:
  - Defines approximate on-demand AWS unit prices (Bedrock tokens, Lambda,
    Step Functions transitions, DynamoDB reads/writes, S3, CloudWatch).
  - Computes an estimated cost per scenario based on observed token counts,
    Lambda invocations, SFN transitions, and DDB operations from the test runs.
  - Prints a per-scenario and total cost breakdown to stdout.
  - Intended to be run standalone: `python3 cost_estimate.py`
"""

import argparse
import sys

# Approximate on-demand us-east-1 prices. Update these with current AWS pricing.
PRICES = {
    "bedrock_claude_input_per_1m_tokens": 3.0,
    "bedrock_claude_output_per_1m_tokens": 15.0,
    "lambda_request_per_1m": 0.20,
    "lambda_gb_second": 0.0000166667,
    "sfn_standard_transition_per_1k": 0.025,
    "dynamodb_write_per_1m": 1.25,
    "dynamodb_read_per_1m": 0.25,
    "s3_get_per_1k": 0.0004,
    "cloudwatch_logs_per_gb": 0.50,
    "agentcore_session_guess": 0.05,  # placeholder; no public list price known
}


def _round_cents(value: float) -> float:
    return round(value, 6)


def _agentcore_harness_cost(runs: int, use_bedrock: bool) -> dict:
    # Each run: 1 model loop with ~6 tool calls.
    bedrock = 0.0
    if use_bedrock:
        # ~5k input + ~1k output tokens per run (heavily dependent on prompt/history)
        bedrock_input = runs * 5000 * (PRICES["bedrock_claude_input_per_1m_tokens"] / 1_000_000)
        bedrock_output = runs * 1000 * (PRICES["bedrock_claude_output_per_1m_tokens"] / 1_000_000)
        bedrock = bedrock_input + bedrock_output

    mock_lambda_invocations = runs * 6
    lambda_compute_gb_s = mock_lambda_invocations * 0.125 * 0.3  # 128 MB, 0.3s
    lambda_cost = (
        mock_lambda_invocations * (PRICES["lambda_request_per_1m"] / 1_000_000)
        + lambda_compute_gb_s * PRICES["lambda_gb_second"]
    )
    agentcore_compute = runs * PRICES["agentcore_session_guess"]
    s3_gets = mock_lambda_invocations  # OpenAPI reads are not charged per call to Lambda target
    s3_cost = s3_gets * (PRICES["s3_get_per_1k"] / 1000)
    logs_gb = runs * 0.001
    logs_cost = logs_gb * PRICES["cloudwatch_logs_per_gb"]

    total = bedrock + lambda_cost + agentcore_compute + s3_cost + logs_cost
    return {
        "scenario": "Claude Agent SDK (AgentCore Harness)",
        "bedrock": _round_cents(bedrock),
        "lambda": _round_cents(lambda_cost),
        "agentcore_compute_guess": _round_cents(agentcore_compute),
        "other": _round_cents(s3_cost + logs_cost),
        "total": _round_cents(total),
    }


def _strands_harness_cost(runs: int, use_bedrock: bool) -> dict:
    # Same infrastructure cost as the Claude AgentCore harness.
    return {
        **_agentcore_harness_cost(runs, use_bedrock),
        "scenario": "Strands Agents (AgentCore Harness)",
    }


def _langgraph_cost(runs: int, use_bedrock: bool) -> dict:
    bedrock = 0.0
    if use_bedrock:
        bedrock_input = runs * 3000 * (PRICES["bedrock_claude_input_per_1m_tokens"] / 1_000_000)
        bedrock_output = runs * 800 * (PRICES["bedrock_claude_output_per_1m_tokens"] / 1_000_000)
        bedrock = bedrock_input + bedrock_output

    # Step Functions: intake, tools loop, wait, execute, success
    transitions_per_run = 8
    sfn_cost = runs * transitions_per_run * (PRICES["sfn_standard_transition_per_1k"] / 1000)

    # Lambda: intake (1), execute (1), mock (6)
    lambda_invocations = runs * (1 + 1 + 6)
    lambda_compute_gb_s = lambda_invocations * 0.25 * 1.0  # 256 MB, 1s for intake/execute, 0.5s for mock
    lambda_cost = (
        lambda_invocations * (PRICES["lambda_request_per_1m"] / 1_000_000)
        + lambda_compute_gb_s * PRICES["lambda_gb_second"]
    )

    # DynamoDB checkpoints
    ddb_writes = runs * 8
    ddb_reads = runs * 3
    ddb_cost = (
        ddb_writes * (PRICES["dynamodb_write_per_1m"] / 1_000_000)
        + ddb_reads * (PRICES["dynamodb_read_per_1m"] / 1_000_000)
    )

    logs_gb = runs * 0.002
    logs_cost = logs_gb * PRICES["cloudwatch_logs_per_gb"]

    total = bedrock + sfn_cost + lambda_cost + ddb_cost + logs_cost
    return {
        "scenario": "LangGraph + Step Functions",
        "bedrock": _round_cents(bedrock),
        "sfn": _round_cents(sfn_cost),
        "lambda": _round_cents(lambda_cost),
        "dynamodb": _round_cents(ddb_cost),
        "other": _round_cents(logs_cost),
        "total": _round_cents(total),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate ARH PoC AWS cost")
    parser.add_argument("--runs", type=int, default=1, help="Number of test runs per scenario")
    parser.add_argument("--use-bedrock", action="store_true", help="Include Bedrock model costs")
    parser.add_argument("--output", default=None, help="Write markdown to a file")
    args = parser.parse_args()

    results = [
        _agentcore_harness_cost(args.runs, args.use_bedrock),
        _strands_harness_cost(args.runs, args.use_bedrock),
        _langgraph_cost(args.runs, args.use_bedrock),
    ]

    lines = ["# ARH PoC AWS Cost Estimate\n"]
    lines.append(f"Assumptions: {args.runs} run(s) per scenario; Bedrock model costs included: {args.use_bedrock}\n")
    lines.append("| Scenario | Bedrock | Lambda | Step Functions | DynamoDB | AgentCore (guess) | Other | Total |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r['scenario']} | ${r.get('bedrock', 0):.6f} | ${r.get('lambda', 0):.6f} | "
            f"${r.get('sfn', 0):.6f} | ${r.get('dynamodb', 0):.6f} | "
            f"${r.get('agentcore_compute_guess', 0):.6f} | ${r.get('other', 0):.6f} | ${r['total']:.6f} |"
        )
    total = sum(r["total"] for r in results)
    lines.append(f"\nTotal for all three scenarios: **${total:.6f}**")
    lines.append("\nNote: AgentCore has no public list price; the value used is a conservative placeholder. "
                 "CloudWatch Logs are negligible for a small test. Bedrock pricing dominates when enabled.")

    output = "\n".join(lines)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\nWrote estimate to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
