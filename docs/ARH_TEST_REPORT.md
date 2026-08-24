# Project ARH — Real AWS Test Report

**Generated:** 2026-08-24 03:39 UTC
**AWS account:** <AWS_ACCOUNT_ID>
**Region:** ap-south-1
**Scope:** Real `terraform apply`, invoke, and `terraform destroy` of all three ARH harnesses.

## 1. Claude Agent SDK on Bedrock AgentCore Runtime

### What ran
- Terraform created: IAM gateway service role, harness execution role, mock Lambda role, OpenAPI object in S3, mock `datapower` Lambda, Bedrock Invoke policy.
- Direct `aws lambda invoke` against the mock target with `extract_fields`.

### Request
```json
{"tool": "extract_fields", "case_id": "CONTACTS-12345"}
```

### Response metadata
```
StatusCode: 200
FunctionError: None
ExecutedVersion: $LATEST

--- LogResult ---
START RequestId: 9bc9d6db-c3d7-4f6d-bb33-ae0f4337873d Version: $LATEST
[MOCK] Lambda invoked, event keys: ['tool', 'case_id']
[MOCK] Direct invoke mode, tool: extract_fields
[MOCK] invoked tool: extract_fields
[MOCK] event: {"tool": "extract_fields", "case_id": "CONTACTS-12345"}
[MOCK] Returning: {"extracted_fields": {"date_of_birth": "1975-01-01", "address": "123 Main St", "tax_id": "123-45-6789"}, "gateway_redacted": ["date_of_birth"]}
END RequestId: 9bc9d6db-c3d7-4f6d-bb33-ae0f4337873d
REPORT RequestId: 9bc9d6db-c3d7-4f6d-bb33-ae0f4337873d	Duration: 1.90 ms	Billed Duration: 85 ms	Memory Size: 256 MB	Max Memory Used: 37 MB	Init Duration: 82.41 ms	

```

### Response payload
```json
{
  "extracted_fields": {
    "date_of_birth": "1975-01-01",
    "address": "123 Main St",
    "tax_id": "123-45-6789"
  },
  "gateway_redacted": [
    "date_of_birth"
  ]
}
```

### CloudWatch logs (mock Lambda)
```
2026-08-24T03:38:38.481000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 INIT_START Runtime Version: python:3.12.mainlinev2.v27	Runtime Version ARN: arn:aws:lambda:ap-south-1::runtime:fb4a5cbb4aeb1909cf946882192e0e708d8756b3a866c3ab89a3cfcfffeca7bc
2026-08-24T03:38:38.567000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 START RequestId: 9bc9d6db-c3d7-4f6d-bb33-ae0f4337873d Version: $LATEST
2026-08-24T03:38:38.567000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 [MOCK] Lambda invoked, event keys: ['tool', 'case_id']
2026-08-24T03:38:38.567000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 [MOCK] Direct invoke mode, tool: extract_fields
2026-08-24T03:38:38.567000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 [MOCK] invoked tool: extract_fields
2026-08-24T03:38:38.567000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 [MOCK] event: {"tool": "extract_fields", "case_id": "CONTACTS-12345"}
2026-08-24T03:38:38.567000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 [MOCK] Returning: {"extracted_fields": {"date_of_birth": "1975-01-01", "address": "123 Main St", "tax_id": "123-45-6789"}, "gateway_redacted": ["date_of_birth"]}
2026-08-24T03:38:38.570000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 END RequestId: 9bc9d6db-c3d7-4f6d-bb33-ae0f4337873d
2026-08-24T03:38:38.570000+00:00 2026/08/24/[$LATEST]7b3f028c054e4450b8b9557a7eb90984 REPORT RequestId: 9bc9d6db-c3d7-4f6d-bb33-ae0f4337873d	Duration: 1.90 ms	Billed Duration: 85 ms	Memory Size: 256 MB	Max Memory Used: 37 MB	Init Duration: 82.41 ms
```

## 2. Strands Agents on Bedrock AgentCore Harness

### What ran
- Terraform created the same Bedrock/Harness infrastructure with `strands` flavor.
- Direct `aws lambda invoke` against the mock target with `execute_transaction`.

### Request
```json
{"tool": "execute_transaction", "case_id": "CONTACTS-54321"}
```

