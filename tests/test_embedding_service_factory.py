"""
Unit tests for EmbeddingServiceFactory.

Tests the factory pattern for creating embedding services.
"""
import pytest
from unittest.mock import Mock, patch

from app.adapters.outbound.embeddings.factory import EmbeddingServiceFactory, create_embedding_service
from app.adapters.outbound.embeddings.local_embedding_service import LocalEmbeddingService
from app.adapters.outbound.embeddings.openai_embedding_service import OpenAIEmbeddingService
from app.adapters.outbound.embeddings.fastembed_embedding_service import FastEmbedEmbeddingService
from app.adapters.outbound.embeddings.langchain_embedding_adapter import LangChainEmbeddingAdapter
from app.domain.repositories import EmbeddingError


@pytest.mark.unit
class TestEmbeddingServiceFactory:
    """Unit tests for EmbeddingServiceFactory."""
    
    def test_create_local_service(self):
        """Test creating a local embedding service."""
        service = EmbeddingServiceFactory.create(
            provider="local",
            model="test-model"
        )
        
        assert isinstance(service, LocalEmbeddingService)
        assert service.model_name == "test-model"
    
    def test_create_openai_service(self):
        """Test creating an OpenAI embedding service."""
        service = EmbeddingServiceFactory.create(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="test-key"
        )
        
        assert isinstance(service, OpenAIEmbeddingService)
        assert service.api_key == "test-key"
        assert service.model == "text-embedding-ada-002"
    
    def test_create_openai_service_missing_api_key(self):
        """Test that creating OpenAI service without API key raises error."""
        with patch('app.adapters.outbound.embeddings.factory.settings') as mock_settings:
            mock_settings.openai_api_key = None
            
            with pytest.raises(EmbeddingError, match="API key required"):
                EmbeddingServiceFactory.create(
                    provider="openai",
                    model="text-embedding-ada-002"
                )
    
    def test_create_fastembed_service(self):
        """Test creating a FastEmbed service."""
        service = EmbeddingServiceFactory.create(
            provider="fastembed",
            model="test-model"
        )
        
        assert isinstance(service, FastEmbedEmbeddingService)
        assert service.model_name == "test-model"
    
    def test_create_langchain_adapter(self):
        """Test creating a LangChain adapter."""
        mock_embeddings = Mock()
        
        service = EmbeddingServiceFactory.create(
            provider="langchain",
            langchain_embeddings=mock_embeddings
        )
        
        assert isinstance(service, LangChainEmbeddingAdapter)
        assert service.langchain_embeddings == mock_embeddings
    
    def test_create_langchain_adapter_missing_embeddings(self):
        """Test that creating LangChain adapter without embeddings raises error."""
        with pytest.raises(EmbeddingError, match="langchain_embeddings"):
            EmbeddingServiceFactory.create(provider="langchain")
    
    def test_create_unknown_provider(self):
        """Test that unknown provider raises error."""
        with pytest.raises(EmbeddingError, match="Unknown embedding provider"):
            EmbeddingServiceFactory.create(provider="unknown")
    
    def test_create_with_defaults_from_settings(self):
        """Test that factory uses settings as defaults."""
        with patch('app.adapters.outbound.embeddings.factory.settings') as mock_settings:
            mock_settings.embedding_provider = "local"
            mock_settings.embedding_model = "default-model"
            mock_settings.embedding_dimension = 1536
            
            service = EmbeddingServiceFactory.create()
            
            assert isinstance(service, LocalEmbeddingService)
            assert service.model_name == "default-model"
            assert service.target_dimension == 1536
    
    def test_create_embedding_service_convenience_function(self):
        """Test the convenience function."""
        service = create_embedding_service(
            provider="local",
            model="test-model"
        )
        
        assert isinstance(service, LocalEmbeddingService)
