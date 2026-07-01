"""Gestionnaire central de permissions + approbations à usage unique."""
import time

from permissions import PermissionManager, Level


def test_levels():
    pm = PermissionManager()
    assert pm.level_of("heure") == Level.READ_ONLY
    assert pm.level_of("controler_lumiere") == Level.REVERSIBLE
    assert pm.level_of("ecrire_fichier") == Level.SENSITIVE
    assert pm.level_of("tuer_processus") == Level.SENSITIVE
    assert pm.level_of("armer_alarme") == Level.CRITICAL
    assert pm.level_of("appel_police") == Level.CRITICAL


def test_unknown_action_is_fail_closed_sensitive():
    pm = PermissionManager()
    assert pm.level_of("outil_inconnu_xyz") == Level.SENSITIVE
    assert pm.requires_approval("outil_inconnu_xyz")


def test_read_only_needs_no_approval():
    pm = PermissionManager()
    ok, info = pm.guard("heure", {})
    assert ok and info["approval"] == "non_requise"


def test_sensitive_requires_approval_then_confirm():
    """10. LLM tente d'écrire un fichier : demande d'approbation, pas d'exécution."""
    pm = PermissionManager()
    ok, info = pm.guard("ecrire_fichier", {"chemin": "a.txt", "contenu": "x"})
    assert not ok and info["approval"] == "requise"
    token = info["request"]["approval_id"]
    ok2, info2 = pm.guard("ecrire_fichier", {"chemin": "a.txt", "contenu": "x"}, approval_token=token)
    assert ok2 and info2["approval"] == "ok"


def test_approval_single_use():
    pm = PermissionManager()
    req = pm.request("tuer_processus", {"cible": "chrome"})
    tok = req["approval_id"]
    assert pm.confirm(tok, "tuer_processus", {"cible": "chrome"})[0]
    assert not pm.confirm(tok, "tuer_processus", {"cible": "chrome"})[0]   # 2e usage refusé


def test_approval_param_mismatch_rejected():
    pm = PermissionManager()
    req = pm.request("tuer_processus", {"cible": "chrome"})
    ok, msg = pm.confirm(req["approval_id"], "tuer_processus", {"cible": "firefox"})
    assert not ok and "paramètre" in msg.lower()


def test_approval_action_mismatch_rejected():
    pm = PermissionManager()
    req = pm.request("ecrire_fichier", {"chemin": "a"})
    ok, _ = pm.confirm(req["approval_id"], "tuer_processus", {"chemin": "a"})
    assert not ok


def test_approval_expiry():
    pm = PermissionManager(ttl_seconds=0.01)
    req = pm.request("armer_alarme", {"armer": False})
    time.sleep(0.05)
    ok, msg = pm.confirm(req["approval_id"], "armer_alarme", {"armer": False})
    assert not ok and "expir" in msg.lower()


def test_audit_log_called():
    seen = []
    pm = PermissionManager(audit_log=lambda k, s, meta=None: seen.append((k, s)))
    pm.request("armer_alarme", {"armer": True})
    assert any(k == "approbation_demande" for k, _ in seen)
