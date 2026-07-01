"""Tests des conversations persistantes côté serveur."""
import os
import tempfile


def test_store_crud():
    from conversations import ConversationStore
    cs = ConversationStore(os.path.join(tempfile.mkdtemp(), "c.json"))
    c = cs.create("Test")
    assert c["id"] in cs.data
    c["messages"].append({"role": "user", "content": "hi"})
    cs.touch(c["id"], "hi")
    cs.save()
    assert cs.get(c["id"])["messages"][0]["content"] == "hi"
    assert any(x["id"] == c["id"] for x in cs.list())
    assert cs.delete(c["id"]) is True
    assert cs.get(c["id"]) is None


def test_store_persists(tmp_path=None):
    from conversations import ConversationStore
    p = os.path.join(tempfile.mkdtemp(), "c.json")
    cs = ConversationStore(p)
    c = cs.create("Persist")
    c["messages"].append({"role": "user", "content": "x"})
    cs.save()
    cs2 = ConversationStore(p)   # recharge depuis le disque
    assert cs2.get(c["id"]) is not None


def test_endpoints_conversations(client):
    r = client.post("/api/conversations", json={"title": "Démo"})
    cid = r.get_json()["id"]
    assert client.get("/api/conversations").get_json()["conversations"]
    assert client.get("/api/conversations/" + cid).status_code == 200
    assert client.get("/api/conversations/inexistant").status_code == 404
    assert client.delete("/api/conversations/" + cid).get_json()["deleted"] is True


def test_chat_uses_conversation_fallback(client, J):
    # Sans LLM joignable, l'agent renvoie None → fallback ; en mode conversation,
    # le message user doit être stocké dans la conversation.
    cid = client.post("/api/conversations", json={}).get_json()["id"]
    client.post("/api/chat", json={"message": "Bonjour test", "conversation_id": cid})
    msgs = J.convo_store.get(cid)["messages"]
    assert any(m["role"] == "user" and "Bonjour test" in m["content"] for m in msgs)
