"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS — Approbation des urgences (appels, protocole)        ║
╚══════════════════════════════════════════════════════════════╝

Corrige la faille où `allow_call=True` était posé simplement parce que le LLM
avait écrit une balise. Désormais un appel nécessite :

  1. création d'une demande côté serveur (cible + raison) ;
  2. affichage de la cible et de la raison ;
  3. confirmation explicite de l'utilisateur ;
  4. jeton d'approbation à usage unique ;
  5. cooldown ;
  6. journalisation.

Par défaut, on contacte le PROPRIÉTAIRE / un contact de confiance — pas un
service d'urgence.
"""

import time
import logging

from permissions import PermissionManager

logger = logging.getLogger("JARVIS.emergency_approval")


class EmergencyApproval:
    def __init__(self, dispatcher, permission_manager: PermissionManager = None,
                 cooldown: float = 120.0, audit_log=None):
        self.dispatcher = dispatcher
        self.perms = permission_manager or PermissionManager(ttl_seconds=120, audit_log=audit_log)
        self.cooldown = cooldown
        self._last_call = 0.0
        self.audit_log = audit_log

    def request_call(self, target: str = "owner", reason: str = "") -> dict:
        """Crée une demande d'appel à confirmer. NE COMPOSE RIEN."""
        target = target or "owner"
        action = "appeler_hote" if target == "owner" else "appel_police"
        params = {"target": target, "reason": reason[:200]}
        req = self.perms.request(action, params)
        if self.audit_log:
            try:
                self.audit_log("urgence_demande", f"Appel demandé ({target}): {reason[:80]}",
                               meta=params)
            except Exception:
                pass
        return {"pending": True, "target": target, "reason": reason,
                "approval_id": req["approval_id"], "expires_in": req["expires_in"],
                "message": f"Confirmation requise pour appeler « {target} ». Raison : {reason}"}

    def confirm_call(self, approval_token: str, target: str = "owner", reason: str = "") -> dict:
        """Confirme et déclenche l'appel — seulement avec un jeton valide."""
        action = "appeler_hote" if target == "owner" else "appel_police"
        params = {"target": target, "reason": reason[:200]}
        ok, msg = self.perms.confirm(approval_token, action, params)
        if not ok:
            return {"ok": False, "message": f"Appel refusé : {msg}"}
        now = time.time()
        if now - self._last_call < self.cooldown:
            return {"ok": False, "message": "Appel récent (anti-rappel). Réessaie plus tard."}
        self._last_call = now
        if target == "owner":
            res = self.dispatcher.call_owner(reason or "Alerte à votre domicile.")
        else:
            disp = self.dispatcher.dispatch(reason or "Urgence confirmée",
                                            source="approbation utilisateur", allow_call=True)
            res = " | ".join(disp.get("actions", []))
        if self.audit_log:
            try:
                self.audit_log("urgence_confirmee", f"Appel exécuté ({target})", meta=params)
            except Exception:
                pass
        return {"ok": True, "message": res}
