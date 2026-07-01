"""Contexte d'exécution propagé aux outils sans variable globale partagée.

Un sous-agent de mission définit ``mission_id`` pendant son travail. Le
PermissionManager recopie cet identifiant dans la demande d'approbation afin
que l'interface et l'orchestrateur puissent reprendre la bonne mission après
validation humaine.
"""
from contextlib import contextmanager
from contextvars import ContextVar

CURRENT_MISSION_ID = ContextVar("jarvis_current_mission_id", default="")
CURRENT_STEP_ID = ContextVar("jarvis_current_step_id", default="")


@contextmanager
def execution_scope(mission_id: str = "", step_id: str = ""):
    mt = CURRENT_MISSION_ID.set(str(mission_id or ""))
    st = CURRENT_STEP_ID.set(str(step_id or ""))
    try:
        yield
    finally:
        CURRENT_STEP_ID.reset(st)
        CURRENT_MISSION_ID.reset(mt)
