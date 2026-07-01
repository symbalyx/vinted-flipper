"""Orchestrateur durable de missions multi-agents.

Principes v5.6 :
- une mission n'est ``completed`` qu'après un contrôle de définition de fini ;
- les erreurs transitoires sont retentées avec backoff persistant ;
- les étapes écrivent heartbeat et checkpoints dans SQLite ;
- les missions interrompues/retry_wait/paused sont reprises automatiquement ;
- une action sensible reste arrêtée sur approbation humaine ;
- l'utilisateur peut toujours annuler explicitement.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Callable

from .models import MissionStatus, StepStatus
from .planner import plan_with_llm, ROLES

logger = logging.getLogger("JARVIS.agency")


def _env_int(name: str, default: int, lo: int, hi: int) -> int:
    """Lit un entier borné depuis l'environnement (fail-safe sur défaut clampé)."""
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(value, hi))


TERMINAL = {
    MissionStatus.COMPLETED.value,
    MissionStatus.FAILED.value,
    MissionStatus.CANCELLED.value,
}


class MissionOrchestrator:
    def __init__(self, store, step_executor: Callable, planner_callable=None,
                 approval_probe: Callable[[str], list] | None = None,
                 event_log=None, default_max_agents: int = 3,
                 completion_validator: Callable[[dict], dict] | None = None,
                 memory_provider: Callable[[str], list] | None = None,
                 default_step_attempts: int = 4,
                 auto_recover: bool = True,
                 supervisor_interval: float = 1.0):
        self.store = store
        self.step_executor = step_executor
        self.planner_callable = planner_callable
        self.approval_probe = approval_probe or (lambda _mid: [])
        self.event_log = event_log
        # Limites configurables (spec v5.7 §6). Les valeurs par défaut préservent
        # le comportement v5.6 ; les variables d'environnement permettent de les
        # ajuster sans toucher au code.
        self.default_max_agents = _env_int(
            "AGENCY_MAX_CONCURRENT_AGENTS", int(default_max_agents), 1, 32)
        self.default_step_attempts = _env_int(
            "AGENCY_DEFAULT_MAX_ATTEMPTS", int(default_step_attempts), 1, 20)
        self.completion_validator = completion_validator
        self.memory_provider = memory_provider or (lambda _query: [])
        self._threads: dict[str, threading.Thread] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._lease_owners: dict[str, str] = {}
        self._worker_id = uuid.uuid4().hex[:12]
        self._lease_seconds = float(_env_int("AGENCY_LEASE_SECONDS", 30, 15, 3600))
        self._heartbeat_seconds = float(_env_int("AGENCY_HEARTBEAT_SECONDS", 5, 2, 120))
        # Baux d'ÉTAPE + reaper des workers morts (incrément 2).
        self._step_lease_seconds = float(_env_int("AGENCY_STEP_LEASE_SECONDS", 120, 20, 7200))
        self._step_heartbeat_seconds = float(_env_int("AGENCY_STEP_HEARTBEAT_SECONDS", 20, 5, 600))
        self._reaper_interval = float(_env_int("AGENCY_REAPER_INTERVAL_SECONDS", 30, 5, 600))
        self._last_reap = 0.0
        self._lock = threading.RLock()
        self._shutdown = threading.Event()
        self._supervisor_interval = max(0.2, float(supervisor_interval))
        self._supervisor = None
        if auto_recover:
            self._supervisor = threading.Thread(
                target=self._supervise, daemon=True, name="jarvis-agency-supervisor")
            self._supervisor.start()

    def close(self):
        self._shutdown.set()

    def create(self, goal: str, max_minutes=180, max_steps=12, max_agents=None,
               metadata=None, autostart=True, completion_criteria: str = "",
               continue_until_done: bool = True, max_repair_cycles: int = 3):
        goal = str(goal or "").strip()
        if not goal:
            raise ValueError("La mission est vide")
        if len(goal) > 12000:
            raise ValueError("Mission trop longue")
        # Une tranche peut durer jusqu'à 7 jours. Si continue_until_done est actif,
        # le superviseur peut reprendre une nouvelle tranche au lieu de déclarer
        # arbitrairement la mission terminée ou échouée.
        max_minutes = max(1, min(int(max_minutes), 7 * 24 * 60))
        max_steps = max(2, min(int(max_steps), 40))
        max_agents = max(1, min(int(max_agents or self.default_max_agents), 8))
        mid = uuid.uuid4().hex
        meta = dict(metadata or {})
        meta.setdefault("auto_run", bool(autostart))
        meta.setdefault("engine", "durable-agency-v5.6")
        mission = self.store.create(
            mid, goal, max_minutes, max_steps, max_agents, meta,
            completion_criteria=completion_criteria,
            continue_until_done=continue_until_done,
            max_repair_cycles=max(0, min(int(max_repair_cycles), 12)),
        )
        if autostart:
            self.start(mid)
        return mission

    def start(self, mission_id: str):
        mission = self.store.get(mission_id)
        if not mission:
            raise KeyError("Mission introuvable")
        if mission["status"] in TERMINAL:
            raise ValueError("Mission terminée")
        with self._lock:
            thread = self._threads.get(mission_id)
            if thread and thread.is_alive():
                return mission
            flag = self._cancel.get(mission_id) or threading.Event()
            flag.clear()
            self._cancel[mission_id] = flag
            thread = threading.Thread(
                target=self._run, args=(mission_id, flag), daemon=True,
                name=f"jarvis-mission-{mission_id[:8]}")
            self._threads[mission_id] = thread
            thread.start()
        return self.store.get(mission_id)

    def cancel(self, mission_id: str):
        mission = self.store.get(mission_id)
        if not mission:
            return False
        with self._lock:
            self._cancel.setdefault(mission_id, threading.Event()).set()
        now = time.time()
        self.store.update_mission(
            mission_id, status=MissionStatus.CANCELLED.value,
            finished_at=now, error="Annulée par l'utilisateur")
        for step in self.store.steps(mission_id):
            if step["status"] in (
                StepStatus.PENDING.value, StepStatus.RUNNING.value,
                StepStatus.RETRY_WAIT.value, StepStatus.BLOCKED.value,
            ):
                self.store.update_step(
                    step["id"], status=StepStatus.CANCELLED.value,
                    finished_at=now)
        self._event(mission_id, "mission_cancelled", "Mission annulée")
        return True

    def resume(self, mission_id: str, note: str = ""):
        mission = self.store.get(mission_id)
        if not mission:
            raise KeyError("Mission introuvable")
        if mission["status"] in TERMINAL:
            raise ValueError("Mission terminée")
        if note:
            self.store.event(mission_id, "resume_note", note)
        pending = self.approval_probe(mission_id)
        if pending:
            self.store.update_mission(
                mission_id, status=MissionStatus.WAITING_APPROVAL.value)
            return self.store.get(mission_id)

        # Après un redémarrage, les approbations en mémoire sont perdues. L'étape
        # est rejouée pour recréer une demande explicite, jamais déclarée réussie.
        for step in self.store.steps(mission_id):
            if step["status"] == StepStatus.WAITING_APPROVAL.value:
                self.store.update_step(
                    step["id"], status=StepStatus.PENDING.value,
                    error="", started_at=None, finished_at=None, next_run_at=0)
            elif step["status"] == StepStatus.BLOCKED.value:
                self.store.update_step(
                    step["id"], status=StepStatus.RETRY_WAIT.value,
                    attempt=0, error="", next_run_at=time.time())

        update = {
            "status": MissionStatus.QUEUED.value,
            "error": "",
            "next_run_at": time.time(),
        }
        if mission["status"] == MissionStatus.BLOCKED.value:
            # Une reprise manuelle offre un cycle de réparation supplémentaire.
            update["max_repair_cycles"] = int(mission.get("max_repair_cycles", 3)) + 1
        self.store.update_mission(mission_id, **update)
        return self.start(mission_id)

    def on_approval_result(self, mission_id: str, result: str, step_id: str = "",
                           approved: bool = True):
        """Rattache une approbation à l'étape exacte.

        Un refus explicite est un blocage causé par l'utilisateur. L'étape et la
        mission restent ouvertes en état ``blocked`` : elles ne sont ni comptées
        comme réussies, ni abandonnées silencieusement. Une reprise explicite peut
        demander une autre stratégie ou recréer une approbation.
        """
        if not mission_id:
            return
        kind = "approval_executed" if approved else "approval_rejected"
        self.store.event(mission_id, kind, str(result)[:1000], {"step_id": step_id})
        waiting = [s for s in self.store.steps(mission_id)
                   if s["status"] == StepStatus.WAITING_APPROVAL.value]
        target = next((s for s in waiting if s["id"] == step_id), None)
        if target is None and len(waiting) == 1:
            target = waiting[0]

        if target:
            combined = "\n".join(
                x for x in [target.get("result", ""), str(result)] if x).strip()
            if not approved:
                self.store.update_step(
                    target["id"], status=StepStatus.BLOCKED.value,
                    result=combined[:20000], error=str(result)[:4000],
                    error_kind="approval_rejected", finished_at=None)
                self.store.update_mission(
                    mission_id, status=MissionStatus.BLOCKED.value,
                    error=("Action refusée par l'utilisateur ; la mission reste ouverte "
                           "pour une stratégie alternative."), next_run_at=0)
            else:
                remaining = [a for a in self.approval_probe(mission_id)
                             if a.get("step_id") == target["id"]]
                self.store.update_step(
                    target["id"],
                    status=(StepStatus.WAITING_APPROVAL.value if remaining
                            else StepStatus.COMPLETED.value),
                    result=combined[:20000],
                    finished_at=None if remaining else time.time(),
                )

        if not self.approval_probe(mission_id):
            latest = self.store.get(mission_id) or {}
            if latest.get("status") != MissionStatus.BLOCKED.value:
                self.store.update_mission(
                    mission_id, status=MissionStatus.QUEUED.value,
                    next_run_at=time.time())
                self.start(mission_id)

    def _supervise(self):
        """Relance les missions persistées après crash ou tranche de temps."""
        while not self._shutdown.wait(self._supervisor_interval):
            try:
                self._reaper_tick()
                for mission in self.store.recoverable(limit=25):
                    if mission.get("metadata", {}).get("auto_run", True) is False:
                        continue
                    self.start(mission["id"])
            except Exception:
                logger.exception("Le superviseur Agency a rencontré une erreur")

    def _reaper_tick(self):
        """Reprend les étapes dont le worker est mort (bail expiré) et réconcilie
        les reçus in_flight bloqués. Cadencé par AGENCY_REAPER_INTERVAL_SECONDS."""
        now = time.time()
        if now - self._last_reap < self._reaper_interval:
            return
        self._last_reap = now
        try:
            from .backoff import next_delay
            delay = next_delay(1)  # premier retry après reprise, borné + jitter
        except Exception:
            delay = 30.0

        def _abandon(mission_id, step_id, attempt):
            self._event(mission_id, "step_abandoned",
                        f"Étape {step_id[:8]} reprise (worker mort, bail expiré) "
                        f"— essai {attempt}, classée TRANSIENT_WORKER_LOST")

        try:
            reaped = self.store.reap_expired_steps(next_run_delay=delay, event_cb=_abandon)
            if reaped:
                logger.info("Reaper : %d étape(s) récupérée(s)", reaped)
        except Exception:
            logger.exception("Reaper d'étapes en échec")
        try:
            self.store.reconcile_stuck_receipts()
        except Exception:
            logger.exception("Réconciliation des reçus en échec")

    def _run(self, mission_id: str, cancel_flag: threading.Event):
        owner = f"{self._worker_id}:{mission_id[:12]}"
        if not self.store.claim_mission(mission_id, owner, self._lease_seconds):
            logger.info("Mission %s déjà prise par un autre worker", mission_id)
            return
        self._lease_owners[mission_id] = owner
        try:
            mission = self.store.get(mission_id)
            if not mission:
                return
            overall_start = mission.get("started_at") or time.time()
            self.store.update_mission(
                mission_id,
                status=(MissionStatus.PLANNING.value if not mission.get("steps")
                        else MissionStatus.RUNNING.value),
                started_at=overall_start, heartbeat_at=time.time(), next_run_at=0)
            self._event(mission_id, "mission_started", "Mission démarrée ou reprise")
            try:
                if not mission.get("steps"):
                    plan = plan_with_llm(
                        mission["goal"], self.planner_callable, mission["max_steps"])
                    steps = []
                    for step in plan.steps:
                        item = step.to_dict()
                        item["max_attempts"] = self.default_step_attempts
                        steps.append(item)
                    self.store.set_plan(mission_id, plan.summary, steps)
                self.store.update_mission(
                    mission_id, status=MissionStatus.RUNNING.value,
                    heartbeat_at=time.time())
                self._execute_plan(mission_id, cancel_flag)
            except Exception as exc:
                logger.exception("Mission %s interrompue par une erreur", mission_id)
                latest = self.store.get(mission_id) or mission or {}
                if (latest.get("continue_until_done", True)
                        and latest.get("status") != MissionStatus.CANCELLED.value):
                    cycle = int(latest.get("failure_cycle") or 0) + 1
                    delay = min(6 * 3600, 30 * (2 ** min(cycle - 1, 9)))
                    self.store.update_mission(
                        mission_id, status=MissionStatus.RETRY_WAIT.value,
                        failure_cycle=cycle, error=str(exc)[:2000],
                        finished_at=None, next_run_at=time.time() + delay)
                    self._event(
                        mission_id, "mission_retry",
                        f"Erreur d'orchestration ; reprise automatique dans {delay}s",
                        {"failure_cycle": cycle, "error": str(exc)[:500]})
                else:
                    self.store.update_mission(
                        mission_id, status=MissionStatus.FAILED.value,
                        error=str(exc)[:2000], finished_at=time.time())
                    self._event(mission_id, "mission_failed", str(exc)[:1000])
        finally:
            self.store.release_mission(mission_id, owner)
            self._lease_owners.pop(mission_id, None)

    def _execute_plan(self, mission_id: str, cancel_flag: threading.Event):
        mission = self.store.get(mission_id)
        max_workers = mission["max_agents"]
        # max_minutes est une tranche d'exécution. En mode continue_until_done,
        # une nouvelle tranche est reprise automatiquement.
        deadline = time.time() + mission["max_minutes"] * 60
        futures = {}
        with ThreadPoolExecutor(
                max_workers=max_workers, thread_name_prefix="jarvis-subagent") as pool:
            while True:
                current_mission = self.store.get(mission_id)
                if not current_mission:
                    return
                owner = self._lease_owners.get(mission_id, "")
                if owner and not self.store.renew_mission_lease(
                        mission_id, owner, self._lease_seconds):
                    logger.warning("Bail perdu pour la mission %s", mission_id)
                    return
                self.store.heartbeat_mission(mission_id)
                if cancel_flag.is_set() or current_mission["status"] == MissionStatus.CANCELLED.value:
                    return
                if time.time() > deadline:
                    if current_mission.get("continue_until_done", True):
                        self.store.update_mission(
                            mission_id, status=MissionStatus.PAUSED.value,
                            error="Tranche de calcul terminée ; reprise automatique programmée.",
                            next_run_at=time.time() + 2)
                        self._event(
                            mission_id, "runtime_slice_complete",
                            "Tranche de calcul terminée, la mission sera reprise automatiquement")
                        return
                    raise TimeoutError("Durée maximale de la mission atteinte")
                if self.approval_probe(mission_id):
                    self.store.update_mission(
                        mission_id, status=MissionStatus.WAITING_APPROVAL.value)
                    self._event(
                        mission_id, "waiting_approval",
                        "Mission en attente d'une approbation humaine")
                    return

                steps = self.store.steps(mission_id)
                by_id = {s["id"]: s for s in steps}
                completed = {s["id"] for s in steps
                             if s["status"] == StepStatus.COMPLETED.value}
                failed = [s for s in steps if s["status"] == StepStatus.FAILED.value]
                if failed:
                    raise RuntimeError(
                        f"Étape échouée : {failed[0]['title']} — {failed[0]['error']}")
                blocked = [s for s in steps if s["status"] == StepStatus.BLOCKED.value]
                if blocked:
                    self.store.update_mission(
                        mission_id, status=MissionStatus.BLOCKED.value,
                        error=f"Étape bloquée : {blocked[0]['title']} — {blocked[0]['error']}")
                    self._event(
                        mission_id, "mission_blocked",
                        f"Intervention requise : {blocked[0]['title']}")
                    return
                if steps and len(completed) == len(steps):
                    if self._finalize_or_repair(mission_id, steps):
                        return
                    # Un plan de réparation a été ajouté.
                    continue

                running_ids = {sid for sid, _ in futures.values()}
                slots = max_workers - len(futures)
                now = time.time()
                if slots > 0:
                    ready = [
                        s for s in steps
                        if s["status"] in (
                            StepStatus.PENDING.value, StepStatus.RETRY_WAIT.value)
                        and s["id"] not in running_ids
                        and float(s.get("next_run_at") or 0) <= now
                        and all(dep in completed for dep in s.get("depends_on", []))
                    ]
                    for step in ready[:slots]:
                        # Acquisition avec BAIL d'étape (worker_id + lease_token) :
                        # deux workers ne peuvent pas prendre la même étape, et un
                        # worker mort verra son bail expirer puis l'étape reprise.
                        claimed = self.store.claim_step(
                            step["id"], worker_id=self._lease_owners.get(mission_id, ""),
                            lease_seconds=self._step_lease_seconds)
                        if not claimed:
                            continue
                        self._event(
                            mission_id, "step_started",
                            f"{claimed['role']} — {claimed['title']}",
                            {"step_id": claimed["id"], "attempt": claimed["attempt"]})
                        fut = pool.submit(
                            self._execute_step_with_heartbeat,
                            mission_id, claimed, by_id)
                        futures[fut] = (claimed["id"], claimed["title"])

                if not futures:
                    steps = self.store.steps(mission_id)
                    if not steps:
                        raise RuntimeError("Plan vide")
                    waiting_retry = [
                        s for s in steps if s["status"] == StepStatus.RETRY_WAIT.value]
                    if waiting_retry:
                        next_run = min(float(s.get("next_run_at") or now)
                                       for s in waiting_retry)
                        delay = max(0.05, next_run - time.time())
                        if delay > 5:
                            self.store.update_mission(
                                mission_id, status=MissionStatus.RETRY_WAIT.value,
                                next_run_at=next_run,
                                error="Nouvel essai programmé après une erreur transitoire.")
                            self._event(
                                mission_id, "retry_scheduled",
                                f"Reprise dans environ {int(delay)} seconde(s)")
                            return
                        time.sleep(min(0.25, delay))
                        continue
                    pending = [s for s in steps
                               if s["status"] == StepStatus.PENDING.value]
                    if pending:
                        raise RuntimeError(
                            "Plan bloqué par des dépendances non satisfaites")
                    time.sleep(0.05)
                    continue

                done, _ = wait(
                    list(futures), timeout=0.25, return_when=FIRST_COMPLETED)
                for fut in done:
                    step_id, title = futures.pop(fut)
                    step_now = next(
                        (s for s in self.store.steps(mission_id) if s["id"] == step_id),
                        None)
                    try:
                        result = fut.result()
                        if self.approval_probe(mission_id):
                            self.store.update_step(
                                step_id, status=StepStatus.WAITING_APPROVAL.value,
                                result=str(result)[:20000], heartbeat_at=time.time())
                            self.store.update_mission(
                                mission_id, status=MissionStatus.WAITING_APPROVAL.value)
                            self._event(
                                mission_id, "waiting_approval",
                                f"{title} attend une approbation",
                                {"step_id": step_id})
                            return
                        self.store.update_step(
                            step_id, status=StepStatus.COMPLETED.value,
                            result=str(result)[:20000], error="", error_kind="",
                            finished_at=time.time(), heartbeat_at=time.time())
                        self.store.save_checkpoint(step_id, {
                            "state": "completed", "saved_at": time.time(),
                            "result_preview": str(result)[:1000],
                        })
                        self.store.update_mission(
                            mission_id, failure_cycle=0, last_progress_at=time.time())
                        self._event(
                            mission_id, "step_completed", title,
                            {"step_id": step_id,
                             "attempt": (step_now or {}).get("attempt", 1)})
                    except Exception as exc:
                        self._schedule_step_retry(
                            mission_id, step_now or {"id": step_id, "title": title,
                                                     "attempt": 1, "max_attempts": 1,
                                                     "failure_cycle": 0}, exc)

    def _schedule_step_retry(self, mission_id: str, step: dict, exc: Exception):
        attempt = int(step.get("attempt") or 1)
        max_attempts = int(step.get("max_attempts") or self.default_step_attempts)
        failure_cycle = int(step.get("failure_cycle") or 0)
        message = str(exc)[:4000]
        if attempt < max_attempts:
            delay = min(300, 2 ** min(attempt, 8))
            self.store.update_step(
                step["id"], status=StepStatus.RETRY_WAIT.value,
                error=message, error_kind="transient", next_run_at=time.time() + delay,
                finished_at=None)
            self.store.save_checkpoint(step["id"], {
                "state": "retry_wait", "attempt": attempt,
                "error": message[:1000], "retry_in_seconds": delay,
            })
            self._event(
                mission_id, "step_retry",
                f"{step['title']} : nouvel essai {attempt + 1}/{max_attempts} dans {delay}s",
                {"step_id": step["id"], "error": message[:500]})
            return

        mission = self.store.get(mission_id) or {}
        if mission.get("continue_until_done", True):
            # Une série d'essais épuisée ne termine pas la mission. Le compteur
            # repart après un backoff plus long, persistant entre redémarrages.
            failure_cycle += 1
            delay = min(6 * 3600, 60 * (2 ** min(failure_cycle - 1, 6)))
            self.store.update_step(
                step["id"], status=StepStatus.RETRY_WAIT.value,
                attempt=0, failure_cycle=failure_cycle, error=message,
                error_kind="persistent", next_run_at=time.time() + delay,
                finished_at=None)
            self.store.save_checkpoint(step["id"], {
                "state": "persistent_retry", "failure_cycle": failure_cycle,
                "error": message[:1000], "retry_in_seconds": delay,
            })
            self.store.update_mission(
                mission_id, status=MissionStatus.RETRY_WAIT.value,
                next_run_at=time.time() + delay,
                error="Une étape reste incomplète ; nouvelle stratégie programmée.")
            self._event(
                mission_id, "persistent_retry",
                f"{step['title']} reste incomplète ; reprise dans {delay}s",
                {"step_id": step["id"], "failure_cycle": failure_cycle})
            return

        self.store.update_step(
            step["id"], status=StepStatus.FAILED.value,
            error=message, error_kind="permanent", finished_at=time.time())
        self._event(
            mission_id, "step_failed", f"{step['title']}: {message}",
            {"step_id": step["id"]})

    def _finalize_or_repair(self, mission_id: str, steps: list[dict]) -> bool:
        mission = self.store.get(mission_id) or {}
        report = steps[-1].get("result", "") if steps else ""
        if self.completion_validator is None:
            verdict = {"complete": True, "reason": "Toutes les étapes sont terminées"}
        else:
            self.store.update_mission(
                mission_id, status=MissionStatus.VERIFYING.value,
                heartbeat_at=time.time())
            payload = {
                "mission": mission,
                "steps": steps,
                "completion_criteria": mission.get("completion_criteria", ""),
            }
            try:
                verdict = self.completion_validator(payload) or {}
            except Exception as exc:
                verdict = {
                    "complete": False,
                    "reason": f"Validation finale indisponible : {exc}",
                    "missing": ["Relancer la validation finale"],
                }
        complete = verdict.get("complete") is True
        self.store.event(
            mission_id, "completion_check",
            str(verdict.get("reason") or ("terminé" if complete else "incomplet"))[:1000],
            {"complete": complete, "missing": verdict.get("missing", [])[:20]})
        if complete:
            self.store.update_mission(
                mission_id, status=MissionStatus.COMPLETED.value,
                result=report, error="", finished_at=time.time(),
                heartbeat_at=time.time())
            self._event(mission_id, "mission_completed", "Mission terminée et validée")
            memory_text = self._build_memory_text(mission, steps, verdict)
            self.store.add_memory(
                "mission_lesson", mission.get("goal", "Mission"), memory_text,
                tags=[s.get("role", "") for s in steps[-8:]],
                source_mission_id=mission_id)
            return True

        repair_cycle = int(mission.get("repair_cycle") or 0)
        max_cycles = int(mission.get("max_repair_cycles") or 3)
        if repair_cycle >= max_cycles:
            self.store.update_mission(
                mission_id, status=MissionStatus.BLOCKED.value,
                error=("La définition de fini n'est pas satisfaite après "
                       f"{repair_cycle} cycle(s) de réparation. ") +
                      str(verdict.get("reason") or ""),
                finished_at=None)
            self._event(
                mission_id, "completion_blocked",
                "La mission reste ouverte : validation humaine ou nouveau contexte requis")
            return True

        self._append_repair_cycle(mission_id, steps, verdict, repair_cycle + 1)
        self.store.update_mission(
            mission_id, status=MissionStatus.RUNNING.value,
            repair_cycle=repair_cycle + 1, error="")
        return False

    def _append_repair_cycle(self, mission_id: str, steps: list[dict],
                             verdict: dict, cycle: int):
        missing = verdict.get("missing") or [verdict.get("reason") or "Résultat incomplet"]
        if not isinstance(missing, list):
            missing = [str(missing)]
        instructions = "\n".join(f"- {str(item)[:1000]}" for item in missing[:12])
        base = max((int(s.get("seq") or 0) for s in steps), default=0)
        deps = [s["id"] for s in steps if s["status"] == StepStatus.COMPLETED.value]
        builder_id = f"repair{cycle}-{uuid.uuid4().hex[:8]}"
        verify_id = f"reverify{cycle}-{uuid.uuid4().hex[:8]}"
        report_id = f"rereport{cycle}-{uuid.uuid4().hex[:8]}"
        new_steps = [
            {
                "id": builder_id, "seq": base + 1, "role": "builder",
                "title": f"Corriger les éléments manquants · cycle {cycle}",
                "instructions": (
                    "La validation finale a trouvé ces éléments incomplets :\n"
                    f"{instructions}\nCorrige réellement le livrable, réutilise les preuves "
                    "existantes et crée de nouvelles preuves. Ne te contente pas d'une promesse."),
                "depends_on": deps, "status": StepStatus.PENDING.value,
                "max_attempts": self.default_step_attempts,
            },
            {
                "id": verify_id, "seq": base + 2, "role": "verifier",
                "title": f"Revalider après correction · cycle {cycle}",
                "instructions": (
                    "Vérifie chaque élément de la définition de fini avec des preuves. "
                    "Signale explicitement ce qui reste incomplet."),
                "depends_on": [builder_id], "status": StepStatus.PENDING.value,
                "max_attempts": self.default_step_attempts,
            },
            {
                "id": report_id, "seq": base + 3, "role": "reporter",
                "title": f"Mettre à jour le rapport final · cycle {cycle}",
                "instructions": (
                    "Actualise le rapport final avec le travail réellement effectué, "
                    "les preuves, limites et approbations."),
                "depends_on": [verify_id], "status": StepStatus.PENDING.value,
                "max_attempts": self.default_step_attempts,
            },
        ]
        self.store.append_steps(
            mission_id, new_steps,
            summary_suffix=f"Cycle de réparation {cycle} ajouté après validation incomplète.")

    def _execute_step_with_heartbeat(self, mission_id: str, step: dict, all_steps: dict):
        stop = threading.Event()

        owner = self._lease_owners.get(mission_id, "")
        lease_token = step.get("lease_token", "")

        def beat():
            while not stop.wait(min(self._heartbeat_seconds, self._step_heartbeat_seconds)):
                if owner:
                    self.store.renew_mission_lease(
                        mission_id, owner, self._lease_seconds)
                    # Renouvelle le BAIL d'étape tant que ce worker est vivant.
                    if lease_token:
                        self.store.renew_step_lease(
                            step["id"], owner, lease_token, self._step_lease_seconds)
                self.store.heartbeat_mission(mission_id)
                self.store.heartbeat_step(step["id"])

        thread = threading.Thread(target=beat, daemon=True,
                                  name=f"heartbeat-{step['id'][:12]}")
        thread.start()
        try:
            return self._execute_step(mission_id, step, all_steps)
        finally:
            stop.set()
            self.store.heartbeat_step(step["id"])

    def _execute_step(self, mission_id: str, step: dict, all_steps: dict):
        context = []
        for dep in step.get("depends_on", []):
            prior = all_steps.get(dep)
            if prior and prior.get("result"):
                context.append(f"[{prior['title']}]\n{prior['result'][:5000]}")
        mission = self.store.get(mission_id) or {}
        memories = self.memory_provider(mission.get("goal", "")) or []
        memory_text = "\n\n".join(
            f"[{m.get('kind', 'mémoire')}] {m.get('title', '')}\n{m.get('content', '')[:3000]}"
            for m in memories[:6] if isinstance(m, dict))
        role_desc = ROLES.get(step["role"], ROLES["builder"])
        payload = {
            "mission_id": mission_id,
            "step_id": step["id"],
            "idempotency_key": step.get("idempotency_key") or f"{mission_id}:{step['id']}",
            "attempt": int(step.get("attempt") or 1),
            "max_attempts": int(step.get("max_attempts") or self.default_step_attempts),
            "checkpoint": step.get("checkpoint") or {},
            "role": step["role"],
            "role_description": role_desc,
            "title": step["title"],
            "instructions": step["instructions"],
            "dependency_context": "\n\n".join(context),
            "durable_memory": memory_text,
            "completion_criteria": mission.get("completion_criteria", ""),
        }
        self.store.save_checkpoint(step["id"], {
            "state": "running", "attempt": payload["attempt"],
            "started_at": time.time(), "prior_checkpoint": payload["checkpoint"],
        })
        return self.step_executor(payload)

    @staticmethod
    def _redact_memory_text(text: str) -> str:
        """Retire coordonnées et secrets avant mémoire inter-missions.

        Le CRM conserve les coordonnées nécessaires dans sa base dédiée. La
        mémoire Agency ne doit retenir que méthodes, décisions et preuves.
        """
        text = str(text or "")
        text = re.sub(
            r"(?i)\b(?:sk|api|token|secret|password|passwd)[_-]?[A-Z0-9]{12,}\b",
            "<secret-masqué>", text)
        text = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
                      "<email-masqué>", text, flags=re.I)
        text = re.sub(r"(?<!\d)(?:\+?\d[ .-]?){8,15}(?!\d)",
                      "<téléphone-masqué>", text)
        return text

    @classmethod
    def _build_memory_text(cls, mission: dict, steps: list[dict], verdict: dict) -> str:
        # La mémoire inter-missions retient les méthodes, décisions et preuves,
        # pas un duplicata du CRM, des coordonnées ou des secrets.
        safe_roles = {"analyst", "security_auditor", "verifier", "reporter",
                      "compliance_reviewer", "automation_engineer"}
        snippets = []
        for step in steps[-16:]:
            if step.get("role") not in safe_roles or not step.get("result"):
                continue
            text = cls._redact_memory_text(str(step["result"])[:3000])
            snippets.append(
                f"{step.get('role')} · {step.get('title')}: {text}")
        assembled = (
            f"Objectif: {mission.get('goal', '')[:2000]}\n"
            f"Critères: {mission.get('completion_criteria', '')[:2000]}\n"
            f"Verdict: {json.dumps(verdict, ensure_ascii=False)[:3000]}\n"
            "Leçons et preuves réutilisables:\n" + "\n\n".join(snippets)
        )
        return cls._redact_memory_text(assembled)[:50000]



    def _event(self, mission_id: str, kind: str, message: str, meta=None):
        self.store.event(mission_id, kind, message, meta)
        if self.event_log:
            try:
                self.event_log(
                    "agency", message,
                    meta={"mission_id": mission_id, "kind": kind, **(meta or {})})
            except Exception:
                pass
