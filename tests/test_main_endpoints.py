import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "mcp-backend"}

@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint returns correct structure."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "MCP Backend API"
    assert "version" in data
    assert "endpoints" in data

@pytest.mark.asyncio
async def test_ingest_conversation(async_client, override_get_db, override_dependencies):
    """Test conversation ingestion with mocked dependencies."""
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
    
    response = await async_client.post("/ingest", json=conversation_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["scenario_title"] == "Test Scenario"

@pytest.mark.asyncio
async def test_search_conversations(async_client, override_get_db, override_dependencies):
    """Test conversation search functionality."""
    # First, ingest a conversation
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
    
    ingest_response = await async_client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 201
    
    # Now search for it
    search_response = await async_client.get("/search?q=Python programming&top_k=5")
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert "results" in search_data
    assert "query" in search_data
    assert search_data["query"] == "Python programming"

@pytest.mark.asyncio
async def test_get_conversations(async_client, override_get_db, override_dependencies):
    """Test getting conversations list with pagination."""
    response = await async_client.get("/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Test pagination parameters
    response = await async_client.get("/conversations?skip=0&limit=10")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_specific_conversation(async_client, override_get_db, override_dependencies):
    """Test getting a specific conversation by ID."""
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
    
    ingest_response = await async_client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 201
    conversation_id = ingest_response.json()["id"]
    
    # Get the specific conversation
    get_response = await async_client.get(f"/conversations/{conversation_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == conversation_id
    assert data["scenario_title"] == "Specific Test"

@pytest.mark.asyncio
async def test_get_nonexistent_conversation(async_client, override_get_db):
    """Test getting a non-existent conversation returns 404."""
    response = await async_client.get("/conversations/99999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_conversation(async_client, override_get_db, override_dependencies):
    """Test deleting a conversation."""
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
    
    ingest_response = await async_client.post("/ingest", json=conversation_data)
    assert ingest_response.status_code == 201
    conversation_id = ingest_response.json()["id"]
    
    # Delete the conversation
    delete_response = await async_client.delete(f"/conversations/{conversation_id}")
    assert delete_response.status_code == 200
    
    # Verify it's deleted
    get_response = await async_client.get(f"/conversations/{conversation_id}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_delete_nonexistent_conversation(async_client, override_get_db):
    """Test deleting a non-existent conversation returns 404."""
    response = await async_client.delete("/conversations/99999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_search_validation_errors(async_client):
    """Test search endpoint validation."""
    # Test without query parameter
    response = await async_client.get("/search")
    assert response.status_code == 422  # Validation error
    
    # Test with invalid top_k (too low)
    response = await async_client.get("/search?q=test&top_k=0")
    assert response.status_code == 422  # Validation error
    
    # Test with invalid top_k (too high)
    response = await async_client.get("/search?q=test&top_k=100")
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_conversations_pagination_validation(async_client):
    """Test conversations endpoint pagination validation."""
    # Test with invalid skip (negative)
    response = await async_client.get("/conversations?skip=-1")
    assert response.status_code == 422
    
    # Test with invalid limit (too high)
    response = await async_client.get("/conversations?limit=2000")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_ingest_validation_errors(async_client):
    """Test ingestion endpoint validation."""
    # Test with missing required fields
    response = await async_client.post("/ingest", json={})
    assert response.status_code == 422
    
    # Test with invalid message structure
    invalid_data = {
        "scenario_title": "Test",
        "messages": ["invalid_message_format"]
    }
    response = await async_client.post("/ingest", json=invalid_data)
    assert response.status_code == 422
