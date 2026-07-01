"""STT local à chargement paresseux avec faster-whisper.

Le modèle n'est jamais téléchargé ou chargé à l'import du serveur. Le premier
appel (ou /warmup) le charge une seule fois sous verrou. Les enregistrements
sont écrits dans un fichier temporaire puis supprimés immédiatement.
"""
from __future__ import annotations
import importlib.util
import logging
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger("JARVIS.voice")


class VoiceService:
    def __init__(self, config):
        self.config = config
        self._model = None
        self._lock = threading.RLock()
        self._last_error = ""

    @property
    def dependency_available(self):
        return importlib.util.find_spec("faster_whisper") is not None

    def status(self):
        return {
            "enabled": self.config.enabled,
            "dependency_available": self.dependency_available,
            "ready": self._model is not None,
            "model": self.config.model,
            "device": self.config.device,
            "compute_type": self.config.compute_type,
            "language": self.config.language,
            "auto_send": self.config.auto_send,
            "last_error": self._last_error,
        }

    def _load_model(self):
        if not self.config.enabled:
            raise RuntimeError("Reconnaissance vocale locale désactivée")
        if not self.dependency_available:
            raise RuntimeError("faster-whisper n'est pas installé")
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from faster_whisper import WhisperModel
                    started = time.perf_counter()
                    self._model = WhisperModel(self.config.model,
                                               device=self.config.device,
                                               compute_type=self.config.compute_type)
                    logger.info("Modèle Whisper %s chargé en %.2fs", self.config.model,
                                time.perf_counter() - started)
        return self._model

    def warmup(self):
        started = time.perf_counter()
        try:
            self._load_model()
            self._last_error = ""
            return {"ok": True, "latency_ms": round((time.perf_counter() - started) * 1000)}
        except Exception as exc:
            self._last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def transcribe(self, audio: bytes, suffix=".webm", language=None):
        if not isinstance(audio, (bytes, bytearray)) or not audio:
            raise ValueError("Audio vide")
        if len(audio) > self.config.max_audio_bytes:
            raise ValueError("Audio trop volumineux")
        if suffix not in {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".mp4"}:
            suffix = ".webm"
        model = self._load_model()
        started = time.perf_counter()
        path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="jarvis_voice_", suffix=suffix, delete=False) as tmp:
                tmp.write(audio)
                path = Path(tmp.name)
            segments, info = model.transcribe(
                str(path),
                language=language or self.config.language or None,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
                condition_on_previous_text=False,
                word_timestamps=False,
                temperature=0.0,
            )
            text = " ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
            latency = round((time.perf_counter() - started) * 1000)
            self._last_error = ""
            return {
                "ok": True,
                "text": text,
                "language": getattr(info, "language", language or self.config.language),
                "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
                "duration": float(getattr(info, "duration", 0.0) or 0.0),
                "latency_ms": latency,
                "model": self.config.model,
            }
        except Exception as exc:
            self._last_error = str(exc)
            raise
        finally:
            if path:
                try:
                    path.unlink(missing_ok=True)
                except Exception as cleanup_error:
                    logger.warning("Suppression du fichier audio temporaire impossible: %s", cleanup_error)
