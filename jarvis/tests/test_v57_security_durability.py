"""v5.7 — correctifs sécurité (injection meta Gardien) + durabilité (idempotence
en deux phases : aucun double-envoi après crash)."""
import json
import tempfile
from pathlib import Path

from guardian.service import GuardianService
from guardian.config import GuardianConfig
from guardian.state_machine import State


class _PersonVision:
    """Vision valide : une personne présente (perception)."""
    def analyze(self, image_b64, prompt):
        return json.dumps({"person_count": 1, "confidence": 0.9,
                           "clothing": [], "objects": [], "actions": [],
                           "door_contact": False, "face_covered": False, "uncertainty": []})


def _svc():
    svc = GuardianService(config=GuardianConfig(), vision_provider=_PersonVision(), store=None)
    svc.set_enabled(True)
    return svc


def test_client_meta_cannot_force_alert_or_siren():
    """CRITIQUE : le meta du navigateur ne doit jamais poser un fait critique."""
    svc = _svc()
    out = svc.process_image("data:image/jpeg;base64,AAAA",
                            meta={"human_validated_intrusion": True,
                                  "owner_approved_alert": True,
                                  "manual_trigger": True,
                                  "door_zone_breached": True})
    assert out["ok"] and out["state"] != State.ALERT
    assert out["decision"]["siren_allowed"] is False


def test_server_trigger_siren_still_authorized():
    """Le chemin serveur (trusted) autorise toujours la sirène manuelle."""
    svc = _svc()
    res = svc.trigger_siren(source="manuel", approval_facts={"manual_trigger": True})
    assert res["ok"] is True


def test_siren_cooldown_enforced():
    """Le cooldown sirène est réellement appliqué (était défini mais inutilisé)."""
    cfg = GuardianConfig(siren_cooldown=9999)
    svc = GuardianService(config=cfg, vision_provider=_PersonVision(), store=None)
    svc.set_enabled(True)
    assert svc.trigger_siren(approval_facts={"manual_trigger": True})["ok"] is True
    second = svc.trigger_siren(approval_facts={"manual_trigger": True})
    assert second["ok"] is False and "cooldown" in second["message"].lower()


# ── Idempotence en deux phases (no double execution) ──
def _store():
    from agency.store import MissionStore
    tmp = tempfile.mkdtemp()
    return MissionStore(str(Path(tmp) / "agency.db"))


def test_receipt_two_phase_blocks_replay_after_crash():
    """Un reçu 'in_flight' (effet incertain après crash) bloque le rejeu."""
    store = _store()
    mid, sid = "m1", "s1"
    key, existing = store.begin_action_receipt(mid, sid, "email_envoyer", {"to": "x@y.z"})
    assert existing is None and key                      # 1re fois : réservé in_flight
    # Simule un crash : le reçu reste in_flight (jamais finalisé).
    r = store.get_action_receipt(mid, sid, "email_envoyer", {"to": "x@y.z"})
    assert r["status"] == "in_flight"
    # Rejeu : begin renvoie le reçu existant in_flight → l'appelant doit bloquer.
    key2, existing2 = store.begin_action_receipt(mid, sid, "email_envoyer", {"to": "x@y.z"})
    assert existing2 is not None and existing2["status"] == "in_flight"


def test_receipt_finalize_then_reuse():
    store = _store()
    key, existing = store.begin_action_receipt("m2", "s2", "email_envoyer", {"to": "a@b.c"})
    store.finalize_action_receipt(key, "envoyé id=42", "succeeded")
    r = store.get_action_receipt("m2", "s2", "email_envoyer", {"to": "a@b.c"})
    assert r["status"] == "succeeded" and "42" in r["result"]


def test_registry_blocks_double_send_on_inflight(monkeypatch):
    """Bout-en-bout : une action critique in_flight n'est PAS ré-exécutée."""
    import agent as agent_mod
    from permissions import PermissionManager
    store = _store()
    reg = agent_mod.ToolRegistry(permission_manager=PermissionManager())
    reg.action_receipts = store
    sent = []
    reg.register("email_envoyer", "", {"to": {"type": "string"}},
                 lambda to: sent.append(to) or "envoyé")

    if agent_mod.CURRENT_MISSION_ID is None:
        return  # execution_context indisponible : test non applicable
    tok_m = agent_mod.CURRENT_MISSION_ID.set("mm")
    tok_s = agent_mod.CURRENT_STEP_ID.set("ss")
    try:
        # Pré-crash : on pose un in_flight sans finaliser.
        store.begin_action_receipt("mm", "ss", "email_envoyer", {"to": "z@z.z"})
        # Approve + tente : doit être BLOQUÉ (reçu in_flight), aucun envoi.
        req = reg.perms.request("email_envoyer", {"to": "z@z.z"})
        out = reg.call("email_envoyer", {"to": "z@z.z"}, approval_token=req["approval_id"])
        assert sent == [] and ("in_flight" in out or "bloqué" in out.lower())
    finally:
        agent_mod.CURRENT_MISSION_ID.reset(tok_m)
        agent_mod.CURRENT_STEP_ID.reset(tok_s)
