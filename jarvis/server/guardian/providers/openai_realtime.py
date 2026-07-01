"""Fournisseur OpenAI : vision optionnelle et jetons Realtime éphémères.

La clé permanente ``OPENAI_API_KEY`` reste côté serveur. Pour WebRTC, le
navigateur ne reçoit qu'un client secret de courte durée créé par l'endpoint
Realtime actuel. Aucune clé permanente n'est renvoyée ni journalisée.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from .base import ProviderError, RealtimeProvider, VisionProvider

logger = logging.getLogger("JARVIS.guardian.openai")

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
DEFAULT_REALTIME_MODEL = "gpt-realtime-2"
DEFAULT_VISION_MODEL = "gpt-4o-mini"  # configurable; kept for Chat Completions compatibility


def _key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def _bounded_ttl() -> int:
    try:
        ttl = int(os.getenv("OPENAI_REALTIME_TOKEN_TTL", "60"))
    except (TypeError, ValueError):
        ttl = 60
    return max(10, min(ttl, 600))


def _safe_headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
    }
    safety_id = os.getenv("OPENAI_SAFETY_IDENTIFIER", "").strip()
    if safety_id:
        headers["OpenAI-Safety-Identifier"] = safety_id
    return headers


class OpenAIVisionProvider(VisionProvider):
    name = "openai"

    def __init__(self, config=None):
        self.config = config
        self.model = os.getenv("OPENAI_VISION_MODEL", DEFAULT_VISION_MODEL)
        self.timeout = getattr(config, "request_timeout", 20.0) if config else 20.0

    def available(self) -> bool:
        return bool(_key())

    def analyze(self, image_b64: str, prompt: str) -> str:
        if not _key():
            raise ProviderError("OPENAI_API_KEY absente (côté serveur).")
        url = image_b64 if image_b64.startswith("data:") else f"data:image/jpeg;base64,{image_b64}"
        try:
            response = requests.post(
                f"{OPENAI_BASE}/chat/completions",
                headers=_safe_headers(),
                json={
                    "model": self.model,
                    "max_tokens": 300,
                    "temperature": 0.0,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except (requests.exceptions.RequestException, KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"OpenAI vision: {exc}") from exc


class OpenAIRealtimeProvider(RealtimeProvider):
    name = "openai"

    def __init__(self, config=None):
        self.config = config
        self.model = (
            getattr(config, "openai_realtime_model", None)
            or os.getenv("OPENAI_REALTIME_MODEL", DEFAULT_REALTIME_MODEL)
        )
        self.voice = os.getenv("OPENAI_REALTIME_VOICE", "marin")

    def available(self) -> bool:
        return bool(_key())

    def mint_ephemeral_session(self) -> dict[str, Any]:
        """Crée un client secret Realtime court via ``/realtime/client_secrets``.

        La structure de retour conserve ``client_secret.value`` pour rester
        compatible avec l'interface JARVIS existante, mais ne contient jamais la
        clé permanente utilisée dans l'en-tête serveur.
        """
        if not _key():
            raise ProviderError("OPENAI_API_KEY absente (côté serveur).")

        payload = {
            "expires_after": {"anchor": "created_at", "seconds": _bounded_ttl()},
            "session": {
                "type": "realtime",
                "model": self.model,
                "audio": {"output": {"voice": self.voice}},
            },
        }
        try:
            response = requests.post(
                f"{OPENAI_BASE}/realtime/client_secrets",
                headers=_safe_headers(),
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            value = data.get("value") if isinstance(data, dict) else None
            expires_at = data.get("expires_at") if isinstance(data, dict) else None
            if not isinstance(value, str) or not value.startswith("ek_"):
                raise ProviderError("OpenAI Realtime: client secret invalide ou absent.")
            return {
                "provider": "openai",
                "model": self.model,
                "client_secret": {"value": value, "expires_at": expires_at},
                "expires_at": expires_at,
            }
        except ProviderError:
            raise
        except (requests.exceptions.RequestException, ValueError, TypeError) as exc:
            raise ProviderError(f"OpenAI Realtime session: {exc}") from exc
