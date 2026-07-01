"""Tests de la boucle agentique + function-calling."""
from agent import Agent, ToolRegistry


class FakeAI:
    backend = "deepseek"
    base_url = ""
    api_key = ""
    model = "x"

    def __init__(self):
        self.history = []

    def _save_history(self):
        pass


def test_registry_register_and_call():
    reg = ToolRegistry()
    reg.register("ping", "test", {}, lambda: "pong")
    assert reg.call("ping", {}) == "pong"
    assert "ping" in reg.names()


def test_registry_unknown_tool():
    reg = ToolRegistry()
    assert "inconnu" in reg.call("nope", {}).lower()


def test_registry_handler_error_caught():
    reg = ToolRegistry()
    reg.register("boom", "", {}, lambda: 1 / 0)
    assert "erreur" in reg.call("boom", {}).lower()


def test_schema_required_vs_optional():
    reg = ToolRegistry()
    reg.register("t", "d", {"a": {"type": "string"},
                            "b": {"type": "string", "optional": True}}, lambda a, b="": a)
    params = reg.schemas()[0]["function"]["parameters"]
    assert params["required"] == ["a"]
    assert "b" in params["properties"]


def test_agent_multi_turn_tool_then_final():
    reg = ToolRegistry()
    called = []
    reg.register("allumer", "", {}, lambda: called.append(1) or "ok")
    ai = FakeAI()
    ag = Agent(ai, reg, max_turns=4)
    seq = [
        {"message": {"role": "assistant", "content": None,
                     "tool_calls": [{"id": "1", "function": {"name": "allumer", "arguments": "{}"}}]}},
        {"message": {"role": "assistant", "content": "C'est fait."}},
    ]
    ag._call_llm = lambda messages: seq.pop(0)
    out = ag.run("allume", "SYS")
    assert called == [1]
    assert out == "C'est fait."


def test_agent_fallback_when_no_tooluse():
    ai = FakeAI()
    ag = Agent(ai, ToolRegistry())
    ag._call_llm = lambda messages: None
    assert ag.run("salut", "SYS") is None


def test_agent_max_turns_guard():
    reg = ToolRegistry()
    reg.register("loop", "", {}, lambda: "encore")
    ai = FakeAI()
    ag = Agent(ai, reg, max_turns=3)
    # Le LLM rappelle toujours un outil → on doit s'arrêter proprement
    ag._call_llm = lambda messages: {"message": {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "1", "function": {"name": "loop", "arguments": "{}"}}]}}
    out = ag.run("x", "SYS")
    assert isinstance(out, str) and len(out) > 0


def test_sensitive_tool_arguments_are_redacted_for_logs():
    from agent import _redact_tool_args
    out = _redact_tool_args("email_envoyer", {
        "destinataire": "a@example.com", "corps": "secret privé", "approval_token": "abc"
    })
    assert out["destinataire"] == "a@example.com"
    assert "secret privé" not in out["corps"]
    assert out["approval_token"] == "<secret>"
