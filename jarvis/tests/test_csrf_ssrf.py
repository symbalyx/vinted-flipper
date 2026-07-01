"""v5.7 incrément 2 — protections CSRF (Origin) et SSRF (validation d'URL)."""
from integrations import websearch


# ── SSRF ──
def test_ssrf_blocks_localhost_and_metadata():
    assert not websearch.is_safe_public_url("http://127.0.0.1/")
    assert not websearch.is_safe_public_url("http://localhost/")
    assert not websearch.is_safe_public_url("http://169.254.169.254/latest/meta-data/")
    assert not websearch.is_safe_public_url("http://0.0.0.0/")


def test_ssrf_blocks_private_and_ipv6_local():
    assert not websearch.is_safe_public_url("http://10.0.0.5/")
    assert not websearch.is_safe_public_url("http://192.168.1.1/")
    assert not websearch.is_safe_public_url("http://[::1]/")


def test_ssrf_blocks_scheme_and_embedded_credentials():
    assert not websearch.is_safe_public_url("file:///etc/passwd")
    assert not websearch.is_safe_public_url("ftp://example.com/")
    assert not websearch.is_safe_public_url("http://user:pass@example.com/")


def test_ssrf_blocks_dns_name_resolving_to_private(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("10.1.2.3", 0))])
    ok, reason, _ = websearch.validate_url_for_fetch("http://intranet.example/")
    assert not ok and "interne" in reason.lower()


def test_ssrf_allows_public(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))])
    ok, _, ips = websearch.validate_url_for_fetch("https://example.com/")
    assert ok and ips == ["93.184.216.34"]


def test_read_page_refuses_redirect_to_localhost(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **k: [(2, 1, 6, "", (
                            "127.0.0.1" if "evil" in host else "93.184.216.34", 0))])

    class _Resp:
        is_redirect = True
        status_code = 302
        headers = {"Location": "http://evil.internal/"}
        encoding = "utf-8"
        def iter_content(self, n): return []
        def close(self): pass

    monkeypatch.setattr(websearch.requests, "get", lambda *a, **k: _Resp())
    out = websearch.read_page("https://example.com/")
    assert "⛔" in out or "refus" in out.lower()


def test_osint_resolve_drops_private(monkeypatch):
    import osint, socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: [(2, 1, 6, "", ("10.0.0.1", 0)),
                                         (2, 1, 6, "", ("93.184.216.34", 0))])
    assert osint.resolve_domain("mixed.example") == ["93.184.216.34"]


# ── CSRF (via l'app Flask) ──
def test_csrf_blocks_foreign_origin(J, client):
    r = client.post("/api/system/standby", json={"on": False},
                    headers={"Origin": "http://evil.example"})
    assert r.status_code == 403


def test_csrf_allows_same_origin(J, client):
    r = client.post("/api/system/standby", json={"on": False},
                    headers={"Origin": "http://localhost"})
    assert r.status_code != 403


def test_csrf_allows_no_origin_client(client):
    # test_client / scripts n'envoient pas d'Origin → pas un vecteur CSRF.
    r = client.post("/api/system/standby", json={"on": False})
    assert r.status_code != 403


def test_logout_is_post_only(client):
    # Authentifié : GET est refusé (405 method not allowed), seul POST déconnecte.
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code in (302, 200)
