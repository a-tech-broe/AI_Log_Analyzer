from app.analyzer import analyze_logs
from app.ai import investigate
from app.config import settings

def analyze(raw: str, use_ai: bool = True) -> dict:
    if not raw or not raw.strip():
        raise ValueError("No log content supplied.")
    encoded = raw.encode("utf-8")
    if len(encoded) > settings.max_log_bytes:
        raise ValueError(f"Input exceeds MAX_LOG_BYTES ({settings.max_log_bytes}).")
    if len(raw.splitlines()) > settings.max_lines:
        raise ValueError(f"Input exceeds MAX_LINES ({settings.max_lines}).")
    result = analyze_logs(raw)
    result["ai"] = investigate(result) if use_ai else None
    return result
