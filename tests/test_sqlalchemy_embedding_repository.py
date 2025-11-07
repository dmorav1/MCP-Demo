"""
Unit tests for SqlAlchemyEmbeddingRepository.

Tests cover embedding storage and retrieval operations.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.persistence import (
    SqlAlchemyEmbeddingRepository, SqlAlchemyChunkRepository,
    SqlAlchemyConversationRepository
)
from app.domain.entities import Conversation, ConversationChunk
from app.domain.value_objects import (
    ConversationId, ConversationMetadata, ChunkId, ChunkText,
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
def embedding_repository(session):
    """Create embedding repository instance."""
    return SqlAlchemyEmbeddingRepository(session)


@pytest.fixture
def chunk_repository(session):
    """Create chunk repository instance."""
    return SqlAlchemyChunkRepository(session)


@pytest.fixture
def conversation_repository(session):
    """Create conversation repository instance."""
    return SqlAlchemyConversationRepository(session)


@pytest.fixture
async def saved_chunk(conversation_repository, chunk_repository):
    """Create and save a chunk for testing."""
    # First create a conversation
    metadata = ConversationMetadata(
        scenario_title="Test Conversation",
        created_at=datetime.utcnow()
    )
    conversation = Conversation(id=None, metadata=metadata, chunks=[])
    saved_conversation = await conversation_repository.save(conversation)
    
    # Create a chunk without embedding
    chunk = ConversationChunk(
        id=None,
        conversation_id=saved_conversation.id,
        text=ChunkText(content="Test chunk"),
        metadata=ChunkMetadata(
            order_index=0,
            author_info=AuthorInfo(name="User", author_type="human")
        )
    )
    saved_chunks = await chunk_repository.save_chunks([chunk])
    return saved_chunks[0]


class TestSqlAlchemyEmbeddingRepository:
    """Test suite for SqlAlchemyEmbeddingRepository."""
    
    @pytest.mark.asyncio
    async def test_store_embedding_success(self, embedding_repository, saved_chunk):
        """Test storing an embedding for a chunk."""
        # Arrange
        embedding = Embedding(vector=[0.1] * 1536)
        
        # Act
        result = await embedding_repository.store_embedding(saved_chunk.id, embedding)
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_store_embedding_nonexistent_chunk(self, embedding_repository):
        """Test storing embedding for non-existent chunk."""
        # Arrange
        embedding = Embedding(vector=[0.1] * 1536)
        
        # Act
        result = await embedding_repository.store_embedding(ChunkId(99999), embedding)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_embedding_exists(self, embedding_repository, saved_chunk):
        """Test retrieving an existing embedding."""
        # Arrange
        embedding = Embedding(vector=[0.1] * 1536)
        await embedding_repository.store_embedding(saved_chunk.id, embedding)
        
        # Act
        retrieved_embedding = await embedding_repository.get_embedding(saved_chunk.id)
        
        # Assert
        assert retrieved_embedding is not None
        assert len(retrieved_embedding.vector) == 1536
        # Compare with approximate equality due to floating point storage
        assert all(abs(a - b) < 0.001 for a, b in zip(retrieved_embedding.vector, embedding.vector))
    
    @pytest.mark.asyncio
    async def test_get_embedding_not_exists(self, embedding_repository, saved_chunk):
        """Test retrieving embedding that doesn't exist."""
        # Act
        result = await embedding_repository.get_embedding(saved_chunk.id)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_embedding_nonexistent_chunk(self, embedding_repository):
        """Test retrieving embedding for non-existent chunk."""
        # Act
        result = await embedding_repository.get_embedding(ChunkId(99999))
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_has_embedding_true(self, embedding_repository, saved_chunk):
        """Test has_embedding returns True when embedding exists."""
        # Arrange
        embedding = Embedding(vector=[0.1] * 1536)
        await embedding_repository.store_embedding(saved_chunk.id, embedding)
        
        # Act
        result = await embedding_repository.has_embedding(saved_chunk.id)
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_has_embedding_false(self, embedding_repository, saved_chunk):
        """Test has_embedding returns False when no embedding."""
        # Act
        result = await embedding_repository.has_embedding(saved_chunk.id)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_has_embedding_nonexistent_chunk(self, embedding_repository):
        """Test has_embedding for non-existent chunk."""
        # Act
        result = await embedding_repository.has_embedding(ChunkId(99999))
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_chunks_needing_embeddings_empty(self, embedding_repository):
        """Test getting chunks needing embeddings when none exist."""
        # Act
        chunk_ids = await embedding_repository.get_chunks_needing_embeddings()
        
        # Assert
        assert chunk_ids == []
    
    @pytest.mark.asyncio
    async def test_get_chunks_needing_embeddings(
        self, embedding_repository, conversation_repository, chunk_repository
    ):
        """Test retrieving chunk IDs that need embeddings."""
        # Arrange
        # Create a conversation
        metadata = ConversationMetadata(scenario_title="Test")
        conversation = Conversation(id=None, metadata=metadata, chunks=[])
        saved_conversation = await conversation_repository.save(conversation)
        
        # Create chunks: some with embeddings, some without
        chunk_with_embedding = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Chunk with embedding"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User", author_type="human")
            ),
            embedding=Embedding(vector=[0.1] * 1536)
        )
        
        chunk_without_1 = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Chunk without 1"),
            metadata=ChunkMetadata(
                order_index=1,
                author_info=AuthorInfo(name="User", author_type="human")
            )
        )
        
        chunk_without_2 = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Chunk without 2"),
            metadata=ChunkMetadata(
                order_index=2,
                author_info=AuthorInfo(name="User", author_type="human")
            )
        )
        
        saved_chunks = await chunk_repository.save_chunks([
            chunk_with_embedding, chunk_without_1, chunk_without_2
        ])
        
        # Act
        chunk_ids = await embedding_repository.get_chunks_needing_embeddings()
        
        # Assert
        assert len(chunk_ids) == 2
        chunk_id_values = [cid.value for cid in chunk_ids]
        assert saved_chunks[1].id.value in chunk_id_values
        assert saved_chunks[2].id.value in chunk_id_values
        assert saved_chunks[0].id.value not in chunk_id_values
    
    @pytest.mark.asyncio
    async def test_store_embedding_updates_existing(self, embedding_repository, saved_chunk):
        """Test that storing an embedding updates an existing one."""
        # Arrange
        embedding1 = Embedding(vector=[0.1] * 1536)
        embedding2 = Embedding(vector=[0.2] * 1536)
        
        # Store first embedding
        await embedding_repository.store_embedding(saved_chunk.id, embedding1)
        
        # Act - Store second embedding (should update)
        result = await embedding_repository.store_embedding(saved_chunk.id, embedding2)
        
        # Assert
        assert result is True
        retrieved_embedding = await embedding_repository.get_embedding(saved_chunk.id)
        # Compare with approximate equality due to floating point storage
        assert len(retrieved_embedding.vector) == 1536
        assert all(abs(a - b) < 0.001 for a, b in zip(retrieved_embedding.vector, embedding2.vector))
