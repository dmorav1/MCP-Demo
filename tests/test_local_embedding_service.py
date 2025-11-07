"""
Unit tests for LocalEmbeddingService.

Tests the local sentence-transformers embedding service with mocked dependencies.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.adapters.outbound.embeddings.local_embedding_service import LocalEmbeddingService
from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding, STANDARD_EMBEDDING_DIMENSION


@pytest.mark.unit
class TestLocalEmbeddingService:
    """Unit tests for LocalEmbeddingService."""
    
    @pytest.fixture
    def mock_model(self):
        """Create a mock sentence-transformers model."""
        model = Mock()
        model.encode = Mock()
        return model
    
    @pytest.fixture
    def service(self):
        """Create a LocalEmbeddingService instance."""
        return LocalEmbeddingService(
            model_name="test-model",
            device="cpu",
            target_dimension=STANDARD_EMBEDDING_DIMENSION
        )
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, service, mock_model):
        """Test successful embedding generation."""
        # Mock the model loading and encoding
        native_vector = [0.1] * 384
        mock_model.encode.return_value = MagicMock(tolist=lambda: native_vector)
        
        with patch('sentence_transformers.SentenceTransformer', return_value=mock_model):
            embedding = await service.generate_embedding("test text")
        
        assert isinstance(embedding, Embedding)
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
        # First 384 should be from native vector, rest should be padding zeros
        assert embedding.vector[:384] == native_vector
        assert all(v == 0.0 for v in embedding.vector[384:])
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, service):
        """Test that empty text raises EmbeddingError."""
        with pytest.raises(EmbeddingError, match="empty text"):
            await service.generate_embedding("")
        
        with pytest.raises(EmbeddingError, match="empty text"):
            await service.generate_embedding("   ")
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_success(self, service, mock_model):
        """Test successful batch embedding generation."""
        texts = ["text1", "text2", "text3"]
        native_vectors = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
        
        mock_model.encode.return_value = MagicMock(tolist=lambda: native_vectors)
        
        with patch('sentence_transformers.SentenceTransformer', return_value=mock_model):
            embeddings = await service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        assert all(isinstance(e, Embedding) for e in embeddings)
        assert all(len(e.vector) == STANDARD_EMBEDDING_DIMENSION for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_with_empty_texts(self, service, mock_model):
        """Test batch generation handles empty texts gracefully."""
        texts = ["text1", "", "text3"]
        valid_vectors = [[0.1] * 384, [0.3] * 384]
        
        mock_model.encode.return_value = MagicMock(tolist=lambda: valid_vectors)
        
        with patch('sentence_transformers.SentenceTransformer', return_value=mock_model):
            embeddings = await service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        # Empty text should get zero embedding
        assert all(v == 0.0 for v in embeddings[1].vector)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_empty_list(self, service):
        """Test that empty list returns empty list."""
        embeddings = await service.generate_embeddings_batch([])
        assert embeddings == []
    
    @pytest.mark.asyncio
    async def test_lazy_loading(self, service, mock_model):
        """Test that model is loaded lazily."""
        # Model should not be loaded yet
        assert service._model is None
        
        with patch('sentence_transformers.SentenceTransformer', return_value=mock_model):
            mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
            await service.generate_embedding("test")
        
        # Model should now be loaded
        assert service._model is not None
    
    def test_pad_vector(self, service):
        """Test vector padding logic."""
        # Test no padding needed
        vector_1536 = [0.1] * 1536
        assert service._pad_vector(vector_1536) == vector_1536
        
        # Test padding needed
        vector_384 = [0.1] * 384
        padded = service._pad_vector(vector_384)
        assert len(padded) == 1536
        assert padded[:384] == vector_384
        assert all(v == 0.0 for v in padded[384:])
        
        # Test truncation (edge case)
        vector_2000 = [0.1] * 2000
        truncated = service._pad_vector(vector_2000)
        assert len(truncated) == 1536
