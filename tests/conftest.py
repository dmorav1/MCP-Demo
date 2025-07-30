import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.database import get_db
from app.dependencies import get_embedding_service, get_conversation_processor
from app.services import EmbeddingService, ConversationProcessor

# Test database URL using asyncpg
TEST_DATABASE_URL = (
    "postgresql+asyncpg://test_user:test_password@localhost:5432/test_mcp_db"
)

# Create async engine for testing
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Create async session factory
TestAsyncSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def async_db_session():
    """Create a mock async database session for testing."""
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock common database operations
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.flush.return_value = None
    mock_session.refresh.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None

    # Mock execute to return empty results by default
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    return mock_session


@pytest.fixture
def override_get_db(async_db_session):
    """Override the get_db dependency to use test database."""

    async def _override_get_db():
        yield async_db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


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


@pytest.fixture
def override_dependencies(
    mock_embedding_service, mock_conversation_processor, async_db_session
):
    """Override dependency injection for testing."""
    from app.dependencies import get_conversation_crud

    # Override service dependencies
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
    app.dependency_overrides[get_conversation_processor] = (
        lambda: mock_conversation_processor
    )

    # Override CRUD dependency
    def mock_get_crud():
        from app.crud import ConversationCRUD

        return ConversationCRUD(
            db=async_db_session, processor=mock_conversation_processor
        )

    app.dependency_overrides[get_conversation_crud] = mock_get_crud

    yield

    # Clean up overrides
    app.dependency_overrides.pop(get_embedding_service, None)
    app.dependency_overrides.pop(get_conversation_processor, None)
    app.dependency_overrides.pop(get_conversation_crud, None)


@pytest_asyncio.fixture
async def async_client():
    """Provide an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
