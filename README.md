# AI Log Analyzer

Local-first log analysis for SRE/DevOps teams. It includes a CLI, a FastAPI web UI, deterministic pattern detection, CloudWatch Logs ingestion, optional local inference with Ollama, and optional Amazon Bedrock fallback.

## Features

- **Pattern detection without AI**: finds database connectivity problems, memory pressure, full disks, upstream timeouts, auth failures, and crash/restart loops, and counts lines by log level.
- **Secret redaction**: masks passwords, tokens, API keys, Bearer tokens, AWS access key IDs, and credentials in URLs before anything reaches a model. Set `REDACT_SECRETS=false` to turn this off.
- **AI investigation**: produces a structured hypothesis (root cause, confidence, evidence, checks, safe remediation options, unknowns) using Ollama, Bedrock, or both.
- **CloudWatch ingestion**: lists log groups and fetches a bounded time window, following `nextToken` pagination up to the requested limit.
- **Falls back cleanly**: if no AI provider can be reached, you still get the rule-based findings.

## Project layout

```
app/
  analyzer.py      Deterministic level counting and pattern detection
  ai.py            Ollama / Bedrock investigation, rules-only fallback
  api.py           FastAPI app + single-page web UI
  aws_logs.py      CloudWatch Logs listing and fetching (paginated)
  aws_session.py   Shared boto3 session (profile + region)
  cli.py           Command-line interface
  config.py        Environment-based settings
  redaction.py     Secret redaction
  service.py       Input limits + analysis pipeline
iam/               Least-privilege IAM policy template
samples/           Example log file
tests/             Pytest suite (no network or AWS access needed)
```

## Safety and cost defaults

- No auto-remediation and no infrastructure write permissions.
- Input is limited by size and line count. Common credentials are redacted before AI analysis.
- `AI_PROVIDER=hybrid` tries Ollama first, then Bedrock. If both are unavailable, the rule-based findings still work.
- Bedrock charges per invocation. To avoid cloud AI charges, use `AI_PROVIDER=ollama`, `AI_PROVIDER=none`, or `--no-ai`.
- Logs may contain sensitive information. Check your organization's data handling policy before sending log data to a hosted model.
- This MVP is meant for a trusted local environment. Do not expose the API publicly without authentication, TLS, rate limiting, and tenant isolation.

## Requirements

- Python 3.11+ (3.12 recommended)
- Optional: Docker + Docker Compose
- Optional: Ollama installed locally, or the included Compose service
- AWS credentials, only if you use CloudWatch or Bedrock

## 1. Run locally

```bash
git clone <repo-url> AI_Log_Analyzer
cd AI_Log_Analyzer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set your AWS region and profile. For local Ollama, install it from https://ollama.com and run:

```bash
ollama pull qwen2.5:3b
ollama serve
```

In another terminal:

```bash
set -a && source .env && set +a
uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000.

### CLI

```bash
# Analyze a local file with AI
python -m app.cli file samples/sample.log

# Analyze without AI (free, rule-based only)
python -m app.cli file samples/sample.log --no-ai

# List CloudWatch log groups
python -m app.cli groups

# Analyze the last 2 hours of a CloudWatch log group
python -m app.cli cloudwatch /aws/ecs/my-service --hours 2 --limit 1000
```

## 2. Docker Compose

Compose runs the API and Ollama locally and mounts your AWS config read-only.

```bash
cp .env.example .env
# Edit .env; set AWS_PROFILE and AWS_REGION
docker compose up --build -d   # production: ENV_FILE=.env.production docker compose up --build -d
docker compose exec ollama ollama pull qwen2.5:3b
```

Open http://localhost:8000. `docker compose down` stops the stack and keeps the model cache (the named volume remains). `docker compose down -v` also deletes the cache.

Compose mounts `${HOME}/.aws` read-only. If your AWS credentials use SSO, sign in on the host first with `aws sso login --profile YOUR_PROFILE`, and make sure the profile name in `.env` matches.

## 3. Configuration

### Local vs. production

| Environment | Env file | `AI_PROVIDER` | Behavior |
|---|---|---|---|
| Local development | `.env` (from `.env.example`) | `ollama` | Local model only; never calls Bedrock, so no cloud AI charges |
| Production | `.env.production` (from `.env.production.example`) | `hybrid` | Ollama first, Bedrock fallback if Ollama is down or returns unusable output |

```bash
# Local
cp .env.example .env
docker compose up --build -d          # or run uvicorn / the CLI directly

# Production
cp .env.production.example .env.production
ENV_FILE=.env.production docker compose up --build -d
```

Both real env files are git-ignored; only the `*.example` templates are committed. In production, leave `AWS_PROFILE` empty so boto3 uses the task role or instance profile. Check which provider is active with `curl localhost:8000/health`.

