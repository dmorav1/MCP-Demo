"""Shared fixtures for integration tests.

This module provides fixtures for:
- PostgreSQL testcontainer with pgvector extension
- Database sessions and repositories
- Test data generators
- Embedding services
"""
import os
import pytest
from datetime import datetime
from typing import Generator, List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from testcontainers.postgres import PostgresContainer

from app.models import Base
from app.domain.entities import Conversation, ConversationChunk
from app.domain.value_objects import (
    ConversationId, ConversationMetadata, ChunkId, ChunkText,
    ChunkMetadata, AuthorInfo, Embedding
)
from app.adapters.outbound.persistence import (
    SqlAlchemyConversationRepository,
    SqlAlchemyChunkRepository,
    SqlAlchemyEmbeddingRepository,
    SqlAlchemyVectorSearchRepository
)
from app.logging_config import get_logger

logger = get_logger(__name__)


# PostgreSQL testcontainer fixture (session scope for performance)
@pytest.fixture(scope="session")
def postgres_container():
    """
    Start a PostgreSQL container with pgvector extension.
    
    Uses session scope to reuse container across all integration tests.
    """
    logger.info("🐳 Starting PostgreSQL testcontainer with pgvector...")
    
    # Use pgvector/pgvector image
    postgres = PostgresContainer(
        image="pgvector/pgvector:pg15",
        username="test_user",
        password="test_password",
        dbname="test_db",
    )
    
    postgres.start()
    logger.info(f"✅ PostgreSQL testcontainer started: {postgres.get_connection_url()}")
    
    yield postgres
    
    logger.info("🛑 Stopping PostgreSQL testcontainer...")
    postgres.stop()


@pytest.fixture(scope="session")
def postgres_url(postgres_container) -> str:
    """Get PostgreSQL connection URL from container."""
    # Convert to psycopg3 format
    url = postgres_container.get_connection_url()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@pytest.fixture(scope="session")
def engine(postgres_url):
    """
    Create SQLAlchemy engine connected to testcontainer.
    
    Session-scoped engine is reused across tests for performance.
    """
    logger.info(f"🔗 Creating database engine: {postgres_url}")
    
    engine = create_engine(
        postgres_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    
    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        logger.info("✅ pgvector extension enabled")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database schema created")
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    """
    Provide a clean database session for each test.
    
    Uses transaction rollback for isolation between tests.
    """
    connection = engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        expire_on_commit=False
    )
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


# Repository fixtures
@pytest.fixture
def conversation_repository(db_session):
    """Create conversation repository instance."""
    return SqlAlchemyConversationRepository(db_session)


@pytest.fixture
def chunk_repository(db_session):
    """Create chunk repository instance."""
    return SqlAlchemyChunkRepository(db_session)


@pytest.fixture
def embedding_repository(db_session):
    """Create embedding repository instance."""
    return SqlAlchemyEmbeddingRepository(db_session)


@pytest.fixture
def vector_search_repository(db_session):
    """Create vector search repository instance."""
    return SqlAlchemyVectorSearchRepository(db_session)


