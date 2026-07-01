"""
Orchestration du Gardien : perception → suivi temporel → politique → action.

Le flux respecte la séparation des responsabilités :
  1. perception   : le fournisseur de vision renvoie un JSON BRUT ;
  2. validation   : schemas.parse_observation (strict, sinon UNKNOWN) ;
  3. suivi        : agrégation temporelle (présence, durée, confirmations…) ;
  4. machine d'état : transition déterministe (state_machine) ;
  5. politique    : décision d'action + parole sûre (policy) ;
  6. parole       : un LLM produit la phrase, nettoyée par la politique ;
  7. actions      : notification / sirène (autorisation seulement, jamais auto
                    sans condition critique ou approbation).

La sirène n'est jamais déclenchée par une phrase ou un « OUI » du LLM.
"""

import time
import logging
import threading

from .config import GuardianConfig, load_config
from .schemas import parse_observation, VISION_SYSTEM_PROMPT
from .state_machine import GuardianStateMachine, State, Facts
from .policy import GuardianPolicy

logger = logging.getLogger("JARVIS.guardian.service")


class _SessionAggregator:
    """Suivi temporel léger pour une caméra/onglet (présence, durée, retours)."""

    def __init__(self):
        self.present_since = None
        self.last_present = 0.0
        self.consecutive = 0
        self.absent_streak = 0
        self.returns = 0
        self.last_state = State.IDLE
        self.last_spoke = 0.0
        self.last_alert = 0.0

    def update(self, present: bool, now: float):
        if present:
            if self.present_since is None:
                self.present_since = now
                if self.absent_streak >= 3:     # revenu après une absence nette
                    self.returns += 1
                self.absent_streak = 0
            self.consecutive += 1
            self.last_present = now
        else:
            self.present_since = None
            self.consecutive = 0
            self.absent_streak += 1

    @property
    def dwell(self):
        return (time.time() - self.present_since) if self.present_since else 0.0


