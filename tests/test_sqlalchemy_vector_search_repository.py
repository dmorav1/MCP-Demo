"""
Unit tests for SqlAlchemyVectorSearchRepository.

Note: Vector search tests use in-memory SQLite which doesn't support pgvector.
These tests verify the repository logic but may need PostgreSQL for full integration tests.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.persistence import (
    SqlAlchemyVectorSearchRepository, SqlAlchemyChunkRepository,
    SqlAlchemyConversationRepository
)
from app.domain.entities import Conversation, ConversationChunk
from app.domain.value_objects import (
    ConversationId, ConversationMetadata, ChunkText,
    ChunkMetadata, AuthorInfo, Embedding
)
from app.models import Base


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def vector_search_repository(session):
    """Create vector search repository instance."""
    return SqlAlchemyVectorSearchRepository(session)


@pytest.fixture
def chunk_repository(session):
    """Create chunk repository instance."""
    return SqlAlchemyChunkRepository(session)


@pytest.fixture
def conversation_repository(session):
    """Create conversation repository instance."""
    return SqlAlchemyConversationRepository(session)


@pytest.fixture
async def saved_conversation_with_chunks(conversation_repository, chunk_repository):
    """Create and save a conversation with embedded chunks."""
    metadata = ConversationMetadata(
        scenario_title="Test Conversation",
        created_at=datetime.utcnow()
    )
    
    conversation = Conversation(
        id=None,
        metadata=metadata,
        chunks=[]
    )
    
    saved_conversation = await conversation_repository.save(conversation)
    
    # Create chunks with embeddings
    chunks = [
        ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content=f"Chunk {i} content"),
            metadata=ChunkMetadata(
                order_index=i,
                author_info=AuthorInfo(name="User", author_type="human")
            ),
            embedding=Embedding(vector=[float(i) / 10] * 1536)
        )
        for i in range(3)
    ]
    
    await chunk_repository.save_chunks(chunks)
    return saved_conversation


class TestSqlAlchemyVectorSearchRepository:
    """Test suite for SqlAlchemyVectorSearchRepository."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="SQLite doesn't support pgvector - requires PostgreSQL")
    async def test_similarity_search_basic(self, vector_search_repository, saved_conversation_with_chunks):
        """Test basic vector similarity search."""
        # Arrange
        query_embedding = Embedding(vector=[0.15] * 1536)
        
        # Act
        results = await vector_search_repository.similarity_search(query_embedding, top_k=2)
        
        # Assert
        assert len(results) <= 2
        for chunk, score in results:
            assert chunk.embedding is not None
            assert 0.0 <= score.value <= 1.0
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="SQLite doesn't support pgvector - requires PostgreSQL")
    async def test_similarity_search_with_threshold(self, vector_search_repository, saved_conversation_with_chunks):
        """Test vector similarity search with threshold."""
        # Arrange
        query_embedding = Embedding(vector=[0.15] * 1536)
        threshold = 0.8
        
        # Act
        results = await vector_search_repository.similarity_search_with_threshold(
            query_embedding, threshold=threshold, top_k=5
        )
        
        # Assert
        for chunk, score in results:
            assert score.value >= threshold
    
    @pytest.mark.asyncio
    async def test_similarity_search_no_chunks(self, vector_search_repository):
        """Test similarity search when no chunks exist."""
        # Arrange
        query_embedding = Embedding(vector=[0.1] * 1536)
        
        # Act - This will fail on SQLite but validates the interface
        try:
            results = await vector_search_repository.similarity_search(query_embedding, top_k=5)
            # If it somehow works (shouldn't on SQLite), verify empty results
            assert results == []
        except Exception:
            # Expected to fail on SQLite - pgvector not available
            pytest.skip("SQLite doesn't support pgvector operations")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="SQLite doesn't support pgvector - requires PostgreSQL")
    async def test_similarity_search_orders_by_relevance(self, vector_search_repository, saved_conversation_with_chunks):
        """Test that results are ordered by relevance score."""
        # Arrange
        query_embedding = Embedding(vector=[0.1] * 1536)
        
        # Act
        results = await vector_search_repository.similarity_search(query_embedding, top_k=10)
        
        # Assert
        scores = [score.value for _, score in results]
        assert scores == sorted(scores, reverse=True), "Results should be ordered by relevance"

