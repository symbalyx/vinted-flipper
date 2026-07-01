"""
Fournisseur LOCAL via Ollama (vision + parole). Aucune image ne quitte le réseau.

  ollama pull llava            # vision (ou llama3.2-vision / qwen2.5-vl)
  ollama pull llama3.1         # parole

Mode dégradé clairement signalé : si Ollama est injoignable, `available()`
renvoie False et l'appelant retombe sur le fournisseur de parole « template ».
"""

import os
import json
import logging

import requests

from .base import VisionProvider, SpeechProvider, ProviderError

logger = logging.getLogger("JARVIS.guardian.ollama")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_GEN = os.getenv("OLLAMA_VISION_URL", f"{OLLAMA_HOST}/api/generate")
OLLAMA_CHAT = f"{OLLAMA_HOST}/api/chat"


class OllamaVisionProvider(VisionProvider):
    name = "ollama"

    def __init__(self, config=None):
        self.config = config
        self.model = os.getenv("JARVIS_VISION_MODEL", "llava")
        self.timeout = getattr(config, "request_timeout", 20.0) if config else 20.0

    def available(self) -> bool:
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
            names = [m.get("name", "") for m in r.json().get("models", [])]
            return any(self.model.split(":")[0] in n for n in names)
        except Exception:
            return False

    def analyze(self, image_b64: str, prompt: str) -> str:
        if "," in image_b64[:40]:
            image_b64 = image_b64.split(",", 1)[1]
        try:
            r = requests.post(OLLAMA_GEN, json={
                "model": self.model, "prompt": prompt, "images": [image_b64],
                "format": "json",            # force une sortie JSON
                "options": {"temperature": 0.0},   # analyse structurée déterministe
                "stream": False}, timeout=self.timeout)
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Ollama vision indisponible: {e}")


class OllamaSpeechProvider(SpeechProvider):
    name = "ollama"

    def __init__(self, config=None):
        self.config = config
        self.model = os.getenv("JARVIS_SPEECH_MODEL", os.getenv("OLLAMA_MODEL", "llama3.1"))
        self.timeout = getattr(config, "request_timeout", 20.0) if config else 20.0

    def generate_line(self, level: str, context: dict) -> dict:
        ctx = context or {}
        lang = "en" if str(ctx.get("lang", "fr")).startswith("en") else "fr"
        sys = (
            "Tu es JARVIS, gardien d'une propriété privée. Tu produis UNIQUEMENT "
            "une courte phrase à prononcer (max 20 mots), ferme mais sans menace "
            "de violence. INTERDIT : prétendre être la police, parler d'un chien, "
            "d'une arme, de voisins/police/secours prévenus, ou d'une reconnaissance "
            "faciale. Décris seulement des faits vérifiables (la personne est filmée, "
            "enregistrée, sur une propriété privée). "
            + ("Réponds en anglais." if lang == "en" else "Réponds en français.")
        )
        user = (f"Niveau: {level}. Observation: {json.dumps(ctx.get('observation', {}), ensure_ascii=False)}. "
                "Donne la phrase.")
        try:
            r = requests.post(OLLAMA_CHAT, json={
                "model": self.model,
                "messages": [{"role": "system", "content": sys},
                             {"role": "user", "content": user}],
                "options": {"temperature": 0.7}, "stream": False}, timeout=self.timeout)
            r.raise_for_status()
            phrase = r.json().get("message", {}).get("content", "").strip()
            return {"phrase": phrase, "lang": lang, "tone": "ferme"}
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Ollama speech indisponible: {e}")
