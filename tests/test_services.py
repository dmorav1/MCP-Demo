import pytest
from unittest.mock import AsyncMock, patch
from app.services import EmbeddingService, ConversationProcessor
from app.dependencies import (
    get_embedding_service,
    get_conversation_processor,
    get_conversation_crud,
)


@pytest.mark.asyncio
async def test_embedding_service_initialization():
    """Test EmbeddingService initialization with parameters."""
    service = EmbeddingService(api_key="test_key", model="test-model", dimension=512)

    assert service.model == "test-model"
    assert service.dimension == 512
    assert service.client is not None


@pytest.mark.asyncio
async def test_embedding_service_generate_embedding():
    """Test embedding generation."""
    with patch("app.services.AsyncOpenAI") as mock_openai:
        # Mock the OpenAI client response
        mock_response = AsyncMock()
        mock_response.data = [AsyncMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]

        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = EmbeddingService(api_key="test_key", model="test-model", dimension=3)

        result = await service.generate_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once_with(
            model="test-model", input="test text"
        )


@pytest.mark.asyncio
async def test_embedding_service_error_fallback():
    """Test that embedding service returns fallback vector on error."""
    with patch("app.services.AsyncOpenAI") as mock_openai:
        # Mock the OpenAI client to raise an exception
        mock_client = AsyncMock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        service = EmbeddingService(api_key="test_key", model="test-model", dimension=3)

        result = await service.generate_embedding("test text")

        # Should return zero vector fallback
        assert result == [0.0, 0.0, 0.0]


@pytest.mark.asyncio
async def test_embedding_service_batch_generation():
    """Test batch embedding generation."""
    with patch("app.services.AsyncOpenAI") as mock_openai:
        # Mock the OpenAI client response for batch
        mock_response = AsyncMock()
        mock_response.data = [AsyncMock(), AsyncMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        mock_response.data[1].embedding = [0.4, 0.5, 0.6]

        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = EmbeddingService(api_key="test_key", model="test-model", dimension=3)

        texts = ["text1", "text2"]
        result = await service.generate_embeddings_batch(texts)

        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_client.embeddings.create.assert_called_once_with(
            model="test-model", input=texts
        )


def test_conversation_processor_initialization():
    """Test ConversationProcessor initialization."""
    mock_embedding_service = AsyncMock()
    processor = ConversationProcessor(embedding_service=mock_embedding_service)

    assert processor.embedding_service == mock_embedding_service


def test_conversation_processor_chunking():
    """Test conversation chunking logic."""
    mock_embedding_service = AsyncMock()
    processor = ConversationProcessor(embedding_service=mock_embedding_service)

    messages = [
        {
            "author_name": "User1",
            "author_type": "human",
            "content": "Short message",
            "timestamp": "2023-01-01T12:00:00Z",
        },
        {
            "author_name": "User2",
            "author_type": "human",
            "content": "Another short message",
            "timestamp": "2023-01-01T12:01:00Z",
        },
    ]

    chunks = processor.chunk_conversation(messages, max_chunk_size=100)

    assert len(chunks) >= 1
    assert chunks[0]["order_index"] == 0
    assert chunks[0]["author_name"] == "User2"  # Should use last message's author
    assert "User1: Short message" in chunks[0]["chunk_text"]


@pytest.mark.asyncio
async def test_conversation_processor_full_processing():
    """Test full conversation processing including embedding generation."""
    with patch("app.services.AsyncOpenAI") as mock_openai:
        # Mock OpenAI client
        mock_response = AsyncMock()
        mock_response.data = [AsyncMock()]
        mock_response.data[0].embedding = [0.1] * 1536

        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        embedding_service = EmbeddingService(
            api_key="test_key", model="test-model", dimension=1536
        )
        processor = ConversationProcessor(embedding_service=embedding_service)

        conversation_data = {
            "scenario_title": "Test Scenario",
            "original_title": "Test Original",
            "url": "https://example.com",
            "messages": [
                {
                    "author_name": "User",
                    "author_type": "human",
                    "content": "Hello world",
                    "timestamp": "2023-01-01T12:00:00Z",
                }
            ],
        }

        result = await processor.process_conversation_for_ingestion(conversation_data)

        assert result["scenario_title"] == "Test Scenario"
        assert result["original_title"] == "Test Original"
        assert result["url"] == "https://example.com"
        assert len(result["chunks"]) == 1
        assert result["chunks"][0]["embedding"] == [0.1] * 1536


def test_dependency_injection_embedding_service():
    """Test that dependency injection returns singleton embedding service."""
    # Mock settings
    with patch("app.dependencies.settings") as mock_settings:
        mock_settings.openai_api_key = "test_key"
        mock_settings.embedding_model = "test-model"
        mock_settings.embedding_dimension = 1536

        # Clear the lru_cache to ensure fresh instance
        get_embedding_service.cache_clear()

        service1 = get_embedding_service()
        service2 = get_embedding_service()

        # Should be the same instance due to lru_cache
        assert service1 is service2
        assert service1.model == "test-model"
        assert service1.dimension == 1536


def test_dependency_injection_conversation_processor():
    """Test conversation processor dependency injection."""
    mock_embedding_service = AsyncMock()

    # Test the function directly
    processor = get_conversation_processor(embedding_service=mock_embedding_service)

    assert processor.embedding_service == mock_embedding_service


@pytest.mark.asyncio
async def test_dependency_injection_crud():
    """Test CRUD dependency injection."""
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_db = AsyncMock(spec=AsyncSession)
    mock_processor = AsyncMock()

    crud = get_conversation_crud(db=mock_db, processor=mock_processor)

    assert crud.db == mock_db
    assert crud.processor == mock_processor
