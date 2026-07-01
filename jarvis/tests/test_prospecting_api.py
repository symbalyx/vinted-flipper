from pathlib import Path


def test_prospecting_page_and_status(client):
    assert client.get("/prospection").status_code == 200
    status = client.get("/api/prospection/status")
    assert status.status_code == 200
    data = status.get_json()
    assert data["ok"] is True
    assert data["policy"]["bulk_send"] is False


def test_prospecting_frontend_has_no_html_injection_sink():
    html = (Path(__file__).resolve().parents[1] / "web" / "prospection.html").read_text(encoding="utf-8")
    assert "innerHTML" not in html
    assert "insertAdjacentHTML" not in html
    assert "textContent" in html


def test_agency_frontend_exposes_definition_of_done():
    html = (Path(__file__).resolve().parents[1] / "web" / "agency.html").read_text(encoding="utf-8")
    assert 'id="criteria"' in html
    assert "continue_until_done" in html
    assert "max_repair_cycles" in html


def test_prospecting_campaign_creates_durable_agency_mission(client, J, monkeypatch):
    captured = {}

    def fake_create(goal, **kwargs):
        captured["goal"] = goal
        captured.update(kwargs)
        return {"id": "campaign-123", "status": "queued"}

    monkeypatch.setattr(J.mission_orchestrator, "create", fake_create)
    response = client.post("/api/prospection/campaigns", json={
        "sector": "menuisiers",
        "region": "Bordeaux",
        "target_count": 12,
        "offer": "site web mobile",
        "prepare_drafts": True,
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["agency_url"].endswith("campaign-123")
    assert captured["continue_until_done"] is True
    assert captured["metadata"]["source"] == "prospecting_campaign"
    assert captured["metadata"]["target_count"] == 12
    assert "Aucun e-mail n'a été envoyé" in captured["completion_criteria"]
    assert "sources professionnelles publiques" in captured["goal"]


def test_prospecting_campaign_requires_sector_and_region(client):
    response = client.post("/api/prospection/campaigns", json={"sector": "menuisiers"})
    assert response.status_code == 400
    assert "Région" in response.get_json()["error"]


def test_prospecting_frontend_exposes_durable_campaign_launcher():
    html = (Path(__file__).resolve().parents[1] / "web" / "prospection.html").read_text(encoding="utf-8")
    assert 'id="campaignStart"' in html
    assert "/api/prospection/campaigns" in html
    assert "Aucun envoi automatique" in html
