import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
from app.main import app
from app.dependencies import get_conversation_crud
from app import schemas


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


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
async def test_ingest_conversation():
    """Test conversation ingestion with mocked dependencies."""
    # Create mock CRUD that returns a successful result
    mock_crud = AsyncMock()

    class MockConversation:
        def __init__(self):
            self.id = 1
            self.scenario_title = "Test Scenario"
            self.original_title = "Test Original Title"
            self.url = "https://example.com/test"
            self.created_at = "2023-01-01T12:00:00Z"
            self.chunks = []

    mock_crud.create_conversation.return_value = MockConversation()

    # Override dependencies
    app.dependency_overrides[get_conversation_crud] = lambda: mock_crud

    try:
        conversation_payload = schemas.ConversationIngest(
            scenario_title="Test Scenario",
            original_title="Test Original Title",
            url="https://example.com/test",
            messages=[
                {
                    "author_name": "User1",
                    "author_type": "human",
                    "content": "Hello, this is a test message.",
                    "timestamp": "2023-01-01T12:00:00Z",
                },
                {
                    "author_name": "Assistant",
                    "author_type": "ai",
                    "content": "Hello! How can I help you today?",
                    "timestamp": "2023-01-01T12:00:30Z",
                },
            ],
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/ingest", json=conversation_payload.model_dump())

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["scenario_title"] == "Test Scenario"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_conversation_crud, None)


@pytest.mark.asyncio
async def test_search_conversations():
    """Test conversation search with mocked dependencies."""
    # Create mock CRUD that returns a search result
    mock_crud = AsyncMock()

    # Mock search result in the format expected by search_conversations method
    mock_search_result = {
        "conversation_id": 1,
        "scenario_title": "Test Scenario",
        "original_title": "Test Original Title",
        "url": "https://example.com/test",
        "created_at": "2023-01-01T12:00:00Z",
        "chunk_id": 1,
        "order_index": 0,
        "chunk_text": "Test content",
        "author_name": "Test Author",
        "author_type": "human",
        "timestamp": "2023-01-01T12:00:00Z",
        "relevance_score": 0.95,  # High relevance score (calculated as 1.0 - distance)
    }

    mock_crud.search_conversations.return_value = [mock_search_result]

    # Override dependencies
    app.dependency_overrides[get_conversation_crud] = lambda: mock_crud

    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/search?q=test")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["conversation"]["scenario_title"] == "Test Scenario"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_conversation_crud, None)


@pytest.mark.asyncio
async def test_get_conversations():
    """Test getting conversations list with pagination."""
    # Create mock CRUD that returns conversations
    mock_crud = AsyncMock()

    class MockConversation:
        def __init__(self):
            self.id = 1
            self.scenario_title = "Test"
            self.original_title = "Test Original"
            self.url = "https://example.com/test"
            self.created_at = "2023-01-01T12:00:00Z"
            self.chunks = []

    mock_crud.get_conversations.return_value = [MockConversation()]

    # Override dependencies
    app.dependency_overrides[get_conversation_crud] = lambda: mock_crud

    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/conversations")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test pagination parameters
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/conversations?skip=0&limit=10")
        assert response.status_code == 200

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_conversation_crud, None)


