import pytest
from httpx import AsyncClient
from app.main import fastapi_app
from app import schemas


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint returns correct structure."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "MCP Backend API"
    assert "version" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_ingest_and_get_conversation_integration(app_dependency_overrides, async_client: AsyncClient):
    """Test the full conversation lifecycle: ingest, retrieve, and verify against real database."""
    # Test data
    conversation_payload = schemas.ConversationIngest(
        scenario_title="Integration Test Scenario", 
        original_title="Integration Test Original Title",
        url="https://example.com/integration-test",
        messages=[
            {
                "author_name": "User1",
                "author_type": "human", 
                "content": "Hello, this is an integration test message.",
                "timestamp": "2023-01-01T12:00:00Z",
            },
            {
                "author_name": "Assistant",
                "author_type": "ai",
                "content": "Hello! I'm responding in the integration test.",
                "timestamp": "2023-01-01T12:00:30Z",
            },
        ],
    )
    
    # 1. Ingest conversation
    response_ingest = await async_client.post("/ingest", json=conversation_payload.model_dump())
    assert response_ingest.status_code == 201
    ingested_data = response_ingest.json()
    conversation_id = ingested_data["id"]
    assert ingested_data["scenario_title"] == conversation_payload.scenario_title
    
    # 2. Retrieve the conversation
    response_get = await async_client.get(f"/conversations/{conversation_id}")
    assert response_get.status_code == 200
    retrieved_data = response_get.json()
    
    # 3. Verify the data matches
    assert retrieved_data["scenario_title"] == conversation_payload.scenario_title
    assert retrieved_data["original_title"] == conversation_payload.original_title
    assert retrieved_data["url"] == conversation_payload.url
    assert len(retrieved_data["chunks"]) == len(conversation_payload.messages)


@pytest.mark.asyncio
async def test_search_conversations_integration(app_dependency_overrides, async_client: AsyncClient):
    """Test conversation search against real database."""
    # First ingest a conversation
    conversation_payload = schemas.ConversationIngest(
        scenario_title="Searchable Test Scenario", 
        original_title="Searchable Test Original Title",
        url="https://example.com/searchable-test",
        messages=[
            {
                "author_name": "User1",
                "author_type": "human", 
                "content": "This message contains searchable keywords like python programming.",
                "timestamp": "2023-01-01T12:00:00Z",
            },
        ],
    )
    
    # Ingest the conversation
    response_ingest = await async_client.post("/ingest", json=conversation_payload.model_dump())
    assert response_ingest.status_code == 201
    
    # Search for it
    response_search = await async_client.get("/search?q=searchable&limit=10")
    assert response_search.status_code == 200
    search_data = response_search.json()
    
    assert "results" in search_data
    # We should find at least our test conversation
    assert len(search_data["results"]) >= 1


@pytest.mark.asyncio
async def test_get_conversations_list_integration(app_dependency_overrides, async_client: AsyncClient):
    """Test getting conversations list with pagination against real database."""
    # First ingest a conversation to ensure we have data
    conversation_payload = schemas.ConversationIngest(
        scenario_title="List Test Scenario", 
        original_title="List Test Original Title",
        url="https://example.com/list-test",
        messages=[
            {
                "author_name": "User1",
                "author_type": "human", 
                "content": "This is a test for the conversations list.",
                "timestamp": "2023-01-01T12:00:00Z",
            },
        ],
    )
    
    # Ingest the conversation
    response_ingest = await async_client.post("/ingest", json=conversation_payload.model_dump())
    assert response_ingest.status_code == 201
    
    # Get conversations list
    response_list = await async_client.get("/conversations?limit=10&offset=0")
    assert response_list.status_code == 200
    list_data = response_list.json()
    
    assert isinstance(list_data, list)
    # We should have at least our test conversation
    assert len(list_data) >= 1


@pytest.mark.asyncio
async def test_delete_conversation_integration(app_dependency_overrides, async_client: AsyncClient):
    """Test deleting a conversation against real database."""
    # First ingest a conversation
    conversation_payload = schemas.ConversationIngest(
        scenario_title="Delete Test Scenario", 
        original_title="Delete Test Original Title",
        url="https://example.com/delete-test",
        messages=[
            {
                "author_name": "User1",
                "author_type": "human", 
                "content": "This conversation will be deleted.",
                "timestamp": "2023-01-01T12:00:00Z",
            },
        ],
    )
    
    # Ingest the conversation
    response_ingest = await async_client.post("/ingest", json=conversation_payload.model_dump())
    assert response_ingest.status_code == 201
    conversation_id = response_ingest.json()["id"]
    
    # Verify it exists
    response_get = await async_client.get(f"/conversations/{conversation_id}")
    assert response_get.status_code == 200
    
    # Delete it
    response_delete = await async_client.delete(f"/conversations/{conversation_id}")
    assert response_delete.status_code == 200
    
    # Verify it's gone
    response_get_after = await async_client.get(f"/conversations/{conversation_id}")
    assert response_get_after.status_code == 404
