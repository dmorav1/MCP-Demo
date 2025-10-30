"""
Unit tests for SearchConversationsUseCase

Tests cover:
- Successful search workflow
- Query validation
- Embedding generation
- Result filtering and ranking
- Edge cases
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.application.search_conversations import SearchConversationsUseCase
from app.application.dto import (
    SearchConversationRequest, SearchConversationResponse,
    SearchFilters
)
from app.domain.entities import ConversationChunk
from app.domain.value_objects import (
    ConversationId, ChunkId, ChunkText, Embedding,
    AuthorInfo, ChunkMetadata, RelevanceScore
)
from app.domain.repositories import (
    IVectorSearchRepository, IEmbeddingService,
    RepositoryError, EmbeddingError, ValidationError
)
from app.domain.services import SearchRelevanceService


class TestSearchConversationsUseCase:
    """Test suite for SearchConversationsUseCase."""
    
    @pytest.fixture
    def mock_vector_search_repo(self):
        """Mock vector search repository."""
        repo = Mock(spec=IVectorSearchRepository)
        repo.similarity_search = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock(spec=IEmbeddingService)
        service.generate_embedding = AsyncMock()
        return service
    
    @pytest.fixture
    def relevance_service(self):
        """Real relevance service."""
        return SearchRelevanceService()
    
    @pytest.fixture
    def use_case(
        self, 
        mock_vector_search_repo,
        mock_embedding_service,
        relevance_service
    ):
        """Create use case with mocked dependencies."""
        return SearchConversationsUseCase(
            vector_search_repository=mock_vector_search_repo,
            embedding_service=mock_embedding_service,
            relevance_service=relevance_service
        )
    
    @pytest.fixture
    def valid_search_request(self):
        """Create a valid search request."""
        return SearchConversationRequest(
            query="How do I reset my password?",
            top_k=5
        )
    
    @pytest.fixture
    def sample_chunks(self):
        """Create sample conversation chunks for testing."""
        conv_id = ConversationId("conv-123")
        
        chunks = [
            ConversationChunk(
                id=ChunkId("chunk-1"),
                conversation_id=conv_id,
                text=ChunkText("To reset your password, click the forgot password link."),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="Agent", author_type="assistant"),
                    timestamp=datetime(2024, 1, 1, 10, 0, 0)
                ),
                embedding=Embedding([0.1] * 384)
            ),
            ConversationChunk(
                id=ChunkId("chunk-2"),
                conversation_id=conv_id,
                text=ChunkText("You can also reset your password from the settings page."),
                metadata=ChunkMetadata(
                    order_index=1,
                    author_info=AuthorInfo(name="Agent", author_type="assistant"),
                    timestamp=datetime(2024, 1, 1, 10, 1, 0)
                ),
                embedding=Embedding([0.2] * 384)
            ),
            ConversationChunk(
                id=ChunkId("chunk-3"),
                conversation_id=ConversationId("conv-456"),
                text=ChunkText("I can't remember my password."),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="User", author_type="user"),
                    timestamp=datetime(2024, 1, 2, 14, 30, 0)
                ),
                embedding=Embedding([0.3] * 384)
            )
        ]
        
        return chunks
    
    @pytest.mark.asyncio
    async def test_successful_search(
        self, 
        use_case,
        valid_search_request,
        sample_chunks,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test successful search workflow."""
        # Setup mocks
        query_embedding = Embedding([0.15] * 384)
        mock_embedding_service.generate_embedding.return_value = query_embedding
        
        # Mock search results with scores
        search_results = [
            (sample_chunks[0], RelevanceScore(0.95)),
            (sample_chunks[1], RelevanceScore(0.87)),
            (sample_chunks[2], RelevanceScore(0.72))
        ]
        mock_vector_search_repo.similarity_search.return_value = search_results
        
        # Execute
        response = await use_case.execute(valid_search_request)
        
        # Assert
        assert response.success is True
        assert response.total_results == 3
        assert len(response.results) == 3
        assert response.query == "How do I reset my password?"
        assert response.error_message is None
        assert response.execution_time_ms > 0
        
        # Verify results are properly converted to DTOs
        assert response.results[0].chunk_id == "chunk-1"
        assert response.results[0].score == 0.95
        assert "reset your password" in response.results[0].text.lower()
        
        # Verify mocks called
        mock_embedding_service.generate_embedding.assert_called_once_with(
            "How do I reset my password?"
        )
        mock_vector_search_repo.similarity_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_empty_query_validation(self, use_case):
        """Test that empty query is rejected."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            SearchConversationRequest(query="", top_k=5)
    
    @pytest.mark.asyncio
    async def test_whitespace_query_validation(self, use_case):
        """Test that whitespace-only query is rejected."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            SearchConversationRequest(query="   ", top_k=5)
    
    @pytest.mark.asyncio
    async def test_invalid_top_k_validation(self, use_case):
        """Test that invalid top_k values are rejected."""
        with pytest.raises(ValueError, match="top_k must be at least 1"):
            SearchConversationRequest(query="test", top_k=0)
        
        with pytest.raises(ValueError, match="top_k cannot exceed 100"):
            SearchConversationRequest(query="test", top_k=150)
    
    @pytest.mark.asyncio
    async def test_query_too_long_validation(
        self, 
        use_case,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test that excessively long queries are rejected."""
        long_query = "A" * 10001  # Exceeds 10000 char limit
        request = SearchConversationRequest(query=long_query, top_k=5)
        
        response = await use_case.execute(request)
        
        assert response.success is False
        assert "exceeds maximum length" in response.error_message
    
    @pytest.mark.asyncio
    async def test_embedding_generation_failure(
        self, 
        use_case,
        valid_search_request,
        mock_embedding_service
    ):
        """Test handling of embedding generation failure."""
        mock_embedding_service.generate_embedding.side_effect = Exception(
            "Embedding service unavailable"
        )
        
        response = await use_case.execute(valid_search_request)
        
        assert response.success is False
        assert "Query embedding generation failed" in response.error_message
        assert response.total_results == 0
    
    @pytest.mark.asyncio
    async def test_search_repository_failure(
        self, 
        use_case,
        valid_search_request,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test handling of vector search repository failure."""
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        mock_vector_search_repo.similarity_search.side_effect = RepositoryError(
            "Database connection failed"
        )
        
        response = await use_case.execute(valid_search_request)
        
        assert response.success is False
        assert "Search operation failed" in response.error_message
        assert response.total_results == 0
    
    @pytest.mark.asyncio
    async def test_no_results_found(
        self, 
        use_case,
        valid_search_request,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test search with no results."""
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        mock_vector_search_repo.similarity_search.return_value = []
        
        response = await use_case.execute(valid_search_request)
        
        assert response.success is True
        assert response.total_results == 0
        assert len(response.results) == 0
    
    @pytest.mark.asyncio
    async def test_filter_by_min_score(
        self, 
        use_case,
        sample_chunks,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test filtering results by minimum score."""
        # Create request with min_score filter
        filters = SearchFilters(min_score=0.8)
        request = SearchConversationRequest(
            query="password reset",
            top_k=10,
            filters=filters
        )
        
        # Setup mocks
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        search_results = [
            (sample_chunks[0], RelevanceScore(0.95)),  # Should pass
            (sample_chunks[1], RelevanceScore(0.87)),  # Should pass
            (sample_chunks[2], RelevanceScore(0.72))   # Should be filtered out
        ]
        mock_vector_search_repo.similarity_search.return_value = search_results
        
        # Execute
        response = await use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.total_results == 2
        assert all(result.score >= 0.8 for result in response.results)
    
    @pytest.mark.asyncio
    async def test_filter_by_author_name(
        self, 
        use_case,
        sample_chunks,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test filtering results by author name."""
        filters = SearchFilters(author_name="Agent")
        request = SearchConversationRequest(
            query="password",
            top_k=10,
            filters=filters
        )
        
        # Setup mocks
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        search_results = [
            (sample_chunks[0], RelevanceScore(0.95)),  # Agent
            (sample_chunks[1], RelevanceScore(0.87)),  # Agent
            (sample_chunks[2], RelevanceScore(0.72))   # User
        ]
        mock_vector_search_repo.similarity_search.return_value = search_results
        
        # Execute
        response = await use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.total_results == 2
        assert all(result.author_name == "Agent" for result in response.results)
    
    @pytest.mark.asyncio
    async def test_filter_by_author_type(
        self, 
        use_case,
        sample_chunks,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test filtering results by author type."""
        filters = SearchFilters(author_type="assistant")
        request = SearchConversationRequest(
            query="password",
            top_k=10,
            filters=filters
        )
        
        # Setup mocks
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        search_results = [
            (sample_chunks[0], RelevanceScore(0.95)),  # assistant
            (sample_chunks[1], RelevanceScore(0.87)),  # assistant
            (sample_chunks[2], RelevanceScore(0.72))   # user
        ]
        mock_vector_search_repo.similarity_search.return_value = search_results
        
        # Execute
        response = await use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.total_results == 2
        assert all(result.author_type == "assistant" for result in response.results)
    
    @pytest.mark.asyncio
    async def test_filter_by_date_range(
        self, 
        use_case,
        sample_chunks,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test filtering results by date range."""
        filters = SearchFilters(
            date_from=datetime(2024, 1, 1, 0, 0, 0),
            date_to=datetime(2024, 1, 1, 23, 59, 59)
        )
        request = SearchConversationRequest(
            query="password",
            top_k=10,
            filters=filters
        )
        
        # Setup mocks
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        search_results = [
            (sample_chunks[0], RelevanceScore(0.95)),  # 2024-01-01
            (sample_chunks[1], RelevanceScore(0.87)),  # 2024-01-01
            (sample_chunks[2], RelevanceScore(0.72))   # 2024-01-02
        ]
        mock_vector_search_repo.similarity_search.return_value = search_results
        
        # Execute
        response = await use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.total_results == 2
        assert all(
            result.timestamp.date() == datetime(2024, 1, 1).date() 
            for result in response.results
        )
    
    @pytest.mark.asyncio
    async def test_multiple_filters_combined(
        self, 
        use_case,
        sample_chunks,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test combining multiple filters."""
        filters = SearchFilters(
            min_score=0.8,
            author_type="assistant"
        )
        request = SearchConversationRequest(
            query="password",
            top_k=10,
            filters=filters
        )
        
        # Setup mocks
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        search_results = [
            (sample_chunks[0], RelevanceScore(0.95)),  # assistant, score 0.95 ✓
            (sample_chunks[1], RelevanceScore(0.87)),  # assistant, score 0.87 ✓
            (sample_chunks[2], RelevanceScore(0.72))   # user, score 0.72 ✗
        ]
        mock_vector_search_repo.similarity_search.return_value = search_results
        
        # Execute
        response = await use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.total_results == 2
        assert all(result.score >= 0.8 for result in response.results)
        assert all(result.author_type == "assistant" for result in response.results)
    
    @pytest.mark.asyncio
    async def test_result_dto_conversion(
        self, 
        use_case,
        valid_search_request,
        sample_chunks,
        mock_embedding_service,
        mock_vector_search_repo
    ):
        """Test proper conversion of domain entities to DTOs."""
        mock_embedding_service.generate_embedding.return_value = Embedding([0.1] * 384)
        search_results = [(sample_chunks[0], RelevanceScore(0.95))]
        mock_vector_search_repo.similarity_search.return_value = search_results
        
        response = await use_case.execute(valid_search_request)
        
        assert response.success is True
        assert len(response.results) == 1
        
        result = response.results[0]
        chunk = sample_chunks[0]
        
        assert result.chunk_id == chunk.id.value
        assert result.conversation_id == chunk.conversation_id.value
        assert result.text == chunk.text.value
        assert result.score == 0.95
        assert result.author_name == chunk.metadata.author_info.name
        assert result.author_type == chunk.metadata.author_info.author_type
        assert result.timestamp == chunk.metadata.timestamp
        assert result.order_index == chunk.metadata.order_index
