import time

from agency.store import MissionStore
from agency.orchestrator import MissionOrchestrator


def wait_status(store, mission_id, wanted, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        status = store.get(mission_id)["status"]
        if status in wanted:
            return status
        time.sleep(0.03)
    return store.get(mission_id)["status"]


def test_transient_step_failure_is_retried_and_not_marked_done(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    calls = {"n": 0}

    def execute(payload):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary network error")
        return f"ok {payload['title']}"

    orch = MissionOrchestrator(
        store, execute, planner_callable=None, default_max_agents=1,
        default_step_attempts=2, auto_recover=False)
    mission = orch.create("Tester les retries", max_minutes=2, max_steps=8, max_agents=1)
    assert wait_status(store, mission["id"], {"completed", "failed"}) == "completed"
    loaded = store.get(mission["id"])
    assert calls["n"] >= len(loaded["steps"]) + 1
    assert any(e["kind"] == "step_retry" for e in loaded["events"])
    assert loaded["steps"][0]["attempt"] == 2


def test_persistent_error_enters_retry_wait_in_continue_mode(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))

    def execute(_payload):
        raise RuntimeError("service unavailable")

    orch = MissionOrchestrator(
        store, execute, planner_callable=None, default_max_agents=1,
        default_step_attempts=1, auto_recover=False)
    mission = orch.create(
        "Ne pas abandonner", max_minutes=2, max_steps=8, max_agents=1,
        continue_until_done=True)
    status = wait_status(store, mission["id"], {"retry_wait", "failed"})
    assert status == "retry_wait"
    step = store.steps(mission["id"])[0]
    assert step["status"] == "retry_wait"
    assert step["failure_cycle"] == 1
    assert step["next_run_at"] > time.time()


def test_completion_gate_adds_repair_cycle_before_completion(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    verdicts = {"n": 0}

    def execute(payload):
        return f"preuve {payload['role']} {payload['title']}"

    def validate(_payload):
        verdicts["n"] += 1
        if verdicts["n"] == 1:
            return {"complete": False, "reason": "preuve manquante", "missing": ["ajouter une preuve"]}
        return {"complete": True, "reason": "preuve ajoutée", "missing": []}

    orch = MissionOrchestrator(
        store, execute, planner_callable=None, completion_validator=validate,
        default_max_agents=2, auto_recover=False)
    mission = orch.create(
        "Produire puis vérifier", max_minutes=2, max_steps=8, max_agents=2,
        completion_criteria="preuve finale présente", max_repair_cycles=2)
    assert wait_status(store, mission["id"], {"completed", "failed", "blocked"}) == "completed"
    loaded = store.get(mission["id"])
    assert loaded["repair_cycle"] == 1
    assert any("cycle 1" in s["title"] for s in loaded["steps"])
    assert verdicts["n"] == 2


def test_memory_survives_store_reopen_and_is_retrieved(tmp_path):
    path = str(tmp_path / "agency.db")
    store = MissionStore(path)
    store.add_memory(
        "mission_lesson", "Prospection artisans Bordeaux",
        "Toujours conserver les URL sources et ne pas envoyer sans approbation.",
        tags=["prospection", "bordeaux"], source_mission_id="m1")
    reopened = MissionStore(path)
    found = reopened.search_memory("prospection artisans Bordeaux")
    assert found
    assert found[0]["source_mission_id"] == "m1"
    assert "URL sources" in found[0]["content"]


def test_supervisor_recovers_interrupted_mission(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    mission = store.create(
        "recover-1", "Reprendre après crash", 2, 8, 1,
        metadata={"auto_run": True})
    store.update_mission(mission["id"], status="interrupted", next_run_at=time.time())
    orch = MissionOrchestrator(
        store, lambda payload: f"ok {payload['title']}", planner_callable=None,
        default_max_agents=1, auto_recover=True, supervisor_interval=0.05)
    try:
        assert wait_status(store, mission["id"], {"completed", "failed"}) == "completed"
    finally:
        orch.close()


def test_sensitive_action_receipt_prevents_duplicate_after_retry(tmp_path):
    from agent import ToolRegistry
    from permissions import PermissionManager
    from execution_context import execution_scope

    store = MissionStore(str(tmp_path / "agency.db"))
    # La FK du reçu n'est pas requise, mais une mission réelle documente le cas.
    store.create("m-receipt", "Action externe", 10, 4, 1)
    pm = PermissionManager(ttl_seconds=60)
    registry = ToolRegistry(permission_manager=pm)
    registry.action_receipts = store
    calls = {"n": 0}

    def handler(value):
        calls["n"] += 1
        return f"sent:{value}"

    registry.register("email_envoyer", "send", {"value": {"type": "string"}}, handler)
    args = {"value": "one"}
    with execution_scope("m-receipt", "step-1"):
        waiting = registry.call("email_envoyer", args)
    assert "attente" in waiting
    token = pm.pending()[0]["approval_id"]
    first = registry.call("email_envoyer", args, approval_token=token)
    assert first == "sent:one"
    assert calls["n"] == 1

    # Même étape et mêmes paramètres après redémarrage logique : reçu réutilisé.
    with execution_scope("m-receipt", "step-1"):
        second = registry.call("email_envoyer", args)
    assert "idempotence" in second
    assert calls["n"] == 1
    assert pm.pending() == []


def test_two_orchestrators_do_not_execute_same_mission_twice(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    calls = []

    def execute(payload):
        calls.append(payload["step_id"])
        time.sleep(0.01)
        return "ok"

    mission = store.create("lease-1", "Mission unique", 2, 8, 2,
                           metadata={"auto_run": False})
    orch1 = MissionOrchestrator(store, execute, planner_callable=None,
                                default_max_agents=2, auto_recover=False)
    orch2 = MissionOrchestrator(store, execute, planner_callable=None,
                                default_max_agents=2, auto_recover=False)
    orch1.start(mission["id"])
    orch2.start(mission["id"])
    assert wait_status(store, mission["id"], {"completed", "failed"}) == "completed"
    step_ids = [s["id"] for s in store.steps(mission["id"])]
    assert sorted(calls) == sorted(step_ids)


def test_orchestration_error_is_retried_instead_of_terminal_failure(tmp_path, monkeypatch):
    import agency.orchestrator as orchestrator_module

    store = MissionStore(str(tmp_path / "agency.db"))
    monkeypatch.setattr(orchestrator_module, "plan_with_llm",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("planner offline")))
    orch = MissionOrchestrator(
        store, lambda payload: "never", planner_callable=lambda _p: "{}",
        default_max_agents=1, auto_recover=False)
    mission = orch.create("Continuer malgré panne planificateur", max_minutes=2,
                          max_steps=8, max_agents=1, continue_until_done=True)
    assert wait_status(store, mission["id"], {"retry_wait", "failed"}) == "retry_wait"
    loaded = store.get(mission["id"])
    assert loaded["failure_cycle"] == 1
    assert loaded["next_run_at"] > time.time()
    assert any(e["kind"] == "mission_retry" for e in loaded["events"])


def test_memory_redacts_goal_criteria_verdict_and_step_coordinates():
    mission = {
        "goal": "Contacter john@example.com au +33 6 12 34 56 78",
        "completion_criteria": "Utiliser token_ABCDEF1234567890",
    }
    steps = [{
        "role": "reporter", "title": "Rapport",
        "result": "Résultat pour lead@example.org, téléphone 0611223344",
    }]
    verdict = {"complete": True, "reason": "secret_ABCDEF1234567890 confirmé"}
    text = MissionOrchestrator._build_memory_text(mission, steps, verdict)
    assert "john@example.com" not in text
    assert "lead@example.org" not in text
    assert "0611223344" not in text
    assert "ABCDEF1234567890" not in text
    assert "<email-masqué>" in text
    assert "<téléphone-masqué>" in text
    assert "<secret-masqué>" in text
