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
    async def test_save_and_retrieve_chunks(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test saving and retrieving chunks."""
        # First create a conversation
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create new chunks to add
        new_chunks = [
            ConversationChunk(
                id=None,
                conversation_id=saved_conv.id,
                text=ChunkText(content="New chunk 1"),
                metadata=ChunkMetadata(
                    order_index=10,
                    author_info=AuthorInfo(name="NewUser", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=None,
            ),
            ConversationChunk(
                id=None,
                conversation_id=saved_conv.id,
                text=ChunkText(content="New chunk 2"),
                metadata=ChunkMetadata(
                    order_index=11,
                    author_info=AuthorInfo(name="NewUser", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=None,
            ),
        ]
        
        # Save chunks in batch
        saved_chunks = await chunk_repository.save_chunks(new_chunks)
        
        # Verify
        assert len(saved_chunks) == 2
        assert all(chunk.id is not None for chunk in saved_chunks)
        
        # Retrieve by conversation
        all_chunks = await chunk_repository.get_by_conversation(saved_conv.id)
        # Should include original chunks + new chunks
        assert len(all_chunks) >= 2
    
    @pytest.mark.asyncio
    async def test_get_by_conversation(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test retrieving chunks by conversation ID."""
        # Save conversation with chunks
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Retrieve chunks by conversation ID
        chunks = await chunk_repository.get_by_conversation(saved_conv.id)
        
        # Verify
        assert len(chunks) == len(sample_conversation.chunks)
        
        # Verify ordering
        for i, chunk in enumerate(chunks):
            assert chunk.metadata.order_index == i
    
    @pytest.mark.asyncio
    async def test_save_chunks_with_embeddings(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test saving chunks with embedding vectors."""
        # Create conversation first
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create chunks with embeddings
        vector = [0.5] * 1536
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=saved_conv.id,
                text=ChunkText(content=f"Chunk with embedding {i}"),
                metadata=ChunkMetadata(
                    order_index=100 + i,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=Embedding(vector=vector),
            )
            for i in range(3)
        ]
        
        # Save
        saved_chunks = await chunk_repository.save_chunks(chunks)
        
        # Retrieve and verify embeddings
        for saved_chunk in saved_chunks:
            retrieved = await chunk_repository.get_by_id(saved_chunk.id)
            assert retrieved.embedding is not None
            assert len(retrieved.embedding.vector) == 1536
            assert all(abs(v - 0.5) < 0.001 for v in retrieved.embedding.vector)
    
    @pytest.mark.asyncio
    async def test_update_chunk_embedding(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test updating a chunk's embedding."""
        # Create conversation and chunks
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Get first chunk
        chunks = await chunk_repository.get_by_conversation(saved_conv.id)
        chunk = chunks[0]
        
        # Initially should have no embedding (from sample_conversation)
        assert chunk.embedding is None
        
        # Update embedding
        vector = [0.3] * 1536
        embedding = Embedding(vector=vector)
        result = await chunk_repository.update_embedding(chunk.id, embedding)
        
        assert result is True
        
        # Verify embedding was added
        retrieved = await chunk_repository.get_by_id(chunk.id)
        assert retrieved.embedding is not None
        assert len(retrieved.embedding.vector) == 1536
    
    @pytest.mark.asyncio
    async def test_get_chunks_without_embeddings(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test retrieving chunks that don't have embeddings."""
        # Save conversation (chunks have no embeddings)
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Get chunks without embeddings
        chunks_no_emb = await chunk_repository.get_chunks_without_embeddings()
        
        # Should include at least our chunks
        assert len(chunks_no_emb) >= len(sample_conversation.chunks)
        
        # Add embedding to one chunk
        chunks = await chunk_repository.get_by_conversation(saved_conv.id)
        if chunks:
            vector = [0.1] * 1536
            await chunk_repository.update_embedding(chunks[0].id, Embedding(vector=vector))
        
        # Get chunks without embeddings again
        chunks_no_emb_after = await chunk_repository.get_chunks_without_embeddings()
        
        # Should have one fewer
        assert len(chunks_no_emb_after) < len(chunks_no_emb)
    
    @pytest.mark.asyncio
    async def test_chunk_cascade_delete_with_conversation(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test that chunks are deleted when conversation is deleted."""
        # Create conversation with chunks
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Verify chunks exist
        chunks = await chunk_repository.get_by_conversation(saved_conv.id)
        assert len(chunks) > 0
        chunk_ids = [c.id for c in chunks]
        
        # Delete conversation
        await conversation_repository.delete(saved_conv.id)
        
        # Verify chunks are also deleted (cascade)
        for chunk_id in chunk_ids:
            retrieved = await chunk_repository.get_by_id(chunk_id)
            assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_edge_case_max_length_chunk_text(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test handling of chunk text at maximum length (10000 chars)."""
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create chunk with text at max length (10000 chars)
        max_text = "A" * 9999  # Just under limit
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=saved_conv.id,
                text=ChunkText(content=max_text),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=None,
            )
        ]
        
        # Should save successfully
        saved_chunks = await chunk_repository.save_chunks(chunks)
        assert len(saved_chunks) == 1
        
        # Should retrieve with full text
        retrieved = await chunk_repository.get_by_id(saved_chunks[0].id)
        assert len(retrieved.text.content) == 9999
    
    @pytest.mark.asyncio
    async def test_edge_case_special_characters_in_text(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test handling special characters in chunk text."""
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create chunk with special characters
        special_text = "Test émojis 🎉🎊 <script>alert('xss')</script> quotes: \"'`"
        chunks = [
            ConversationChunk(
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
        ]
        
        # Should save and retrieve correctly
        saved_chunks = await chunk_repository.save_chunks(chunks)
        retrieved = await chunk_repository.get_by_id(saved_chunks[0].id)
        
        assert retrieved.text.content == special_text
        assert "👤" in retrieved.metadata.author_info.name
    
    @pytest.mark.asyncio
    async def test_batch_save_performance(
        self, chunk_repository, conversation_repository, sample_conversation
    ):
        """Test performance of batch chunk saving."""
        import time
        
        saved_conv = await conversation_repository.save(sample_conversation)
        
        # Create 50 chunks
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=saved_conv.id,
                text=ChunkText(content=f"Batch chunk {i}"),
                metadata=ChunkMetadata(
                    order_index=i,
                    author_info=AuthorInfo(name=f"User{i}", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=None,
            )
            for i in range(50)
        ]
        
        # Measure batch save time
        start_time = time.time()
        saved_chunks = await chunk_repository.save_chunks(chunks)
        elapsed = time.time() - start_time
        
        # Should complete quickly (< 2 seconds for 50 chunks)
        assert elapsed < 2.0
        assert len(saved_chunks) == 50
        
        print(f"\n⏱️  Saved 50 chunks in batch in {elapsed:.3f}s ({elapsed/50:.4f}s per chunk)")
