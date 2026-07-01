"""
Fournisseur OpenAI (vision + Realtime).

⚠️ La clé principale OPENAI_API_KEY reste CÔTÉ SERVEUR. Pour la conversation
temps réel dans le navigateur (WebRTC), le serveur ne renvoie qu'un JETON DE
SESSION ÉPHÉMÈRE (`client_secret`) créé via l'API OpenAI ; la clé permanente
n'est jamais transmise au client.

Le modèle Realtime est configurable via OPENAI_REALTIME_MODEL (ne pas figer un
nom de modèle ancien dans plusieurs fichiers).

État : la vision est utilisable ; le mint de session Realtime est implémenté
mais NON TESTÉ ici sans clé réelle — voir LIMITATIONS dans CHANGELOG_GUARDIAN.md.
"""

import os
import logging

import requests

from .base import VisionProvider, RealtimeProvider, ProviderError

logger = logging.getLogger("JARVIS.guardian.openai")

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def _key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


class OpenAIVisionProvider(VisionProvider):
    name = "openai"

    def __init__(self, config=None):
        self.config = config
        self.model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
        self.timeout = getattr(config, "request_timeout", 20.0) if config else 20.0

    def available(self) -> bool:
        return bool(_key())

    def analyze(self, image_b64: str, prompt: str) -> str:
        if not _key():
            raise ProviderError("OPENAI_API_KEY absente (côté serveur).")
        url = image_b64 if image_b64.startswith("data:") else f"data:image/jpeg;base64,{image_b64}"
        try:
            r = requests.post(f"{OPENAI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {_key()}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "max_tokens": 300, "temperature": 0.0,
                      "messages": [{"role": "user", "content": [
                          {"type": "text", "text": prompt},
                          {"type": "image_url", "image_url": {"url": url}}]}]},
                timeout=self.timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"OpenAI vision: {e}")


class OpenAIRealtimeProvider(RealtimeProvider):
    name = "openai"

    def __init__(self, config=None):
        self.config = config
        self.model = (getattr(config, "openai_realtime_model", None)
                      or os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview"))
        self.voice = os.getenv("OPENAI_REALTIME_VOICE", "verse")

    def mint_ephemeral_session(self) -> dict:
        """Crée une session Realtime éphémère côté serveur. Le navigateur reçoit
        seulement le `client_secret` à durée de vie courte, jamais la clé."""
        if not _key():
            raise ProviderError("OPENAI_API_KEY absente (côté serveur).")
        try:
            r = requests.post(f"{OPENAI_BASE}/realtime/sessions",
                headers={"Authorization": f"Bearer {_key()}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "voice": self.voice},
                timeout=15)
            r.raise_for_status()
            data = r.json()
            # On ne renvoie QUE le secret éphémère + métadonnées non sensibles.
            return {
                "provider": "openai",
                "model": self.model,
                "client_secret": data.get("client_secret", {}),
                "expires_at": data.get("client_secret", {}).get("expires_at"),
            }
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"OpenAI Realtime session: {e}")
