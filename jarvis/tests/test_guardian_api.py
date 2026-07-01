"""API Gardien (Flask) : auth, cycle d'analyse, sirène, urgence, anti-clé-API."""
import re


def test_guardian_status_requires_auth(J):
    c = J.app.test_client()
    assert c.get("/api/guardian/status").status_code == 401


def test_guardian_status_ok(client):
    d = client.get("/api/guardian/status").get_json()
    assert "enabled" in d and "state" in d and "config" in d
    # La config exposée ne doit contenir AUCUN secret.
    blob = str(d["config"]).lower()
    assert "api_key" not in blob and "sk-" not in blob


def test_guardian_enable_and_disable(client):
    assert client.post("/api/guardian/enable", json={"on": True}).get_json()["enabled"] is True
    assert client.post("/api/guardian/enable", json={"on": False}).get_json()["enabled"] is False


def test_guardian_analyze_needs_image(client):
    client.post("/api/guardian/enable", json={"on": True})
    assert client.post("/api/guardian/analyze", json={}).status_code == 400


def test_guardian_analyze_disabled_returns_error(client):
    client.post("/api/guardian/enable", json={"on": False})
    d = client.post("/api/guardian/analyze", json={"image": "data:,AAAA"}).get_json()
    assert not d["ok"]


def test_guardian_manual_siren_allowed(client):
    d = client.post("/api/guardian/siren", json={"action": "start"}).get_json()
    assert d["ok"] is True                       # déclenchement manuel autorisé


def test_guardian_siren_stop(client):
    d = client.post("/api/guardian/siren", json={"action": "stop"}).get_json()
    assert d["ok"] is True


def test_emergency_request_then_confirm(client):
    req = client.post("/api/guardian/emergency/request",
                      json={"target": "owner", "reason": "test"}).get_json()
    assert req["pending"] and req["approval_id"]
    # Sans jeton → refusé.
    bad = client.post("/api/guardian/emergency/confirm",
                      json={"target": "owner", "reason": "test"}).get_json()
    assert bad.get("ok") is False or "requis" in str(bad).lower()


def test_pairing_code_then_redeem(client):
    code = client.post("/api/guardian/pair/create", json={"name": "Tablette entrée"}).get_json()
    assert re.fullmatch(r"\d{6}", code["code"])
    dev = client.post("/api/guardian/pair/redeem",
                      json={"code": code["code"], "device_name": "iPad"}).get_json()
    assert dev["ok"] and dev["token"]
    # L'appareil Gardien n'a QUE des scopes limités (pas de contrôle PC/urgence).
    assert all(s.startswith("guardian:") for s in dev["scopes"])


def test_root_redirects_to_app(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (301, 302) and "/app" in r.headers.get("Location", "")


# ── Scénario 12 : aucune clé d'API dans les fichiers servis au navigateur ──
def test_gardien_page_has_no_apikey_and_no_external_script(client):
    html = client.get("/gardien").get_data(as_text=True)
    low = html.lower()
    assert "claude.ai" not in low                # script opaque supprimé
    assert "apikey" not in low and "api-key" not in low
    assert "sk-" not in html                     # aucune clé de démo
    assert 'type="password"' not in low          # plus de champ clé
    assert "content-security-policy" in low      # CSP présente


def test_index_page_has_no_apikey_field(client):
    html = client.get("/app").get_data(as_text=True).lower()
    assert "saisir une clé" not in html
    # le champ jeton API existant est un jeton de session, pas une clé fournisseur
    assert "openai" not in html and "gemini" not in html
