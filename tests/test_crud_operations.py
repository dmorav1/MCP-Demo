import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import ConversationCRUD
from app.services import ConversationProcessor, EmbeddingService
from app import models, schemas


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    mock = AsyncMock(spec=AsyncSession)
    return mock


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    mock = AsyncMock(spec=EmbeddingService)
    mock.dimension = 1536
    mock.generate_embedding.return_value = [0.1] * 1536
    return mock


@pytest.fixture
def mock_conversation_processor(mock_embedding_service):
    """Create a mock conversation processor."""
    mock = MagicMock(spec=ConversationProcessor)
    mock.embedding_service = mock_embedding_service

    # Mock the processing method
    async def mock_process(conversation_data):
        messages = conversation_data.get("messages", [])
        chunks = []
        for i, message in enumerate(messages):
            chunks.append(
                {
                    "order_index": i,
                    "chunk_text": f"{message.get('author_name', 'Unknown')}: {message.get('content', '')}",
                    "embedding": [0.1] * 1536,
                    "author_name": message.get("author_name"),
                    "author_type": message.get("author_type"),
                    "timestamp": message.get("timestamp"),
                }
            )

        return {
            "scenario_title": conversation_data.get("scenario_title"),
            "original_title": conversation_data.get("original_title"),
            "url": conversation_data.get("url"),
            "chunks": chunks,
        }

    # Use AsyncMock for proper call tracking
    mock.process_conversation_for_ingestion = AsyncMock(side_effect=mock_process)
    return mock


@pytest.fixture
def crud_instance(mock_db_session, mock_conversation_processor):
    """Create a ConversationCRUD instance with mocked dependencies."""
    return ConversationCRUD(db=mock_db_session, processor=mock_conversation_processor)


@pytest.mark.asyncio
async def test_create_conversation(crud_instance, mock_db_session):
    """Test creating a conversation with chunks."""
    conversation_data = schemas.ConversationIngest(
        scenario_title="Test Scenario",
        original_title="Test Original",
        url="https://example.com",
        messages=[
            {
                "author_name": "User",
                "author_type": "human",
                "content": "Hello world",
                "timestamp": "2023-01-01T12:00:00Z",
            }
        ],
    )

    # Mock the database conversation object
    mock_conversation = MagicMock()
    mock_conversation.id = 1
    mock_conversation.scenario_title = "Test Scenario"

    # Configure mock behavior
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    # Mock the add behavior to assign ID when flushed
    def mock_add_side_effect(obj):
        if isinstance(obj, models.Conversation):
            obj.id = 1

    mock_db_session.add.side_effect = mock_add_side_effect

    await crud_instance.create_conversation(conversation_data)

    # Verify the processor was called
    crud_instance.processor.process_conversation_for_ingestion.assert_called_once()

    # Verify database operations
    assert mock_db_session.add.call_count == 1  # Just the conversation
    assert mock_db_session.add_all.call_count == 1  # The chunks
    assert mock_db_session.commit.call_count == 1  # Single atomic commit
    assert mock_db_session.refresh.call_count == 1  # Refresh conversation


@pytest.mark.asyncio
async def test_get_conversation(crud_instance, mock_db_session):
    """Test getting a conversation by ID."""
    conversation_id = 1

    # Mock the result
    mock_result = MagicMock()
    mock_conversation = MagicMock()
    mock_conversation.id = conversation_id
    mock_result.scalars.return_value.first.return_value = mock_conversation

    mock_db_session.execute.return_value = mock_result

    result = await crud_instance.get_conversation(conversation_id)

    # Verify database query was called
    mock_db_session.execute.assert_called_once()
    assert result == mock_conversation


