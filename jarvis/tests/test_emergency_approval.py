"""Approbation des urgences : aucun appel sans confirmation explicite."""
from emergency_approval import EmergencyApproval
from permissions import PermissionManager


class FakeDispatcher:
    def __init__(self):
        self.owner_calls = []
        self.dispatches = []

    def call_owner(self, message=""):
        self.owner_calls.append(message)
        return f"Appel hôte: {message}"

    def dispatch(self, reason, source="", allow_call=False, **kw):
        self.dispatches.append((reason, allow_call))
        return {"ok": True, "actions": [f"dispatch:{reason}:allow_call={allow_call}"]}


def make():
    disp = FakeDispatcher()
    ea = EmergencyApproval(disp, PermissionManager(ttl_seconds=60), cooldown=0.0)
    return disp, ea


def test_call_requires_confirmation():
    """11. Appel d'urgence sans confirmation : refusé (aucune exécution)."""
    disp, ea = make()
    # Confirmer avec un jeton bidon → refusé.
    res = ea.confirm_call("jeton-bidon", target="owner", reason="test")
    assert not res["ok"]
    assert disp.owner_calls == []       # rien n'a été composé


def test_request_then_confirm_owner():
    disp, ea = make()
    req = ea.request_call(target="owner", reason="Inconnu à la porte")
    assert req["pending"] and req["approval_id"]
    assert disp.owner_calls == []       # la demande ne compose rien
    res = ea.confirm_call(req["approval_id"], target="owner", reason="Inconnu à la porte")
    assert res["ok"] and len(disp.owner_calls) == 1


def test_token_single_use():
    disp, ea = make()
    req = ea.request_call(target="owner", reason="x")
    tok = req["approval_id"]
    assert ea.confirm_call(tok, target="owner", reason="x")["ok"]
    assert not ea.confirm_call(tok, target="owner", reason="x")["ok"]   # réutilisation refusée


def test_reason_mismatch_rejected():
    disp, ea = make()
    req = ea.request_call(target="owner", reason="raison A")
    res = ea.confirm_call(req["approval_id"], target="owner", reason="raison B")
    assert not res["ok"] and disp.owner_calls == []


def test_default_target_is_owner_not_emergency_services():
    disp, ea = make()
    req = ea.request_call(reason="doute")
    assert req["target"] == "owner"