To try hybrid behavior locally for a single run without editing `.env`:

```bash
AI_PROVIDER=hybrid python -m app.cli file samples/sample.log
```

### Settings

All settings come from environment variables:

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `AI Log Analyzer` | Name shown in the API and health check |
| `AWS_PROFILE` | _(empty)_ | Named AWS profile; empty uses the default credential chain |
| `AWS_REGION` | `us-east-1` | Region for CloudWatch and Bedrock |
| `AWS_ENDPOINT_URL` | _(empty)_ | Custom CloudWatch Logs endpoint (e.g. LocalStack) |
| `AI_PROVIDER` | `hybrid` | `hybrid`, `ollama`, `bedrock`, or `none`. Any other value fails at startup. `.env.example` sets `ollama` |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Ollama model name |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model or inference profile ID |
| `MAX_LOG_BYTES` | `2000000` | Maximum input size in bytes |
| `MAX_LINES` | `10000` | Maximum input line count |
| `REDACT_SECRETS` | `true` | Redact credentials before analysis |

## 4. AWS setup (read-only)

Configure a named profile with the AWS CLI:

```bash
aws configure --profile log-analyzer
# Or, for IAM Identity Center:
aws configure sso --profile log-analyzer
aws sso login --profile log-analyzer
```

Set `AWS_PROFILE=log-analyzer` and `AWS_REGION=us-east-1` in `.env`.

Attach an IAM policy based on `iam/cloudwatch-readonly-policy.json` to the identity the analyzer uses. For least privilege, replace `"Resource": "*"` for CloudWatch with the ARNs of the log groups you want to inspect. If you use Bedrock, restrict `bedrock:InvokeModel` to the selected model ARN where possible. Bedrock model access must also be enabled in the AWS account and region.

**Do not put long-lived access keys in `.env` or bake credentials into the image.** Use AWS SSO locally, and task roles or instance profiles when deployed.

## 5. AI provider behavior

- `AI_PROVIDER=hybrid`: Ollama first, Bedrock second.
- `AI_PROVIDER=ollama`: local model only.
- `AI_PROVIDER=bedrock`: Bedrock only.
- `AI_PROVIDER=none`: skips inference and always returns rule-based results. You can also skip AI per request with `--no-ai` in the CLI or by unchecking "Use AI" in the web UI.

Model IDs and availability vary by account and region. Set `BEDROCK_MODEL_ID` to a model enabled in your account. Newer models may need a cross-region inference profile ID such as `us.anthropic...`. The response's `ai.provider` field shows which provider answered (`ollama`, `bedrock`, or `rules-only`). When it is `rules-only`, `ai.analysis.unknowns` lists why each provider failed.

## 6. API endpoints

| Method | Path | Body | Notes |
|---|---|---|---|
| `GET` | `/` | — | Web UI |
| `GET` | `/health` | — | Status and active AI provider |
| `POST` | `/api/analyze` | `{"logs":"...","use_ai":true}` | 400 on empty or oversized input |
| `GET` | `/api/aws/log-groups` | — | 502 if the CloudWatch call fails |
| `POST` | `/api/aws/analyze` | `{"log_group":"/aws/ecs/service","hours":1,"limit":1000,"use_ai":true}` | 404 if no events; `hours` 1–168, `limit` 1–10000 |

Interactive API docs: http://127.0.0.1:8000/docs

## 7. Running tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite mocks the AI providers and CloudWatch, so it needs no network access or AWS credentials.

## 8. MVP limitations / production hardening backlog

- Add authentication, authorization, audit logs, tenant isolation, rate limiting, encrypted persistent storage, and secrets management before multi-user deployment.
- Add structured parsing for JSON logs, trace/request correlation, deployment markers, metrics/events correlation, and configurable detection rules.
- Add CI security scanning, automated dependency updates, SBOM generation, and observability for the analyzer itself.
- Add a queue and async workers before high-volume ingestion.
- AI output is a hypothesis. Require engineer review, and never run suggested commands automatically.

## Troubleshooting

- `Unable to locate credentials`: run `aws sso login --profile log-analyzer` or configure the intended AWS profile.
- `AccessDeniedException`: check `logs:DescribeLogGroups`, `logs:FilterLogEvents`, and the resource scope.
- Ollama connection error: check that `ollama serve` is running, the model is pulled, and `OLLAMA_URL` is correct. Inside Compose it is `http://ollama:11434`.
- Bedrock errors: check model access, region, model ID, and IAM permission.
- `AI_PROVIDER must be one of ...`: fix the typo in `.env`. The app refuses to start with an unknown provider.
