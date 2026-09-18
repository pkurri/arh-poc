# Scoped IAM policies to unblock deploys under `PowerUserAccess`

Every deploy attempt in this repo (`langgraph-stepfunctions`, `agentcore-base`,
`agentcore-mcp-agent`) fails identically on the current `PowerUserAccess`
session: `iam:CreateRole` and `iam:PassRole` are both denied, because AWS's
managed `PowerUserAccess` policy explicitly excludes all IAM management
(`NotAction: iam:*` with a small self-service allowlist). There is no way to
work around this from inside the session - it needs a grant from someone with
IAM admin rights on account `000789387090`.

These two files are that grant, scoped as tightly as possible so it can't be
used for anything beyond what this repo creates.

## `arh-scoped-role-permissions.json` - the minimum needed

Attach this as an inline or managed policy to the `PowerUserAccess`
permission set (IAM Identity Center) or directly to the assumed role.

- **`CreateManageArhRolesOnly`**: full role lifecycle (`CreateRole` through
  `ListAttachedRolePolicies`), but the `Resource` is pinned to
  `arn:aws:iam::000789387090:role/arh-*`. Every role this project creates -
  `arh-langgraph-*`, `arh-claude-*`, `arh-strands-*`,
  `arh-agentcore-runtime-role`, `arh-agentcore-gateway-role` - matches that
  prefix (verified against every `name = "..."` in `terraform/modules` and
  `terraform/scenarios`). Nothing outside that namespace - `AWSReservedSSO_*`,
  `OrganizationAccountAccessRole`, any other team's roles - can be touched.
- **`PassArhRolesToKnownServicesOnly`**: `iam:PassRole` on the same `arh-*`
  resource, further restricted by the `iam:PassedToService` condition key to
  only the three services this repo actually hands a role to: Lambda, Step
  Functions, and Bedrock AgentCore. An `arh-*` role can't be passed to EC2,
  another IAM principal, or anything else.

## `arh-role-boundary-deny.json` - optional extra hardening

A `Deny` statement that blocks `iam:CreateRole` on `arh-*` unless the caller
also attaches a specific permissions boundary
(`arn:aws:iam::000789387090:policy/arh-role-boundary`). This caps what *any*
`arh-*` role can do, regardless of what inline policy later gets attached to
it - defense in depth against a mistake in this repo's Terraform, not just a
restriction on who can create the role.

To use it, first create the boundary policy itself (not included here - it
should allow only what `arh-*` roles legitimately need: `bedrock:InvokeModel*`,
`bedrock-agentcore:*`, `lambda:InvokeFunction`, `states:*`, `logs:*`,
`dynamodb:*`, and the `ecr:GetAuthorizationToken`/`BatchGetImage`/
`GetDownloadUrlForLayer` trio for container pulls), then attach both this
Deny statement and the boundary to the calling identity.

## After this is attached

No code changes needed on this end - re-run the same `terraform apply`
commands that failed in `terraform/scenarios/langgraph-stepfunctions`,
`terraform/scenarios/agentcore-base`, and
`terraform/scenarios/agentcore-mcp-agent`.
