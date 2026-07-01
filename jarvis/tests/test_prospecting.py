import time
import pytest

from prospecting.store import ProspectingStore
from prospecting.service import ProspectingService
from permissions import ACTION_LEVELS, Level


class FakeEmail:
    def __init__(self):
        self.sent = []
    def send(self, to, subject, body, cc=""):
        self.sent.append((to, subject, body, cc))
        return {"ok": True, "to": [to], "subject": subject}


def make_service(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECTING_MAX_SENDS_PER_DAY", "10")
    monkeypatch.setenv("PROSPECTING_MAX_SENDS_PER_DOMAIN", "2")
    monkeypatch.setenv("PROSPECTING_MIN_SEND_INTERVAL", "30")
    return ProspectingService(ProspectingStore(str(tmp_path / "prospecting.db")))


def test_add_qualify_and_deduplicate_public_business(tmp_path, monkeypatch):
    service = make_service(tmp_path, monkeypatch)
    p = service.add_prospect(
        "Atelier Test", "https://atelier-test.example/contact",
        website="https://atelier-test.example", public_email="contact@atelier-test.example",
        region="Bordeaux", notes="pas de site mobile clairement adapté")
    assert p["score"] >= 45
    assert p["source_url"].startswith("https://")
    with pytest.raises(ValueError):
        service.add_prospect(
            "Atelier Test", "https://atelier-test.example/contact",
            website="https://atelier-test.example")


def test_source_is_mandatory_and_private_style_data_not_supported(tmp_path, monkeypatch):
    service = make_service(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        service.add_prospect("Sans source", "")
    # Le schéma ne contient volontairement aucun champ d'adresse privée.
    assert "address" not in service.store.add.__code__.co_varnames


def test_draft_is_honest_and_contains_opt_out(tmp_path, monkeypatch):
    service = make_service(tmp_path, monkeypatch)
    p = service.add_prospect(
        "Menuiserie Exemple", "https://menuiserie.example/contact",
        public_email="contact@menuiserie.example", notes="pas de site trouvé")
    draft = service.prepare_message(p["id"], sender_name="Symbalyx")
    assert "déjà créé votre site" not in draft["body"].lower()
    assert "stop" in draft["body"].lower()
    assert "sans engagement" in draft["body"].lower()


def test_demo_is_only_claimed_when_real_url_is_supplied(tmp_path, monkeypatch):
    service = make_service(tmp_path, monkeypatch)
    p = service.add_prospect(
        "Studio Exemple", "https://studio.example", public_email="info@studio.example")
    no_demo = service.prepare_message(p["id"])
    assert "démonstration consultable" not in no_demo["body"]
    with_demo = service.prepare_message(p["id"], demo_url="https://demo.example/studio")
    assert "https://demo.example/studio" in with_demo["body"]


def test_suppression_blocks_future_contact(tmp_path, monkeypatch):
    service = make_service(tmp_path, monkeypatch)
    p = service.add_prospect(
        "Société Stop", "https://stop.example", public_email="contact@stop.example")
    draft = service.prepare_message(p["id"])
    service.suppress(p["id"], "opposition")
    with pytest.raises(PermissionError):
        service.send_draft(draft["id"], FakeEmail())


def test_each_send_is_individual_and_rate_limited(tmp_path, monkeypatch):
    service = make_service(tmp_path, monkeypatch)
    service.min_send_interval = 0
    emailer = FakeEmail()
    p = service.add_prospect(
        "Société Envoi", "https://send.example", public_email="contact@send.example")
    d = service.prepare_message(p["id"])
    result = service.send_draft(d["id"], emailer)
    assert result["ok"] is True
    duplicate = service.send_draft(d["id"], emailer)
    assert duplicate["duplicate_prevented"] is True
    assert len(emailer.sent) == 1
    assert service.store.get(p["id"])["status"] == "contacted"


def test_prospecting_send_requires_critical_app_approval():
    assert ACTION_LEVELS["prospection_envoyer_brouillon"] == Level.CRITICAL
    assert ACTION_LEVELS["prospection_ajouter_prospect"] == Level.SENSITIVE


def test_permission_audit_redacts_prospecting_message_and_coordinates():
    from permissions import PermissionManager
    events = []
    pm = PermissionManager(audit_log=lambda kind, summary, meta=None: events.append((kind, meta)))
    pm.request("email_envoyer", {
        "destinataire": "client@example.com",
        "corps": "contenu commercial confidentiel",
        "notes": "ne pas journaliser",
    })
    meta = events[-1][1]
    assert meta["params"]["destinataire"] == "<coordonnée masquée>"
    assert meta["params"]["corps"].startswith("<masqué:")
    assert meta["params"]["notes"].startswith("<masqué:")
    assert "client@example.com" not in str(meta)