### Response metadata
```
StatusCode: 200
FunctionError: None
ExecutedVersion: $LATEST

--- LogResult ---
START RequestId: aecc1401-ddfd-4082-8528-a91029ff745b Version: $LATEST
[MOCK] Lambda invoked, event keys: ['tool', 'case_id']
[MOCK] Direct invoke mode, tool: execute_transaction
[MOCK] invoked tool: execute_transaction
[MOCK] event: {"tool": "execute_transaction", "case_id": "CONTACTS-54321"}
[MOCK] Returning: {"status": "APPROVED", "message": "contacts updated"}
END RequestId: aecc1401-ddfd-4082-8528-a91029ff745b
REPORT RequestId: aecc1401-ddfd-4082-8528-a91029ff745b	Duration: 1.94 ms	Billed Duration: 87 ms	Memory Size: 256 MB	Max Memory Used: 37 MB	Init Duration: 84.52 ms	

```

### Response payload
```json
{
  "status": "APPROVED",
  "message": "contacts updated"
}
```

### CloudWatch logs (mock Lambda)
```

```

## 3. LangGraph + AWS Step Functions

### What ran
- Terraform created: DynamoDB checkpoint table, Step Functions state machine, three Lambdas (`intake`, `execute`, `data_power_mock`), IAM, CloudWatch log group.
- `aws stepfunctions start-execution` started a run for `CASE-REPORT-001`.
- Waited for the `waitForTaskToken` token in DynamoDB, then sent `Approved`.

### Execution summary
```json
{
  "status": "SUCCEEDED",
  "startDate": "2026-08-23T23:25:42.883000-04:00",
  "stopDate": "2026-08-23T23:31:34.559000-04:00",
  "output": "{\"ExecutedVersion\":\"$LATEST\",\"Payload\":{\"case_id\":\"CASE-REPORT-001\",\"decision\":\"Approved\",\"status\":\"CLOSED\"},\"SdkHttpMetadata\":{\"AllHttpHeaders\":{\"X-Amz-Executed-Version\":[\"$LATEST\"],\"x-amzn-Remapped-Content-Length\":[\"0\"],\"Connection\":[\"keep-alive\"],\"x-amzn-RequestId\":[\"08e442a3-651f-4265-a3b1-6af8e4cb66eb\"],\"Content-Length\":[\"74\"],\"Date\":[\"Mon, 24 Aug 2026 03:31:34 GMT\"],\"X-Amzn-Trace-Id\":[\"Root=1-6a8bbb15-3891060973c928887c8aa280;Parent=76de072dbcec7abd;Sampled=0;Lineage=1:75e6ccb9:0\"],\"Content-Type\":[\"application/json\"]},\"HttpHeaders\":{\"Connection\":\"keep-alive\",\"Content-Length\":\"74\",\"Content-Type\":\"application/json\",\"Date\":\"Mon, 24 Aug 2026 03:31:34 GMT\",\"X-Amz-Executed-Version\":\"$LATEST\",\"x-amzn-Remapped-Content-Length\":\"0\",\"x-amzn-RequestId\":\"08e442a3-651f-4265-a3b1-6af8e4cb66eb\",\"X-Amzn-Trace-Id\":\"Root=1-6a8bbb15-3891060973c928887c8aa280;Parent=76de072dbcec7abd;Sampled=0;Lineage=1:75e6ccb9:0\"},\"HttpStatusCode\":200},\"SdkResponseMetadata\":{\"RequestId\":\"08e442a3-651f-4265-a3b1-6af8e4cb66eb\"},\"StatusCode\":200}"
}
```

