import pytest
import pytest_asyncio
import asyncio
import os
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, MagicMock

from app.main import fastapi_app
from app.database import get_db
from app.dependencies import get_embedding_service, get_conversation_processor
from app.services import EmbeddingService, ConversationProcessor


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service for testing."""
    mock = AsyncMock(spec=EmbeddingService)
    mock.dimension = 1536
    mock.model = "text-embedding-ada-002"
    # Mock embedding generation to return predictable vectors
    mock.generate_embedding.return_value = [0.1] * 1536
    mock.generate_embeddings_batch.return_value = [[0.1] * 1536, [0.2] * 1536]
    return mock


@pytest.fixture
def mock_conversation_processor(mock_embedding_service):
    """Create a mock conversation processor for testing."""
    mock = MagicMock(spec=ConversationProcessor)
    mock.embedding_service = mock_embedding_service

    # Mock the chunking and processing behavior
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


@pytest.fixture(scope="function")
def app_dependency_overrides(mock_embedding_service, mock_conversation_processor):
    """
    Fixture to override dependencies with mock services for unit testing.
    """
    fastapi_app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
    fastapi_app.dependency_overrides[get_conversation_processor] = lambda: mock_conversation_processor
    yield
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client():
    """Provide an async test client."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        yield ac
