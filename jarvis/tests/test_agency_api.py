def test_agency_ui_and_create_without_autostart(client):
    assert client.get("/agency").status_code == 200
    r = client.post("/api/agency/missions", json={
        "goal": "Faire un rapport de test", "autostart": False,
        "max_minutes": 5, "max_steps": 5, "max_agents": 2,
    })
    assert r.status_code == 201
    mid = r.get_json()["mission"]["id"]
    detail = client.get(f"/api/agency/missions/{mid}")
    assert detail.status_code == 200
    assert detail.get_json()["mission"]["status"] == "queued"
    assert client.post(f"/api/agency/missions/{mid}/cancel").status_code == 200
    assert client.delete(f"/api/agency/missions/{mid}").status_code == 200


def test_voice_status_is_exposed(client):
    r = client.get("/api/voice/status")
    assert r.status_code == 200
    assert "dependency_available" in r.get_json()


def test_frontend_links_agency_and_local_voice():
    from pathlib import Path
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    assert 'href="/agency"' in html
    assert "/api/voice/transcribe" in html
    assert "echoCancellation:true" in html
    assert "innerHTML" not in html