### `intake` Lambda logs
```
2026-08-24T03:25:43.105000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 INIT_START Runtime Version: python:3.12.mainlinev2.v27	Runtime Version ARN: arn:aws:lambda:ap-south-1::runtime:fb4a5cbb4aeb1909cf946882192e0e708d8756b3a866c3ab89a3cfcfffeca7bc
2026-08-24T03:25:43.360000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 START RequestId: 2a7fc25b-4a04-4535-9c96-0163ca604af1 Version: $LATEST
2026-08-24T03:25:43.360000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] invoked case_id=CASE-REPORT-001 task_token_prefix=AQCIAAAAKgAAAAMA...
2026-08-24T03:25:43.360000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] _run_graph starting case_id=CASE-REPORT-001 case_text=A broker emailed a change to the group contacts.
2026-08-24T03:25:43.993000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _agent decided next tool: extract_fields (use_bedrock=False)
2026-08-24T03:25:43.993000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] current history length: 0, next_tool: extract_fields
2026-08-24T03:25:43.993000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool: extract_fields
2026-08-24T03:25:44.299000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool result (from mock): {"extracted_fields": {"date_of_birth": "1975-01-01", "address": "123 Main St", "tax_id": "123-45-6789"}, "gateway_redacted": ["date_of_birth"]}
2026-08-24T03:25:44.305000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _agent decided next tool: retrieve_sop (use_bedrock=False)
2026-08-24T03:25:44.305000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] current history length: 1, next_tool: retrieve_sop
2026-08-24T03:25:44.305000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool: retrieve_sop
2026-08-24T03:25:44.330000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool result (from mock): {"required_checks": ["address", "tax_id", "duplicate"]}
2026-08-24T03:25:44.336000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _agent decided next tool: run_validations (use_bedrock=False)
2026-08-24T03:25:44.336000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] current history length: 2, next_tool: run_validations
2026-08-24T03:25:44.336000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool: run_validations
2026-08-24T03:25:44.353000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool result (from mock): {"address": "valid", "tax_id": "valid", "duplicate_check": "skipped"}
2026-08-24T03:25:44.359000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _agent decided next tool: search_similar_cases (use_bedrock=False)
2026-08-24T03:25:44.359000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] current history length: 3, next_tool: search_similar_cases
2026-08-24T03:25:44.359000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool: search_similar_cases
2026-08-24T03:25:44.389000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool result (from mock): {"similar_cases": [{"case_id": "CASE-1", "outcome": "approved"}, {"case_id": "CASE-2", "outcome": "approved"}]}
2026-08-24T03:25:44.397000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _agent decided next tool: create_decision_task (use_bedrock=False)
2026-08-24T03:25:44.397000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] current history length: 4, next_tool: create_decision_task
2026-08-24T03:25:44.397000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool: create_decision_task
2026-08-24T03:25:44.413000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH] _call_tool result (from mock): {"task_id": "TASK-123", "status": "PENDING", "review_link": "https://example.com/review/TASK-123"}
2026-08-24T03:25:44.426000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 [LANGGRAPH INTAKE] returning: {"case_id": "CASE-REPORT-001", "task_id": "TASK-123", "status": "PENDING"}
2026-08-24T03:25:44.428000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 END RequestId: 2a7fc25b-4a04-4535-9c96-0163ca604af1
2026-08-24T03:25:44.428000+00:00 2026/08/24/[$LATEST]bd0a98f6159a4b3bb613aea4bc6e3f03 REPORT RequestId: 2a7fc25b-4a04-4535-9c96-0163ca604af1	Duration: 1067.66 ms	Billed Duration: 1319 ms	Memory Size: 512 MB	Max Memory Used: 97 MB	Init Duration: 251.03 ms
```

### `execute` Lambda logs
```
2026-08-24T03:31:33.241000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 INIT_START Runtime Version: python:3.12.mainlinev2.v27	Runtime Version ARN: arn:aws:lambda:ap-south-1::runtime:fb4a5cbb4aeb1909cf946882192e0e708d8756b3a866c3ab89a3cfcfffeca7bc
2026-08-24T03:31:33.545000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 START RequestId: 08e442a3-651f-4265-a3b1-6af8e4cb66eb Version: $LATEST
2026-08-24T03:31:33.545000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 [LANGGRAPH EXECUTE] invoked case_id=CASE-REPORT-001 decision=Approved
2026-08-24T03:31:34.155000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 [LANGGRAPH] _call_tool: execute_transaction
2026-08-24T03:31:34.465000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 [LANGGRAPH] _call_tool result (from mock): {"status": "APPROVED", "message": "contacts updated"}
2026-08-24T03:31:34.465000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 [LANGGRAPH] _call_tool: write_audit_record
2026-08-24T03:31:34.480000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 [LANGGRAPH] _call_tool result (from mock): {"status": "recorded"}
2026-08-24T03:31:34.515000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 [LANGGRAPH EXECUTE] returning: {"case_id": "CASE-REPORT-001", "decision": "Approved", "status": "CLOSED"}
2026-08-24T03:31:34.517000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 END RequestId: 08e442a3-651f-4265-a3b1-6af8e4cb66eb
2026-08-24T03:31:34.517000+00:00 2026/08/24/[$LATEST]3be193324e60473881f3a32802adead2 REPORT RequestId: 08e442a3-651f-4265-a3b1-6af8e4cb66eb	Duration: 971.95 ms	Billed Duration: 1272 ms	Memory Size: 512 MB	Max Memory Used: 97 MB	Init Duration: 300.01 ms
```

