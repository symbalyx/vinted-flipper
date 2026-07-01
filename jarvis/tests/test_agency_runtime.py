import time

from agency.store import MissionStore
from agency.orchestrator import MissionOrchestrator
from execution_context import execution_scope
from permissions import PermissionManager


def wait_status(store, mission_id, wanted, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        status = store.get(mission_id)["status"]
        if status in wanted:
            return status
        time.sleep(0.03)
    return store.get(mission_id)["status"]


def test_mission_store_roundtrip(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    mission = store.create("m1", "Tester", 10, 6, 2)
    assert mission["status"] == "queued"
    store.set_plan("m1", "plan", [{
        "id": "s1", "seq": 1, "role": "analyst", "title": "Cadre",
        "instructions": "Faire", "depends_on": [], "status": "pending",
    }])
    loaded = store.get("m1")
    assert loaded["summary"] == "plan"
    assert loaded["steps"][0]["role"] == "analyst"
    store.event("m1", "proof", "ok", {"x": 1})
    assert store.get("m1")["events"][-1]["meta"]["x"] == 1


def test_orchestrator_completes_with_subagents(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    calls = []

    def execute(payload):
        calls.append(payload["role"])
        return f"résultat {payload['title']}"

    orch = MissionOrchestrator(store, execute, planner_callable=None, default_max_agents=3)
    mission = orch.create("Audite puis corrige ce projet", max_minutes=2, max_steps=10, max_agents=3)
    status = wait_status(store, mission["id"], {"completed", "failed"})
    assert status == "completed"
    loaded = store.get(mission["id"])
    assert loaded["result"]
    assert "security_auditor" in calls
    assert "verifier" in calls
    assert all(s["status"] == "completed" for s in loaded["steps"])


def test_orchestrator_waits_then_resumes_after_approval(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    pending = []
    first = {"done": False}

    def execute(payload):
        if not first["done"]:
            first["done"] = True
            pending.append({"approval_id": "a"})
            return "action en attente"
        return "ok"

    orch = MissionOrchestrator(store, execute, planner_callable=None,
                               approval_probe=lambda _mid: list(pending), default_max_agents=1)
    mission = orch.create("Prépare un email", max_minutes=2, max_steps=8, max_agents=1)
    status = wait_status(store, mission["id"], {"waiting_approval", "failed"})
    assert status == "waiting_approval"
    pending.clear()
    orch.resume(mission["id"], "envoi approuvé")
    assert wait_status(store, mission["id"], {"completed", "failed"}) == "completed"


def test_permission_request_is_linked_to_mission():
    pm = PermissionManager()
    with execution_scope("mission-123", "step-9"):
        req = pm.request("email_envoyer", {"destinataire": "a@example.com"})
    assert req["context_id"] == "mission-123"
    assert req["step_id"] == "step-9"
    assert pm.pending()[0]["context_id"] == "mission-123"


def test_rejected_approval_blocks_step_without_counting_success(tmp_path):
    store = MissionStore(str(tmp_path / "agency.db"))
    pending = []

    def execute(payload):
        pending.append({"approval_id": "a", "step_id": payload["step_id"]})
        return "action en attente"

    orch = MissionOrchestrator(store, execute, planner_callable=None,
                               approval_probe=lambda _mid: list(pending), default_max_agents=1)
    mission = orch.create("Envoie un email", max_minutes=2, max_steps=8, max_agents=1)
    assert wait_status(store, mission["id"], {"waiting_approval", "failed"}) == "waiting_approval"
    step = next(s for s in store.steps(mission["id"]) if s["status"] == "waiting_approval")
    pending.clear()
    orch.on_approval_result(mission["id"], "Action refusée", step_id=step["id"], approved=False)
    assert wait_status(store, mission["id"], {"blocked", "failed", "completed"}) == "blocked"
    loaded = store.get(mission["id"])
    assert loaded["steps"][step["seq"] - 1]["status"] == "blocked"
    assert loaded["finished_at"] is None


def test_manual_resume_replays_lost_approval_after_restart(tmp_path):
    path = str(tmp_path / "agency.db")
    store = MissionStore(path)
    pending = []
    calls = {"count": 0}

    def execute(payload):
        calls["count"] += 1
        if calls["count"] == 1:
            pending.append({"approval_id": "a", "step_id": payload["step_id"]})
            return "action en attente"
        return "action recréée puis terminée"

    orch = MissionOrchestrator(store, execute, planner_callable=None,
                               approval_probe=lambda _mid: list(pending), default_max_agents=1)
    mission = orch.create("Prépare un email", max_minutes=2, max_steps=8, max_agents=1)
    assert wait_status(store, mission["id"], {"waiting_approval"}) == "waiting_approval"
    pending.clear()  # simule la perte des jetons en mémoire après redémarrage
    orch.resume(mission["id"], "reprise après redémarrage")
    assert wait_status(store, mission["id"], {"completed", "failed"}) == "completed"
    assert calls["count"] >= 2
