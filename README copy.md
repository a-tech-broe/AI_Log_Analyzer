# AI Log Analyzer MVP

Local-first log analysis for SRE/DevOps teams. Includes a CLI, FastAPI web UI, deterministic pattern detection, CloudWatch Logs ingestion, optional Ollama inference, and optional Amazon Bedrock fallback.

## Safety and cost defaults

- No auto-remediation or infrastructure write permissions.
- Log input is size/line limited and common credentials are redacted before AI analysis.
- `AI_PROVIDER=hybrid` tries Ollama first, then Bedrock. If both are unavailable, deterministic rule-based findings still work.
- Bedrock is pay-per-invocation. To avoid cloud AI charges, use `AI_PROVIDER=ollama` or `--no-ai`.
- Logs may contain sensitive information. Review your organization's data handling policy before sending any log data to a hosted model.
- This MVP is intended for a trusted local environment. Do not expose the API publicly without authentication, TLS, rate limiting, and tenant isolation.

## Requirements

- Python 3.11+ (3.12 recommended)
- Optional: Docker + Docker Compose
- Optional: Ollama installed locally, or use the included Compose service
- AWS credentials only if using CloudWatch or Bedrock

## 1. Run locally (recommended)

```bash
unzip ai-log-analyzer-mvp.zip
cd ai-log-analyzer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set your AWS region/profile. For local Ollama, install Ollama from https://ollama.com and run:

```bash
ollama pull qwen2.5:3b
ollama serve
```

In another terminal:

```bash
set -a && source .env && set +a
uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000

### CLI

```bash
# Analyze a local file with AI
python -m app.cli file ./sample.log

# Analyze without AI (free, deterministic rules)
python -m app.cli file ./sample.log --no-ai

# List CloudWatch log groups
python -m app.cli groups

# Analyze the last 2 hours of a CloudWatch log group
python -m app.cli cloudwatch /aws/ecs/my-service --hours 2 --limit 1000
```

## 2. Docker Compose

The Compose setup runs the API and Ollama locally. It mounts your AWS config read-only.

```bash
cp .env.example .env
# Edit .env; set AWS_PROFILE and AWS_REGION
docker compose up --build -d
docker compose exec ollama ollama pull qwen2.5:3b
```

Open http://localhost:8000. Stop with `docker compose down`; preserve the model cache with `docker compose down` (the named volume remains). Remove the cache only with `docker compose down -v`.

Note: Compose mounts `${HOME}/.aws` read-only. If your AWS credentials use SSO, authenticate on the host first with `aws sso login --profile YOUR_PROFILE`. Ensure the profile name in `.env` matches.

## 3. AWS setup (read-only)

Configure a named profile using AWS CLI:

```bash
aws configure --profile log-analyzer
# Or, for IAM Identity Center:
aws configure sso --profile log-analyzer
aws sso login --profile log-analyzer
```

Set `AWS_PROFILE=log-analyzer` and `AWS_REGION=us-east-1` in `.env`.

Attach an IAM policy based on `iam/cloudwatch-readonly-policy.json` to the identity used by the analyzer. For least privilege, replace `"Resource": "*"` for CloudWatch with the specific log-group ARNs you want to inspect. If using Bedrock, restrict `bedrock:InvokeModel` to the selected model ARN where possible. Bedrock model access must also be enabled in the AWS account/region.

**Do not use long-lived access keys in `.env` or bake credentials into the image.** Prefer AWS SSO locally and task roles/instance profiles when deployed.

## 4. AI provider behavior

- `AI_PROVIDER=hybrid`: Ollama first, Bedrock second.
- `AI_PROVIDER=ollama`: local model only.
- `AI_PROVIDER=bedrock`: Bedrock only.
- `AI_PROVIDER=none`: set this value to skip inference (or use `--no-ai` in CLI / uncheck AI in web UI).

For a Bedrock-only test, set `AI_PROVIDER=bedrock`. Model IDs and availability vary by account and region; update `BEDROCK_MODEL_ID` to a model enabled in your account.

## 5. API endpoints

- `GET /health`
- `POST /api/analyze` with `{"logs":"...","use_ai":true}`
- `GET /api/aws/log-groups`
- `POST /api/aws/analyze` with `{"log_group":"/aws/ecs/service","hours":1,"limit":1000,"use_ai":true}`

Interactive API docs: http://127.0.0.1:8000/docs

## 6. MVP limitations / production hardening backlog

- CloudWatch fetch currently reads a bounded time window and first page of events; add pagination and `nextToken` handling for larger investigations.
- Add authentication, authorization, audit logs, tenant isolation, rate limiting, encrypted persistent storage, and secrets management before multi-user deployment.
- Add structured parsing for JSON logs, trace/request correlation, deployment markers, metrics/events correlation, and configurable detection rules.
- Add tests, CI security scanning, dependency pinning automation, SBOM generation, and observability for the analyzer itself.
- Add a queue and async workers before high-volume ingestion.
- AI output is a hypothesis. Require engineer review; never execute suggested commands automatically.

## Troubleshooting

- `Unable to locate credentials`: run `aws sso login --profile log-analyzer` or configure the intended AWS profile.
- `AccessDeniedException`: verify `logs:DescribeLogGroups`, `logs:FilterLogEvents`, and resource scope.
- Ollama connection error: verify `ollama serve`, model availability, and `OLLAMA_URL`.
- Bedrock errors: verify model access, region, model ID, and IAM permission.
