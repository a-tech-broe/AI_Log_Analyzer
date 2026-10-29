import pytest
from app import ai
from app.analyzer import analyze_logs

RESULT = analyze_logs("ERROR Database connection timeout")

def _settings(monkeypatch, provider):
    monkeypatch.setattr(ai.settings, "ai_provider", provider, raising=False)

@pytest.fixture(autouse=True)
def unfrozen_settings(monkeypatch):
    # Settings is a frozen dataclass; swap in a mutable copy for tests.
    from types import SimpleNamespace
    monkeypatch.setattr(ai, "settings", SimpleNamespace(**ai.settings.__dict__))

def test_none_provider_skips_inference(monkeypatch):
    _settings(monkeypatch, "none")
    monkeypatch.setattr(ai, "_ollama", lambda p: pytest.fail("should not call Ollama"))
    out = ai.investigate(RESULT)
    assert out["provider"] == "rules-only"
    assert out["analysis"]["severity"] == "high"

def test_hybrid_falls_back_to_bedrock(monkeypatch):
    _settings(monkeypatch, "hybrid")
    def boom(prompt):
        raise ConnectionError("ollama down")
    monkeypatch.setattr(ai, "_ollama", boom)
    monkeypatch.setattr(ai, "_bedrock", lambda p: {"incident_title": "db"})
    assert ai.investigate(RESULT) == {"provider": "bedrock", "analysis": {"incident_title": "db"}}

def test_all_providers_fail_returns_rules_only_with_errors(monkeypatch):
    _settings(monkeypatch, "hybrid")
    def boom(prompt):
        raise ConnectionError("down")
    monkeypatch.setattr(ai, "_ollama", boom)
    monkeypatch.setattr(ai, "_bedrock", boom)
    out = ai.investigate(RESULT)
    assert out["provider"] == "rules-only"
    assert len(out["analysis"]["unknowns"]) == 2

def test_parse_json_tolerates_code_fences():
    assert ai._parse_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}