@pytest.mark.asyncio
async def test_get_conversation_not_found(crud_instance, mock_db_session):
    """Test getting a non-existent conversation."""
    conversation_id = 999

    # Mock no result
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None

    mock_db_session.execute.return_value = mock_result

    result = await crud_instance.get_conversation(conversation_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_conversations_with_pagination(crud_instance, mock_db_session):
    """Test getting conversations with pagination."""
    skip = 10
    limit = 5

    # Mock conversations list
    mock_conversations = [MagicMock() for _ in range(5)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_conversations

    mock_db_session.execute.return_value = mock_result

    result = await crud_instance.get_conversations(skip=skip, limit=limit)

    # Verify database query was called
    mock_db_session.execute.assert_called_once()
    assert len(result) == 5
    assert result == mock_conversations


@pytest.mark.asyncio
async def test_search_conversations(
    crud_instance, mock_db_session, mock_embedding_service
):
    """Test searching conversations with vector similarity."""
    query = "test query"
    top_k = 3

    # Mock search results
    # Mock database rows as mappings
    mock_rows = [
        {
            "conversation_id": 1,
            "scenario_title": "Test 1",
            "original_title": "Original 1",
            "url": "https://example1.com",
            "created_at": "2023-01-01T12:00:00Z",
            "chunk_id": 1,
            "order_index": 0,
            "chunk_text": "Test chunk 1",
            "author_name": "User",
            "author_type": "human",
            "timestamp": "2023-01-01T12:00:00Z",
            "distance": 0.2,
        },
        {
            "conversation_id": 2,
            "scenario_title": "Test 2",
            "original_title": "Original 2",
            "url": "https://example2.com",
            "created_at": "2023-01-01T12:00:00Z",
            "chunk_id": 2,
            "order_index": 0,
            "chunk_text": "Test chunk 2",
            "author_name": "Assistant",
            "author_type": "ai",
            "timestamp": "2023-01-01T12:00:00Z",
            "distance": 0.3,
        },
    ]

    # Create a mock result object with mappings method
    mock_result = MagicMock()
    mock_result.mappings.return_value = [MagicMock(**row) for row in mock_rows]

    mock_db_session.execute.return_value = mock_result

    result = await crud_instance.search_conversations(query, top_k)

    # Verify embedding service was called
    mock_embedding_service.generate_embedding.assert_called_once_with(query)

    # Verify database query was called
    mock_db_session.execute.assert_called_once()

    # Verify results structure
    assert len(result) == 2
    assert result[0]["conversation_id"] == 1
    assert result[0]["relevance_score"] == 0.8  # 1.0 - 0.2
    assert result[1]["relevance_score"] == 0.7  # 1.0 - 0.3


@pytest.mark.asyncio
async def test_delete_conversation_success(crud_instance, mock_db_session):
    """Test successfully deleting a conversation."""
    conversation_id = 1

    # Mock the database execute result with rowcount
    mock_result = MagicMock()
    mock_result.rowcount = 1  # Simulate one row deleted
    mock_db_session.execute.return_value = mock_result

    result = await crud_instance.delete_conversation(conversation_id)

    # Verify database operations - should use the new atomic approach
    assert mock_db_session.execute.call_count == 1  # Only one DELETE statement
    assert mock_db_session.commit.call_count == 1

    assert result is True


@pytest.mark.asyncio
async def test_delete_conversation_not_found(crud_instance, mock_db_session):
    """Test deleting a non-existent conversation."""
    conversation_id = 999

    # Mock the database execute result with rowcount = 0 (no rows deleted)
    mock_result = MagicMock()
    mock_result.rowcount = 0  # Simulate no rows deleted
    mock_db_session.execute.return_value = mock_result

    result = await crud_instance.delete_conversation(conversation_id)

    # Verify database operations - should use the new atomic approach
    assert mock_db_session.execute.call_count == 1  # Only one DELETE statement
    assert mock_db_session.commit.call_count == 1

    assert result is False


@pytest.mark.asyncio
async def test_crud_initialization(mock_db_session, mock_conversation_processor):
    """Test that ConversationCRUD initializes correctly with dependencies."""
    crud = ConversationCRUD(db=mock_db_session, processor=mock_conversation_processor)

    assert crud.db == mock_db_session
    assert crud.processor == mock_conversation_processor
    assert crud.embedding_service == mock_conversation_processor.embedding_service
