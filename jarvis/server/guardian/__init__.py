"""
JARVIS — Mode Gardien (module de sécurité domestique).

Séparation stricte des responsabilités :
  • schemas.py        — validation stricte des sorties de vision (perception)
  • tracking.py       — suivi temporel persistant des personnes
  • zones.py          — zones configurables (porche, porte, privé, masque public)
  • state_machine.py  — machine d'état déterministe (IDLE…COOLDOWN)
  • policy.py         — politique de sécurité + politique de parole sûre
  • store.py          — persistance SQLite (événements, décisions, approbations…)
  • service.py        — orchestration perception → suivi → décision → action
  • config.py         — configuration via variables d'environnement
  • providers/        — fournisseurs vision / parole / temps-réel (local + cloud)

Principes :
  1. Aucune action physique n'est déclenchée par une simple phrase du LLM.
  2. Une perception invalide ⇒ UNKNOWN ⇒ observation seule, aucune action.
  3. Fail-closed : en cas de doute, on n'agit pas.
"""

from .config import GuardianConfig, load_config
from .state_machine import GuardianStateMachine, State
from .schemas import VisionObservation, parse_observation
from .policy import GuardianPolicy, Facts, Decision

__all__ = [
    "GuardianConfig",
    "load_config",
    "GuardianStateMachine",
    "State",
    "VisionObservation",
    "parse_observation",
    "GuardianPolicy",
    "Facts",
    "Decision",
]
