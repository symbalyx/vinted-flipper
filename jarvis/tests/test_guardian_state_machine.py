"""Machine d'état déterministe du Gardien — scénarios de non-déclenchement."""
import time

from guardian.state_machine import GuardianStateMachine, State, Facts


def sm():
    return GuardianStateMachine(loiter_seconds=20.0, min_confirmations=3)


def test_empty_porch_stays_idle():
    """1. Porche vide plusieurs minutes : aucune montée d'état."""
    m = sm()
    for i in range(200):
        st = m.step(Facts(observation_valid=True, person_present=False), now=i)
    assert st == State.IDLE


def test_invalid_observation_is_unknown_no_action():
    """2. Réponse modèle invalide ⇒ observation seule, aucune action/alerte."""
    m = sm()
    st = m.step(Facts(observation_valid=False, person_present=True, confirmations=99), now=1)
    assert st in (State.OBSERVING, State.IDLE)
    assert st != State.ALERT and st != State.WARNING


def test_five_positive_frames_never_trigger_alert():
    """3. Cinq images identiques avec une personne : jamais ALERT (ni sirène)."""
    m = sm()
    st = None
    for i in range(5):
        st = m.step(Facts(observation_valid=True, person_present=True,
                          confirmations=i + 1, dwell_seconds=2.0), now=i)
    assert st != State.ALERT           # le simple comptage n'escalade pas


def test_known_person_no_auto_escalation():
    """4. Personne connue : reste en observation, pas d'escalade automatique."""
    m = sm()
    st = m.step(Facts(observation_valid=True, person_present=True, known_person=True,
                      confirmations=10, dwell_seconds=120.0), now=1)
    assert st == State.OBSERVING


def test_unknown_person_polite_engage_no_emergency():
    """5. Inconnu sans geste menaçant : engagement poli, pas d'ALERT."""
    m = sm()
    st = m.step(Facts(observation_valid=True, person_present=True,
                      confirmations=3, dwell_seconds=5.0), now=1)
    assert st == State.ENGAGING


def test_repeated_door_contact_goes_warning_not_alert():
    """6. Contact répété avec la porte (zone) : WARNING, pas ALERT sans armement."""
    m = sm()
    st = m.step(Facts(observation_valid=True, person_present=True, confirmations=4,
                      dwell_seconds=6.0, door_contact=True, alarm_armed=False), now=1)
    assert st == State.WARNING


def test_alert_requires_critical_fact():
    """ALERT n'advient que sur un fait critique déterministe (porte + armé)."""
    m = sm()
    st = m.step(Facts(observation_valid=True, person_present=True, confirmations=4,
                      dwell_seconds=6.0, door_contact=True, door_zone_breached=True,
                      alarm_armed=True, within_active_schedule=True), now=1)
    assert st == State.ALERT


def test_manual_trigger_reaches_alert():
    m = sm()
    st = m.step(Facts(observation_valid=True, manual_trigger=True), now=1)
    assert st == State.ALERT


def test_still_person_not_dangerous():
    """Personne immobile (aucun comportement confirmé) ⇒ pas de WARNING/ALERT."""
    m = sm()
    st = m.step(Facts(observation_valid=True, person_present=True, confirmations=2,
                      dwell_seconds=1.0), now=1)
    assert st in (State.OBSERVING, State.ENGAGING)
    assert st not in (State.WARNING, State.ALERT)
