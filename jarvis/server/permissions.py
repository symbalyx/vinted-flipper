"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS — Gestionnaire central de permissions des outils      ║
╚══════════════════════════════════════════════════════════════╝

Toute action de l'agent est classée dans une catégorie de risque. Les actions
SENSITIVE et CRITICAL exigent une approbation côté APPLICATION (pas seulement
dans le prompt) : un jeton aléatoire à usage unique, lié à l'action exacte et à
ses paramètres, avec expiration et journal d'audit.

Le fallback (parser de tags) ne doit JAMAIS exécuter une action sensible : il
passe obligatoirement par une demande d'approbation.
"""

import time
import json
import secrets
import logging
import threading
from dataclasses import dataclass, field

logger = logging.getLogger("JARVIS.permissions")


class Level:
    READ_ONLY = "READ_ONLY"
    REVERSIBLE = "REVERSIBLE"
    SENSITIVE = "SENSITIVE"
    CRITICAL = "CRITICAL"


# Classement des actions (par nom d'outil). Tout outil inconnu est traité comme
# SENSITIVE par défaut (fail-closed).
ACTION_LEVELS = {
    # READ_ONLY
    "heure": Level.READ_ONLY, "meteo": Level.READ_ONLY, "info_systeme": Level.READ_ONLY,
    "etat_lumieres": Level.READ_ONLY, "home_lights": Level.READ_ONLY,
    "calculer": Level.READ_ONLY, "processus_top": Level.READ_ONLY,
    "recherche_web": Level.READ_ONLY, "lire_page_web": Level.READ_ONLY,
    # REVERSIBLE
    "controler_lumiere": Level.REVERSIBLE, "activer_scene": Level.REVERSIBLE,
    "volume": Level.REVERSIBLE, "luminosite_ecran": Level.REVERSIBLE,
    "controle_media": Level.REVERSIBLE, "rappel": Level.REVERSIBLE,
    "mot_de_passe": Level.REVERSIBLE, "memoriser": Level.REVERSIBLE,
    # SENSITIVE
    "lire_fichier": Level.SENSITIVE, "ecrire_fichier": Level.SENSITIVE,
    "lister_fichiers": Level.SENSITIVE, "presse_papier_lire": Level.SENSITIVE,
    "presse_papier_ecrire": Level.SENSITIVE, "ouvrir_app": Level.SENSITIVE,
    "ouvrir_url": Level.SENSITIVE, "capture_ecran": Level.SENSITIVE,
    "tuer_processus": Level.SENSITIVE, "homepod_dire": Level.SENSITIVE,
    "notif_tel": Level.SENSITIVE, "camera": Level.SENSITIVE,
    "verrouiller_pc": Level.SENSITIVE,
    # CRITICAL
    "armer_alarme": Level.CRITICAL, "desarmer_alarme": Level.CRITICAL,
    "alimentation_pc": Level.CRITICAL, "appeler_hote": Level.CRITICAL,
    "appel_police": Level.CRITICAL, "protocole_urgence": Level.CRITICAL,
    "supprimer_donnees": Level.CRITICAL, "deverrouiller_porte": Level.CRITICAL,
}

REQUIRES_APPROVAL = {Level.SENSITIVE, Level.CRITICAL}


@dataclass
class Approval:
    token: str
    action: str
    params: dict
    level: str
    created: float
    expires: float
    used: bool = False


class PermissionManager:
    def __init__(self, ttl_seconds: float = 120.0, audit_log=None):
        self.ttl = ttl_seconds
        self.audit_log = audit_log          # callable(kind, summary, meta) ex: event_log.add
        self._approvals = {}
        self._lock = threading.Lock()

    def level_of(self, action: str) -> str:
        return ACTION_LEVELS.get(action, Level.SENSITIVE)   # inconnu → fail-closed

    def requires_approval(self, action: str) -> bool:
        return self.level_of(action) in REQUIRES_APPROVAL

    # ── Création d'une demande d'approbation ───────────────────
    def request(self, action: str, params: dict = None) -> dict:
        level = self.level_of(action)
        token = secrets.token_urlsafe(24)
        now = time.time()
        appr = Approval(token=token, action=action, params=params or {}, level=level,
                        created=now, expires=now + self.ttl)
        with self._lock:
            self._approvals[token] = appr
        self._audit("approbation_demande", f"{action} ({level})",
                    {"params": params, "token": token[:6] + "…"})
        return {"approval_id": token, "action": action, "params": params or {},
                "level": level, "expires_in": int(self.ttl)}

    # ── Confirmation (usage unique, action+params exacts) ──────
    def confirm(self, token: str, action: str, params: dict = None):
        """Retourne (ok, message). N'AUTORISE que si le jeton correspond
        EXACTEMENT à l'action et aux paramètres demandés."""
        with self._lock:
            appr = self._approvals.get(token)
            if not appr:
                return False, "Jeton d'approbation inconnu"
            if appr.used:
                return False, "Jeton déjà utilisé (usage unique)"
            if time.time() > appr.expires:
                del self._approvals[token]
                return False, "Jeton expiré"
            if appr.action != action:
                return False, "L'action ne correspond pas au jeton"
            if _normalize(appr.params) != _normalize(params or {}):
                return False, "Les paramètres ne correspondent pas au jeton"
            appr.used = True
        self._audit("approbation_confirmee", f"{action} ({appr.level})", {"params": params})
        return True, "Approuvé"

    def guard(self, action: str, params: dict, approval_token: str = None):
        """Point d'entrée unique. Retourne (autorise: bool, info: dict)."""
        level = self.level_of(action)
        if level not in REQUIRES_APPROVAL:
            return True, {"level": level, "approval": "non_requise"}
        if not approval_token:
            return False, {"level": level, "approval": "requise",
                           "request": self.request(action, params)}
        ok, msg = self.confirm(approval_token, action, params)
        return ok, {"level": level, "approval": "ok" if ok else "refusee", "message": msg}

    def reject(self, token: str) -> bool:
        """Refus explicite d'une approbation (l'invalide définitivement)."""
        with self._lock:
            appr = self._approvals.get(token)
            if not appr or appr.used:
                return False
            appr.used = True
        self._audit("approbation_refusee", appr.action, {"params": appr.params})
        return True

    def pending(self) -> list:
        """Approbations en attente (non utilisées, non expirées) pour l'UI."""
        now = time.time()
        with self._lock:
            # Purge opportuniste des jetons expirés.
            for tok in [t for t, a in self._approvals.items() if now > a.expires]:
                del self._approvals[tok]
            return [{"approval_id": a.token, "action": a.action, "params": a.params,
                     "level": a.level, "expires_in": max(0, int(a.expires - now))}
                    for a in self._approvals.values() if not a.used]

    def _audit(self, kind, summary, meta):
        logger.info(f"[PERM] {kind}: {summary}")
        if self.audit_log:
            try:
                self.audit_log(kind, summary, meta=meta)
            except Exception:
                pass


def _normalize(d: dict):
    """Comparaison stable des paramètres (ordre indépendant)."""
    try:
        return json.dumps(d, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(d)
