from __future__ import annotations
from flask import Blueprint, jsonify, request


def create_voice_blueprint(service):
    bp = Blueprint("voice", __name__, url_prefix="/api/voice")

    @bp.get("/status")
    def status():
        return jsonify(service.status())

    @bp.post("/warmup")
    def warmup():
        result = service.warmup()
        return jsonify(result), (200 if result.get("ok") else 503)

    @bp.post("/transcribe")
    def transcribe():
        upload = request.files.get("audio")
        if upload is None:
            return jsonify({"ok": False, "error": "Fichier audio requis"}), 400
        data = upload.read(service.config.max_audio_bytes + 1)
        if len(data) > service.config.max_audio_bytes:
            return jsonify({"ok": False, "error": "Audio trop volumineux"}), 413
        name = (upload.filename or "audio.webm").lower()
        suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ".webm"
        language = str(request.form.get("language") or service.config.language)[:10]
        try:
            return jsonify(service.transcribe(data, suffix=suffix, language=language))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 503
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Transcription impossible : {exc}"}), 500

    return bp
