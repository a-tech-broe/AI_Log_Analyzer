from app.redaction import redact

def test_redacts_key_value_secrets():
    assert redact("password=hunter2 user=bob") == "password=[REDACTED] user=bob"
    assert redact('api_key: "abc123"') == "api_key: [REDACTED]\""

def test_redacts_bearer_tokens_and_aws_keys():
    out = redact("Authorization: Bearer eyJ.abc.def key AKIAABCDEFGHIJKLMNOP")
    assert "eyJ" not in out and "AKIA" not in out
    assert "Bearer [REDACTED]" in out and "[REDACTED_AWS_ACCESS_KEY]" in out

def test_redacts_url_credentials():
    assert redact("postgres://admin:s3cret@db:5432/app") == "postgres://[REDACTED]@db:5432/app"
