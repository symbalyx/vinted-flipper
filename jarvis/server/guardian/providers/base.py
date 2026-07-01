"""
Interfaces des fournisseurs + fournisseur de parole « template » (100% local,
sans LLM). Les clés d'API ne sont JAMAIS exposées au client : un fournisseur
temps-réel ne renvoie au navigateur qu'un jeton de session éphémère.
"""

import random
from abc import ABC, abstractmethod


class ProviderError(Exception):
    pass


class VisionProvider(ABC):
    """Perception : image → texte JSON brut (validé ensuite par schemas.py)."""

    name = "base"

    @abstractmethod
    def analyze(self, image_b64: str, prompt: str) -> str:
        ...

    def available(self) -> bool:        # pragma: no cover - dépend du réseau
        return True


class SpeechProvider(ABC):
    """Génération de la phrase à prononcer (et UNIQUEMENT cela)."""

    name = "base"

    @abstractmethod
    def generate_line(self, level: str, context: dict) -> dict:
        """Retourne {phrase, lang, tone}. Aucune décision d'action ici."""
        ...


class RealtimeProvider(ABC):
    """Conversation audio temps réel. Le serveur ne délivre qu'un jeton éphémère."""

    name = "base"

    @abstractmethod
    def mint_ephemeral_session(self) -> dict:
        """Retourne un jeton de session éphémère (jamais la clé permanente)."""
        ...


# ── Fournisseur de parole local, sans LLM (toujours disponible) ──
_TEMPLATES = {
    "engage": {
        "fr": ["Vous êtes filmé. Cette zone est sous surveillance.",
               "Bonjour. Vous êtes enregistré sur une propriété privée."],
        "en": ["You are being recorded. This area is under surveillance.",
               "Hello. You are being recorded on private property."],
    },
    "warn": {
        "fr": ["Veuillez vous éloigner de la porte. Zone surveillée et enregistrée.",
               "Propriété privée filmée. Merci de quitter les lieux."],
        "en": ["Please step away from the door. This area is recorded.",
               "Private property under recording. Please leave."],
    },
    "alert": {
        "fr": ["Une alerte locale vient d'être enregistrée. Vous êtes filmé."],
        "en": ["A local alert has just been logged. You are being recorded."],
    },
}


class TemplateSpeechProvider(SpeechProvider):
    """Parole 100% locale, sans modèle — sûre par construction."""

    name = "template"

    def __init__(self, config=None):
        self.config = config

    def generate_line(self, level: str, context: dict) -> dict:
        lang = (context or {}).get("lang", "fr")
        lang = "en" if str(lang).startswith("en") else "fr"
        bank = _TEMPLATES.get(level, _TEMPLATES["engage"]).get(lang, _TEMPLATES["engage"]["fr"])
        return {"phrase": random.choice(bank), "lang": lang, "tone": "ferme"}
