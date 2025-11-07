"""
Unit tests for OpenAIEmbeddingService.

Tests the OpenAI embedding service with mocked API calls.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.adapters.outbound.embeddings.openai_embedding_service import OpenAIEmbeddingService
from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding, STANDARD_EMBEDDING_DIMENSION


@pytest.mark.unit
class TestOpenAIEmbeddingService:
    """Unit tests for OpenAIEmbeddingService."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        client = Mock()
        client.embeddings = Mock()
        client.embeddings.create = AsyncMock()
        return client
    
    @pytest.fixture
    def service(self):
        """Create an OpenAIEmbeddingService instance."""
        return OpenAIEmbeddingService(
            api_key="test-key",
            model="text-embedding-ada-002"
        )
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, service, mock_client):
        """Test successful embedding generation."""
        # Mock API response
        vector = [0.1] * STANDARD_EMBEDDING_DIMENSION
        mock_response = Mock()
        mock_response.data = [Mock(embedding=vector)]
        mock_response.usage = Mock(total_tokens=10)
        
        mock_client.embeddings.create.return_value = mock_response
        
        with patch('openai.AsyncOpenAI', return_value=mock_client):
            embedding = await service.generate_embedding("test text")
        
        assert isinstance(embedding, Embedding)
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
        assert embedding.vector == vector
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, service):
        """Test that empty text raises EmbeddingError."""
        with pytest.raises(EmbeddingError, match="empty text"):
            await service.generate_embedding("")
    
    @pytest.mark.asyncio
    async def test_generate_embedding_caching(self, service, mock_client):
        """Test that embeddings are cached."""
        vector = [0.1] * STANDARD_EMBEDDING_DIMENSION
        mock_response = Mock()
        mock_response.data = [Mock(embedding=vector)]
        mock_response.usage = Mock(total_tokens=10)
        
        mock_client.embeddings.create.return_value = mock_response
        
        with patch('openai.AsyncOpenAI', return_value=mock_client):
            # First call
            embedding1 = await service.generate_embedding("test text")
            # Second call (should use cache)
            embedding2 = await service.generate_embedding("test text")
        
        # Should only call API once
        assert mock_client.embeddings.create.call_count == 1
        assert embedding1.vector == embedding2.vector
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_success(self, service, mock_client):
        """Test successful batch embedding generation."""
        texts = ["text1", "text2", "text3"]
        vectors = [[0.1] * STANDARD_EMBEDDING_DIMENSION for _ in texts]
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=v) for v in vectors]
        mock_response.usage = Mock(total_tokens=30)
        
        mock_client.embeddings.create.return_value = mock_response
        
        with patch('openai.AsyncOpenAI', return_value=mock_client):
            embeddings = await service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        assert all(isinstance(e, Embedding) for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, service, mock_client):
        """Test that rate limit errors trigger retry with backoff."""
        vector = [0.1] * STANDARD_EMBEDDING_DIMENSION
        mock_response = Mock()
        mock_response.data = [Mock(embedding=vector)]
        mock_response.usage = Mock(total_tokens=10)
        
        # First call fails with rate limit, second succeeds
        mock_client.embeddings.create.side_effect = [
            Exception("429 rate_limit_exceeded"),
            mock_response
        ]
        
        with patch('openai.AsyncOpenAI', return_value=mock_client):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Mock sleep to speed up test
                embedding = await service.generate_embedding("test text")
        
        # Should have retried
        assert mock_client.embeddings.create.call_count == 2
        assert isinstance(embedding, Embedding)
    
    @pytest.mark.asyncio
    async def test_rate_limit_max_retries_exceeded(self, service, mock_client):
        """Test that max retries are respected."""
        # All calls fail with rate limit
        mock_client.embeddings.create.side_effect = Exception("429 rate_limit_exceeded")
        
        with patch('openai.AsyncOpenAI', return_value=mock_client):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(EmbeddingError, match="Rate limit exceeded"):
                    await service.generate_embedding("test text")
        
        # Should have tried MAX_RETRIES + 1 times
        assert mock_client.embeddings.create.call_count == service.MAX_RETRIES + 1
    
    @pytest.mark.asyncio
    async def test_batch_with_empty_texts(self, service, mock_client):
        """Test batch generation handles empty texts."""
        texts = ["text1", "", "text3"]
        vectors = [[0.1] * STANDARD_EMBEDDING_DIMENSION, [0.3] * STANDARD_EMBEDDING_DIMENSION]
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=v) for v in vectors]
        mock_response.usage = Mock(total_tokens=20)
        
        mock_client.embeddings.create.return_value = mock_response
        
        with patch('openai.AsyncOpenAI', return_value=mock_client):
            embeddings = await service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        # Empty text should get zero embedding
        assert all(v == 0.0 for v in embeddings[1].vector)
    
    @pytest.mark.asyncio
    async def test_batching_respects_max_batch_size(self, service, mock_client):
        """Test that large batches are split according to max_batch_size."""
        service.max_batch_size = 2
        texts = ["text1", "text2", "text3", "text4"]
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * STANDARD_EMBEDDING_DIMENSION) for _ in range(2)]
        mock_response.usage = Mock(total_tokens=20)
        
        mock_client.embeddings.create.return_value = mock_response
        
        with patch('openai.AsyncOpenAI', return_value=mock_client):
            embeddings = await service.generate_embeddings_batch(texts)
        
        # Should have made 2 API calls (2 batches of 2 texts each)
        assert mock_client.embeddings.create.call_count == 2
        assert len(embeddings) == 4
