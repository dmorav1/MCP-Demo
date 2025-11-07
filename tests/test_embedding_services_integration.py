"""
Integration tests for embedding services.

These tests interact with real models/APIs and are marked as slow.
Run with: pytest -m slow
"""
import pytest
import os

from app.adapters.outbound.embeddings.local_embedding_service import LocalEmbeddingService
from app.adapters.outbound.embeddings.openai_embedding_service import OpenAIEmbeddingService
from app.adapters.outbound.embeddings.factory import create_embedding_service
from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding, STANDARD_EMBEDDING_DIMENSION


@pytest.mark.integration
@pytest.mark.slow
class TestLocalEmbeddingServiceIntegration:
    """Integration tests for LocalEmbeddingService with real model."""
    
    @pytest.fixture
    def service(self):
        """Create a LocalEmbeddingService with real model."""
        return LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            device="cpu"
        )
    
    @pytest.mark.asyncio
    async def test_generate_embedding_real_model(self, service):
        """Test embedding generation with real sentence-transformers model."""
        text = "This is a test sentence for embedding generation."
        
        embedding = await service.generate_embedding(text)
        
        assert isinstance(embedding, Embedding)
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
        assert all(isinstance(v, float) for v in embedding.vector)
        # Check that at least some values are non-zero (actual embeddings)
        assert sum(abs(v) for v in embedding.vector) > 0
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_real_model(self, service):
        """Test batch embedding generation with real model."""
        texts = [
            "First test sentence.",
            "Second test sentence with different content.",
            "Third sentence about something else."
        ]
        
        embeddings = await service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        assert all(isinstance(e, Embedding) for e in embeddings)
        
        # Embeddings should be different for different texts
        assert embeddings[0].vector != embeddings[1].vector
        assert embeddings[1].vector != embeddings[2].vector
    
    @pytest.mark.asyncio
    async def test_similar_texts_have_similar_embeddings(self, service):
        """Test that similar texts produce similar embeddings."""
        text1 = "The cat sat on the mat."
        text2 = "A cat was sitting on a mat."
        text3 = "Python is a programming language."
        
        emb1 = await service.generate_embedding(text1)
        emb2 = await service.generate_embedding(text2)
        emb3 = await service.generate_embedding(text3)
        
        # Compute cosine similarity (simplified dot product for normalized vectors)
        def cosine_similarity(v1, v2):
            dot = sum(a * b for a, b in zip(v1, v2))
            mag1 = sum(a * a for a in v1) ** 0.5
            mag2 = sum(b * b for b in v2) ** 0.5
            return dot / (mag1 * mag2) if mag1 > 0 and mag2 > 0 else 0
        
        sim_12 = cosine_similarity(emb1.vector, emb2.vector)
        sim_13 = cosine_similarity(emb1.vector, emb3.vector)
        
        # Similar sentences should have higher similarity than dissimilar ones
        assert sim_12 > sim_13


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not available"
)
class TestOpenAIEmbeddingServiceIntegration:
    """Integration tests for OpenAIEmbeddingService with real API."""
    
    @pytest.fixture
    def service(self):
        """Create an OpenAIEmbeddingService with real API key."""
        api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIEmbeddingService(
            api_key=api_key,
            model="text-embedding-ada-002"
        )
    
    @pytest.mark.asyncio
    async def test_generate_embedding_real_api(self, service):
        """Test embedding generation with real OpenAI API."""
        text = "This is a test sentence for OpenAI embeddings."
        
        embedding = await service.generate_embedding(text)
        
        assert isinstance(embedding, Embedding)
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
        assert all(isinstance(v, float) for v in embedding.vector)
        assert sum(abs(v) for v in embedding.vector) > 0
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_real_api(self, service):
        """Test batch embedding generation with real API."""
        texts = [
            "First test sentence.",
            "Second test sentence."
        ]
        
        embeddings = await service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 2
        assert all(isinstance(e, Embedding) for e in embeddings)
        assert embeddings[0].vector != embeddings[1].vector
    
    @pytest.mark.asyncio
    async def test_caching_works_real_api(self, service):
        """Test that caching prevents redundant API calls."""
        text = "Test sentence for caching."
        
        # First call - should hit API
        emb1 = await service.generate_embedding(text)
        
        # Second call - should use cache
        emb2 = await service.generate_embedding(text)
        
        # Should be identical
        assert emb1.vector == emb2.vector


@pytest.mark.integration
@pytest.mark.slow
class TestEmbeddingServiceFactoryIntegration:
    """Integration tests for the embedding service factory."""
    
    @pytest.mark.asyncio
    async def test_factory_creates_working_local_service(self):
        """Test that factory creates a working local service."""
        service = create_embedding_service(provider="local")
        
        embedding = await service.generate_embedding("Test text")
        
        assert isinstance(embedding, Embedding)
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OpenAI API key not available"
    )
    async def test_factory_creates_working_openai_service(self):
        """Test that factory creates a working OpenAI service."""
        service = create_embedding_service(
            provider="openai",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        embedding = await service.generate_embedding("Test text")
        
        assert isinstance(embedding, Embedding)
        assert len(embedding.vector) == STANDARD_EMBEDDING_DIMENSION
