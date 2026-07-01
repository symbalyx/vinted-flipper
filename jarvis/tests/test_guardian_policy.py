"""Politique de sécurité + politique de parole sûre."""
from guardian.config import GuardianConfig
from guardian.policy import GuardianPolicy
from guardian.state_machine import State, Facts


def pol(auto=False):
    return GuardianPolicy(GuardianConfig(auto_escalate=auto))


def test_observing_no_speech():
    d = pol().decide(State.OBSERVING, Facts(person_present=True))
    assert not d.should_speak and not d.siren_allowed


def test_engaging_speaks_no_siren():
    d = pol().decide(State.ENGAGING, Facts(person_present=True))
    assert d.should_speak and d.speech_level == "engage"
    assert not d.siren_allowed


def test_warning_notifies_no_siren():
    d = pol().decide(State.WARNING, Facts(person_present=True, door_contact=True))
    assert d.should_speak and d.should_notify
    assert not d.siren_allowed


def test_alert_siren_needs_authorization():
    """ALERT seul n'autorise pas la sirène sans fait critique/approbation."""
    d = pol().decide(State.ALERT, Facts(person_present=True))
    assert not d.siren_allowed


def test_alert_siren_allowed_on_manual_trigger():
    d = pol().decide(State.ALERT, Facts(manual_trigger=True))
    assert d.siren_allowed


def test_alert_siren_allowed_on_owner_approval():
    d = pol().decide(State.ALERT, Facts(owner_approved_alert=True))
    assert d.siren_allowed


def test_auto_escalate_requires_config_and_facts():
    facts = Facts(door_zone_breached=True, door_contact=True, alarm_armed=True)
    assert not pol(auto=False).decide(State.ALERT, facts).siren_allowed
    assert pol(auto=True).decide(State.ALERT, facts).siren_allowed


# ── Politique de parole ──
def test_phrase_rejects_police_claim():
    ok_text, ok = pol().sanitize_phrase("La police a été prévenue, elle arrive.")
    assert not ok


def test_phrase_rejects_dog_and_weapon_bluff():
    assert not pol().sanitize_phrase("Attention au chien derrière la porte.")[1]
    assert not pol().sanitize_phrase("J'ai une arme, ne bougez plus.")[1]


def test_phrase_rejects_impersonating_police():
    assert not pol().sanitize_phrase("Je suis la police, restez où vous êtes.")[1]


def test_phrase_rejects_violence_threat():
    assert not pol().sanitize_phrase("Je vais te frapper si tu avances.")[1]


def test_owner_notified_only_if_confirmed():
    txt = "Le propriétaire vient d'être averti."
    assert not pol().sanitize_phrase(txt)[1]                       # non confirmé → rejeté
    clean, ok = pol().sanitize_phrase(txt, confirmed_facts=["owner_notified"])
    assert ok and "propriétaire" in clean.lower()                 # confirmé → autorisé


def test_safe_phrase_allowed():
    clean, ok = pol().sanitize_phrase("Vous êtes filmé, cette zone est surveillée.")
    assert ok and clean


def test_html_payload_is_kept_as_plain_text_not_stripped_to_action():
    """Une chaîne HTML malveillante reste du TEXTE (pas d'exécution côté serveur)."""
    payload = "<img src=x onerror=alert(1)>"
    clean, ok = pol().sanitize_phrase(payload)
    # Elle n'enfreint aucune règle de claim → conservée telle quelle, en texte.
    assert ok and clean == payload
