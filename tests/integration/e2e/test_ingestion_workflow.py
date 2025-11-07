"""End-to-end integration tests for conversation ingestion workflow."""
import pytest
from datetime import datetime

from app.application.ingest_conversation import IngestConversationUseCase
from app.application.dto import ConversationDTO, MessageDTO
from app.adapters.outbound.embeddings.local_embedding_service import LocalEmbeddingService
from app.domain.value_objects import STANDARD_EMBEDDING_DIMENSION


@pytest.mark.integration
@pytest.mark.slow
class TestIngestionWorkflowE2E:
    """End-to-end tests for complete ingestion workflow."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create real embedding service."""
        return LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
            target_dimension=STANDARD_EMBEDDING_DIMENSION
        )
    
    @pytest.fixture
    def use_case(self, conversation_repository, chunk_repository, embedding_service):
        """Create ingestion use case with real dependencies."""
        return IngestConversationUseCase(
            conversation_repository=conversation_repository,
            chunk_repository=chunk_repository,
            embedding_service=embedding_service,
        )
    
    @pytest.mark.asyncio
    async def test_complete_ingestion_workflow(self, use_case, conversation_repository):
        """Test complete workflow from DTO to database with embeddings."""
        # Create input DTO (simulating API request)
        dto = ConversationDTO(
            scenario_title="E2E Test Conversation",
            original_title="Original E2E Title",
            url="https://test.com/e2e",
            messages=[
                MessageDTO(
                    author_name="User1",
                    author_type="human",
                    content="Hello, I need help with my account.",
                    timestamp=datetime.now().isoformat(),
                ),
                MessageDTO(
                    author_name="Support",
                    author_type="human",
                    content="Of course! I'd be happy to help you with your account.",
                    timestamp=datetime.now().isoformat(),
                ),
                MessageDTO(
                    author_name="User1",
                    author_type="human",
                    content="I can't log in. I keep getting an error message.",
                    timestamp=datetime.now().isoformat(),
                ),
            ],
        )
        
        # Execute ingestion
        result = await use_case.execute(dto)
        
        # Verify result
        assert result.success is True
        assert result.conversation_id is not None
        assert result.chunks_created == 3
        
        # Verify conversation was saved
        from app.domain.value_objects import ConversationId
        conv_id = ConversationId(int(result.conversation_id))
        saved_conv = await conversation_repository.get_by_id(conv_id)
        
        assert saved_conv is not None
        assert saved_conv.metadata.scenario_title == "E2E Test Conversation"
        assert len(saved_conv.chunks) == 3
        
        # Verify embeddings were generated
        for chunk in saved_conv.chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding.vector) == STANDARD_EMBEDDING_DIMENSION
            # Verify not all zeros
            assert any(v != 0.0 for v in chunk.embedding.vector)
    
    @pytest.mark.asyncio
    async def test_ingestion_with_realistic_conversation(
        self, use_case, conversation_repository
    ):
        """Test ingestion with realistic customer support conversation."""
        dto = ConversationDTO(
            scenario_title="Customer Support - Mobile App Issue",
            original_title="App Crashes on Settings",
            url="https://support.example.com/chat/12345",
            messages=[
                MessageDTO(
                    author_name="John Doe",
                    author_type="human",
                    content="Hi, I'm having trouble with your mobile app. It keeps crashing every time I try to open the settings page.",
                    timestamp="2024-01-15T10:30:00Z",
                ),
                MessageDTO(
                    author_name="Sarah (Support)",
                    author_type="human",
                    content="Hello John! I'm sorry to hear you're experiencing crashes with our mobile app. I'd be happy to help you resolve this issue. Can you tell me which device and operating system version you're using?",
                    timestamp="2024-01-15T10:31:00Z",
                ),
                MessageDTO(
                    author_name="John Doe",
                    author_type="human",
                    content="I'm using an iPhone 13 with iOS 17.2. The app was working fine until last week when I updated it to the latest version.",
                    timestamp="2024-01-15T10:32:30Z",
                ),
            ],
        )
        
        # Execute ingestion
        result = await use_case.execute(dto)
        
        # Verify success
        assert result.success is True
        assert result.chunks_created == 3
        
        # Verify content preservation
        from app.domain.value_objects import ConversationId
        conv_id = ConversationId(int(result.conversation_id))
        saved_conv = await conversation_repository.get_by_id(conv_id)
        
        assert "iPhone 13" in saved_conv.chunks[2].text.content
        assert "Sarah (Support)" in saved_conv.chunks[1].metadata.author_info.name
    
    @pytest.mark.asyncio
    async def test_ingestion_preserves_message_order(
        self, use_case, conversation_repository
    ):
        """Test that message order is preserved through ingestion."""
        messages = []
        for i in range(10):
            messages.append(
                MessageDTO(
                    author_name=f"User{i % 2}",
                    author_type="human",
                    content=f"Message number {i}",
                    timestamp=datetime.now().isoformat(),
                )
            )
        
        dto = ConversationDTO(
            scenario_title="Order Test",
            original_title="Test",
            url="https://test.com",
            messages=messages,
        )
        
        result = await use_case.execute(dto)
        
        # Verify order
        from app.domain.value_objects import ConversationId
        conv_id = ConversationId(int(result.conversation_id))
        saved_conv = await conversation_repository.get_by_id(conv_id)
        
        for i, chunk in enumerate(saved_conv.chunks):
            assert chunk.metadata.order_index == i
            assert f"Message number {i}" in chunk.text.content
    
    @pytest.mark.asyncio
    async def test_ingestion_with_special_characters(
        self, use_case, conversation_repository
    ):
        """Test ingestion handles special characters correctly."""
        dto = ConversationDTO(
            scenario_title="Special Characters Test 🚀",
            original_title="Émojis and Spëcial Cháracters",
            url="https://test.com/special",
            messages=[
                MessageDTO(
                    author_name="User with émoji 👤",
                    author_type="human",
                    content="Test with émojis 🎉🎊 and spëcial cháracters: <>&\"'",
                    timestamp=datetime.now().isoformat(),
                ),
            ],
        )
        
        result = await use_case.execute(dto)
        
        # Verify success and preservation
        assert result.success is True
        
        from app.domain.value_objects import ConversationId
        conv_id = ConversationId(int(result.conversation_id))
        saved_conv = await conversation_repository.get_by_id(conv_id)
        
        assert "🎉" in saved_conv.chunks[0].text.content
        assert "👤" in saved_conv.chunks[0].metadata.author_info.name
    
    @pytest.mark.asyncio
    async def test_ingestion_error_handling(self, use_case):
        """Test error handling in ingestion workflow."""
        # Create invalid DTO (empty messages)
        dto = ConversationDTO(
            scenario_title="Test",
            original_title="Test",
            url="https://test.com",
            messages=[],
        )
        
        # Should handle gracefully
        result = await use_case.execute(dto)
        
        # May succeed with 0 chunks or fail gracefully
        # Either way, should not raise unhandled exception
        assert result is not None


