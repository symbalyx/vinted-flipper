"""Régressions de sécurité des interfaces servies et des requêtes HTTP."""


DANGEROUS_SINKS = ("inner" + "HTML", "insertAdjacent" + "HTML", "document." + "write", "ev" + "al(", "new " + "Function")


def test_app_uses_safe_dom_and_does_not_persist_token(client):
    html = client.get("/app").get_data(as_text=True)
    for sink in DANGEROUS_SINKS:
        assert sink not in html
    assert 'localStorage.setItem("jarvis_conn"' not in html
    assert 'localStorage.setItem("jtoken"' not in html
    assert "TOKEN = \"\"" in html
    assert "fonts.googleapis.com" not in html
    assert "Photo → globe" in html
    assert 'id="photo-file"' in html
    assert 'id="photo-auth"' in html
    assert "personne privée" in html


def test_os_uses_safe_dom_and_exposes_photo_geolocation(client):
    html = client.get("/os").get_data(as_text=True)
    for sink in DANGEROUS_SINKS:
        assert sink not in html
    assert "/api/guardian/geolocate" in html
    assert "Photo → globe" in html
    assert "Estimation visuelle — non exacte" in html
    assert "authorization:true" in html
    assert "adresse privée" in html


def test_login_and_headers_have_no_external_fonts(client):
    login_client = client.application.test_client()
    login = login_client.get("/login")
    assert login.status_code == 200
    assert "fonts.googleapis.com" not in login.get_data(as_text=True)

    page = client.get("/app")
    csp = page.headers.get("Content-Security-Policy", "")
    assert "object-src 'none'" in csp
    assert "font-src 'self'" in csp
    assert "fonts.googleapis.com" not in csp
    assert "camera=(self)" in page.headers.get("Permissions-Policy", "")


def test_request_size_limit_returns_json(client):
    response = client.post("/api/chat", data=b"x" * 4_100_000,
                           content_type="application/json")
    assert response.status_code == 413
    assert response.get_json()["error"] == "Requête trop volumineuse"


def test_disarm_requires_explicit_confirmation(J, client):
    J.security.set_armed(True)
    denied = client.post("/api/security/arm", json={"armed": False})
    assert denied.status_code == 400
    assert J.security.armed is True
    accepted = client.post("/api/security/arm", json={"armed": False, "confirm": True})
    assert accepted.status_code == 200
    assert accepted.get_json()["armed"] is False
