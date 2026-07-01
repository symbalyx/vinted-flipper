"""
Machine d'état DÉTERMINISTE du Gardien.

États :
    IDLE       — rien à signaler
    OBSERVING  — présence détectée, on observe (aucune parole)
    ENGAGING   — engagement verbal poli (« vous êtes filmé »)
    WARNING    — avertissement ferme + notification
    ALERT      — niveau critique (déclenchement possible d'actions physiques)
    COOLDOWN   — apaisement temporisé après un événement

Règles fondamentales (sécurité) :
  • La répétition de N images positives ne suffit JAMAIS à atteindre ALERT.
    ALERT exige un FAIT critique déterministe (porte franchie + alarme armée,
    intrusion confirmée par un humain, ou validation propriétaire).
  • Une personne immobile n'est pas dangereuse → reste en OBSERVING/ENGAGING.
  • Une observation invalide (UNKNOWN) ⇒ on reste en observation, aucune action.
  • Fail-closed : en cas de doute, on ne monte pas en ALERT.
"""

from dataclasses import dataclass


class State:
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    ENGAGING = "ENGAGING"
    WARNING = "WARNING"
    ALERT = "ALERT"
    COOLDOWN = "COOLDOWN"

    ALL = (IDLE, OBSERVING, ENGAGING, WARNING, ALERT, COOLDOWN)


@dataclass
class Facts:
    """Faits MESURABLES alimentant la transition. Aucun n'est produit par un LLM
    de façon non vérifiée : ils viennent du tracker, des zones, des capteurs et
    des validations humaines."""

    observation_valid: bool = True       # False ⇒ UNKNOWN ⇒ aucune action
    person_present: bool = False
    dwell_seconds: float = 0.0
    confirmations: int = 0
    door_contact: bool = False           # contact physique avec la porte
    door_zone_breached: bool = False     # le sujet est entré dans la zone 'door'/'private'
    face_covered: bool = False
    approaching_door: bool = False       # trajectoire qui converge vers la porte
    repeated_return: bool = False        # la personne revient plusieurs fois
    behavior_confirmed: bool = False     # comportement suspect confirmé dans le temps
    in_public_zone: bool = False         # passant sur la voie publique → ne pas engager
    known_person: bool = False           # visage reconnu (jamais seule condition d'alerte)

    # Décisions humaines / système (déterministes, hors LLM)
    human_validated_intrusion: bool = False
    owner_approved_alert: bool = False
    manual_trigger: bool = False
    alarm_armed: bool = False
    within_active_schedule: bool = True  # plage horaire de surveillance active


class GuardianStateMachine:
    """Transitions pures. `step()` renvoie le nouvel état (et le mémorise)."""

    def __init__(self, loiter_seconds: float = 20.0, min_confirmations: int = 3,
                 engage_after_confirmations: int = 3):
        self.state = State.IDLE
        self.loiter_seconds = loiter_seconds
        self.min_confirmations = min_confirmations
        self.engage_after = engage_after_confirmations
        self._cooldown_until = 0.0

    # ── Conditions critiques (les SEULES qui autorisent ALERT) ──
    @staticmethod
    def _critical(f: Facts) -> bool:
        if f.manual_trigger:
            return True
        if f.owner_approved_alert:
            return True
        if f.human_validated_intrusion:
            return True
        # Porte franchie/forcée pendant que l'alarme est armée et la surveillance active.
        if f.door_zone_breached and f.door_contact and f.alarm_armed and f.within_active_schedule:
            return True
        return False

    def step(self, f: Facts, now: float = 0.0) -> str:
        # 1) Observation invalide → on n'agit pas. On retombe en observation/idle.
        if not f.observation_valid:
            if self.state in (State.ALERT, State.WARNING):
                # On ne « désescalade » pas brutalement une alerte réelle sur un
                # simple JSON cassé : on reste prudemment où on est sans monter.
                return self.state
            self.state = State.OBSERVING if f.person_present else State.IDLE
            return self.state

        # 2) Faits critiques → ALERT (déterministe, indépendant du nombre d'images).
        if self._critical(f):
            self.state = State.ALERT
            self._cooldown_until = now + 1
            return self.state

        # 3) Personne connue : on n'escalade pas automatiquement (mais on observe).
        if not f.person_present:
            # Plus personne : redescendre via COOLDOWN puis IDLE.
            if self.state in (State.ENGAGING, State.WARNING, State.ALERT):
                self.state = State.COOLDOWN
                self._cooldown_until = now + 5
            elif self.state == State.COOLDOWN and now >= self._cooldown_until:
                self.state = State.IDLE
            elif self.state != State.COOLDOWN:
                self.state = State.IDLE
            return self.state

        # 4) Présence d'un passant sur la voie publique : on observe, on n'engage pas.
        if f.in_public_zone and not (f.door_zone_breached or f.door_contact):
            self.state = State.OBSERVING
            return self.state

        # 5) Personne connue et aucun comportement confirmé : observation seule.
        if f.known_person and not f.behavior_confirmed and not f.door_contact:
            self.state = State.OBSERVING
            return self.state

        # 6) Montée graduelle, fondée sur des faits.
        loitering = f.dwell_seconds >= self.loiter_seconds
        confirmed = f.confirmations >= self.min_confirmations

        # WARNING : faits aggravants NON critiques (porte approchée/contact léger,
        # rôdage confirmé, visage couvert + rôdage, retours répétés…).
        warn = (
            (f.door_contact and not f.alarm_armed)
            or (f.approaching_door and confirmed)
            or (loitering and f.face_covered)
            or (f.behavior_confirmed and confirmed)
            or f.repeated_return
        )

        if warn:
            self.state = State.WARNING
            return self.state

        # ENGAGING : présence confirmée → engagement verbal poli.
        if confirmed or loitering:
            self.state = State.ENGAGING
            return self.state

        # Sinon : on observe (présence non encore confirmée).
        self.state = State.OBSERVING
        return self.state
