"""
Politique de sécurité + politique de PAROLE sûre.

Sépare clairement :
  • la DÉCISION d'agir (déterministe, ici) ;
  • la GÉNÉRATION de la phrase (déléguée à un LLM, mais bornée et nettoyée).

Le LLM ne décide jamais d'une action physique. La sirène / les actions
physiques ne dépendent que de la politique ci-dessous, jamais d'un « OUI » ou
d'une phrase produite par le modèle.

Politique de parole :
  • Interdiction d'inventer : chien, arme, voisins/police prévenus, secours en
    route, reconnaissance faciale certaine.
  • Une action n'est ANNONÇABLE que si confirmée par un événement serveur.
  • Pas de menace de violence, pas de discrimination, pas d'usurpation de police.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .state_machine import State, Facts


# ── Politique de parole : motifs interdits (claims non vérifiables) ──
_FORBIDDEN_PATTERNS = [
    r"\bchien\b", r"\bdog\b",
    r"\barme\b|\bflingue\b|\bgun\b|\bweapon\b",
    r"\bvoisins?\b.{0,20}\bpréven", r"\bneighbou?rs?\b.{0,20}\bnotif",
    r"\bpolice\b.{0,25}\b(préven|en route|arriv|appel|notif|called|on (?:their|the) way)",
    r"\bgendarm", r"\b1?7\b.{0,6}\bappel", r"\b911\b", r"\b112\b",
    r"\bsecours\b.{0,20}\b(route|arriv|préven)",
    r"\bje suis (?:la|de la) police\b", r"\bthis is the police\b",
    r"\breconnu? (?:ton|votre) visage\b", r"\bje (?:te|vous) (?:connais|reconnais)\b",
    r"\bje vais (?:te|vous) (?:frapper|tuer|casser)\b", r"\bi('?| wi)ll hurt you\b",
]
_FORBIDDEN_RE = re.compile("|".join(_FORBIDDEN_PATTERNS), re.IGNORECASE)

# Phrases sûres par défaut (fallback si le LLM est indisponible ou la phrase rejetée).
SAFE_LINES = {
    State.ENGAGING: [
        "Vous êtes filmé. Cette zone est sous surveillance.",
        "Bonjour. Vous êtes actuellement enregistré sur cette propriété privée.",
    ],
    State.WARNING: [
        "Veuillez vous éloigner de la porte. Cette zone est surveillée et enregistrée.",
        "Vous êtes sur une propriété privée filmée. Merci de quitter les lieux.",
    ],
    State.ALERT: [
        "Une alerte locale vient d'être enregistrée. Vous êtes filmé.",
    ],
}


@dataclass
class Decision:
    state: str
    should_speak: bool = False
    speech_level: str = ""               # engage | warn | alert
    should_notify: bool = False
    siren_allowed: bool = False          # autorisation (≠ déclenchement)
    reason: str = ""
    safe_fallback_line: str = ""
    confirmed_facts: List[str] = field(default_factory=list)


class GuardianPolicy:
    def __init__(self, config):
        self.cfg = config

    # ── Décision d'action (déterministe) ────────────────────────
    def decide(self, state: str, facts: Facts,
               confirmed_facts: Optional[List[str]] = None) -> Decision:
        confirmed_facts = confirmed_facts or []
        d = Decision(state=state, confirmed_facts=list(confirmed_facts))

        if state in (State.IDLE, State.COOLDOWN):
            d.reason = "rien à signaler"
            return d

        if state == State.OBSERVING:
            d.reason = "observation seule, aucune parole"
            return d

        if state == State.ENGAGING:
            d.should_speak = True
            d.speech_level = "engage"
            d.safe_fallback_line = SAFE_LINES[State.ENGAGING][0]
            d.reason = "engagement verbal poli"
            return d

        if state == State.WARNING:
            d.should_speak = True
            d.should_notify = True
            d.speech_level = "warn"
            d.safe_fallback_line = SAFE_LINES[State.WARNING][0]
            d.reason = "avertissement ferme + notification"
            return d

        if state == State.ALERT:
            d.should_speak = True
            d.should_notify = True
            d.speech_level = "alert"
            d.safe_fallback_line = SAFE_LINES[State.ALERT][0]
            # La sirène n'est AUTORISÉE qu'ici, et seulement si :
            #   • déclenchement manuel / approbation propriétaire / intrusion
            #     confirmée  (faits critiques)  OU
            #   • escalade auto explicitement activée dans la config.
            d.siren_allowed = bool(
                facts.manual_trigger or facts.owner_approved_alert
                or facts.human_validated_intrusion
                or (self.cfg.auto_escalate and facts.door_zone_breached
                    and facts.door_contact and facts.alarm_armed)
            )
            d.reason = "niveau critique (action physique sous conditions)"
            return d

        return d

    # ── Politique de parole : nettoyage de la phrase produite par le LLM ──
    def sanitize_phrase(self, text: str, confirmed_facts: Optional[List[str]] = None):
        """
        Retourne (texte_sûr, ok). Si la phrase enfreint la politique (claim
        interdit non confirmé), on la REJETTE (ok=False) et l'appelant utilise
        le fallback sûr. Aucune annonce d'action non confirmée par le serveur.
        """
        confirmed_facts = set(confirmed_facts or [])
        if not text or not text.strip():
            return "", False
        clean = text.strip().strip('"\'' ).replace("\n", " ")
        clean = re.sub(r"\s+", " ", clean)[:240]

        # Autorise « propriétaire prévenu » UNIQUEMENT si confirmé par le serveur.
        owner_claim = re.search(r"propriétaire.{0,20}(préven|averti|notif)|owner.{0,15}notif",
                                clean, re.IGNORECASE)
        if owner_claim and "owner_notified" not in confirmed_facts:
            return "", False

        if _FORBIDDEN_RE.search(clean):
            return "", False

        return clean, True

    def safe_line_for(self, level: str) -> str:
        mapping = {"engage": State.ENGAGING, "warn": State.WARNING, "alert": State.ALERT}
        lines = SAFE_LINES.get(mapping.get(level, State.ENGAGING), [""])
        return lines[0]
