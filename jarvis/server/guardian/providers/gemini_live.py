"""
Fournisseur Gemini (vision + Live) — OPTIONNEL.

⚠️ État : SQUELETTE explicitement NON TERMINÉ. La clé GEMINI_API_KEY reste
côté serveur. Le mint d'un jeton éphémère pour Gemini Live n'est pas encore
implémenté ; tant qu'il ne l'est pas, `mint_ephemeral_session` lève une erreur
claire plutôt que d'exposer une clé. La vision par image est fonctionnelle.

Ne JAMAIS renvoyer GEMINI_API_KEY au navigateur.
"""

import os
import json
import logging

import requests

from .base import VisionProvider, RealtimeProvider, ProviderError

logger = logging.getLogger("JARVIS.guardian.gemini")

GEMINI_BASE = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")


def _key() -> str:
    return os.getenv("GEMINI_API_KEY", "")


class GeminiVisionProvider(VisionProvider):
    name = "gemini"

    def __init__(self, config=None):
        self.config = config
        self.model = os.getenv("GEMINI_VISION_MODEL", "gemini-1.5-flash")
        self.timeout = getattr(config, "request_timeout", 20.0) if config else 20.0

    def available(self) -> bool:
        return bool(_key())

    def analyze(self, image_b64: str, prompt: str) -> str:
        if not _key():
            raise ProviderError("GEMINI_API_KEY absente (côté serveur).")
        if "," in image_b64[:40]:
            image_b64 = image_b64.split(",", 1)[1]
        url = f"{GEMINI_BASE}/models/{self.model}:generateContent?key={_key()}"
        try:
            r = requests.post(url, headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}]}],
                    "generationConfig": {"temperature": 0.0}},
                timeout=self.timeout)
            r.raise_for_status()
            cands = r.json().get("candidates", [])
            return cands[0]["content"]["parts"][0]["text"].strip() if cands else ""
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Gemini vision: {e}")


class GeminiLiveProvider(RealtimeProvider):
    name = "gemini"

    def __init__(self, config=None):
        self.config = config

    def mint_ephemeral_session(self) -> dict:
        # NON IMPLÉMENTÉ : on échoue proprement au lieu d'exposer une clé.
        raise ProviderError(
            "Gemini Live n'est pas encore implémenté (jeton éphémère manquant). "
            "Utilise GUARDIAN_REALTIME_PROVIDER=openai ou le mode local Ollama.")
