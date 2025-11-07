"""
Unit tests for SqlAlchemyChunkRepository.

Tests cover chunk-specific operations with in-memory SQLite database.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.persistence import (
    SqlAlchemyChunkRepository, SqlAlchemyConversationRepository
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
def chunk_repository(session):
    """Create chunk repository instance."""
    return SqlAlchemyChunkRepository(session)


@pytest.fixture
def conversation_repository(session):
    """Create conversation repository instance."""
    return SqlAlchemyConversationRepository(session)


@pytest.fixture
async def saved_conversation(conversation_repository):
    """Create and save a conversation for testing."""
    metadata = ConversationMetadata(
        scenario_title="Test Conversation",
        created_at=datetime.utcnow()
    )
    
    conversation = Conversation(
        id=None,
        metadata=metadata,
        chunks=[]
    )
    
    return await conversation_repository.save(conversation)


class TestSqlAlchemyChunkRepository:
    """Test suite for SqlAlchemyChunkRepository."""
    
    @pytest.mark.asyncio
    async def test_save_chunks_empty_list(self, chunk_repository):
        """Test saving empty list of chunks."""
        # Act
        result = await chunk_repository.save_chunks([])
        
        # Assert
        assert result == []
    
    @pytest.mark.asyncio
    async def test_save_chunks_single(self, chunk_repository, saved_conversation):
        """Test saving a single chunk."""
        # Arrange
        chunk = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Test chunk content"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User", author_type="human"),
                timestamp=datetime.utcnow()
            )
        )
        
        # Act
        saved_chunks = await chunk_repository.save_chunks([chunk])
        
        # Assert
        assert len(saved_chunks) == 1
        assert saved_chunks[0].id is not None
        assert saved_chunks[0].text.content == "Test chunk content"
    
    @pytest.mark.asyncio
    async def test_save_chunks_batch(self, chunk_repository, saved_conversation):
        """Test batch saving multiple chunks."""
        # Arrange
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=saved_conversation.id,
                text=ChunkText(content=f"Chunk {i}"),
                metadata=ChunkMetadata(
                    order_index=i,
                    author_info=AuthorInfo(name=f"User{i}", author_type="human")
                )
            )
            for i in range(5)
        ]
        
        # Act
        saved_chunks = await chunk_repository.save_chunks(chunks)
        
        # Assert
        assert len(saved_chunks) == 5
        assert all(chunk.id is not None for chunk in saved_chunks)
        for i, chunk in enumerate(saved_chunks):
            assert chunk.text.content == f"Chunk {i}"
    
    @pytest.mark.asyncio
    async def test_get_by_conversation(self, chunk_repository, saved_conversation):
        """Test retrieving all chunks for a conversation."""
        # Arrange
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=saved_conversation.id,
                text=ChunkText(content=f"Chunk {i}"),
                metadata=ChunkMetadata(
                    order_index=i,
                    author_info=AuthorInfo(name="User", author_type="human")
                )
            )
            for i in range(3)
        ]
        await chunk_repository.save_chunks(chunks)
        
        # Act
        retrieved_chunks = await chunk_repository.get_by_conversation(saved_conversation.id)
        
        # Assert
        assert len(retrieved_chunks) == 3
        # Verify ordering
        for i, chunk in enumerate(retrieved_chunks):
            assert chunk.metadata.order_index == i
    
    @pytest.mark.asyncio
    async def test_get_by_conversation_empty(self, chunk_repository, saved_conversation):
        """Test retrieving chunks when none exist."""
        # Act
        chunks = await chunk_repository.get_by_conversation(saved_conversation.id)
        
        # Assert
        assert chunks == []
    
    @pytest.mark.asyncio
    async def test_get_by_id_existing(self, chunk_repository, saved_conversation):
        """Test retrieving an existing chunk by ID."""
        # Arrange
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
        chunk_id = saved_chunks[0].id
        
        # Act
        retrieved_chunk = await chunk_repository.get_by_id(chunk_id)
        
        # Assert
        assert retrieved_chunk is not None
        assert retrieved_chunk.id == chunk_id
        assert retrieved_chunk.text.content == "Test chunk"
    
    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(self, chunk_repository):
        """Test retrieving a non-existent chunk."""
        # Act
        result = await chunk_repository.get_by_id(ChunkId(99999))
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_embedding(self, chunk_repository, saved_conversation):
        """Test updating embedding for a chunk."""
        # Arrange
        chunk = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Chunk without embedding"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User", author_type="human")
            )
        )
        saved_chunks = await chunk_repository.save_chunks([chunk])
        chunk_id = saved_chunks[0].id
        
        embedding = Embedding(vector=[0.1] * 1536)
        
        # Act
        result = await chunk_repository.update_embedding(chunk_id, embedding)
        
        # Assert
        assert result is True
        updated_chunk = await chunk_repository.get_by_id(chunk_id)
        assert updated_chunk.embedding is not None
        assert len(updated_chunk.embedding.vector) == 1536
    
    @pytest.mark.asyncio
    async def test_update_embedding_nonexistent(self, chunk_repository):
        """Test updating embedding for non-existent chunk."""
        # Arrange
        embedding = Embedding(vector=[0.1] * 1536)
        
        # Act
        result = await chunk_repository.update_embedding(ChunkId(99999), embedding)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_chunks_without_embeddings_empty(self, chunk_repository):
        """Test getting chunks without embeddings when none exist."""
        # Act
        chunks = await chunk_repository.get_chunks_without_embeddings()
        
        # Assert
        assert chunks == []
    
    @pytest.mark.asyncio
    async def test_get_chunks_without_embeddings(self, chunk_repository, saved_conversation):
        """Test retrieving chunks without embeddings."""
        # Arrange
        # Create chunks with and without embeddings
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
        
        chunk_without_embedding1 = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Chunk without embedding 1"),
            metadata=ChunkMetadata(
                order_index=1,
                author_info=AuthorInfo(name="User", author_type="human")
            )
        )
        
        chunk_without_embedding2 = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Chunk without embedding 2"),
            metadata=ChunkMetadata(
                order_index=2,
                author_info=AuthorInfo(name="User", author_type="human")
            )
        )
        
        await chunk_repository.save_chunks([
            chunk_with_embedding,
            chunk_without_embedding1,
            chunk_without_embedding2
        ])
        
        # Act
        chunks_without_embeddings = await chunk_repository.get_chunks_without_embeddings()
        
        # Assert
        assert len(chunks_without_embeddings) == 2
        assert all(chunk.embedding is None for chunk in chunks_without_embeddings)
    
    @pytest.mark.asyncio
    async def test_save_chunks_with_embeddings(self, chunk_repository, saved_conversation):
        """Test saving chunks that already have embeddings."""
        # Arrange
        embedding = Embedding(vector=[0.1] * 1536)
        chunk = ConversationChunk(
            id=None,
            conversation_id=saved_conversation.id,
            text=ChunkText(content="Chunk with embedding"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User", author_type="human")
            ),
            embedding=embedding
        )
        
        # Act
        saved_chunks = await chunk_repository.save_chunks([chunk])
        
        # Assert
        assert len(saved_chunks) == 1
        assert saved_chunks[0].embedding is not None
        retrieved_chunk = await chunk_repository.get_by_id(saved_chunks[0].id)
        assert retrieved_chunk.embedding is not None
        assert len(retrieved_chunk.embedding.vector) == 1536
