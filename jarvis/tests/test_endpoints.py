"""Tests des endpoints Flask : auth, contrôle système, PC, idempotence."""


def test_auth_required(J):
    c = J.app.test_client()
    assert c.get("/api/status").status_code == 401


def test_auth_token_header(J):
    c = J.app.test_client()
    r = c.get("/api/status", headers={"X-JARVIS-Token": J.API_TOKEN})
    assert r.status_code == 200


def test_login_bad_then_good(J):
    J._LOGIN_FAILS.clear()
    c = J.app.test_client()
    assert c.post("/login", data={"password": "wrong"}).status_code == 401
    assert c.post("/login", data={"password": "testpass"}).status_code == 302


def test_login_rate_limit(J):
    J._LOGIN_FAILS.clear()
    c = J.app.test_client()
    codes = [c.post("/login", data={"password": "x"}).status_code for _ in range(7)]
    J._LOGIN_FAILS.clear()   # nettoie pour ne pas bloquer les tests suivants
    assert 429 in codes   # bloqué après plusieurs échecs


def test_status_fields(client):
    d = client.get("/api/status").get_json()
    for k in ("version", "pouvoirs", "agent", "vision", "auth", "tools"):
        assert k in d


def test_shutdown_requires_confirm(client):
    assert client.post("/api/system/shutdown", json={}).status_code == 400


def test_pc_power_endpoint_blocks_destructive(client):
    d = client.post("/api/pc/power", json={"action": "shutdown"}).get_json()
    assert "confirm" in d["message"].lower()


def test_pc_endpoints_ok(client):
    assert client.post("/api/pc/lock").status_code == 200
    assert client.post("/api/pc/media/play").status_code == 200


def test_timeline_and_stream_auth(J):
    c = J.app.test_client()
    assert c.get("/api/timeline").status_code == 401   # protégé


def test_identify_idempotent(J, client):
    J.security.pending.insert(0, {"id": "T1", "timestamp": "x", "event": "PERSONNE",
                                  "threat": "moyen", "snapshot": "", "status": "en_attente"})
    first = client.post("/api/security/identify", json={"id": "T1", "known": True}).get_json()
    second = client.post("/api/security/identify", json={"id": "T1", "known": True}).get_json()
    assert "déjà" in second["message"].lower() or "trait" in second["message"].lower()


def test_standby_then_wake(client):
    client.post("/api/system/standby", json={"on": True})
    r = client.post("/api/chat", json={"message": "bonjour"}).get_json()
    assert "veille" in r["response"].lower()
    r2 = client.post("/api/chat", json={"message": "réveille-toi"}).get_json()
    assert "revoil" in r2["response"].lower()
