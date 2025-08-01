import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import fastapi_app
from app.database import get_db, Base
from app import schemas

# Test database URL (use a test database)
SQLALCHEMY_DATABASE_URL = "postgresql://test_user:test_password@localhost:5432/test_mcp_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

client = TestClient(fastapi_app)

@pytest.fixture(scope="module")
def setup_database():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "MCP Backend API"

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mcp-backend"

def test_ingest_conversation(setup_database):
    """Test conversation ingestion"""
    conversation_data = {
        "scenario_title": "Test Scenario",
        "original_title": "Test Original Title",
        "url": "https://example.com/test",
        "messages": [
            {
                "author_name": "User1",
                "author_type": "human",
                "content": "Hello, this is a test message.",
                "timestamp": "2023-01-01T12:00:00Z"
            },
            {
                "author_name": "Assistant",
                "author_type": "ai",
                "content": "Hello! How can I help you today?",
                "timestamp": "2023-01-01T12:00:30Z"
            }
        ]
    }
    
    response = client.post("/ingest", json=conversation_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["scenario_title"] == "Test Scenario"

def test_get_conversations(setup_database):
    """Test getting conversations list"""
    response = client.get("/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_search_conversations(setup_database):
    """Test conversation search"""
    # First ingest a conversation
    conversation_data = {
        "scenario_title": "Search Test",
        "original_title": "Search Test Original",
        "url": "https://example.com/search",
        "messages": [
            {
                "author_name": "User",
                "author_type": "human",
                "content": "I need help with Python programming.",
                "timestamp": "2023-01-01T12:00:00Z"
            }
        ]
    }
    
    ingest_response = client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 201
    
    # Now search for it
    search_response = client.get("/search?q=Python programming&top_k=5")
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert "results" in search_data
    assert "query" in search_data
    assert search_data["query"] == "Python programming"

def test_get_specific_conversation(setup_database):
    """Test getting a specific conversation by ID"""
    # First ingest a conversation
    conversation_data = {
        "scenario_title": "Specific Test",
        "original_title": "Specific Test Original",
        "url": "https://example.com/specific",
        "messages": [
            {
                "author_name": "User",
                "author_type": "human",
                "content": "This is a specific test message.",
                "timestamp": "2023-01-01T12:00:00Z"
            }
        ]
    }
    
    ingest_response = client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 201
    conversation_id = ingest_response.json()["id"]
    
    # Get the specific conversation
    get_response = client.get(f"/conversations/{conversation_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == conversation_id
    assert data["scenario_title"] == "Specific Test"

def test_get_nonexistent_conversation():
    """Test getting a non-existent conversation"""
    response = client.get("/conversations/99999")
    assert response.status_code == 404

def test_delete_conversation(setup_database):
    """Test deleting a conversation"""
    # First ingest a conversation
    conversation_data = {
        "scenario_title": "Delete Test",
        "original_title": "Delete Test Original",
        "url": "https://example.com/delete",
        "messages": [
            {
                "author_name": "User",
                "author_type": "human",
                "content": "This conversation will be deleted.",
                "timestamp": "2023-01-01T12:00:00Z"
            }
        ]
    }
    
    ingest_response = client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 201
    conversation_id = ingest_response.json()["id"]
    
    # Delete the conversation
    delete_response = client.delete(f"/conversations/{conversation_id}")
    assert delete_response.status_code == 200
    
    # Verify it's deleted
    get_response = client.get(f"/conversations/{conversation_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_conversation():
    """Test deleting a non-existent conversation"""
    response = client.delete("/conversations/99999")
    assert response.status_code == 404

def test_search_with_invalid_parameters():
    """Test search with invalid parameters"""
    # Test without query parameter
    response = client.get("/search")
    assert response.status_code == 422  # Validation error
    
    # Test with invalid top_k
    response = client.get("/search?q=test&top_k=0")
    assert response.status_code == 422  # Validation error
