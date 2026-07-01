"""Le fournisseur Realtime ne doit exposer qu'un secret éphémère."""

import pytest

from guardian.providers.base import ProviderError
from guardian.providers.openai_realtime import OpenAIRealtimeProvider


class _Response:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_realtime_uses_current_client_secret_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _Response({"value": "ek_short_lived", "expires_at": 123456})

    monkeypatch.setenv("OPENAI_API_KEY", "server-only-test-key")
    monkeypatch.setenv("OPENAI_REALTIME_TOKEN_TTL", "45")
    monkeypatch.setattr("guardian.providers.openai_realtime.requests.post", fake_post)

    out = OpenAIRealtimeProvider().mint_ephemeral_session()

    assert captured["url"].endswith("/realtime/client_secrets")
    assert captured["json"]["session"]["type"] == "realtime"
    assert captured["json"]["session"]["model"] == "gpt-realtime-2"
    assert captured["json"]["expires_after"]["seconds"] == 45
    assert captured["headers"]["Authorization"] == "Bearer server-only-test-key"
    assert out["client_secret"]["value"] == "ek_short_lived"
    assert "server-only-test-key" not in str(out)


def test_realtime_rejects_missing_ephemeral_value(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "server-only-test-key")
    monkeypatch.setattr(
        "guardian.providers.openai_realtime.requests.post",
        lambda *args, **kwargs: _Response({"expires_at": 123456}),
    )
    with pytest.raises(ProviderError, match="client secret"):
        OpenAIRealtimeProvider().mint_ephemeral_session()
