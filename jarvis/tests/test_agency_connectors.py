import json
import pytest

from integrations.n8n import N8NClient
from integrations.emailer import EmailService


class FakeResponse:
    content = b'{}'
    def raise_for_status(self): pass
    def json(self): return {"id": "wf1", "ok": True}


def test_n8n_create_uses_public_api_and_api_key(monkeypatch):
    captured = {}
    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse()
    monkeypatch.setattr("integrations.n8n.requests.request", fake_request)
    client = N8NClient("http://127.0.0.1:5678", "secret", timeout=3)
    workflow = {"name": "Test", "nodes": [{
        "id": "1", "name": "Manual", "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1, "position": [0, 0], "parameters": {},
    }], "connections": {}}
    result = client.create_workflow(json.dumps(workflow))
    assert result["id"] == "wf1"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/api/v1/workflows")
    assert captured["kwargs"]["headers"]["X-N8N-API-KEY"] == "secret"


def test_n8n_refuses_execute_command_by_default(monkeypatch):
    monkeypatch.delenv("N8N_ALLOW_RISKY_NODES", raising=False)
    client = N8NClient("http://localhost:5678", "secret")
    workflow = {"name": "Danger", "nodes": [{
        "id": "1", "name": "Shell", "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1, "position": [0, 0], "parameters": {},
    }], "connections": {}}
    with pytest.raises(PermissionError):
        client.validate_workflow(workflow)


def test_email_preview_validates_without_sending(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "jarvis@example.com")
    service = EmailService()
    preview = service.preview("alice@example.com", "Bonjour", "Message")
    assert preview["configured"] is True
    assert preview["to"] == ["alice@example.com"]
    with pytest.raises(ValueError):
        service.preview("not-an-email", "Bonjour", "Message")


def test_n8n_rejects_path_like_workflow_ids(monkeypatch):
    client = N8NClient(base_url="http://127.0.0.1:5678", api_key="test")
    for bad in ("../../users", "abc/activate", "", "a?x=1"):
        try:
            client.activate_workflow(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"workflow id dangereux accepté: {bad}")