@pytest.mark.asyncio
async def test_get_specific_conversation():
    """Test getting a specific conversation by ID."""
    # Create mock CRUD that returns a specific conversation
    mock_crud = AsyncMock()

    # Create proper mock conversation object with attributes
    class MockConversation:
        def __init__(self):
            self.id = 123
            self.scenario_title = "Specific Test"
            self.original_title = "Specific Test Original"
            self.url = "https://example.com/specific"
            self.created_at = "2023-01-01T12:00:00Z"
            self.message_count = 1
            self.chunks = []

    mock_conversation = MockConversation()

    # Mock create for the initial ingest
    mock_crud.create_conversation.return_value = mock_conversation
    # Mock get for retrieving by ID
    mock_crud.get_conversation.return_value = mock_conversation

    # Override dependencies
    app.dependency_overrides[get_conversation_crud] = lambda: mock_crud

    try:
        # First ingest a conversation
        conversation_payload = schemas.ConversationIngest(
            scenario_title="Specific Test",
            original_title="Specific Test Original",
            url="https://example.com/specific",
            messages=[
                {
                    "author_name": "User",
                    "author_type": "human",
                    "content": "This is a specific test message.",
                    "timestamp": "2023-01-01T12:00:00Z",
                }
            ],
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            ingest_response = await ac.post(
                "/ingest", json=conversation_payload.model_dump()
            )
        assert ingest_response.status_code == 201
        conversation_id = ingest_response.json()["id"]

        # Get the specific conversation
        async with AsyncClient(app=app, base_url="http://test") as ac:
            get_response = await ac.get(f"/conversations/{conversation_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == conversation_id
        assert data["scenario_title"] == "Specific Test"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_conversation_crud, None)


@pytest.mark.asyncio
async def test_get_nonexistent_conversation():
    """Test getting a non-existent conversation returns 404."""
    # Create mock CRUD that returns None for non-existent conversation
    mock_crud = AsyncMock()
    mock_crud.get_conversation.return_value = None

    # Override dependencies
    app.dependency_overrides[get_conversation_crud] = lambda: mock_crud

    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/conversations/99999")
        assert response.status_code == 404

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_conversation_crud, None)


@pytest.mark.asyncio
async def test_delete_conversation():
    """Test deleting a conversation."""
    # Create mock CRUD
    mock_crud = AsyncMock()

    class MockConversation:
        def __init__(self):
            self.id = 456
            self.scenario_title = "Delete Test"
            self.original_title = "Delete Test Original"
            self.url = "https://example.com/delete"
            self.created_at = "2023-01-01T12:00:00Z"
            self.chunks = []

    mock_conversation = MockConversation()

    # Mock behaviors
    mock_crud.create_conversation.return_value = mock_conversation
    mock_crud.delete_conversation.return_value = True

    # Override dependencies
    app.dependency_overrides[get_conversation_crud] = lambda: mock_crud

    try:
        # First ingest a conversation
        conversation_payload = schemas.ConversationIngest(
            scenario_title="Delete Test",
            original_title="Delete Test Original",
            url="https://example.com/delete",
            messages=[
                {
                    "author_name": "User",
                    "author_type": "human",
                    "content": "This conversation will be deleted.",
                    "timestamp": "2023-01-01T12:00:00Z",
                }
            ],
        )

        async with AsyncClient(app=app, base_url="http://test") as ac:
            ingest_response = await ac.post(
                "/ingest", json=conversation_payload.model_dump()
            )
        assert ingest_response.status_code == 201
        conversation_id = ingest_response.json()["id"]

        # Delete the conversation
        async with AsyncClient(app=app, base_url="http://test") as ac:
            delete_response = await ac.delete(f"/conversations/{conversation_id}")
        assert delete_response.status_code == 200

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_conversation_crud, None)


@pytest.mark.asyncio
async def test_delete_nonexistent_conversation():
    """Test deleting a non-existent conversation returns 404."""
    # Create mock CRUD that returns False for non-existent conversation
    mock_crud = AsyncMock()
    mock_crud.delete_conversation.return_value = False

    # Override dependencies
    app.dependency_overrides[get_conversation_crud] = lambda: mock_crud

    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.delete("/conversations/99999")
        assert response.status_code == 404

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_conversation_crud, None)


@pytest.mark.asyncio
async def test_search_validation_errors():
    """Test search endpoint validation."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test without query parameter
        response = await ac.get("/search")
    assert response.status_code == 422  # Validation error

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test with invalid top_k (too low)
        response = await ac.get("/search?q=test&top_k=0")
    assert response.status_code == 422  # Validation error

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test with invalid top_k (too high)
        response = await ac.get("/search?q=test&top_k=100")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_conversations_pagination_validation():
    """Test conversations endpoint pagination validation."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test with invalid skip (negative)
        response = await ac.get("/conversations?skip=-1")
    assert response.status_code == 422

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test with invalid limit (too high)
        response = await ac.get("/conversations?limit=2000")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_validation_errors():
    """Test ingestion endpoint validation."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test with missing required fields
        response = await ac.post("/ingest", json={})
        assert response.status_code == 422

        # Test with invalid message structure
        invalid_data = {
            "scenario_title": "Test",
            "messages": ["invalid_message_format"],
        }
        response = await ac.post("/ingest", json=invalid_data)
        assert response.status_code == 422
