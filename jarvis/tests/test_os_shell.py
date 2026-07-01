"""Shell JARVIS OS (HUD multi-modules) : route + sécurité de la page."""


def test_os_requires_auth(J):
    c = J.app.test_client()
    assert c.get("/os").status_code == 401


def test_os_page_served(client):
    r = client.get("/os")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    low = html.lower()
    # Cœur animé + dock + modules présents
    assert "id=\"core\"" in low and "id=\"dock\"" in low and "reactor" in low
    # Aucune clé ni CDN externe ; CSP présente (le seul http(s) autorisé est
    # l'URI de namespace SVG w3.org, pas une ressource réseau).
    assert "claude.ai" not in low and "sk-" not in html
    assert "googleapis" not in low and "cdn." not in low and "unpkg" not in low
    assert "content-security-policy" in low
    # Modules attendus câblés sur l'API réelle (dont carte géo + OSINT)
    for ep in ("/api/chat", "/api/web/search", "/api/approvals", "/api/stream",
               "/api/timeline", "/api/osint/lookup", "/assets/world.geojson"):
        assert ep in html


def test_os_has_no_external_scripts(client):
    html = client.get("/os").get_data(as_text=True)
    # Pas de <script src=…> distant (tout est inline, CSP script-src 'self')
    assert "script src=\"http" not in html.lower().replace(" ", "")
    assert "<script src=" not in html.lower()
