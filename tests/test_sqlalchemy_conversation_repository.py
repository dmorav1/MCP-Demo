"""
Unit tests for SqlAlchemyConversationRepository.

Tests cover all repository operations with in-memory SQLite database.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.persistence import SqlAlchemyConversationRepository
from app.domain.entities import Conversation, ConversationChunk
from app.domain.value_objects import (
    ConversationId, ConversationMetadata, ChunkText, 
    ChunkMetadata, AuthorInfo, Embedding
)
from app.domain.repositories import RepositoryError
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
def repository(session):
    """Create repository instance."""
    return SqlAlchemyConversationRepository(session)


@pytest.fixture
def sample_conversation():
    """Create sample conversation entity."""
    metadata = ConversationMetadata(
        scenario_title="Test Conversation",
        original_title="Original Title",
        url="https://example.com/conversation",
        created_at=datetime.utcnow()
    )
    
    chunks = [
        ConversationChunk(
            id=None,
            conversation_id=ConversationId(1),
            text=ChunkText(content="First chunk content"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User1", author_type="human"),
                timestamp=datetime.utcnow()
            ),
            embedding=None
        ),
        ConversationChunk(
            id=None,
            conversation_id=ConversationId(1),
            text=ChunkText(content="Second chunk content"),
            metadata=ChunkMetadata(
                order_index=1,
                author_info=AuthorInfo(name="Bot", author_type="assistant"),
                timestamp=datetime.utcnow()
            ),
            embedding=None
        )
    ]
    
    return Conversation(
        id=None,
        metadata=metadata,
        chunks=chunks
    )


class TestSqlAlchemyConversationRepository:
    """Test suite for SqlAlchemyConversationRepository."""
    
    @pytest.mark.asyncio
    async def test_save_new_conversation(self, repository, sample_conversation):
        """Test saving a new conversation."""
        # Act
        saved_conversation = await repository.save(sample_conversation)
        
        # Assert
        assert saved_conversation.id is not None
        assert saved_conversation.id.value > 0
        assert saved_conversation.metadata.scenario_title == "Test Conversation"
        assert len(saved_conversation.chunks) == 2
        assert all(chunk.id is not None for chunk in saved_conversation.chunks)
    
    @pytest.mark.asyncio
    async def test_save_updates_existing_conversation(self, repository, sample_conversation):
        """Test updating an existing conversation."""
        # Arrange
        saved_conversation = await repository.save(sample_conversation)
        conversation_id = saved_conversation.id
        
        # Modify conversation
        updated_metadata = ConversationMetadata(
            scenario_title="Updated Title",
            original_title=saved_conversation.metadata.original_title,
            url=saved_conversation.metadata.url,
            created_at=saved_conversation.metadata.created_at
        )
        updated_conversation = Conversation(
            id=conversation_id,
            metadata=updated_metadata,
            chunks=saved_conversation.chunks
        )
        
        # Act
        result = await repository.save(updated_conversation)
        
        # Assert
        assert result.id == conversation_id
        assert result.metadata.scenario_title == "Updated Title"
    
    @pytest.mark.asyncio
    async def test_get_by_id_existing(self, repository, sample_conversation):
        """Test retrieving an existing conversation by ID."""
        # Arrange
        saved_conversation = await repository.save(sample_conversation)
        
        # Act
        retrieved_conversation = await repository.get_by_id(saved_conversation.id)
        
        # Assert
        assert retrieved_conversation is not None
        assert retrieved_conversation.id == saved_conversation.id
        assert retrieved_conversation.metadata.scenario_title == saved_conversation.metadata.scenario_title
        assert len(retrieved_conversation.chunks) == len(saved_conversation.chunks)
    
    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(self, repository):
        """Test retrieving a non-existent conversation."""
        # Act
        result = await repository.get_by_id(ConversationId(99999))
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_empty(self, repository):
        """Test retrieving all conversations when none exist."""
        # Act
        conversations = await repository.get_all()
        
        # Assert
        assert conversations == []
    
    @pytest.mark.asyncio
    async def test_get_all_with_conversations(self, repository, sample_conversation):
        """Test retrieving all conversations."""
        # Arrange
        await repository.save(sample_conversation)
        
        # Create another conversation
        metadata2 = ConversationMetadata(
            scenario_title="Second Conversation",
            original_title="Original 2",
            url="https://example.com/conversation2"
        )
        conversation2 = Conversation(
            id=None,
            metadata=metadata2,
            chunks=[
                ConversationChunk(
                    id=None,
                    conversation_id=ConversationId(2),
                    text=ChunkText(content="Content"),
                    metadata=ChunkMetadata(
                        order_index=0,
                        author_info=AuthorInfo(name="User", author_type="human")
                    )
                )
            ]
        )
        await repository.save(conversation2)
        
        # Act
        conversations = await repository.get_all()
        
        # Assert
        assert len(conversations) == 2
    
    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, sample_conversation):
        """Test pagination in get_all."""
        # Arrange
        for i in range(5):
            metadata = ConversationMetadata(scenario_title=f"Conversation {i}")
            conversation = Conversation(
                id=None,
                metadata=metadata,
                chunks=[
                    ConversationChunk(
                        id=None,
                        conversation_id=ConversationId(i + 1),
                        text=ChunkText(content=f"Content {i}"),
                        metadata=ChunkMetadata(
                            order_index=0,
                            author_info=AuthorInfo(name="User", author_type="human")
                        )
                    )
                ]
            )
            await repository.save(conversation)
        
        # Act
        page1 = await repository.get_all(skip=0, limit=2)
        page2 = await repository.get_all(skip=2, limit=2)
        
        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
    
    @pytest.mark.asyncio
    async def test_delete_existing_conversation(self, repository, sample_conversation):
        """Test deleting an existing conversation."""
        # Arrange
        saved_conversation = await repository.save(sample_conversation)
        
        # Act
        result = await repository.delete(saved_conversation.id)
        
        # Assert
        assert result is True
        deleted_conversation = await repository.get_by_id(saved_conversation.id)
        assert deleted_conversation is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, repository):
        """Test deleting a non-existent conversation."""
        # Act
        result = await repository.delete(ConversationId(99999))
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_exists_true(self, repository, sample_conversation):
        """Test exists returns True for existing conversation."""
        # Arrange
        saved_conversation = await repository.save(sample_conversation)
        
        # Act
        result = await repository.exists(saved_conversation.id)
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, repository):
        """Test exists returns False for non-existent conversation."""
        # Act
        result = await repository.exists(ConversationId(99999))
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_count_empty(self, repository):
        """Test count returns 0 when no conversations exist."""
        # Act
        count = await repository.count()
        
        # Assert
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_count_with_conversations(self, repository, sample_conversation):
        """Test count returns correct number of conversations."""
        # Arrange
        await repository.save(sample_conversation)
        
        metadata2 = ConversationMetadata(scenario_title="Second")
        conversation2 = Conversation(
            id=None,
            metadata=metadata2,
            chunks=[
                ConversationChunk(
                    id=None,
                    conversation_id=ConversationId(2),
                    text=ChunkText(content="Content"),
                    metadata=ChunkMetadata(
                        order_index=0,
                        author_info=AuthorInfo(name="User", author_type="human")
                    )
                )
            ]
        )
        await repository.save(conversation2)
        
        # Act
        count = await repository.count()
        
        # Assert
        assert count == 2
    
    @pytest.mark.asyncio
    async def test_save_conversation_with_embeddings(self, repository):
        """Test saving conversation with chunks that have embeddings."""
        # Arrange
        embedding = Embedding(vector=[0.1] * 1536)
        metadata = ConversationMetadata(scenario_title="With Embeddings")
        
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(1),
                text=ChunkText(content="Chunk with embedding"),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="User", author_type="human")
                ),
                embedding=embedding
            )
        ]
        
        conversation = Conversation(
            id=None,
            metadata=metadata,
            chunks=chunks
        )
        
        # Act
        saved_conversation = await repository.save(conversation)
        retrieved_conversation = await repository.get_by_id(saved_conversation.id)
        
        # Assert
        assert retrieved_conversation.chunks[0].embedding is not None
        assert len(retrieved_conversation.chunks[0].embedding.vector) == 1536
