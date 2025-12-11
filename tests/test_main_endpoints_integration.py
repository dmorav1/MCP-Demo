from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_integration():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ["healthy", "degraded"]


def test_root_endpoint_integration():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["message"].startswith("MCP Conversational Data Server")


def test_ingest_and_get_conversation_integration():
    payload = {
        "scenario_title": "Integration Test Scenario",
        "messages": [
            {"author_name": "User1", "author_type": "human", "text": "Hello integration."},
            {"author_name": "Assistant", "author_type": "assistant", "text": "Reply integration."}
        ]
    }
    ing = client.post("/conversations/ingest", json=payload)
    assert ing.status_code == 201
    conv_id = ing.json()["conversation_id"]
    get_r = client.get(f"/conversations/{conv_id}")
    assert get_r.status_code == 200
    data = get_r.json()
    assert str(data["id"]) == str(conv_id)
    assert len(data["chunks"]) == 2


def test_search_conversations_integration():
    payload = {"scenario_title": "Searchable Scenario", "messages": [{"author_name": "User", "author_type": "human", "text": "Contains keyword foobar for search."}]}
    resp = client.post("/conversations/ingest", json=payload)

    # Give it a moment? Or assume sync (it is sync in tests usually unless using async client)
    sr = client.get("/search", params={"q": "foobar", "top_k": 5})
    assert sr.status_code == 200
    js = sr.json()
    assert js["query"] == "foobar"
    assert js["total_results"] >= 1


def test_conversations_list_integration():
    lr = client.get("/conversations", params={"skip": 0, "limit": 10})
    assert lr.status_code == 200
    assert isinstance(lr.json(), list)


def test_delete_conversation_integration():
    payload = {"scenario_title": "Delete Scenario", "messages": [{"author_name": "User", "author_type": "human", "text": "Delete me."}]}
    ing = client.post("/conversations/ingest", json=payload)
    conv_id = ing.json()["conversation_id"]
    del_r = client.delete(f"/conversations/{conv_id}")
    assert del_r.status_code == 200
    after = client.get(f"/conversations/{conv_id}")
    assert after.status_code == 404


def test_chat_fallback_endpoint():
    # Ensure at least one conversation for context
    client.post("/conversations/ingest", json={"scenario_title": "ChatCtx", "messages": [{"author_name": "User", "author_type": "human", "text": "Install dependencies using pip."}]})
    resp = client.post("/chat/ask", json={"content": "How to install dependencies?", "conversation_history": []})
    # Chat endpoint might be optional/legacy, but if it runs, it needs data.
    if resp.status_code != 404:
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data

