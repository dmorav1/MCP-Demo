"""
Unit tests for IngestConversationUseCase

Tests cover:
- Successful ingestion workflow
- Validation errors
- Embedding generation failures
- Repository failures
- Edge cases
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List

from app.application.ingest_conversation import IngestConversationUseCase
from app.application.dto import (
    IngestConversationRequest, IngestConversationResponse, MessageDTO
)
from app.domain.entities import Conversation, ConversationChunk
from app.domain.value_objects import (
    ConversationId, ChunkId, ChunkText, Embedding, 
    AuthorInfo, ConversationMetadata, ChunkMetadata
)
from app.domain.repositories import (
    IConversationRepository, IChunkRepository, 
    IEmbeddingService, RepositoryError, EmbeddingError, ValidationError
)
from app.domain.services import (
    ConversationChunkingService, ConversationValidationService,
    EmbeddingValidationService, ChunkingParameters
)


class TestIngestConversationUseCase:
    """Test suite for IngestConversationUseCase."""
    
    @pytest.fixture
    def mock_conversation_repo(self):
        """Mock conversation repository."""
        repo = Mock(spec=IConversationRepository)
        repo.save = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_chunk_repo(self):
        """Mock chunk repository."""
        repo = Mock(spec=IChunkRepository)
        repo.save_chunks = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock(spec=IEmbeddingService)
        service.generate_embedding = AsyncMock()
        service.generate_embeddings_batch = AsyncMock()
        return service
    
    @pytest.fixture
    def chunking_service(self):
        """Real chunking service with test parameters."""
        params = ChunkingParameters(
            max_chunk_size=500,
            split_on_speaker_change=True,
            preserve_message_boundaries=True
        )
        return ConversationChunkingService(params)
    
    @pytest.fixture
    def validation_service(self):
        """Real validation service."""
        return ConversationValidationService()
    
    @pytest.fixture
    def embedding_validation_service(self):
        """Real embedding validation service."""
        return EmbeddingValidationService()
    
    @pytest.fixture
    def use_case(
        self, 
        mock_conversation_repo, 
        mock_chunk_repo,
        mock_embedding_service,
        chunking_service,
        validation_service,
        embedding_validation_service
    ):
        """Create use case with mocked dependencies."""
        return IngestConversationUseCase(
            conversation_repository=mock_conversation_repo,
            chunk_repository=mock_chunk_repo,
            embedding_service=mock_embedding_service,
            chunking_service=chunking_service,
            validation_service=validation_service,
            embedding_validation_service=embedding_validation_service
        )
    
    @pytest.fixture
    def valid_request(self):
        """Create a valid ingestion request."""
        messages = [
            MessageDTO(
                text="Hello, how can I help you?",
                author_name="Agent",
                author_type="assistant",
                timestamp=datetime(2024, 1, 1, 10, 0, 0)
            ),
            MessageDTO(
                text="I need help with my account.",
                author_name="User",
                author_type="user",
                timestamp=datetime(2024, 1, 1, 10, 1, 0)
            )
        ]
        
        return IngestConversationRequest(
            messages=messages,
            scenario_title="Customer Support",
            original_title="Account Help",
            url="https://example.com/conversation/123"
        )
    
    @pytest.mark.asyncio
    async def test_successful_ingestion(
        self, 
        use_case, 
        valid_request,
        mock_conversation_repo,
        mock_chunk_repo,
        mock_embedding_service
    ):
        """Test successful conversation ingestion."""
        # Setup mocks
        conversation_id = ConversationId(123)
        saved_conversation = Conversation(
            id=conversation_id,
            metadata=ConversationMetadata(
                scenario_title="Customer Support",
                original_title="Account Help",
                url="https://example.com/conversation/123",
                created_at=datetime.utcnow()
            ),
            chunks=[]
        )
        mock_conversation_repo.save.return_value = saved_conversation
        
        # Mock embedding generation
        embedding = Embedding([0.1] * 1536)
        mock_embedding_service.generate_embeddings_batch.return_value = [
            embedding, embedding
        ]
        
        # Mock chunk save
        chunk1 = ConversationChunk(
            id=ChunkId(1),
            conversation_id=conversation_id,
            text=ChunkText("Hello, how can I help you?"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="Agent", author_type="assistant"),
                timestamp=datetime(2024, 1, 1, 10, 0, 0)
            ),
            embedding=embedding
        )
        chunk2 = ConversationChunk(
            id=ChunkId(2),
            conversation_id=conversation_id,
            text=ChunkText("I need help with my account."),
            metadata=ChunkMetadata(
                order_index=1,
                author_info=AuthorInfo(name="User", author_type="human"),
                timestamp=datetime(2024, 1, 1, 10, 1, 0)
            ),
            embedding=embedding
        )
        mock_chunk_repo.save_chunks.return_value = [chunk1, chunk2]
        
        # Execute
        response = await use_case.execute(valid_request)
        
        # Assert
        assert response.success is True
        assert response.conversation_id == "123"
        assert response.chunks_created == 2
        assert response.error_message is None
        assert response.metadata.scenario_title == "Customer Support"
        
        # Verify mocks called
        mock_conversation_repo.save.assert_called_once()
        mock_embedding_service.generate_embeddings_batch.assert_called_once()
        mock_chunk_repo.save_chunks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_empty_messages_validation_error(self, use_case):
        """Test that empty messages list is rejected."""
        request = IngestConversationRequest(
            messages=[],
            scenario_title="Test"
        )
        
        response = await use_case.execute(request)
        
        assert response.success is False
        assert "Cannot ingest conversation with no messages" in response.error_message
        assert response.chunks_created == 0
    
    @pytest.mark.asyncio
    async def test_empty_message_text_validation_error(self, use_case):
        """Test that messages with empty text are rejected."""
        request = IngestConversationRequest(
            messages=[
                MessageDTO(text="Valid message"),
                MessageDTO(text="   "),  # Only whitespace
                MessageDTO(text="Another valid message")
            ]
        )
        
        response = await use_case.execute(request)
        
        assert response.success is False
        assert "empty text" in response.error_message.lower()
        assert response.chunks_created == 0
    
    @pytest.mark.asyncio
    async def test_embedding_generation_failure(
        self, 
        use_case, 
        valid_request,
        mock_conversation_repo,
        mock_embedding_service
    ):
        """Test handling of embedding generation failure."""
        # Setup mocks
        conversation_id = ConversationId("conv-123")
        saved_conversation = Conversation(
            id=conversation_id,
            metadata=ConversationMetadata(
                scenario_title="Test",
                source="api",
                ingested_at=datetime.utcnow()
            ),
            chunks=[]
        )
        mock_conversation_repo.save.return_value = saved_conversation
        
        # Mock embedding failure
        mock_embedding_service.generate_embeddings_batch.side_effect = Exception(
            "Embedding API unavailable"
        )
        
        # Execute
        response = await use_case.execute(valid_request)
        
        # Assert
        assert response.success is False
        assert "Embedding generation failed" in response.error_message
        assert response.chunks_created == 0
    
    @pytest.mark.asyncio
    async def test_repository_save_failure(
        self, 
        use_case, 
        valid_request,
        mock_conversation_repo
    ):
        """Test handling of repository save failure."""
        # Mock repository failure
        mock_conversation_repo.save.side_effect = RepositoryError(
            "Database connection lost"
        )
        
        # Execute
        response = await use_case.execute(valid_request)
        
        # Assert
        assert response.success is False
        assert "Ingestion failed" in response.error_message
        assert response.chunks_created == 0
    
    @pytest.mark.asyncio
    async def test_large_message_chunking(
        self, 
        use_case, 
        valid_request,
        mock_conversation_repo,
        mock_chunk_repo,
        mock_embedding_service
    ):
        """Test that large messages are properly chunked."""
        # Create a large message
        large_text = "A" * 2000  # Exceeds chunk size of 500
        request = IngestConversationRequest(
            messages=[MessageDTO(text=large_text)]
        )
        
        # Setup mocks
        conversation_id = ConversationId("conv-123")
        saved_conversation = Conversation(
            id=conversation_id,
            metadata=ConversationMetadata(source="api", ingested_at=datetime.utcnow()),
            chunks=[]
        )
        mock_conversation_repo.save.return_value = saved_conversation
        
        # Mock embeddings
        mock_embedding_service.generate_embeddings_batch.return_value = [
            Embedding([0.1] * 384) for _ in range(10)
        ]
        
        # Mock chunk save with proper return
        def save_chunks_side_effect(chunks):
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
        
        mock_chunk_repo.save_chunks.side_effect = save_chunks_side_effect
        
        # Execute
        response = await use_case.execute(request)
        
        # Assert - should create multiple chunks
        assert response.success is True
        assert response.chunks_created > 1  # Large text should be split
    
    @pytest.mark.asyncio
    async def test_metadata_preserved(
        self, 
        use_case, 
        valid_request,
        mock_conversation_repo,
        mock_chunk_repo,
        mock_embedding_service
    ):
        """Test that conversation metadata is preserved."""
        # Setup mocks
        conversation_id = ConversationId("conv-123")
        saved_conversation = Conversation(
            id=conversation_id,
            metadata=ConversationMetadata(
                scenario_title=valid_request.scenario_title,
                original_title=valid_request.original_title,
                url=valid_request.url,
                source="api",
                ingested_at=datetime.utcnow()
            ),
            chunks=[]
        )
        mock_conversation_repo.save.return_value = saved_conversation
        
        mock_embedding_service.generate_embeddings_batch.return_value = [
            Embedding([0.1] * 384), Embedding([0.2] * 384)
        ]
        
        mock_chunk_repo.save_chunks.return_value = [
            ConversationChunk(
                id=ChunkId("chunk-1"),
                conversation_id=conversation_id,
                text=ChunkText("text"),
                metadata=ChunkMetadata(order_index=0),
                embedding=Embedding([0.1] * 384)
            )
        ]
        
        # Execute
        response = await use_case.execute(valid_request)
        
        # Assert
        assert response.success is True
        assert response.metadata.scenario_title == "Customer Support"
        assert response.metadata.original_title == "Account Help"
        assert response.metadata.url == "https://example.com/conversation/123"
