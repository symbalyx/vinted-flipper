"""Le vieux parser [TAG:...] ne doit plus pouvoir déclencher d'action."""


class ExplodingSecurity:
    def set_armed(self, _value):  # pragma: no cover - ne doit jamais être appelé
        raise AssertionError("une balise legacy a exécuté une action critique")


def test_all_legacy_tags_are_inert_by_default(J, monkeypatch):
    monkeypatch.setattr(J, "LEGACY_TAGS_ENABLED", False)
    raw = "[HEURE] [SCENE:retour] [DESARMER] [APPEL_POLICE:test] [CMD:whoami]"
    result = J.execute_jarvis_commands(raw, ExplodingSecurity())
    assert "[HEURE]" not in result
    assert "[DESARMER]" not in result
    assert "[APPEL_POLICE" not in result
    assert result.count("ancienne balise neutralisée") == 5


def test_critical_tags_stay_inert_even_in_compatibility_mode(J, monkeypatch):
    monkeypatch.setattr(J, "LEGACY_TAGS_ENABLED", True)
    result = J.execute_jarvis_commands("[HEURE] [DESARMER] [SCENE:retour]", ExplodingSecurity())
    assert "[HEURE]" not in result             # balise bénigne exécutée en compatibilité
    assert "ancienne balise neutralisée" in result
    assert "[DESARMER]" not in result
    assert "[SCENE:retour]" not in result


def test_system_prompt_requires_function_calling(J):
    prompt = J.get_system_prompt().lower()
    assert "uniquement les outils de function calling" in prompt
    assert "n'écris jamais de balise historique" in prompt
