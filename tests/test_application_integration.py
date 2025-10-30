"""
Integration tests for Application Layer Use Cases

These tests verify the orchestration of multiple components working together,
using mock repositories but real domain services.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.application.ingest_conversation import IngestConversationUseCase
from app.application.search_conversations import SearchConversationsUseCase
from app.application.dto import (
    IngestConversationRequest, MessageDTO,
    SearchConversationRequest
)
from app.domain.entities import Conversation, ConversationChunk
from app.domain.value_objects import (
    ConversationId, ChunkId, ChunkText, Embedding,
    AuthorInfo, ConversationMetadata, ChunkMetadata, RelevanceScore
)
from app.domain.repositories import (
    IConversationRepository, IChunkRepository,
    IVectorSearchRepository, IEmbeddingService
)
from app.domain.services import (
    ConversationChunkingService, ConversationValidationService,
    EmbeddingValidationService, SearchRelevanceService,
    ChunkingParameters
)
from app.infrastructure.container import Container, ApplicationServiceProvider


class TestApplicationLayerIntegration:
    """Integration tests for application layer."""
    
    @pytest.fixture
    def container(self):
        """Create a DI container for testing."""
        return Container()
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories."""
        conversation_repo = Mock(spec=IConversationRepository)
        conversation_repo.save = AsyncMock()
        
        chunk_repo = Mock(spec=IChunkRepository)
        chunk_repo.save_chunks = AsyncMock()
        
        vector_search_repo = Mock(spec=IVectorSearchRepository)
        vector_search_repo.similarity_search = AsyncMock()
        
        embedding_service = Mock(spec=IEmbeddingService)
        embedding_service.generate_embedding = AsyncMock()
        embedding_service.generate_embeddings_batch = AsyncMock()
        
        return {
            'conversation_repo': conversation_repo,
            'chunk_repo': chunk_repo,
            'vector_search_repo': vector_search_repo,
            'embedding_service': embedding_service
        }
    
    @pytest.mark.asyncio
    async def test_ingest_then_search_workflow(self, container, mock_repositories):
        """Test complete workflow: ingest a conversation then search it."""
        # Setup container with real services and mock repositories
        container.register_singleton(
            IConversationRepository,
            instance=mock_repositories['conversation_repo']
        )
        container.register_singleton(
            IChunkRepository,
            instance=mock_repositories['chunk_repo']
        )
        container.register_singleton(
            IVectorSearchRepository,
            instance=mock_repositories['vector_search_repo']
        )
        container.register_singleton(
            IEmbeddingService,
            instance=mock_repositories['embedding_service']
        )
        
        # Register use cases
        provider = ApplicationServiceProvider()
        provider.configure_services(container)
        
        # Step 1: Ingest a conversation
        ingest_use_case = container.resolve(IngestConversationUseCase)
        
        ingest_request = IngestConversationRequest(
            messages=[
                MessageDTO(
                    text="How do I reset my password?",
                    author_name="User",
                    author_type="user"
                ),
                MessageDTO(
                    text="Click the forgot password link on the login page.",
                    author_name="Agent",
                    author_type="assistant"
                )
            ],
            scenario_title="Password Reset Support"
        )
        
        # Mock responses for ingestion
        conversation_id = ConversationId("conv-123")
        saved_conversation = Conversation(
            id=conversation_id,
            metadata=ConversationMetadata(
                scenario_title="Password Reset Support",
                source="api",
                ingested_at=datetime.utcnow()
            ),
            chunks=[]
        )
        mock_repositories['conversation_repo'].save.return_value = saved_conversation
        
        embedding = Embedding([0.1] * 384)
        mock_repositories['embedding_service'].generate_embeddings_batch.return_value = [
            embedding, embedding
        ]
        
        saved_chunks = [
            ConversationChunk(
                id=ChunkId("chunk-1"),
                conversation_id=conversation_id,
                text=ChunkText("How do I reset my password?"),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="User", author_type="user")
                ),
                embedding=embedding
            ),
            ConversationChunk(
                id=ChunkId("chunk-2"),
                conversation_id=conversation_id,
                text=ChunkText("Click the forgot password link on the login page."),
                metadata=ChunkMetadata(
                    order_index=1,
                    author_info=AuthorInfo(name="Agent", author_type="assistant")
                ),
                embedding=embedding
            )
        ]
        mock_repositories['chunk_repo'].save_chunks.return_value = saved_chunks
        
        # Execute ingestion
        ingest_response = await ingest_use_case.execute(ingest_request)
        
        assert ingest_response.success is True
        assert ingest_response.conversation_id == "conv-123"
        assert ingest_response.chunks_created == 2
        
        # Step 2: Search for the ingested conversation
        search_use_case = container.resolve(SearchConversationsUseCase)
        
        search_request = SearchConversationRequest(
            query="password reset",
            top_k=5
        )
        
        # Mock responses for search
        query_embedding = Embedding([0.15] * 384)
        mock_repositories['embedding_service'].generate_embedding.return_value = query_embedding
        
        search_results = [
            (saved_chunks[1], RelevanceScore(0.92)),  # Agent's response
            (saved_chunks[0], RelevanceScore(0.88))   # User's question
        ]
        mock_repositories['vector_search_repo'].similarity_search.return_value = search_results
        
        # Execute search
        search_response = await search_use_case.execute(search_request)
        
        assert search_response.success is True
        assert search_response.total_results == 2
        assert search_response.results[0].conversation_id == "conv-123"
        assert search_response.results[0].score == 0.92
        assert "forgot password" in search_response.results[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_dependency_injection_resolution(self, container):
        """Test that DI container properly resolves all dependencies."""
        # Setup mock repositories
        conversation_repo = Mock(spec=IConversationRepository)
        chunk_repo = Mock(spec=IChunkRepository)
        vector_search_repo = Mock(spec=IVectorSearchRepository)
        embedding_service = Mock(spec=IEmbeddingService)
        
        container.register_singleton(IConversationRepository, instance=conversation_repo)
        container.register_singleton(IChunkRepository, instance=chunk_repo)
        container.register_singleton(IVectorSearchRepository, instance=vector_search_repo)
        container.register_singleton(IEmbeddingService, instance=embedding_service)
        
        # Register application services
        provider = ApplicationServiceProvider()
        provider.configure_services(container)
        
        # Verify IngestConversationUseCase can be resolved
        ingest_use_case = container.resolve(IngestConversationUseCase)
        assert ingest_use_case is not None
        assert ingest_use_case.conversation_repo == conversation_repo
        assert ingest_use_case.chunk_repo == chunk_repo
        assert ingest_use_case.embedding_service == embedding_service
        
        # Verify SearchConversationsUseCase can be resolved
        search_use_case = container.resolve(SearchConversationsUseCase)
        assert search_use_case is not None
        assert search_use_case.vector_search_repo == vector_search_repo
        assert search_use_case.embedding_service == embedding_service
        
        # Verify domain services are injected
        assert ingest_use_case.chunking_service is not None
        assert ingest_use_case.validation_service is not None
        assert search_use_case.relevance_service is not None
    
    @pytest.mark.asyncio
    async def test_chunking_service_integration(self, container, mock_repositories):
        """Test that chunking service properly integrates with use case."""
        # Setup
        container.register_singleton(
            IConversationRepository,
            instance=mock_repositories['conversation_repo']
        )
        container.register_singleton(
            IChunkRepository,
            instance=mock_repositories['chunk_repo']
        )
        container.register_singleton(
            IEmbeddingService,
            instance=mock_repositories['embedding_service']
        )
        
        provider = ApplicationServiceProvider()
        provider.configure_services(container)
        
        ingest_use_case = container.resolve(IngestConversationUseCase)
        
        # Create request with multiple messages that should be chunked
        messages = [
            MessageDTO(text="First message from user", author_name="User"),
            MessageDTO(text="Second message from user", author_name="User"),
            MessageDTO(text="Agent response", author_name="Agent", author_type="assistant"),
        ]
        
        request = IngestConversationRequest(
            messages=messages,
            scenario_title="Test Conversation"
        )
        
        # Mock responses
        conversation_id = ConversationId("conv-123")
        saved_conversation = Conversation(
            id=conversation_id,
            metadata=ConversationMetadata(source="api", ingested_at=datetime.utcnow()),
            chunks=[]
        )
        mock_repositories['conversation_repo'].save.return_value = saved_conversation
        
        # Mock embeddings for 3 chunks
        mock_repositories['embedding_service'].generate_embeddings_batch.return_value = [
            Embedding([0.1] * 384),
            Embedding([0.2] * 384),
            Embedding([0.3] * 384)
        ]
        
        # Capture saved chunks
        saved_chunks = []
        def save_chunks_side_effect(chunks):
            saved_chunks.extend(chunks)
            return [
                ConversationChunk(
                    id=ChunkId(f"chunk-{i}"),
                    conversation_id=chunk.conversation_id,
                    text=chunk.text,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding
                )
                for i, chunk in enumerate(chunks)
            ]
        
        mock_repositories['chunk_repo'].save_chunks.side_effect = save_chunks_side_effect
        
        # Execute
        response = await ingest_use_case.execute(request)
        
        # Assert chunking occurred correctly
        assert response.success is True
        assert len(saved_chunks) >= 2  # Should create at least 2 chunks due to speaker change
        
        # Verify chunks have proper order indices
        order_indices = [chunk.metadata.order_index for chunk in saved_chunks]
        assert order_indices == sorted(order_indices)
        assert order_indices[0] == 0
    
    @pytest.mark.asyncio
    async def test_validation_service_integration(self, container, mock_repositories):
        """Test that validation service properly integrates with use case."""
        # Setup
        container.register_singleton(
            IConversationRepository,
            instance=mock_repositories['conversation_repo']
        )
        container.register_singleton(
            IChunkRepository,
            instance=mock_repositories['chunk_repo']
        )
        container.register_singleton(
            IEmbeddingService,
            instance=mock_repositories['embedding_service']
        )
        
        provider = ApplicationServiceProvider()
        provider.configure_services(container)
        
        ingest_use_case = container.resolve(IngestConversationUseCase)
        
        # Test with valid request
        valid_request = IngestConversationRequest(
            messages=[MessageDTO(text="Valid message")],
            scenario_title="Test"
        )
        
        # Mock responses
        conversation_id = ConversationId("conv-123")
        mock_repositories['conversation_repo'].save.return_value = Conversation(
            id=conversation_id,
            metadata=ConversationMetadata(source="api", ingested_at=datetime.utcnow()),
            chunks=[]
        )
        mock_repositories['embedding_service'].generate_embeddings_batch.return_value = [
            Embedding([0.1] * 384)
        ]
        mock_repositories['chunk_repo'].save_chunks.return_value = [
            ConversationChunk(
                id=ChunkId("chunk-1"),
                conversation_id=conversation_id,
                text=ChunkText("Valid message"),
                metadata=ChunkMetadata(order_index=0),
                embedding=Embedding([0.1] * 384)
            )
        ]
        
        response = await ingest_use_case.execute(valid_request)
        assert response.success is True
        
        # Test with invalid request (empty messages)
        invalid_request = IngestConversationRequest(
            messages=[MessageDTO(text="   ")],  # Only whitespace
            scenario_title="Test"
        )
        
        response = await ingest_use_case.execute(invalid_request)
        assert response.success is False
        assert "empty text" in response.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_transient_use_case_instances(self, container):
        """Test that use cases are transient (new instance per resolution)."""
        # Setup mock repositories
        conversation_repo = Mock(spec=IConversationRepository)
        chunk_repo = Mock(spec=IChunkRepository)
        embedding_service = Mock(spec=IEmbeddingService)
        
        container.register_singleton(IConversationRepository, instance=conversation_repo)
        container.register_singleton(IChunkRepository, instance=chunk_repo)
        container.register_singleton(IEmbeddingService, instance=embedding_service)
        
        provider = ApplicationServiceProvider()
        provider.configure_services(container)
        
        # Resolve use case twice
        use_case_1 = container.resolve(IngestConversationUseCase)
        use_case_2 = container.resolve(IngestConversationUseCase)
        
        # Should be different instances (transient)
        assert use_case_1 is not use_case_2
        
        # But should share the same singleton repositories
        assert use_case_1.conversation_repo is use_case_2.conversation_repo
        assert use_case_1.chunk_repo is use_case_2.chunk_repo
