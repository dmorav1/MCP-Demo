"""Integration tests for SqlAlchemyChunkRepository with real PostgreSQL."""
import pytest
from datetime import datetime

from app.domain.entities import ConversationChunk
from app.domain.value_objects import (
    ConversationId, ChunkId, ChunkText, ChunkMetadata,
    AuthorInfo, Embedding
)


@pytest.mark.integration
class TestChunkRepositoryIntegration:
    """Integration tests for chunk repository with real PostgreSQL."""
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_chunk(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test saving and retrieving a chunk."""
        # First create a conversation
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create a new chunk
        new_chunk = ConversationChunk(
            id=None,
            conversation_id=saved_conv.id,
            text=ChunkText(content="New chunk added later"),
            metadata=ChunkMetadata(
                order_index=10,
                author_info=AuthorInfo(name="NewUser", author_type="human"),
                timestamp=datetime.now(),
            ),
            embedding=None,
        )
        
        # Save chunk
        saved_chunk = await chunk_repository.save(new_chunk)
        
        # Verify
        assert saved_chunk.id is not None
        assert saved_chunk.conversation_id == saved_conv.id
        
        # Retrieve
        retrieved = await chunk_repository.get_by_id(saved_chunk.id)
        assert retrieved is not None
        assert retrieved.text.content == "New chunk added later"
    
    @pytest.mark.asyncio
    async def test_get_by_conversation_id(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test retrieving chunks by conversation ID."""
        # Save conversation with chunks
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Retrieve chunks by conversation ID
        chunks = await chunk_repository.get_by_conversation_id(saved_conv.id)
        
        # Verify
        assert len(chunks) == len(sample_conversation.chunks)
        
        # Verify ordering
        for i, chunk in enumerate(chunks):
            assert chunk.metadata.order_index == i
    
    @pytest.mark.asyncio
    async def test_save_chunk_with_embedding(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test saving chunk with embedding vector."""
        # Create conversation first
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create chunk with embedding
        vector = [0.5] * 1536
        chunk = ConversationChunk(
            id=None,
            conversation_id=saved_conv.id,
            text=ChunkText(content="Chunk with embedding"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User", author_type="human"),
                timestamp=datetime.now(),
            ),
            embedding=Embedding(vector=vector),
        )
        
        # Save
        saved = await chunk_repository.save(chunk)
        
        # Retrieve and verify embedding
        retrieved = await chunk_repository.get_by_id(saved.id)
        assert retrieved.embedding is not None
        assert len(retrieved.embedding.vector) == 1536
        assert all(abs(v - 0.5) < 0.001 for v in retrieved.embedding.vector)
    
    @pytest.mark.asyncio
    async def test_update_chunk_embedding(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test updating a chunk's embedding."""
        # Create conversation and chunk
        saved_conv = await conversation_repository.save(sample_conversation)
        chunk = sample_conversation.chunks[0]
        chunk.conversation_id = saved_conv.id
        
        # Save chunk without embedding
        saved_chunk = await chunk_repository.save(chunk)
        assert saved_chunk.embedding is None
        
        # Add embedding
        vector = [0.3] * 1536
        saved_chunk.embedding = Embedding(vector=vector)
        
        # Update
        updated = await chunk_repository.save(saved_chunk)
        
        # Verify embedding was added
        retrieved = await chunk_repository.get_by_id(updated.id)
        assert retrieved.embedding is not None
        assert len(retrieved.embedding.vector) == 1536
    
    @pytest.mark.asyncio
    async def test_delete_chunk(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test deleting a chunk."""
        # Create conversation
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Get first chunk ID
        chunks = await chunk_repository.get_by_conversation_id(saved_conv.id)
        chunk_id = chunks[0].id
        
        # Delete
        result = await chunk_repository.delete(chunk_id)
        assert result is True
        
        # Verify deletion
        retrieved = await chunk_repository.get_by_id(chunk_id)
        assert retrieved is None
        
        # Verify other chunks still exist
        remaining_chunks = await chunk_repository.get_by_conversation_id(saved_conv.id)
        assert len(remaining_chunks) == len(sample_conversation.chunks) - 1
    
    @pytest.mark.asyncio
    async def test_count_by_conversation(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test counting chunks for a conversation."""
        # Create conversation
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Count chunks
        count = await chunk_repository.count_by_conversation(saved_conv.id)
        
        # Verify
        assert count == len(sample_conversation.chunks)
    
    @pytest.mark.asyncio
    async def test_chunk_cascade_delete_with_conversation(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test that chunks are deleted when conversation is deleted."""
        # Create conversation with chunks
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Verify chunks exist
        chunks = await chunk_repository.get_by_conversation_id(saved_conv.id)
        assert len(chunks) > 0
        chunk_ids = [c.id for c in chunks]
        
        # Delete conversation
        await conversation_repository.delete(saved_conv.id)
        
        # Verify chunks are also deleted (cascade)
        for chunk_id in chunk_ids:
            retrieved = await chunk_repository.get_by_id(chunk_id)
            assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_edge_case_very_long_chunk_text(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test handling very long chunk text."""
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create chunk with very long text
        long_text = "A" * 50000  # 50k characters
        chunk = ConversationChunk(
            id=None,
            conversation_id=saved_conv.id,
            text=ChunkText(content=long_text),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User", author_type="human"),
                timestamp=datetime.now(),
            ),
            embedding=None,
        )
        
        # Should save successfully
        saved = await chunk_repository.save(chunk)
        
        # Should retrieve with full text
        retrieved = await chunk_repository.get_by_id(saved.id)
        assert len(retrieved.text.content) == 50000
    
    @pytest.mark.asyncio
    async def test_edge_case_special_characters_in_text(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test handling special characters in chunk text."""
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create chunk with special characters
        special_text = "Test émojis 🎉🎊 <script>alert('xss')</script> quotes: \"'`"
        chunk = ConversationChunk(
            id=None,
            conversation_id=saved_conv.id,
            text=ChunkText(content=special_text),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User with émoji 👤", author_type="human"),
                timestamp=datetime.now(),
            ),
            embedding=None,
        )
        
        # Should save and retrieve correctly
        saved = await chunk_repository.save(chunk)
        retrieved = await chunk_repository.get_by_id(saved.id)
        
        assert retrieved.text.content == special_text
        assert "👤" in retrieved.metadata.author_info.name