# Test data generators
@pytest.fixture
def sample_conversation_metadata():
    """Generate sample conversation metadata."""
    return ConversationMetadata(
        scenario_title="Integration Test Conversation",
        original_title="Original Test Title",
        url="https://test.example.com/conversation",
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_chunks() -> List[ConversationChunk]:
    """Generate sample conversation chunks."""
    chunks = []
    for i in range(3):
        chunk = ConversationChunk(
            id=None,
            conversation_id=ConversationId(1),
            text=ChunkText(content=f"Test chunk content {i}. This is a sample message."),
            metadata=ChunkMetadata(
                order_index=i,
                author_info=AuthorInfo(
                    name=f"User{i % 2}",
                    author_type="human" if i % 2 == 0 else "assistant",
                ),
                timestamp=datetime.now(),
            ),
            embedding=None,
        )
        chunks.append(chunk)
    return chunks


@pytest.fixture
def sample_conversation(sample_conversation_metadata, sample_chunks):
    """Generate sample conversation entity."""
    return Conversation(
        id=None,
        metadata=sample_conversation_metadata,
        chunks=sample_chunks,
    )


@pytest.fixture
def sample_conversation_with_embeddings(sample_conversation_metadata):
    """Generate conversation with embedding vectors."""
    chunks = []
    for i in range(3):
        # Create test embedding vector (1536 dimensions)
        vector = [float(i * 0.1)] * 1536
        embedding = Embedding(vector=vector)
        
        chunk = ConversationChunk(
            id=None,
            conversation_id=ConversationId(1),
            text=ChunkText(content=f"Test chunk with embedding {i}"),
            metadata=ChunkMetadata(
                order_index=i,
                author_info=AuthorInfo(name=f"User{i}", author_type="human"),
                timestamp=datetime.now(),
            ),
            embedding=embedding,
        )
        chunks.append(chunk)
    
    return Conversation(
        id=None,
        metadata=sample_conversation_metadata,
        chunks=chunks,
    )


@pytest.fixture
def realistic_conversation():
    """Generate realistic conversation from sample data format."""
    metadata = ConversationMetadata(
        scenario_title="Customer Support Chat - Product Issue",
        original_title="Help with Mobile App Crashes",
        url="https://support.example.com/chat/12345",
        created_at=datetime.fromisoformat("2024-01-15T10:30:00"),
    )
    
    messages = [
        ("John Doe", "human", "Hi, I'm having trouble with your mobile app. It keeps crashing every time I try to open the settings page."),
        ("Sarah (Support)", "human", "Hello John! I'm sorry to hear you're experiencing crashes with our mobile app. I'd be happy to help you resolve this issue."),
        ("John Doe", "human", "I'm using an iPhone 13 with iOS 17.2. The app was working fine until last week."),
        ("Sarah (Support)", "human", "This sounds like it could be related to a known issue. Let's try force-closing the app and restarting it."),
        ("John Doe", "human", "I've tried that already, but it still crashes when I tap on Settings."),
    ]
    
    chunks = []
    for i, (author, author_type, content) in enumerate(messages):
        chunk = ConversationChunk(
            id=None,
            conversation_id=ConversationId(1),
            text=ChunkText(content=content),
            metadata=ChunkMetadata(
                order_index=i,
                author_info=AuthorInfo(name=author, author_type=author_type),
                timestamp=datetime.now(),
            ),
            embedding=None,
        )
        chunks.append(chunk)
    
    return Conversation(
        id=None,
        metadata=metadata,
        chunks=chunks,
    )


@pytest.fixture
def edge_case_conversations():
    """Generate edge case test conversations."""
    conversations = []
    
    # Empty conversation (no chunks)
    conv1 = Conversation(
        id=None,
        metadata=ConversationMetadata(
            scenario_title="Empty Conversation",
            original_title="No Messages",
            url="https://test.com/empty",
            created_at=datetime.now(),
        ),
        chunks=[],
    )
    conversations.append(conv1)
    
    # Very long text
    long_text = "Lorem ipsum " * 500  # ~5500 characters
    conv2 = Conversation(
        id=None,
        metadata=ConversationMetadata(
            scenario_title="Long Text Conversation",
            original_title="Large Content",
            url="https://test.com/long",
            created_at=datetime.now(),
        ),
        chunks=[
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(1),
                text=ChunkText(content=long_text),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=None,
            )
        ],
    )
    conversations.append(conv2)
    
    # Special characters
    conv3 = Conversation(
        id=None,
        metadata=ConversationMetadata(
            scenario_title="Special Characters Test 🚀",
            original_title="Émojis and Spëcial Cháracters",
            url="https://test.com/special?param=value&other=123",
            created_at=datetime.now(),
        ),
        chunks=[
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(1),
                text=ChunkText(content="Test with émojis 🎉🎊 and spëcial cháracters: <>&\"'"),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="Tëst Usér 👤", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=None,
            )
        ],
    )
    conversations.append(conv3)
    
    return conversations


# Performance testing helpers
@pytest.fixture
def many_conversations(sample_conversation_metadata):
    """Generate many conversations for load testing."""
    conversations = []
    for i in range(100):
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(i + 1),
                text=ChunkText(content=f"Conversation {i} - Chunk {j}"),
                metadata=ChunkMetadata(
                    order_index=j,
                    author_info=AuthorInfo(name=f"User{j}", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=None,
            )
            for j in range(5)
        ]
        
        conv = Conversation(
            id=None,
            metadata=ConversationMetadata(
                scenario_title=f"Test Conversation {i}",
                original_title=f"Original {i}",
                url=f"https://test.com/conv/{i}",
                created_at=datetime.now(),
            ),
            chunks=chunks,
        )
        conversations.append(conv)
    
    return conversations
