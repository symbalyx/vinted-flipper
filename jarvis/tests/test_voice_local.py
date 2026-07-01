from types import SimpleNamespace
from flask import Flask

from voice.api import create_voice_blueprint
from voice.service import VoiceService


class FakeVoice:
    config = SimpleNamespace(max_audio_bytes=20, language="fr")
    def status(self): return {"enabled": True, "dependency_available": True, "ready": True}
    def warmup(self): return {"ok": True, "latency_ms": 1}
    def transcribe(self, data, suffix=".webm", language="fr"):
        return {"ok": True, "text": "bonjour jarvis", "latency_ms": 12, "language": language}


def test_voice_blueprint_transcribes_multipart():
    app = Flask(__name__)
    app.register_blueprint(create_voice_blueprint(FakeVoice()))
    client = app.test_client()
    import io
    r = client.post("/api/voice/transcribe", data={
        "audio": (io.BytesIO(b"123456"), "voice.webm"), "language": "fr"
    }, content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.get_json()["text"] == "bonjour jarvis"


def test_voice_service_reports_optional_dependency():
    cfg = SimpleNamespace(enabled=True, model="base", device="cpu", compute_type="int8",
                          language="fr", max_audio_bytes=1000, beam_size=1,
                          vad_filter=True, auto_send=False)
    status = VoiceService(cfg).status()
    assert status["model"] == "base"
    assert isinstance(status["dependency_available"], bool)
