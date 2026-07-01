"""v5.7 incrément 2 — baux d'étape, reaper, classification d'erreurs, backoff,
réconciliation des reçus. Tests au niveau du store (là où vivent les garanties)."""
import random
import time

from agency.store import MissionStore
from agency.errors import classify_error, ErrorType, is_transient, is_permanent
from agency.backoff import next_delay


def _store(tmp_path):
    s = MissionStore(str(tmp_path / "agency.db"))
    s.create("m", "goal", max_minutes=10, max_steps=5, max_agents=1)
    s.set_plan("m", "plan", [{"id": "s1", "seq": 1, "role": "builder",
                              "title": "T", "instructions": "do", "status": "pending"}])
    return s


def test_schema_version_is_v57(tmp_path):
    assert _store(tmp_path).schema_version() == 57


def test_two_workers_cannot_both_claim_same_step(tmp_path):
    s = _store(tmp_path)
    a = s.claim_step("s1", worker_id="wA", lease_seconds=120)
    b = s.claim_step("s1", worker_id="wB", lease_seconds=120)
    assert a is not None and b is None            # un seul obtient le bail
    assert a["lease_token"]


def test_renew_requires_correct_worker_and_token(tmp_path):
    s = _store(tmp_path)
    claimed = s.claim_step("s1", worker_id="wA", lease_seconds=120)
    tok = claimed["lease_token"]
    assert s.renew_step_lease("s1", "wA", tok, 120) is True
    assert s.renew_step_lease("s1", "wB", tok, 120) is False       # mauvais worker
    assert s.renew_step_lease("s1", "wA", "wrong", 120) is False   # mauvais token


def test_old_worker_cannot_record_after_lease_taken_over(tmp_path):
    s = _store(tmp_path)
    old = s.claim_step("s1", worker_id="wA", lease_seconds=0.01)
    time.sleep(0.05)
    # Le reaper récupère l'étape (bail expiré) → un nouveau worker la reprend.
    assert s.reap_expired_steps(next_run_delay=0) == 1
    new = s.claim_step("s1", worker_id="wB", lease_seconds=120)
    assert new is not None
    # L'ancien worker tente d'écrire son résultat : REFUSÉ (bail périmé).
    ok_old = s.record_step_result("s1", "wA", old["lease_token"],
                                  status="succeeded", result="stale")
    assert ok_old is False
    # Le nouveau worker, lui, peut enregistrer.
    assert s.record_step_result("s1", "wB", new["lease_token"],
                                status="succeeded", result="fresh") is True


def test_reaper_recovers_dead_worker_and_keeps_checkpoint(tmp_path):
    s = _store(tmp_path)
    claimed = s.claim_step("s1", worker_id="wA", lease_seconds=0.01)
    s.update_step("s1", checkpoint_json='{"progress": 42}')
    time.sleep(0.05)
    assert s.reap_expired_steps(next_run_delay=5) == 1
    step = s.steps("m")[0]
    assert step["status"] == "retry_wait"
    assert step["error_type"] == ErrorType.TRANSIENT_WORKER_LOST
    assert step["checkpoint"] == {"progress": 42}     # checkpoint conservé
    assert step["next_run_at"] > time.time()


def test_reaper_is_idempotent_no_double_count(tmp_path):
    s = _store(tmp_path)
    s.claim_step("s1", worker_id="wA", lease_seconds=0.01)  # attempt -> 1
    time.sleep(0.05)
    first = s.reap_expired_steps(next_run_delay=5)
    second = s.reap_expired_steps(next_run_delay=5)         # 2e passage : rien
    third = s.reap_expired_steps(next_run_delay=5)
    assert first == 1 and second == 0 and third == 0
    assert s.steps("m")[0]["attempt"] == 1                 # compteur non doublé


# ── Classification des erreurs ──
def test_classify_transient_vs_permanent():
    assert classify_error(text="temporary network error") == ErrorType.TRANSIENT_NETWORK
    assert classify_error(text="request timed out") == ErrorType.TRANSIENT_TIMEOUT
    assert classify_error(text="429 too many requests") == ErrorType.TRANSIENT_RATE_LIMIT
    assert classify_error(text="503 service unavailable") == ErrorType.TRANSIENT_SERVICE_UNAVAILABLE
    assert is_transient(classify_error(text="ollama cannot connect"))
    assert classify_error(text="422 validation failed") == ErrorType.PERMANENT_VALIDATION
    assert classify_error(text="403 forbidden") == ErrorType.PERMANENT_PERMISSION
    assert is_permanent(classify_error(text="invalid schema"))


def test_classify_approval_rejection_is_human_required():
    assert classify_error(text="approbation refusée par l'utilisateur") == ErrorType.HUMAN_REQUIRED


# ── Backoff ──
def test_backoff_increases_and_is_bounded():
    d1 = next_delay(1, base=10, maximum=3600, jitter_ratio=0)
    d2 = next_delay(2, base=10, maximum=3600, jitter_ratio=0)
    d3 = next_delay(3, base=10, maximum=3600, jitter_ratio=0)
    assert d1 == 10 and d2 == 20 and d3 == 40           # exponentiel sans jitter
    assert next_delay(50, base=10, maximum=3600, jitter_ratio=0) == 3600   # plafonné


def test_backoff_jitter_is_bounded():
    rng = random.Random(1)
    for _ in range(200):
        d = next_delay(3, base=10, maximum=3600, jitter_ratio=0.2, rng=rng)
        assert 32 <= d <= 48                             # 40 ± 20%


def test_backoff_respects_retry_after():
    assert next_delay(1, base=10, maximum=3600, jitter_ratio=0, retry_after=120) == 120


# ── Réconciliation des reçus in_flight ──
def test_reconcile_marks_old_in_flight_without_reexecution(tmp_path):
    s = MissionStore(str(tmp_path / "a.db"))
    key, existing = s.begin_action_receipt("m", "s1", "email_envoyer", {"to": "x@y.z"})
    assert existing is None
    # Aucun in_flight récent n'est réconcilié…
    assert s.reconcile_stuck_receipts(max_in_flight_seconds=9999) == 0
    # …mais un in_flight « ancien » (seuil 0s) passe en RECONCILIATION_REQUIRED.
    assert s.reconcile_stuck_receipts(max_in_flight_seconds=0) == 1
    r = s.get_action_receipt("m", "s1", "email_envoyer", {"to": "x@y.z"})
    assert r["status"] == "in_flight"                    # jamais réexécuté
    assert r["reconciliation_status"] == "RECONCILIATION_REQUIRED"
