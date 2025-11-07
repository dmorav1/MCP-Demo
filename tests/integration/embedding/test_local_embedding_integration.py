"""Integration tests for LocalEmbeddingService with real models."""
import pytest

from app.adapters.outbound.embeddings.local_embedding_service import LocalEmbeddingService
from app.domain.repositories import EmbeddingError
from app.domain.value_objects import STANDARD_EMBEDDING_DIMENSION


@pytest.mark.integration
@pytest.mark.slow
class TestLocalEmbeddingServiceIntegration:
    """Integration tests with real sentence-transformers models."""
    
    @pytest.fixture
    def service(self):
        """Create service with lightweight test model."""
        # Use a very small model for fast testing
        return LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",  # Small, fast model
            device="cpu",
            target_dimension=STANDARD_EMBEDDING_DIMENSION
        )
    
    @pytest.mark.asyncio
    async def test_generate_embedding_real_model(self, service):
        """Test generating embedding with real model."""
        text = "This is a test sentence for embedding generation."
        
        embedding = await service.generate_embedding(text)
        
        # Verify embedding properties
        assert embedding is not None
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
        
        # Verify values are reasonable floats
        assert all(isinstance(v, float) for v in embedding.vector)
        assert all(-1.0 <= v <= 1.0 for v in embedding.vector)
        
        # Verify not all zeros
        assert any(v != 0.0 for v in embedding.vector)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_real_model(self, service):
        """Test batch embedding generation with real model."""
        texts = [
            "First test sentence.",
            "Second different sentence.",
            "Third completely different text.",
        ]
        
        embeddings = await service.generate_embeddings_batch(texts)
        
        # Verify batch results
        assert len(embeddings) == 3
        assert all(len(e.vector) == STANDARD_EMBEDDING_DIMENSION for e in embeddings)
        
        # Verify embeddings are different
        assert embeddings[0].vector != embeddings[1].vector
        assert embeddings[1].vector != embeddings[2].vector
    
    @pytest.mark.asyncio
    async def test_semantic_similarity(self, service):
        """Test that semantically similar texts have similar embeddings."""
        import numpy as np
        
        # Similar texts
        text1 = "The cat sits on the mat."
        text2 = "A cat is sitting on a mat."
        
        # Different text
        text3 = "Python is a programming language."
        
        emb1 = await service.generate_embedding(text1)
        emb2 = await service.generate_embedding(text2)
        emb3 = await service.generate_embedding(text3)
        
        # Calculate cosine similarities
        def cosine_similarity(v1, v2):
            v1_array = np.array(v1)
            v2_array = np.array(v2)
            return np.dot(v1_array, v2_array) / (
                np.linalg.norm(v1_array) * np.linalg.norm(v2_array)
            )
        
        sim_1_2 = cosine_similarity(emb1.vector, emb2.vector)
        sim_1_3 = cosine_similarity(emb1.vector, emb3.vector)
        
        # Similar texts should have higher similarity
        assert sim_1_2 > sim_1_3
        assert sim_1_2 > 0.7  # Should be quite similar
    
    @pytest.mark.asyncio
    async def test_embedding_consistency(self, service):
        """Test that same text produces same embedding."""
        text = "Consistent embedding test."
        
        emb1 = await service.generate_embedding(text)
        emb2 = await service.generate_embedding(text)
        
        # Should be identical (deterministic)
        assert emb1.vector == emb2.vector
    
    @pytest.mark.asyncio
    async def test_various_text_lengths(self, service):
        """Test embedding generation with various text lengths."""
        texts = [
            "Short.",
            "This is a medium length sentence with several words.",
            "This is a much longer text that contains multiple sentences. " * 10,
        ]
        
        embeddings = await service.generate_embeddings_batch(texts)
        
        # All should succeed and have correct dimension
        assert len(embeddings) == 3
        assert all(len(e.vector) == STANDARD_EMBEDDING_DIMENSION for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_special_characters_handling(self, service):
        """Test embedding generation with special characters."""
        texts = [
            "Text with émojis 🎉🎊",
            "Special chars: <>&\"'",
            "Unicode: 中文字符 العربية",
        ]
        
        embeddings = await service.generate_embeddings_batch(texts)
        
        # Should handle all special characters
        assert len(embeddings) == 3
        assert all(len(e.vector) == STANDARD_EMBEDDING_DIMENSION for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, service):
        """Test that empty text raises appropriate error."""
        with pytest.raises(EmbeddingError):
            await service.generate_embedding("")
        
        with pytest.raises(EmbeddingError):
            await service.generate_embedding("   ")
    
    @pytest.mark.asyncio
    async def test_batch_with_empty_texts(self, service):
        """Test batch processing with some empty texts."""
        texts = [
            "Valid text",
            "",
            "Another valid text",
        ]
        
        embeddings = await service.generate_embeddings_batch(texts)
        
        # Should return embeddings for all, with zero vector for empty
        assert len(embeddings) == 3
        assert all(v == 0.0 for v in embeddings[1].vector)
        assert any(v != 0.0 for v in embeddings[0].vector)
    
    @pytest.mark.asyncio
    async def test_model_lazy_loading(self, service):
        """Test that model is loaded lazily on first use."""
        # Model should not be loaded initially
        assert service._model is None
        
        # Generate embedding (loads model)
        await service.generate_embedding("Test")
        
        # Model should now be loaded
        assert service._model is not None
    
    @pytest.mark.asyncio
    async def test_dimension_padding(self, service):
        """Test that embeddings are padded to target dimension."""
        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        # Should be padded to 1536
        
        embedding = await service.generate_embedding("Test")
        
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
        # First 384 should be non-zero, rest should be padding (zeros)
        assert any(v != 0.0 for v in embedding.vector[:384])
        assert all(v == 0.0 for v in embedding.vector[384:])


@pytest.mark.integration
@pytest.mark.slow
class TestLocalEmbeddingPerformance:
    """Performance tests for local embedding service."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
            target_dimension=STANDARD_EMBEDDING_DIMENSION
        )
    
    @pytest.mark.asyncio
    async def test_single_embedding_performance(self, service):
        """Test performance of generating single embedding."""
        import time
        
        text = "Performance test sentence."
        
        start_time = time.time()
        await service.generate_embedding(text)
        elapsed = time.time() - start_time
        
        # Should be reasonably fast (< 1 second for single embedding)
        assert elapsed < 1.0
        print(f"\n⏱️  Single embedding generated in {elapsed:.3f}s")
    
    @pytest.mark.asyncio
    async def test_batch_embedding_performance(self, service):
        """Test performance of batch embedding generation."""
        import time
        
        # Create 20 text samples
        texts = [f"Test sentence number {i} with some content." for i in range(20)]
        
        start_time = time.time()
        embeddings = await service.generate_embeddings_batch(texts)
        elapsed = time.time() - start_time
        
        # Batch should be faster than 20 individual calls
        # Should complete in < 5 seconds
        assert elapsed < 5.0
        assert len(embeddings) == 20
        
        print(f"\n⏱️  Batch of 20 embeddings generated in {elapsed:.3f}s ({elapsed/20:.3f}s per embedding)")