class GuardianService:
    def __init__(self, config: GuardianConfig = None, vision_provider=None,
                 speech_provider=None, store=None, notifier=None,
                 emergency=None, event_log=None, siren_controller=None):
        self.cfg = config or load_config()
        self.vision = vision_provider
        self.speech = speech_provider
        self.store = store
        self.notifier = notifier
        self.emergency = emergency
        self.event_log = event_log
        self.siren = siren_controller         # callable(action) -> ... (jamais auto)
        self.policy = GuardianPolicy(self.cfg)
        self.fsm = GuardianStateMachine(
            loiter_seconds=self.cfg.loiter_seconds,
            min_confirmations=self.cfg.min_confirmations)
        self.agg = _SessionAggregator()
        self.enabled = False
        self.armed = False
        self._lock = threading.Lock()
        self._rate = []                       # horodatages pour le rate-limit

    # ── Contrôle ───────────────────────────────────────────────
    def set_enabled(self, on: bool):
        self.enabled = bool(on)
        if not on:
            self.fsm.state = State.IDLE
            self.agg = _SessionAggregator()
        return self.enabled

    def set_armed(self, on: bool):
        self.armed = bool(on)
        return self.armed

    def _rate_ok(self) -> bool:
        now = time.time()
        self._rate = [t for t in self._rate if now - t < 60]
        if len(self._rate) >= self.cfg.rate_limit_per_min:
            return False
        self._rate.append(now)
        return True

    # ── Cœur : traite une image et renvoie une décision ────────
    def process_image(self, image_b64: str, meta: dict = None) -> dict:
        meta = meta or {}
        if not self.enabled:
            return {"ok": False, "error": "Gardien désactivé"}
        if not self._rate_ok():
            return {"ok": False, "error": "Trop de requêtes (rate limit)"}

        # Limite de taille (sécurité / robustesse)
        approx_bytes = int(len(image_b64) * 3 / 4)
        if approx_bytes > self.cfg.max_image_bytes:
            return {"ok": False, "error": "Image trop volumineuse"}

        # 1) Perception
        raw = ""
        provider_err = ""
        if self.vision is not None:
            try:
                raw = self.vision.analyze(image_b64, VISION_SYSTEM_PROMPT)
            except Exception as e:
                provider_err = str(e)
        obs, err = parse_observation(raw) if raw else (None, provider_err or "pas de vision")

        # 2) UNKNOWN : observation invalide ⇒ aucune action
        observation_valid = obs is not None
        present = bool(obs and obs.person_count >= 1)
        self.agg.update(present, time.time())

        # 3) Faits mesurables
        facts = self._build_facts(obs, observation_valid, meta)

        # 4) Transition déterministe
        now = time.time()
        state = self.fsm.step(facts, now)

        # 5) Politique
        confirmed = self._confirmed_facts()
        decision = self.policy.decide(state, facts, confirmed)

        # 6) Parole (sous cooldown), phrase nettoyée
        phrase = ""
        if decision.should_speak and now - self.agg.last_spoke >= self.cfg.speak_cooldown:
            phrase = self._make_phrase(decision, obs)
            self.agg.last_spoke = now

        # 7) Actions
        actions = []
        if decision.should_notify and now - self.agg.last_alert >= self.cfg.alert_cooldown:
            self.agg.last_alert = now
            actions += self._notify(state, decision, obs, meta)

        # La sirène n'est jamais déclenchée ici automatiquement : on n'expose
        # qu'une AUTORISATION. Le déclenchement réel passe par trigger_siren().
        # Persistance
        if self.store:
            try:
                self.store.add_decision(decision, phrase=phrase,
                                        meta={"obs": obs.to_dict() if obs else None,
                                              "error": err})
                if state in (State.WARNING, State.ALERT):
                    self.store.add_event("guardian", decision.reason, state=state,
                                         level=decision.speech_level,
                                         meta={"obs": obs.to_dict() if obs else None})
            except Exception:
                pass

        self.agg.last_state = state
        return {
            "ok": True, "state": state, "valid": observation_valid,
            "observation": obs.to_dict() if obs else None,
            "error": err if not observation_valid else "",
            "decision": {
                "should_speak": decision.should_speak, "speech_level": decision.speech_level,
                "should_notify": decision.should_notify, "siren_allowed": decision.siren_allowed,
                "reason": decision.reason,
            },
            "phrase": phrase, "actions": actions,
            "dwell": round(self.agg.dwell, 1), "confirmations": self.agg.consecutive,
        }

    def _build_facts(self, obs, observation_valid: bool, meta: dict) -> Facts:
        dwell = self.agg.dwell
        conf = self.agg.consecutive
        present = bool(obs and obs.person_count >= 1)
        loiter = dwell >= self.cfg.loiter_seconds
        return Facts(
            observation_valid=observation_valid,
            person_present=present,
            dwell_seconds=dwell,
            confirmations=conf,
            door_contact=bool(obs and obs.door_contact),
            door_zone_breached=bool(meta.get("door_zone_breached", False)),
            face_covered=bool(obs and obs.face_covered),
            approaching_door=bool(meta.get("approaching_door", False)),
            repeated_return=self.agg.returns >= 2,
            behavior_confirmed=loiter and conf >= self.cfg.min_confirmations,
            in_public_zone=bool(meta.get("in_public_zone", False)),
            known_person=bool(meta.get("known_person", False)),
            human_validated_intrusion=bool(meta.get("human_validated_intrusion", False)),
            owner_approved_alert=bool(meta.get("owner_approved_alert", False)),
            manual_trigger=bool(meta.get("manual_trigger", False)),
            alarm_armed=self.armed,
            within_active_schedule=bool(meta.get("within_active_schedule", True)),
        )

    def _confirmed_facts(self):
        cf = []
        # 'owner_notified' n'est ajouté qu'après un retour POSITIF du notifier.
        return cf

    def _make_phrase(self, decision, obs) -> str:
        ctx = {"lang": "fr", "observation": obs.to_dict() if obs else {}}
        candidate = ""
        if self.speech is not None:
            try:
                out = self.speech.generate_line(decision.speech_level, ctx)
                candidate = out.get("phrase", "")
            except Exception:
                candidate = ""
        clean, ok = self.policy.sanitize_phrase(candidate, self._confirmed_facts())
        if not ok:
            # Phrase rejetée ou indisponible → fallback sûr déterministe.
            return decision.safe_fallback_line or self.policy.safe_line_for(decision.speech_level)
        return clean

    def _notify(self, state, decision, obs, meta) -> list:
        actions = []
        summary = f"Gardien [{state}] — {decision.reason}"
        if self.notifier and getattr(self.notifier, "enabled", False):
            try:
                res = self.notifier.send(f"🛡️ {summary}")
                ok = True
                actions.append("Notification distante envoyée.")
                if self.store:
                    self.store.add_notification("telegram", ok, res if isinstance(res, str) else "")
            except Exception as e:
                actions.append(f"Notification échouée: {e}")
        if self.event_log:
            try:
                self.event_log.add("guardian", summary, level="alert" if state == State.ALERT else "info")
            except Exception:
                pass
        return actions

    # ── Sirène : autorisation requise, jamais via LLM ──────────
    def trigger_siren(self, source: str = "manuel", approval_facts: dict = None) -> dict:
        """Déclenche la sirène SEULEMENT si la politique l'autorise."""
        facts = self._build_facts(None, True, approval_facts or {"manual_trigger": source == "manuel"})
        decision = self.policy.decide(State.ALERT, facts, self._confirmed_facts())
        if not decision.siren_allowed:
            return {"ok": False, "message": "Sirène non autorisée par la politique (fail-closed)."}
        if self.store:
            self.store.add_event("siren", f"Sirène déclenchée ({source})", state=State.ALERT, level="alert")
        if self.siren:
            try:
                self.siren("start")
            except Exception as e:
                return {"ok": False, "message": f"Erreur sirène: {e}"}
        return {"ok": True, "message": f"Sirène déclenchée ({source}).",
                "max_seconds": self.cfg.siren_max_seconds}

    def status(self) -> dict:
        return {
            "enabled": self.enabled, "armed": self.armed, "state": self.fsm.state,
            "dwell": round(self.agg.dwell, 1), "confirmations": self.agg.consecutive,
            "config": self.cfg.public_dict(),
        }