@pytest.mark.integration
@pytest.mark.slow
class TestIngestionPerformance:
    """Performance tests for ingestion workflow."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create embedding service."""
        return LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
            target_dimension=STANDARD_EMBEDDING_DIMENSION
        )
    
    @pytest.fixture
    def use_case(self, conversation_repository, chunk_repository, embedding_service):
        """Create use case."""
        return IngestConversationUseCase(
            conversation_repository=conversation_repository,
            chunk_repository=chunk_repository,
            embedding_service=embedding_service,
        )
    
    @pytest.mark.asyncio
    async def test_ingestion_performance(self, use_case):
        """Test ingestion performance with realistic conversation."""
        import time
        
        # Create realistic-sized conversation (10 messages)
        messages = []
        for i in range(10):
            messages.append(
                MessageDTO(
                    author_name=f"User{i % 2}",
                    author_type="human",
                    content=f"This is message number {i} with some realistic content that a user might type in a support conversation.",
                    timestamp=datetime.now().isoformat(),
                )
            )
        
        dto = ConversationDTO(
            scenario_title="Performance Test",
            original_title="Test",
            url="https://test.com/perf",
            messages=messages,
        )
        
        # Measure time
        start_time = time.time()
        result = await use_case.execute(dto)
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 10 seconds for 10 messages)
        assert elapsed < 10.0
        assert result.success is True
        
        print(f"\n⏱️  Ingested 10-message conversation in {elapsed:.2f}s ({elapsed/10:.2f}s per message)")
