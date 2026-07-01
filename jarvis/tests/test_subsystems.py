"""Tests des sous-systèmes : learning, event_log, memory, automations, pc, detector."""
import time
import tempfile
import os


# ── Learning ──────────────────────────────────────────────
def test_learning_threshold_adapts():
    from learning import LearningEngine
    le = LearningEngine(os.path.join(tempfile.mkdtemp(), "p.json"))
    base = le.motion_threshold(25)
    le.note_false_alarm()
    le.note_false_alarm()
    assert le.motion_threshold(25) > base


def test_learning_profile_summary():
    from learning import LearningEngine
    le = LearningEngine(os.path.join(tempfile.mkdtemp(), "p.json"))
    le.record_chat(); le.record_chat()
    le.add_fact("aime le café")
    assert "café" in le.profile_summary()


# ── Event log + bus ───────────────────────────────────────
def test_event_log_recent_and_subscribe():
    from event_log import EventLog
    el = EventLog(os.path.join(tempfile.mkdtemp(), "ev.jsonl"))
    got = []
    el.subscribers.append(lambda ev: got.append(ev))
    el.add("scene", "test", meta={"x": 1})
    assert got and got[0]["kind"] == "scene"
    assert el.recent(10)[0]["message"] == "test"


# ── Memory (mode lexical sans ollama) ─────────────────────
def test_memory_lexical_recall():
    from memory import VectorMemory
    m = VectorMemory(os.path.join(tempfile.mkdtemp(), "v.json"))
    m.add("le code wifi est 1234")
    m.add("le chien s'appelle Rex")
    res = m.recall("quel est le code wifi")
    assert any("wifi" in r for r in res)


# ── Automations (évaluateur sûr) ──────────────────────────
def test_automation_match_and_fire():
    from automations import AutomationEngine
    fired = []
    rules_path = os.path.join(tempfile.mkdtemp(), "rules.json")
    eng = AutomationEngine(rules_path, lambda: None, lambda s: fired.append(s), lambda *a, **k: None)
    import json
    with open(rules_path, "w") as f:
        json.dump([{"id": "r1", "name": "t", "scene": "soirée",
                    "when": [{"op": "armed", "value": True}]}], f)
    ctx = {"hhmm": "12:00", "date": "2026-01-01", "armed": True, "present": True, "weather": "clear"}
    eng.ctx_provider = lambda: ctx
    eng.tick()
    assert fired == ["soirée"]
    eng.tick()  # anti-rebond : pas une 2e fois le même jour
    assert fired == ["soirée"]


def test_automation_no_eval_safe():
    from automations import OPS
    # Seules des opérations whitelistées existent (pas d'eval arbitraire)
    assert set(OPS) <= {"time_between", "armed", "presence", "weather"}


# ── PC control (dégradation gracieuse en headless) ────────
def test_pc_power_requires_confirm():
    from pc_control import PCController
    pc = PCController(os.path.join(tempfile.mkdtemp(), "shots"))
    assert "confirm" in pc.power("shutdown").lower()


def test_pc_media_returns_string():
    from pc_control import PCController
    pc = PCController(os.path.join(tempfile.mkdtemp(), "shots"))
    assert isinstance(pc.media("play"), str)


def test_pc_power_unknown_action():
    from pc_control import PCController
    pc = PCController(os.path.join(tempfile.mkdtemp(), "shots"))
    assert "inconnue" in pc.power("explode").lower()


# ── Détection comportementale (Veesion-like) ──────────────
def test_behavior_night_presence_scores():
    from security_mod.detector import BehaviorAnalyzer
    ba = BehaviorAnalyzer(loiter_seconds=1.0)
    behaviors, bonus = ba.update([(0, 0, 100, 200)], 0.05, time.time(), hour=3)
    assert "PRÉSENCE NOCTURNE" in behaviors and bonus >= 2


def test_threat_levels():
    from security_mod.detector import threat_level
    assert threat_level(0) == "bas"
    assert threat_level(3) == "moyen"
    assert threat_level(6) == "élevé"
    assert threat_level(9) == "extrême"
