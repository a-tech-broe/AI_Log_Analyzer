from fastapi.testclient import TestClient
from app import api

client = TestClient(api.app)

def test_health():
    body = client.get("/health").json()
    assert body["status"] == "ok" and "ai_provider" in body

def test_index_renders():
    response = client.get("/")
    assert response.status_code == 200 and "__AI_LABEL__" not in response.text

def test_analyze_without_ai():
    response = client.post("/api/analyze", json={"logs": "ERROR out of memory", "use_ai": False})
    assert response.status_code == 200
    body = response.json()
    assert body["ai"] is None
    assert body["findings"][0]["id"] == "memory_pressure"

def test_analyze_rejects_blank_logs():
    assert client.post("/api/analyze", json={"logs": "   ", "use_ai": False}).status_code == 400

def test_cloudwatch_paginates(monkeypatch):
    from app import aws_logs
    pages = [
        {"events": [{"timestamp": 2, "message": "ERROR b"}], "nextToken": "t1"},
        {"events": [], "nextToken": "t2"},
        {"events": [{"timestamp": 1, "message": "ERROR a"}]},
    ]
    class FakeClient:
        def filter_log_events(self, **kwargs):
            return pages.pop(0)
    monkeypatch.setattr(aws_logs, "_client", lambda: FakeClient())
    assert aws_logs.fetch_logs("/aws/test", 1, 100) == "ERROR a\nERROR b"