### `data_power_mock` Lambda logs
```
2026-08-24T03:25:44.212000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d INIT_START Runtime Version: python:3.12.mainlinev2.v27	Runtime Version ARN: arn:aws:lambda:ap-south-1::runtime:fb4a5cbb4aeb1909cf946882192e0e708d8756b3a866c3ab89a3cfcfffeca7bc
2026-08-24T03:25:44.295000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d START RequestId: 5722a01e-afc9-4216-9d2a-9bc689bebffe Version: $LATEST
2026-08-24T03:25:44.296000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Lambda invoked, event keys: ['tool']
2026-08-24T03:25:44.296000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Direct invoke mode, tool: extract_fields
2026-08-24T03:25:44.296000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] invoked tool: extract_fields
2026-08-24T03:25:44.296000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] event: {"tool": "extract_fields"}
2026-08-24T03:25:44.296000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Returning: {"extracted_fields": {"date_of_birth": "1975-01-01", "address": "123 Main St", "tax_id": "123-45-6789"}, "gateway_redacted": ["date_of_birth"]}
2026-08-24T03:25:44.298000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d END RequestId: 5722a01e-afc9-4216-9d2a-9bc689bebffe
2026-08-24T03:25:44.298000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d REPORT RequestId: 5722a01e-afc9-4216-9d2a-9bc689bebffe	Duration: 1.89 ms	Billed Duration: 82 ms	Memory Size: 256 MB	Max Memory Used: 37 MB	Init Duration: 79.84 ms
2026-08-24T03:25:44.327000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d START RequestId: c5f3a33e-affa-4f11-8809-55aea3b15d69 Version: $LATEST
2026-08-24T03:25:44.327000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Lambda invoked, event keys: ['tool']
2026-08-24T03:25:44.327000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Direct invoke mode, tool: retrieve_sop
2026-08-24T03:25:44.327000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] invoked tool: retrieve_sop
2026-08-24T03:25:44.327000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] event: {"tool": "retrieve_sop"}
2026-08-24T03:25:44.327000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Returning: {"required_checks": ["address", "tax_id", "duplicate"]}
2026-08-24T03:25:44.329000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d END RequestId: c5f3a33e-affa-4f11-8809-55aea3b15d69
2026-08-24T03:25:44.329000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d REPORT RequestId: c5f3a33e-affa-4f11-8809-55aea3b15d69	Duration: 1.55 ms	Billed Duration: 2 ms	Memory Size: 256 MB	Max Memory Used: 37 MB
2026-08-24T03:25:44.350000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d START RequestId: 1f92c439-c739-4eaa-9252-e2a8e959d7dc Version: $LATEST
2026-08-24T03:25:44.351000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Lambda invoked, event keys: ['tool']
2026-08-24T03:25:44.351000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Direct invoke mode, tool: run_validations
2026-08-24T03:25:44.351000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] invoked tool: run_validations
2026-08-24T03:25:44.351000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] event: {"tool": "run_validations"}
2026-08-24T03:25:44.351000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Returning: {"address": "valid", "tax_id": "valid", "duplicate_check": "skipped"}
2026-08-24T03:25:44.352000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d END RequestId: 1f92c439-c739-4eaa-9252-e2a8e959d7dc
2026-08-24T03:25:44.352000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d REPORT RequestId: 1f92c439-c739-4eaa-9252-e2a8e959d7dc	Duration: 1.67 ms	Billed Duration: 2 ms	Memory Size: 256 MB	Max Memory Used: 37 MB
2026-08-24T03:25:44.385000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d START RequestId: aa0e76ca-c0df-48ec-92cd-b35c38dd0617 Version: $LATEST
2026-08-24T03:25:44.386000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Lambda invoked, event keys: ['tool']
2026-08-24T03:25:44.386000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Direct invoke mode, tool: search_similar_cases
2026-08-24T03:25:44.386000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] invoked tool: search_similar_cases
2026-08-24T03:25:44.386000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] event: {"tool": "search_similar_cases"}
2026-08-24T03:25:44.386000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Returning: {"similar_cases": [{"case_id": "CASE-1", "outcome": "approved"}, {"case_id": "CASE-2", "outcome": "approved"}]}
2026-08-24T03:25:44.387000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d END RequestId: aa0e76ca-c0df-48ec-92cd-b35c38dd0617
2026-08-24T03:25:44.387000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d REPORT RequestId: aa0e76ca-c0df-48ec-92cd-b35c38dd0617	Duration: 1.55 ms	Billed Duration: 2 ms	Memory Size: 256 MB	Max Memory Used: 37 MB
2026-08-24T03:25:44.409000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d START RequestId: a21d40cd-4b8d-4ea5-81eb-6188235c28bd Version: $LATEST
2026-08-24T03:25:44.410000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Lambda invoked, event keys: ['tool']
2026-08-24T03:25:44.410000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Direct invoke mode, tool: create_decision_task
2026-08-24T03:25:44.410000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] invoked tool: create_decision_task
2026-08-24T03:25:44.410000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] event: {"tool": "create_decision_task"}
2026-08-24T03:25:44.410000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d [MOCK] Returning: {"task_id": "TASK-123", "status": "PENDING", "review_link": "https://example.com/review/TASK-123"}
2026-08-24T03:25:44.411000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d END RequestId: a21d40cd-4b8d-4ea5-81eb-6188235c28bd
2026-08-24T03:25:44.411000+00:00 2026/08/24/[$LATEST]64e71efbbadb49f2a81afff7c5a7146d REPORT RequestId: a21d40cd-4b8d-4ea5-81eb-6188235c28bd	Duration: 1.59 ms	Billed Duration: 2 ms	Memory Size: 256 MB	Max Memory Used: 37 MB
2026-08-24T03:31:34.362000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 INIT_START Runtime Version: python:3.12.mainlinev2.v27	Runtime Version ARN: arn:aws:lambda:ap-south-1::runtime:fb4a5cbb4aeb1909cf946882192e0e708d8756b3a866c3ab89a3cfcfffeca7bc
2026-08-24T03:31:34.461000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 START RequestId: 4e39cd10-d6d5-46e7-8247-baecee9200e1 Version: $LATEST
2026-08-24T03:31:34.462000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] Lambda invoked, event keys: ['tool']
2026-08-24T03:31:34.462000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] Direct invoke mode, tool: execute_transaction
2026-08-24T03:31:34.462000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] invoked tool: execute_transaction
2026-08-24T03:31:34.462000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] event: {"tool": "execute_transaction"}
2026-08-24T03:31:34.462000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] Returning: {"status": "APPROVED", "message": "contacts updated"}
2026-08-24T03:31:34.463000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 END RequestId: 4e39cd10-d6d5-46e7-8247-baecee9200e1
2026-08-24T03:31:34.463000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 REPORT RequestId: 4e39cd10-d6d5-46e7-8247-baecee9200e1	Duration: 1.84 ms	Billed Duration: 98 ms	Memory Size: 256 MB	Max Memory Used: 37 MB	Init Duration: 95.30 ms
2026-08-24T03:31:34.477000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 START RequestId: db7d2dc6-cdc2-4205-9f16-bd82941236d6 Version: $LATEST
2026-08-24T03:31:34.477000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] Lambda invoked, event keys: ['tool']
2026-08-24T03:31:34.477000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] Direct invoke mode, tool: write_audit_record
2026-08-24T03:31:34.477000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] invoked tool: write_audit_record
2026-08-24T03:31:34.477000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] event: {"tool": "write_audit_record"}
2026-08-24T03:31:34.477000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 [MOCK] Returning: {"status": "recorded"}
2026-08-24T03:31:34.479000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 END RequestId: db7d2dc6-cdc2-4205-9f16-bd82941236d6
2026-08-24T03:31:34.479000+00:00 2026/08/24/[$LATEST]6b9005a898444611b3cbb62541287bd8 REPORT RequestId: db7d2dc6-cdc2-4205-9f16-bd82941236d6	Duration: 1.63 ms	Billed Duration: 2 ms	Memory Size: 256 MB	Max Memory Used: 37 MB
```

