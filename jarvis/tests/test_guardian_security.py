"""Validation stricte de la perception + fail-closed du service."""
from guardian.schemas import parse_observation, VisionObservation
from guardian.config import GuardianConfig
from guardian.service import GuardianService


def test_valid_observation_parsed():
    raw = ('{"person_count":1,"confidence":0.93,"clothing":["capuche noire"],'
           '"objects":["téléphone"],"actions":["regarde la caméra"],'
           '"door_contact":false,"face_covered":true,"uncertainty":[]}')
    obs, err = parse_observation(raw)
    assert err == "" and isinstance(obs, VisionObservation)
    assert obs.person_count == 1 and obs.face_covered is True


def test_json_embedded_in_text_is_extracted():
    raw = "Voici l'analyse : {\"person_count\":0,\"confidence\":0.5} — fin."
    obs, err = parse_observation(raw)
    assert err == "" and obs.person_count == 0


def test_invalid_json_is_unknown():
    obs, err = parse_observation("pas du json du tout")
    assert obs is None and err


def test_out_of_range_confidence_rejected():
    obs, err = parse_observation('{"person_count":1,"confidence":5}')
    assert obs is None and err


def test_missing_required_field_rejected():
    obs, err = parse_observation('{"confidence":0.5}')
    assert obs is None and err


def test_html_payload_in_fields_is_data_not_code():
    raw = '{"person_count":1,"confidence":0.5,"clothing":["<script>alert(1)</script>"]}'
    obs, err = parse_observation(raw)
    assert err == "" and obs.clothing[0] == "<script>alert(1)</script>"   # texte brut


class _StubVision:
    """Renvoie un JSON invalide pour simuler un modèle défaillant."""
    def analyze(self, image_b64, prompt):
        return "je ne sais pas décrire, désolé"


def test_service_unknown_takes_no_action():
    svc = GuardianService(config=GuardianConfig(), vision_provider=_StubVision(),
                          speech_provider=None, store=None)
    svc.set_enabled(True)
    out = svc.process_image("data:image/jpeg;base64,AAAA")
    assert out["ok"] and out["valid"] is False
    assert not out["decision"]["should_speak"]
    assert not out["decision"]["siren_allowed"]


def test_service_image_too_large_rejected():
    cfg = GuardianConfig(max_image_bytes=10)
    svc = GuardianService(config=cfg, vision_provider=_StubVision(), store=None)
    svc.set_enabled(True)
    out = svc.process_image("A" * 5000)
    assert not out["ok"] and "volumineuse" in out["error"].lower()


def test_service_rate_limit():
    cfg = GuardianConfig(rate_limit_per_min=2)
    svc = GuardianService(config=cfg, vision_provider=_StubVision(), store=None)
    svc.set_enabled(True)
    r1 = svc.process_image("data:,AAAA")
    r2 = svc.process_image("data:,AAAA")
    r3 = svc.process_image("data:,AAAA")
    assert r1["ok"] and r2["ok"] and not r3["ok"]


def test_manual_siren_allowed_but_unknown_scene_not():
    svc = GuardianService(config=GuardianConfig(), vision_provider=_StubVision(), store=None)
    svc.set_enabled(True)
    # Déclenchement manuel → autorisé.
    assert svc.trigger_siren(source="manuel", approval_facts={"manual_trigger": True})["ok"]
    # Aucun fait critique → refusé (fail-closed).
    assert not svc.trigger_siren(source="auto", approval_facts={"manual_trigger": False})["ok"]
