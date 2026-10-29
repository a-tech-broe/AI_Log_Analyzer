import re
from app.config import settings

PATTERNS = [
    re.compile(r'(?i)(aws_secret_access_key|aws_access_key_id|password|passwd|token|api[_-]?key|client_secret)\s*([=:]\s*)["\']?([^\s,"\']+)'),
    re.compile(r'(?i)Bearer\s+[A-Za-z0-9._~+/=-]+'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'(?i)://[^:/\s]+:[^@/\s]+@'),
]

def redact(text: str) -> str:
    if not settings.redact_secrets:
        return text
    text = PATTERNS[0].sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    text = PATTERNS[1].sub("Bearer [REDACTED]", text)
    text = PATTERNS[2].sub("[REDACTED_AWS_ACCESS_KEY]", text)
    text = PATTERNS[3].sub("://[REDACTED]@", text)
    return text
