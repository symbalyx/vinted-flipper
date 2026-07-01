"""OSINT d'infrastructure : classification pure + dispatch + garde-fous."""
import osint


def test_classify_ip():
    assert osint.classify_ip("8.8.8.8")["global"] is True
    assert osint.classify_ip("10.0.0.1")["private"] is True
    assert osint.classify_ip("127.0.0.1")["loopback"] is True
    assert osint.classify_ip("not-an-ip")["valid"] is False


def test_is_public_ip():
    assert osint.is_public_ip("1.1.1.1") is True
    assert osint.is_public_ip("192.168.1.1") is False
    assert osint.is_public_ip("::1") is False


def test_hash_type():
    assert osint.hash_type("d41d8cd98f00b204e9800998ecf8427e") == "md5"
    assert osint.hash_type("a" * 40) == "sha1"
    assert osint.hash_type("b" * 64) == "sha256"
    assert osint.hash_type("xyz") == ""


def test_is_domain_and_query_type():
    assert osint.is_domain("example.com")
    assert not osint.is_domain("not a domain")
    assert osint.query_type("8.8.8.8") == "ip"
    assert osint.query_type("example.com") == "domain"
    assert osint.query_type("a" * 64) == "hash"
    assert osint.query_type("???") == "inconnu"


def test_geolocate_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OSINT_GEO_URL", raising=False)
    assert osint.geolocate_ip("8.8.8.8") == {}


def test_geolocate_with_injected_provider(monkeypatch):
    monkeypatch.setenv("OSINT_GEO_URL", "http://example/{ip}")
    fake = lambda url: {"lat": 37.75, "lon": -97.82, "country": "US", "org": "TestNet"}
    geo = osint.geolocate_ip("8.8.8.8", fetch=fake)
    assert geo["lat"] == 37.75 and geo["country"] == "US"


def test_geolocate_refuses_private_ip(monkeypatch):
    monkeypatch.setenv("OSINT_GEO_URL", "http://example/{ip}")
    assert osint.geolocate_ip("10.0.0.1", fetch=lambda u: {"lat": 1, "lon": 2}) == {}


def test_lookup_private_ip_no_external():
    r = osint.lookup("192.168.1.50")
    assert r["ok"] and r["type"] == "ip" and "note" in r
    assert "whois" not in r          # aucune requête externe pour une IP privée


def test_lookup_hash():
    r = osint.lookup("d41d8cd98f00b204e9800998ecf8427e")
    assert r["ok"] and r["type"] == "hash" and r["algo"] == "md5"


def test_lookup_unknown_rejected():
    assert osint.lookup("bonjour le monde")["ok"] is False


# ── API ──
def test_api_osint_requires_auth(J):
    c = J.app.test_client()
    assert c.get("/api/osint/lookup?q=8.8.8.8").status_code == 401


def test_api_osint_needs_q(client):
    assert client.get("/api/osint/lookup").status_code == 400


def test_api_osint_private_ip(client):
    d = client.get("/api/osint/lookup?q=10.0.0.1").get_json()
    assert d["ok"] and d["type"] == "ip" and "note" in d


def test_assets_geojson_served(client):
    r = client.get("/assets/world.geojson")
    assert r.status_code == 200
    assert b"FeatureCollection" in r.get_data()
