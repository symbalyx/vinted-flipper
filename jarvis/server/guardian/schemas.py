"""
Schémas de PERCEPTION — sortie stricte du modèle de vision.

Le modèle de vision NE décide PAS du niveau de menace ni de la sirène. Il ne
fait que DÉCRIRE l'image, sous une forme structurée et validée. Toute valeur
hors schéma ⇒ observation invalide ⇒ UNKNOWN ⇒ aucune action.

On valide avec Pydantic si présent, sinon avec un validateur pur équivalent
(le module reste utilisable dans une installation minimale).
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple

try:                                  # Pydantic optionnel
    from pydantic import BaseModel, Field, ValidationError, field_validator
    _HAS_PYDANTIC = True
except Exception:                     # pragma: no cover - dépend de l'install
    _HAS_PYDANTIC = False


# Listes de chaînes : on borne la taille pour éviter les abus du modèle.
_MAX_ITEMS = 12
_MAX_LEN = 80


def _clean_str_list(value, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} doit être une liste")
    out = []
    for item in value[:_MAX_ITEMS]:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} ne doit contenir que des chaînes")
        s = item.strip()[:_MAX_LEN]
        if s:
            out.append(s)
    return out


@dataclass
class VisionObservation:
    """Description structurée et bornée d'une image de sécurité."""

    person_count: int = 0
    confidence: float = 0.0
    clothing: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    door_contact: bool = False
    face_covered: bool = False
    uncertainty: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


if _HAS_PYDANTIC:

    class _PydObs(BaseModel):
        model_config = {"extra": "forbid"}
        person_count: int = Field(ge=0, le=50)
        confidence: float = Field(ge=0.0, le=1.0)
        clothing: List[str] = Field(default_factory=list, max_length=_MAX_ITEMS)
        objects: List[str] = Field(default_factory=list, max_length=_MAX_ITEMS)
        actions: List[str] = Field(default_factory=list, max_length=_MAX_ITEMS)
        door_contact: bool = False
        face_covered: bool = False
        uncertainty: List[str] = Field(default_factory=list, max_length=_MAX_ITEMS)

        @field_validator("clothing", "objects", "actions", "uncertainty")
        @classmethod
        def _trim(cls, v):
            return [str(x).strip()[:_MAX_LEN] for x in v if str(x).strip()]


def _extract_json(raw: str) -> Optional[dict]:
    """Extrait le 1er objet JSON d'une réponse de LLM (souvent entourée de texte)."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    # Retire d'éventuelles clôtures ```json … ```
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Cherche le premier { … } équilibré.
    start = raw.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start:i + 1])
                except Exception:
                    return None
    return None


def parse_observation(raw) -> Tuple[Optional[VisionObservation], str]:
    """
    Valide une sortie de vision.

    Retourne (observation, "") si valide, sinon (None, message_d_erreur).
    Une erreur ⇒ l'appelant DOIT traiter comme UNKNOWN et NE rien déclencher.
    """
    data = _extract_json(raw)
    if data is None:
        return None, "JSON de vision introuvable ou illisible"
    if not isinstance(data, dict):
        return None, "La sortie de vision n'est pas un objet JSON"

    # Champs obligatoires minimaux
    for key in ("person_count", "confidence"):
        if key not in data:
            return None, f"Champ obligatoire manquant: {key}"

    try:
        if _HAS_PYDANTIC:
            m = _PydObs(**data)
            obs = VisionObservation(**m.model_dump())
        else:
            pc = data["person_count"]
            conf = data["confidence"]
            if not isinstance(pc, int) or isinstance(pc, bool):
                raise ValueError("person_count doit être un entier")
            if not (0 <= pc <= 50):
                raise ValueError("person_count hors bornes")
            if not isinstance(conf, (int, float)) or isinstance(conf, bool):
                raise ValueError("confidence doit être un nombre")
            if not (0.0 <= float(conf) <= 1.0):
                raise ValueError("confidence hors bornes [0,1]")
            obs = VisionObservation(
                person_count=pc,
                confidence=float(conf),
                clothing=_clean_str_list(data.get("clothing"), "clothing"),
                objects=_clean_str_list(data.get("objects"), "objects"),
                actions=_clean_str_list(data.get("actions"), "actions"),
                door_contact=bool(data.get("door_contact", False)),
                face_covered=bool(data.get("face_covered", False)),
                uncertainty=_clean_str_list(data.get("uncertainty"), "uncertainty"),
            )
    except Exception as e:                       # pydantic ValidationError incluse
        if _HAS_PYDANTIC and isinstance(e, ValidationError):
            return None, f"Validation vision échouée: {e.errors()[0].get('msg', 'invalide')}"
        return None, f"Validation vision échouée: {e}"

    return obs, ""


# Prompt strict à donner au modèle de vision (température ~0).
VISION_SYSTEM_PROMPT = (
    "Tu es un module de PERCEPTION. Tu DÉCRIS uniquement ce que tu vois sur "
    "l'image de sécurité. Tu ne juges pas la dangerosité, tu ne donnes aucune "
    "consigne. Réponds STRICTEMENT par un objet JSON valide, sans texte autour, "
    "au format exact :\n"
    '{"person_count": <entier>=0>, "confidence": <0.0-1.0>, '
    '"clothing": [<chaînes>], "objects": [<chaînes>], "actions": [<chaînes>], '
    '"door_contact": <bool>, "face_covered": <bool>, "uncertainty": [<chaînes>]}\n'
    "Si tu n'es pas sûr d'un élément, ajoute-le dans \"uncertainty\" plutôt que "
    "d'inventer. Si l'image est vide, person_count vaut 0."
)
