import os
from dataclasses import dataclass

AI_PROVIDERS = {"hybrid", "ollama", "bedrock", "none"}

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Log Analyzer")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_profile: str = os.getenv("AWS_PROFILE", "")
    aws_endpoint_url: str = os.getenv("AWS_ENDPOINT_URL", "")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    ai_provider: str = os.getenv("AI_PROVIDER", "hybrid").strip().lower()
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    max_log_bytes: int = int(os.getenv("MAX_LOG_BYTES", "2000000"))
    max_lines: int = int(os.getenv("MAX_LINES", "10000"))
    redact_secrets: bool = os.getenv("REDACT_SECRETS", "true").lower() == "true"

    def __post_init__(self):
        if self.ai_provider not in AI_PROVIDERS:
            raise ValueError(f"AI_PROVIDER must be one of {sorted(AI_PROVIDERS)}, got {self.ai_provider!r}.")

settings = Settings()
