"""Cloche d'approbation : l'agent gate les actions sensibles, l'UI confirme."""
from agent import ToolRegistry
from permissions import PermissionManager


def test_registry_gates_sensitive_tool():
    pm = PermissionManager()
    reg = ToolRegistry(permission_manager=pm)
    executed = []
    reg.register("ecrire_fichier", "", {"chemin": {"type": "string"}},
                 lambda chemin: executed.append(chemin) or "écrit")
    out = reg.call("ecrire_fichier", {"chemin": "a.txt"})
    assert "approbation" in out.lower() and executed == []      # pas exécuté
    assert len(pm.pending()) == 1


def test_registry_executes_after_confirmation():
    pm = PermissionManager()
    reg = ToolRegistry(permission_manager=pm)
    executed = []
    reg.register("ecrire_fichier", "", {"chemin": {"type": "string"}},
                 lambda chemin: executed.append(chemin) or "écrit")
    reg.call("ecrire_fichier", {"chemin": "a.txt"})
    token = pm.pending()[0]["approval_id"]
    out = reg.call("ecrire_fichier", {"chemin": "a.txt"}, approval_token=token)
    assert out == "écrit" and executed == ["a.txt"]
    assert pm.pending() == []                                   # consommé (usage unique)


def test_read_only_tool_not_gated():
    pm = PermissionManager()
    reg = ToolRegistry(permission_manager=pm)
    reg.register("heure", "", {}, lambda: "12:00")
    assert reg.call("heure", {}) == "12:00"


def test_no_pm_preserves_legacy_behavior():
    reg = ToolRegistry()                                        # aucun gestionnaire
    reg.register("ecrire_fichier", "", {}, lambda: "écrit")
    assert reg.call("ecrire_fichier", {}) == "écrit"           # exécuté (compat)


# ── API ──
def test_api_approvals_flow(J, client):
    # Déclenche une action sensible via le registre réel → crée une approbation.
    J.tool_registry.call("ecrire_fichier", {"chemin": "ui_test.txt", "contenu": "x"})
    listed = client.get("/api/approvals").get_json()["pending"]
    assert any(a["action"] == "ecrire_fichier" for a in listed)
    tok = next(a["approval_id"] for a in listed if a["action"] == "ecrire_fichier")
    # Confirme → exécute réellement (écrit dans le bac à sable).
    conf = client.post("/api/approvals/confirm", json={"approval_id": tok}).get_json()
    assert conf["ok"] and "✅" in conf["result"]


def test_api_approval_reject(J, client):
    J.tool_registry.call("tuer_processus", {"cible": "chrome"})
    tok = next(a["approval_id"] for a in client.get("/api/approvals").get_json()["pending"]
               if a["action"] == "tuer_processus")
    assert client.post("/api/approvals/reject", json={"approval_id": tok}).get_json()["ok"]
    # Refusée → plus dans la liste.
    remaining = [a["approval_id"] for a in client.get("/api/approvals").get_json()["pending"]]
    assert tok not in remaining


def test_api_confirm_unknown_token_404(client):
    assert client.post("/api/approvals/confirm", json={"approval_id": "nope"}).status_code == 404


def test_app_ui_has_palette_and_bell(client):
    html = client.get("/app").get_data(as_text=True).lower()
    assert "bell-badge" in html and "palette" in html      # cloche + palette présentes
    assert "/api/stream" in html                            # bus SSE branché
    assert "/api/approvals" in html                         # cloche câblée sur l'API réelle

