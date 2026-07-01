"""Garde-fous pour la géolocalisation photo et l'OSINT autorisé.

Le module n'essaie pas de décider si une enquête est juridiquement valide dans
une juridiction donnée. Il impose un périmètre produit plus étroit : médias de
l'utilisateur, biens qu'il contrôle, lieux publics, entreprises et dossiers
explicitement autorisés. Il refuse le pistage de personnes, l'identification
faciale et la recherche d'une adresse privée.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import unicodedata


ALLOWED_PURPOSES = {
    "personal_photo": "Photo personnelle ou média appartenant à l'utilisateur",
    "owned_property": "Bien, véhicule ou site contrôlé par l'utilisateur",
    "public_place": "Lieu public, monument ou infrastructure publique",
    "business": "Entreprise, commerce ou établissement ouvert au public",
    "authorized_case": "Dossier professionnel avec autorisation documentée",
}

ALLOWED_TARGETS = {"place", "public_landmark", "business", "owned_property"}
BLOCKED_TARGETS = {
    "private_person",
    "private_home",
    "live_tracking",
    "face_identity",
    "personal_profile",
}

BLOCKED_INTENT_PHRASES = {
    "doxx", "doxing", "doxxing", "retrouve cette personne",
    "trouve cette personne", "ou habite", "adresse privee",
    "adresse personnelle", "identifie cette personne", "identite de cette personne",
    "profil social", "reseaux sociaux", "numero de telephone",
    "adresse email", "plaque d immatriculation", "suivre en temps reel",
    "track this person", "find this person", "home address", "private address",
    "identify this person", "social media profile", "license plate",
}


def _normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return " ".join("".join(ch for ch in text if not unicodedata.combining(ch)).split())


@dataclass(frozen=True)
class LegalOsintContext:
    purpose: str
    target_type: str
    authorized: bool
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _short_text(value: Any, limit: int = 240) -> str:
    return str(value or "").strip()[:limit]


def validate_legal_osint_context(data: Any) -> tuple[LegalOsintContext | None, str, int]:
    """Valide l'attestation d'usage avant toute analyse d'image.

    Retourne ``(contexte, erreur, code_http)``. Le contrôle est volontairement
    fail-closed : l'absence d'attestation ou une cible personnelle est refusée.
    """
    if not isinstance(data, dict):
        return None, "Contexte d'utilisation manquant", 400

    authorized = data.get("authorization") is True or data.get("authorized") is True
    if not authorized:
        return None, (
            "Confirme que tu possèdes cette photo ou que tu as l'autorisation "
            "d'analyser ce lieu."
        ), 403

    purpose = _short_text(data.get("purpose"), 48)
    if purpose not in ALLOWED_PURPOSES:
        return None, "Finalité OSINT non autorisée", 403

    request_text = _normalized(
        f"{data.get('message', '')} {data.get('hint', '')} {data.get('purpose_note', '')}"
    )
    if any(phrase in request_text for phrase in BLOCKED_INTENT_PHRASES):
        return None, (
            "JARVIS peut localiser un lieu autorisé, mais pas identifier, "
            "pister ou profiler une personne privée."
        ), 403

    target_type = _short_text(data.get("target_type") or "place", 48)
    if target_type in BLOCKED_TARGETS or target_type not in ALLOWED_TARGETS:
        return None, (
            "JARVIS refuse l'identification, le pistage ou la recherche "
            "d'adresse d'une personne privée."
        ), 403

    note = _short_text(data.get("purpose_note"), 240)
    if purpose == "authorized_case" and len(note) < 8:
        return None, "Décris brièvement l'autorisation du dossier", 400

    return LegalOsintContext(
        purpose=purpose,
        target_type=target_type,
        authorized=True,
        note=note,
    ), "", 200
