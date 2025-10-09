import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app as fastapi_app
from app.database import get_db, Base
import os

# Test database URL (use a dedicated test database/port)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://mcp_user:mcp_password@localhost:5433/mcp_db"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def client(setup_database):
    """Provide a TestClient with DB dependency override limited to this module.

    Using a fixture prevents leaking the override to other test modules (notably
    the integration tests) which expect to use the default application engine.
    """
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    # Cleanup override so later modules (e.g. integration tests) use real dependency
    fastapi_app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="module")
def setup_database():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"].startswith("MCP Conversational Data Server")

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mcp-conversational-data-server"

def test_ingest_conversation(client, setup_database):
    conversation_data = {
        "scenario_title": "Test Scenario",
        "messages": [
            {"author_name": "User1", "author_type": "human", "content": "Hello, this is a test message."},
            {"author_name": "Assistant", "author_type": "ai", "content": "Hello! How can I help you today?"}
        ]
    }
    response = client.post("/ingest", json=conversation_data)
    assert response.status_code == 200
    data = response.json()
    assert data["chunks"] == 2
    assert "conversation_id" in data

def test_get_conversations(client, setup_database):
    """Test getting conversations list"""
    response = client.get("/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_search_conversations(client, setup_database):
    conversation_data = {
        "scenario_title": "Search Test",
        "messages": [
            {"author_name": "User", "author_type": "human", "content": "I need help with Python programming."}
        ]
    }
    ingest_response = client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 200
    search_response = client.get("/search?q=Python programming&top_k=5")
    assert search_response.status_code == 200
    data = search_response.json()
    assert data["query"] == "Python programming"
    assert data["total_results"] >= 1

def test_get_specific_conversation(client, setup_database):
    conversation_data = {
        "scenario_title": "Specific Test",
        "messages": [
            {"author_name": "User", "author_type": "human", "content": "This is a specific test message."}
        ]
    }
    ingest_response = client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 200
    conv_id = ingest_response.json()["conversation_id"]
    get_response = client.get(f"/conversations/{conv_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == conv_id

def test_get_nonexistent_conversation(client):
    """Test getting a non-existent conversation"""
    response = client.get("/conversations/99999")
    assert response.status_code == 404

def test_delete_conversation(client, setup_database):
    conversation_data = {
        "scenario_title": "Delete Test",
        "messages": [
            {"author_name": "User", "author_type": "human", "content": "This conversation will be deleted."}
        ]
    }
    ingest_response = client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 200
    conv_id = ingest_response.json()["conversation_id"]
    delete_response = client.delete(f"/conversations/{conv_id}")
    assert delete_response.status_code == 200
    get_response = client.get(f"/conversations/{conv_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_conversation(client):
    """Test deleting a non-existent conversation"""
    response = client.delete("/conversations/99999")
    assert response.status_code == 404

def test_search_with_invalid_parameters(client):
    response = client.get("/search")
    assert response.status_code == 422
    response = client.get("/search?q=test&top_k=0")
    assert response.status_code == 422


def test_chat_fallback_without_openai(client, setup_database, monkeypatch):
    # Ensure OPENAI_API_KEY is unset
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Ingest data so context exists
    data = {"scenario_title": "Chat Fallback", "messages": [{"author_name": "User", "author_type": "human", "content": "How to install dependencies?"}]}
    resp = client.post("/ingest", json=data)
    assert resp.status_code == 200
    chat = client.post("/chat/ask", json={"content": "install dependencies", "conversation_history": []})
    assert chat.status_code == 200
    payload = chat.json()
    assert "answer" in payload
    # Fallback answer should contain marker phrase
    assert "Fallback" in payload["answer"] or "Based on" in payload["answer"]
    assert isinstance(payload.get("context_used"), list)