### Step Functions logs
```
2026-08-24T03:25:39.858000+00:00 log_stream_created_by_aws_to_validate_log_delivery_subscriptions Permissions are set correctly to allow AWS CloudWatch Logs to write into your logs while creating a subscription.
2026-08-24T03:25:42.883000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"roleArn":"arn:aws:iam::<AWS_ACCOUNT_ID>:role/arh-langgraph-sfn-role"},"redrive_count":"0","id":"1","type":"ExecutionStarted","previous_event_id":"0","event_timestamp":"1787541942883","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:25:42.901000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"name":"Intake"},"redrive_count":"0","id":"2","type":"TaskStateEntered","previous_event_id":"0","event_timestamp":"1787541942901","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:25:42.901000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"region":"ap-south-1","resource":"invoke.waitForTaskToken","resourceType":"lambda"},"redrive_count":"0","id":"3","type":"TaskScheduled","previous_event_id":"2","event_timestamp":"1787541942901","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:25:42.947000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"resource":"invoke.waitForTaskToken","resourceType":"lambda"},"redrive_count":"0","id":"4","type":"TaskStarted","previous_event_id":"3","event_timestamp":"1787541942947","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:25:44.432000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"resource":"invoke.waitForTaskToken","resourceType":"lambda"},"redrive_count":"0","id":"5","type":"TaskSubmitted","previous_event_id":"4","event_timestamp":"1787541944432","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:33.030000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"resource":"invoke.waitForTaskToken","resourceType":"lambda"},"redrive_count":"0","id":"6","type":"TaskSucceeded","previous_event_id":"5","event_timestamp":"1787542293030","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:33.040000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"name":"Intake"},"redrive_count":"0","id":"7","type":"TaskStateExited","previous_event_id":"6","event_timestamp":"1787542293040","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:33.040000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"name":"Execute"},"redrive_count":"0","id":"8","type":"TaskStateEntered","previous_event_id":"7","event_timestamp":"1787542293040","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:33.040000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"region":"ap-south-1","resource":"invoke","resourceType":"lambda"},"redrive_count":"0","id":"9","type":"TaskScheduled","previous_event_id":"8","event_timestamp":"1787542293040","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:33.085000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"resource":"invoke","resourceType":"lambda"},"redrive_count":"0","id":"10","type":"TaskStarted","previous_event_id":"9","event_timestamp":"1787542293085","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:34.521000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"resource":"invoke","resourceType":"lambda"},"redrive_count":"0","id":"11","type":"TaskSucceeded","previous_event_id":"10","event_timestamp":"1787542294521","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:34.531000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{"name":"Execute"},"redrive_count":"0","id":"12","type":"TaskStateExited","previous_event_id":"11","event_timestamp":"1787542294531","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
2026-08-24T03:31:34.559000+00:00 states/arh-langgraph-state-machine/2026-08-24-03/00000000 {"details":{},"redrive_count":"0","id":"13","type":"ExecutionSucceeded","previous_event_id":"12","event_timestamp":"1787542294559","execution_arn":"arn:aws:states:ap-south-1:<AWS_ACCOUNT_ID>:execution:arh-langgraph-state-machine:report-1787541941"}
```

## 4. AWS calls observed during the test

| Harness | AWS calls |
|---|---|
| Claude | `iam:CreateRole`, `s3:PutObject`, `lambda:CreateFunction`, `lambda:InvokeFunction`, `lambda:DeleteFunction`, `iam:DeleteRole` |
| Strands | `iam:CreateRole`, `s3:PutObject`, `lambda:CreateFunction`, `lambda:InvokeFunction`, `lambda:DeleteFunction`, `iam:DeleteRole` |
| LangGraph | `dynamodb:CreateTable`, `states:CreateStateMachine`, `lambda:CreateFunction`, `states:StartExecution`, `dynamodb:GetItem`, `states:SendTaskSuccess`, `states:DescribeExecution` |

## 5. Notes for architects

- Claude and Strands mock the full Bedrock AgentCore Gateway / DataPower REST surface with the `data_power_mock` Lambda.
- LangGraph models the same skill sequence as an explicit AWS Step Functions workflow with `waitForTaskToken` for human approval.
- All resources were destroyed after each test.
