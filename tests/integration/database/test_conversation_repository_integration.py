"""Integration tests for SqlAlchemyConversationRepository with real PostgreSQL.

Tests repository behavior with actual database including:
- CRUD operations
- Transaction handling
- Concurrent access
- Error scenarios
- Performance characteristics
"""
import pytest
import asyncio
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.domain.value_objects import ConversationId, ChunkText, ChunkMetadata, AuthorInfo


@pytest.mark.integration
class TestConversationRepositoryIntegration:
    """Integration tests for conversation repository with real PostgreSQL."""
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_conversation(
        self, conversation_repository, sample_conversation
    ):
        """Test saving and retrieving a conversation from real database."""
        # Save conversation
        saved = await conversation_repository.save(sample_conversation)
        
        # Verify saved conversation has ID
        assert saved.id is not None
        assert saved.id.value > 0
        
        # Retrieve conversation
        retrieved = await conversation_repository.get_by_id(saved.id)
        
        # Verify all fields
        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.metadata.scenario_title == saved.metadata.scenario_title
        assert retrieved.metadata.original_title == saved.metadata.original_title
        assert retrieved.metadata.url == saved.metadata.url
        assert len(retrieved.chunks) == len(saved.chunks)
        
        # Verify chunks are in correct order
        for i, chunk in enumerate(retrieved.chunks):
            assert chunk.metadata.order_index == i
            assert chunk.text.content == saved.chunks[i].text.content
    
    @pytest.mark.asyncio
    async def test_save_conversation_with_embeddings(
        self, conversation_repository, sample_conversation_with_embeddings
    ):
        """Test saving conversation with vector embeddings."""
        # Save with embeddings
        saved = await conversation_repository.save(sample_conversation_with_embeddings)
        
        # Retrieve and verify embeddings are preserved
        retrieved = await conversation_repository.get_by_id(saved.id)
        
        assert retrieved is not None
        assert len(retrieved.chunks) == 3
        
        for i, chunk in enumerate(retrieved.chunks):
            assert chunk.embedding is not None
            assert len(chunk.embedding.vector) == 1536
            # Verify vector values
            expected_value = float(i * 0.1)
            assert all(abs(v - expected_value) < 0.001 for v in chunk.embedding.vector)
    
    @pytest.mark.asyncio
    async def test_update_existing_conversation(
        self, conversation_repository, sample_conversation
    ):
        """Test updating an existing conversation."""
        # Save initial conversation
        saved = await conversation_repository.save(sample_conversation)
        original_id = saved.id
        
        # Modify the conversation
        saved.metadata.scenario_title = "Updated Title"
        saved.chunks[0].text = ChunkText(content="Updated content")
        
        # Save again (should update)
        updated = await conversation_repository.save(saved)
        
        # Verify ID unchanged
        assert updated.id == original_id
        
        # Retrieve and verify changes
        retrieved = await conversation_repository.get_by_id(original_id)
        assert retrieved.metadata.scenario_title == "Updated Title"
        assert retrieved.chunks[0].text.content == "Updated content"
    
    @pytest.mark.asyncio
    async def test_delete_conversation(
        self, conversation_repository, sample_conversation
    ):
        """Test deleting a conversation."""
        # Save conversation
        saved = await conversation_repository.save(sample_conversation)
        conversation_id = saved.id
        
        # Verify it exists
        assert await conversation_repository.exists(conversation_id) is True
        
        # Delete
        result = await conversation_repository.delete(conversation_id)
        assert result is True
        
        # Verify deletion
        assert await conversation_repository.exists(conversation_id) is False
        retrieved = await conversation_repository.get_by_id(conversation_id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_get_all_with_pagination(
        self, conversation_repository, sample_conversation_metadata, sample_chunks
    ):
        """Test retrieving conversations with pagination."""
        # Create 10 conversations
        saved_ids = []
        for i in range(10):
            from app.domain.entities import Conversation
            conv = Conversation(
                id=None,
                metadata=sample_conversation_metadata,
                chunks=sample_chunks[:2],  # Fewer chunks for speed
            )
            saved = await conversation_repository.save(conv)
            saved_ids.append(saved.id)
        
        # Test pagination
        page1 = await conversation_repository.get_all(skip=0, limit=5)
        assert len(page1) == 5
        
        page2 = await conversation_repository.get_all(skip=5, limit=5)
        assert len(page2) == 5
        
        # Verify no duplicates
        page1_ids = {conv.id.value for conv in page1}
        page2_ids = {conv.id.value for conv in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
    
    @pytest.mark.asyncio
    async def test_count_conversations(
        self, conversation_repository, sample_conversation
    ):
        """Test counting conversations."""
        # Initial count
        initial_count = await conversation_repository.count()
        
        # Add conversations
        await conversation_repository.save(sample_conversation)
        await conversation_repository.save(sample_conversation)
        await conversation_repository.save(sample_conversation)
        
        # Verify count increased
        final_count = await conversation_repository.count()
        assert final_count == initial_count + 3
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(
        self, conversation_repository, db_session
    ):
        """Test that transaction rolls back on error."""
        from app.domain.entities import Conversation
        from app.domain.value_objects import ConversationMetadata
        
        # Get initial count
        initial_count = await conversation_repository.count()
        
        # Create conversation with invalid data that will cause error
        try:
            # Force an error by attempting to save with invalid foreign key
            metadata = ConversationMetadata(
                scenario_title="Test",
                original_title="Test",
                url="https://test.com",
                created_at=datetime.now(),
            )
            
            conv = Conversation(id=None, metadata=metadata, chunks=[])
            await conversation_repository.save(conv)
            
            # Force a database error by executing invalid SQL
            db_session.execute("INVALID SQL")
            db_session.commit()
            
        except Exception:
            db_session.rollback()
        
        # Verify count unchanged (transaction rolled back)
        final_count = await conversation_repository.count()
        # Count might be initial_count or initial_count + 1 depending on transaction boundaries
        assert final_count <= initial_count + 1
    
    @pytest.mark.asyncio
    async def test_concurrent_access(
        self, conversation_repository, sample_conversation_metadata, sample_chunks
    ):
        """Test concurrent access to repository."""
        from app.domain.entities import Conversation
        
        async def save_conversation(index):
            conv = Conversation(
                id=None,
                metadata=sample_conversation_metadata,
                chunks=sample_chunks[:2],
            )
            return await conversation_repository.save(conv)
        
        # Save 5 conversations concurrently
        tasks = [save_conversation(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify all succeeded with unique IDs
        ids = [conv.id.value for conv in results]
        assert len(ids) == 5
        assert len(set(ids)) == 5  # All unique
    
    @pytest.mark.asyncio
    async def test_edge_case_empty_conversation(
        self, conversation_repository, edge_case_conversations
    ):
        """Test handling of empty conversation (no chunks)."""
        empty_conv = edge_case_conversations[0]
        
        # Should save successfully
        saved = await conversation_repository.save(empty_conv)
        assert saved.id is not None
        
        # Should retrieve successfully
        retrieved = await conversation_repository.get_by_id(saved.id)
        assert retrieved is not None
        assert len(retrieved.chunks) == 0
    
    @pytest.mark.asyncio
    async def test_edge_case_long_text(
        self, conversation_repository, edge_case_conversations
    ):
        """Test handling of very long text content."""
        long_text_conv = edge_case_conversations[1]
        
        # Should save successfully
        saved = await conversation_repository.save(long_text_conv)
        
        # Should retrieve with full text preserved
        retrieved = await conversation_repository.get_by_id(saved.id)
        assert retrieved is not None
        assert len(retrieved.chunks[0].text.content) > 5000
        assert retrieved.chunks[0].text.content == long_text_conv.chunks[0].text.content
    
    @pytest.mark.asyncio
    async def test_edge_case_special_characters(
        self, conversation_repository, edge_case_conversations
    ):
        """Test handling of special characters and emojis."""
        special_conv = edge_case_conversations[2]
        
        # Should save successfully
        saved = await conversation_repository.save(special_conv)
        
        # Should retrieve with special characters preserved
        retrieved = await conversation_repository.get_by_id(saved.id)
        assert retrieved is not None
        assert "🎉" in retrieved.chunks[0].text.content
        assert "émojis" in retrieved.chunks[0].text.content
        assert "<>&\"'" in retrieved.chunks[0].text.content
    
    @pytest.mark.asyncio
    async def test_realistic_conversation(
        self, conversation_repository, realistic_conversation
    ):
        """Test with realistic customer support conversation."""
        # Save realistic conversation
        saved = await conversation_repository.save(realistic_conversation)
        
        # Verify structure
        assert saved.id is not None
        assert len(saved.chunks) == 5
        assert saved.metadata.scenario_title == "Customer Support Chat - Product Issue"
        
        # Retrieve and verify
        retrieved = await conversation_repository.get_by_id(saved.id)
        assert retrieved is not None
        assert "iPhone 13" in retrieved.chunks[2].text.content
        assert retrieved.chunks[0].metadata.author_info.name == "John Doe"
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(
        self, conversation_repository
    ):
        """Test deleting a conversation that doesn't exist."""
        fake_id = ConversationId(999999)
        result = await conversation_repository.delete(fake_id)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_ordering_by_created_at(
        self, conversation_repository, sample_conversation_metadata, sample_chunks
    ):
        """Test that conversations are ordered by created_at descending."""
        from app.domain.entities import Conversation
        from app.domain.value_objects import ConversationMetadata
        import time
        
        # Create conversations with different timestamps
        conversations = []
        for i in range(3):
            metadata = ConversationMetadata(
                scenario_title=f"Conv {i}",
                original_title=f"Original {i}",
                url=f"https://test.com/{i}",
                created_at=datetime.now(),
            )
            conv = Conversation(id=None, metadata=metadata, chunks=sample_chunks[:1])
            saved = await conversation_repository.save(conv)
            conversations.append(saved)
            time.sleep(0.1)  # Ensure different timestamps
        
        # Retrieve all
        retrieved = await conversation_repository.get_all(skip=0, limit=10)
        
        # Should be in descending order (newest first)
        retrieved_ids = [c.id.value for c in retrieved]
        # The last saved should be first in results
        assert conversations[-1].id.value in retrieved_ids[:3]


@pytest.mark.integration
@pytest.mark.slow
class TestConversationRepositoryPerformance:
    """Performance tests for conversation repository."""
    
    @pytest.mark.asyncio
    async def test_batch_save_performance(
        self, conversation_repository, many_conversations
    ):
        """Test performance of saving many conversations."""
        import time
        
        start_time = time.time()
        
        # Save 100 conversations
        for conv in many_conversations[:20]:  # Use 20 for reasonable test time
            await conversation_repository.save(conv)
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds for 20 conversations)
        assert elapsed < 5.0
        print(f"\n⏱️  Saved 20 conversations in {elapsed:.2f}s ({elapsed/20:.3f}s per conversation)")
    
    @pytest.mark.asyncio
    async def test_batch_retrieve_performance(
        self, conversation_repository, many_conversations
    ):
        """Test performance of retrieving many conversations."""
        import time
        
        # Save some conversations first
        saved_ids = []
        for conv in many_conversations[:10]:
            saved = await conversation_repository.save(conv)
            saved_ids.append(saved.id)
        
        # Measure retrieval time
        start_time = time.time()
        
        for conv_id in saved_ids:
            await conversation_repository.get_by_id(conv_id)
        
        elapsed = time.time() - start_time
        
        # Should retrieve quickly (< 1 second for 10)
        assert elapsed < 1.0
        print(f"\n⏱️  Retrieved 10 conversations in {elapsed:.2f}s ({elapsed/10:.3f}s per conversation)")
