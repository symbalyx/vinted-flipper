"""Géolocalisation de photo : vision (validée) → géocodage → coordonnées."""
import geolocate


class StubVision:
    def __init__(self, raw): self.raw = raw
    def analyze(self, image_b64, prompt): return self.raw


def test_valid_latlon():
    assert geolocate._valid_latlon(48.85, 2.35)
    assert not geolocate._valid_latlon(200, 2)
    assert not geolocate._valid_latlon("x", None)


def test_parse_geo_with_model_coords():
    raw = ('{"place":"Tour Eiffel, Paris","country":"France","city":"Paris",'
           '"landmarks":["tour en fer"],"visible_text":[],"lat":48.8584,"lon":2.2945,'
           '"confidence":0.82,"reasoning":"monument reconnaissable"}')
    r = geolocate.parse_geo(raw)
    assert r["ok"] and r["place"].startswith("Tour Eiffel")
    assert r["lat"] == 48.8584 and r["source"] == "model" and r["confidence"] == 0.82


def test_parse_geo_place_without_coords():
    r = geolocate.parse_geo('{"place":"quelque part","confidence":0.2}')
    assert r["ok"] and r["lat"] is None and r["source"] == "none"


def test_parse_geo_invalid():
    assert geolocate.parse_geo("je ne sais pas")["ok"] is False


def test_geocode_disabled_by_default(monkeypatch):
    monkeypatch.delenv("GEOCODER_URL", raising=False)
    assert geolocate.geocode("Paris") == {}


def test_geocode_with_injected_nominatim(monkeypatch):
    monkeypatch.setenv("GEOCODER_URL", "http://nomi/search?q={q}")
    fake = lambda url: [{"lat": "48.8566", "lon": "2.3522", "display_name": "Paris, France"}]
    geo = geolocate.geocode("Paris", fetch=fake)
    assert geo["lat"] == 48.8566 and "Paris" in geo["display"]


def test_locate_photo_uses_model_coords_when_no_geocoder(monkeypatch):
    monkeypatch.delenv("GEOCODER_URL", raising=False)
    vp = StubVision('{"place":"Colisée, Rome","lat":41.8902,"lon":12.4922,"confidence":0.7}')
    r = geolocate.locate_photo("data:,x", vp)
    assert r["ok"] and r["locatable"] and r["source"] == "model" and r["lat"] == 41.8902


def test_locate_photo_prefers_geocoder(monkeypatch):
    monkeypatch.setenv("GEOCODER_URL", "http://nomi/search?q={q}")
    vp = StubVision('{"place":"Colisée, Rome","lat":0,"lon":0,"confidence":0.7}')
    fetch = lambda url: [{"lat": "41.8902", "lon": "12.4922", "display_name": "Colosseo"}]
    r = geolocate.locate_photo("data:,x", vp, geocode_fetch=fetch)
    assert r["source"] == "geocoder" and r["lat"] == 41.8902


def test_locate_photo_no_vision():
    assert geolocate.locate_photo("data:,x", None)["ok"] is False


# ── API ──
def test_api_geo_requires_auth(J):
    c = J.app.test_client()
    assert c.post("/api/geo/locate-photo", json={"image": "data:,x"}).status_code == 401


def test_api_geo_needs_image(client):
    assert client.post("/api/geo/locate-photo", json={}).status_code == 400


def test_api_geo_with_stub_vision(J, client, monkeypatch):
    # Injecte un modèle de vision factice pour éviter tout appel réseau.
    monkeypatch.setattr(J.guardian_service, "vision",
                        StubVision('{"place":"Big Ben, Londres","country":"UK",'
                                   '"lat":51.5007,"lon":-0.1246,"confidence":0.75}'))
    d = client.post("/api/geo/locate-photo", json={"image": "data:,AAAA"}).get_json()
    assert d["ok"] and d["locatable"] and d["country"] == "UK"
