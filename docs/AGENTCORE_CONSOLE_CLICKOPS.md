# AWS Console click-ops: AgentCore Runtime + MCP Gateway + Agent

Manual fallback for `terraform/scenarios/agentcore-base` and
`terraform/scenarios/agentcore-mcp-agent`, for anyone without CLI/Terraform
access, or without the `iam:CreateRole`/`iam:PassRole` permissions this
account's `PowerUserAccess` role is missing. Do Stage 1 fully before
starting Stage 2.

Everywhere below, region is **us-east-1** and the account is the one you're
signed into. Replace `<account-id>` accordingly.

---

## Stage 1 - AgentCore Runtime, alone

### 1.1 Create the runtime's execution role (IAM console)

1. **IAM** → **Roles** → **Create role**.
2. Trusted entity type: **Custom trust policy**. Paste:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": { "Service": "bedrock-agentcore.amazonaws.com" },
       "Action": "sts:AssumeRole",
       "Condition": { "StringEquals": { "aws:SourceAccount": "<account-id>" } }
     }]
   }
   ```
3. Skip attaching managed policies for now - you'll add inline policies after naming the role.
4. Role name: `arh-agentcore-runtime-role`. Create role.
5. Open the role → **Add permissions** → **Create inline policy** → JSON tab. Add these four, one at a time (name them `BedrockInvoke`, `AgentCoreOperations`, `PullContainerImage`, `AgentCoreLogs` to match Terraform):

   **BedrockInvoke**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
       "Resource": [
         "arn:aws:bedrock:*::foundation-model/anthropic.*",
         "arn:aws:bedrock:us-east-1:<account-id>:inference-profile/*"
       ]
     }]
   }
   ```

   **AgentCoreOperations**
   ```json
   { "Version": "2012-10-17", "Statement": [{ "Effect": "Allow", "Action": "bedrock-agentcore:*", "Resource": "*" }] }
   ```

   **PullContainerImage**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       { "Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*" },
       { "Effect": "Allow", "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
         "Resource": "arn:aws:ecr:us-east-1:<account-id>:repository/*" }
     ]
   }
   ```

   **AgentCoreLogs**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                  "logs:DescribeLogGroups", "logs:DescribeLogStreams"],
       "Resource": "arn:aws:logs:us-east-1:<account-id>:log-group:/aws/bedrock-agentcore/*"
     }]
   }
   ```

6. Copy the role's ARN (top of the role's summary page) - you'll need it next.

### 1.2 Build and push the agent's container image (ECR console)

1. **ECR** → **Repositories** → **Create repository**. Name it e.g. `arh-agent`. Private, defaults otherwise fine.
2. Click the new repository → **View push commands**, and run them locally against your agent's Docker image (this repo does not include agent application code - bring your own, or use the AgentCore SDK's `agentcore configure && agentcore launch`, which does this step for you).
3. Copy the pushed image's URI (`<account-id>.dkr.ecr.us-east-1.amazonaws.com/arh-agent:latest`).

### 1.3 Create the AgentCore Runtime (Bedrock console)

1. **Amazon Bedrock** → **AgentCore** (left nav) → **Agent Runtime** → **Create**.
2. Name: `arh-agentcore-runtime`.
3. Artifact source: **Container image** → paste the ECR URI from 1.2.
4. Execution role: pick `arh-agentcore-runtime-role` from 1.1.
5. Protocol: **HTTP**.
6. Create, and wait for status **READY** (can take a few minutes).
7. Copy the Runtime's ARN - needed in Stage 2.

---

## Stage 2 - MCP Gateway + wiring the agent to it

### 2.1 Create the gateway's service role (IAM console)

1. **IAM** → **Roles** → **Create role** → **Custom trust policy**, same trust JSON as 1.1 (principal `bedrock-agentcore.amazonaws.com`).
2. Role name: `arh-agentcore-gateway-role`.
3. Add one inline policy, name it `AgentCoreGatewayOperations`:
   ```json
   { "Version": "2012-10-17", "Statement": [{ "Effect": "Allow", "Action": "bedrock-agentcore:*", "Resource": "*" }] }
   ```
4. Copy the role's ARN.

### 2.2 Create the MCP Gateway (Bedrock console)

1. **Amazon Bedrock** → **AgentCore** → **Gateway** → **Create gateway**.
2. Name: `arh-agentcore-gateway`.
3. Protocol type: **MCP**.
4. Authorizer type: **AWS_IAM**.
5. Service role: pick `arh-agentcore-gateway-role` from 2.1.
6. Create, wait for status **READY**.
7. (Optional, to expose real tools) **Add target** → point at a Lambda function, an OpenAPI schema in S3, or another supported target type. Skip this if you're only testing that the gateway itself can be created.

### 2.3 Point the agent at the gateway

1. Back in **AgentCore** → **Agent Runtime** → open the runtime from Stage 1.
2. Under its tool/gateway configuration, add the Gateway ARN from 2.2 as a tool source (exact field name depends on the console version at the time you're reading this - if you don't see it, the association may instead happen per-invocation via the client SDK's request parameters rather than as a runtime-level setting).
3. Test by invoking the runtime (console "Test" panel, or `python3 scripts/test_harness.py`-style client code pointed at the runtime's invoke endpoint).

---

## If you hit `AccessDenied` on any step above

That means your IAM session (e.g. `PowerUserAccess`) doesn't have `iam:CreateRole`/`iam:PassRole`/`bedrock-agentcore:*` - the same restriction documented in this repo's README for the Terraform path. There's no console workaround for a missing IAM permission; someone with IAM admin rights on the account needs to grant it (see the scoped policy JSON in the README) or do steps 1.1/2.1 on your behalf and hand you the resulting role ARNs.
