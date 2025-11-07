"""
Tests for Dependency Injection Container configuration and wiring.

Validates that all adapters are properly registered and can be resolved
through the container.
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.infrastructure.container import (
    Container, 
    initialize_container, 
    get_container,
    CoreServiceProvider,
    ApplicationServiceProvider,
    EmbeddingServiceProvider,
    AdapterServiceProvider
)
from app.infrastructure.config import AppSettings
from app.domain.repositories import (
    IConversationRepository,
    IChunkRepository,
    IEmbeddingRepository,
    IVectorSearchRepository,
    IEmbeddingService
)
from app.domain.services import (
    ConversationChunkingService,
    EmbeddingValidationService,
    SearchRelevanceService,
    ConversationValidationService
)


class TestContainerBasics:
    """Test basic container functionality."""
    
    def test_container_creation(self):
        """Test that a container can be created."""
        container = Container()
        assert container is not None
    
    def test_register_and_resolve_singleton(self):
        """Test registering and resolving a singleton service."""
        container = Container()
        
        # Create a simple test class
        class TestService:
            pass
        
        # Register as singleton
        container.register_singleton(TestService)
        
        # Resolve twice
        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)
        
        # Should be the same instance
        assert instance1 is instance2
    
    def test_register_and_resolve_transient(self):
        """Test registering and resolving a transient service."""
        container = Container()
        
        # Create a simple test class
        class TestService:
            pass
        
        # Register as transient
        container.register_transient(TestService)
        
        # Resolve twice
        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)
        
        # Should be different instances
        assert instance1 is not instance2
    
    def test_is_registered(self):
        """Test checking if a service is registered."""
        container = Container()
        
        class TestService:
            pass
        
        # Not registered yet
        assert not container.is_registered(TestService)
        
        # Register and check again
        container.register_singleton(TestService)
        assert container.is_registered(TestService)


class TestServiceProviders:
    """Test service provider configuration."""
    
    def test_core_service_provider(self):
        """Test that core service provider configures domain services."""
        container = Container()
        provider = CoreServiceProvider()
        provider.configure_services(container)
        
        # Core services should be registered
        assert container.is_registered(ConversationChunkingService)
        assert container.is_registered(EmbeddingValidationService)
        assert container.is_registered(SearchRelevanceService)
        assert container.is_registered(ConversationValidationService)
    
    def test_application_service_provider(self):
        """Test that application service provider configures use cases."""
        container = Container()
        
        # Configure core services first (dependencies)
        CoreServiceProvider().configure_services(container)
        
        # Configure application services
        provider = ApplicationServiceProvider()
        provider.configure_services(container)
        
        # Use cases should be registered
        from app.application import IngestConversationUseCase, SearchConversationsUseCase
        assert container.is_registered(IngestConversationUseCase)
        assert container.is_registered(SearchConversationsUseCase)
    
    @patch('app.database.SessionLocal')
    def test_adapter_service_provider(self, mock_session_local):
        """Test that adapter service provider configures repository adapters."""
        container = Container()
        
        # Mock session
        mock_session = Mock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Configure adapters
        provider = AdapterServiceProvider()
        provider.configure_services(container)
        
        # Repository interfaces should be registered
        assert container.is_registered(IConversationRepository)
        assert container.is_registered(IChunkRepository)
        assert container.is_registered(IEmbeddingRepository)
        assert container.is_registered(IVectorSearchRepository)
    
    def test_embedding_service_provider(self):
        """Test that embedding service provider configures embedding service."""
        container = Container()
        
        # Register settings first
        container.register_singleton(AppSettings)
        
        # Configure embedding service
        provider = EmbeddingServiceProvider()
        provider.configure_services(container)
        
        # Embedding service should be registered
        assert container.is_registered(IEmbeddingService)


class TestContainerInitialization:
    """Test full container initialization."""
    
    @patch('app.infrastructure.container._configured', False)
    @patch('app.database.SessionLocal')
    def test_initialize_container_with_adapters(self, mock_session_local):
        """Test initializing container with all adapters."""
        # Mock session
        mock_session = Mock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Initialize container
        container = initialize_container(include_adapters=True)
        
        # Verify core services are registered
        assert container.is_registered(ConversationChunkingService)
        assert container.is_registered(EmbeddingValidationService)
        
        # Verify use cases are registered
        from app.application import IngestConversationUseCase, SearchConversationsUseCase
        assert container.is_registered(IngestConversationUseCase)
        assert container.is_registered(SearchConversationsUseCase)
        
        # Verify adapters are registered
        assert container.is_registered(IConversationRepository)
        assert container.is_registered(IChunkRepository)
        assert container.is_registered(IEmbeddingService)
        assert container.is_registered(IVectorSearchRepository)
    
    def test_initialize_container_without_adapters(self):
        """Test initializing container without adapter dependencies."""
        # Reset the configured flag for this test
        import app.infrastructure.container as container_module
        container_module._configured = False
        
        # Also need a fresh container
        container_module._container = Container()
        
        # Initialize container without adapters (for testing)
        container = initialize_container(include_adapters=False)
        
        # Verify core services are registered
        assert container.is_registered(ConversationChunkingService)
        
        # Verify adapters are NOT registered
        assert not container.is_registered(IConversationRepository)
        assert not container.is_registered(IChunkRepository)
        
        # Reset for next tests
        container_module._configured = False
        container_module._container = Container()
    
    @patch('app.infrastructure.container._configured', False)
    def test_get_container_returns_global_instance(self):
        """Test that get_container returns the global instance."""
        container1 = get_container()
        container2 = get_container()
        
        # Should be the same instance
        assert container1 is container2


class TestAdapterResolution:
    """Test resolving adapters through the container."""
    
    @patch('app.infrastructure.container._configured', False)
    @patch('app.database.SessionLocal')
    def test_resolve_conversation_repository(self, mock_session_local):
        """Test resolving conversation repository."""
        # Mock session
        mock_session = Mock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Initialize container
        container = initialize_container(include_adapters=True)
        
        # Resolve repository
        repo = container.resolve(IConversationRepository)
        
        # Should be an instance of the correct type
        from app.adapters.outbound.persistence import SqlAlchemyConversationRepository
        assert isinstance(repo, SqlAlchemyConversationRepository)
    
    @patch('app.infrastructure.container._configured', False)
    @patch('app.database.SessionLocal')
    def test_resolve_chunk_repository(self, mock_session_local):
        """Test resolving chunk repository."""
        # Mock session
        mock_session = Mock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Initialize container
        container = initialize_container(include_adapters=True)
        
        # Resolve repository
        repo = container.resolve(IChunkRepository)
        
        # Should be an instance of the correct type
        from app.adapters.outbound.persistence import SqlAlchemyChunkRepository
        assert isinstance(repo, SqlAlchemyChunkRepository)
    
    @patch('app.infrastructure.container._configured', False)
    def test_resolve_embedding_service_local(self):
        """Test resolving embedding service with local provider."""
        # Set up settings for local provider
        settings = AppSettings(
            embedding_provider="local",
            embedding_model="all-MiniLM-L6-v2",
            embedding_dimension=384
        )
        
        # Initialize container
        container = Container()
        container.register_instance(AppSettings, settings)
        
        # Configure embedding service
        EmbeddingServiceProvider().configure_services(container)
        
        # Resolve service
        service = container.resolve(IEmbeddingService)
        
        # Should be an instance of the correct type
        from app.adapters.outbound.embeddings import LocalEmbeddingService
        assert isinstance(service, LocalEmbeddingService)


class TestConfigurationBasedSelection:
    """Test that correct services are selected based on configuration."""
    
    @patch('app.infrastructure.container._configured', False)
    def test_embedding_service_selection_local(self):
        """Test that local embedding service is selected from config."""
        # Set up settings for local provider
        settings = AppSettings(
            embedding_provider="local",
            embedding_model="all-MiniLM-L6-v2"
        )
        
        container = Container()
        container.register_instance(AppSettings, settings)
        EmbeddingServiceProvider().configure_services(container)
        
        # Resolve and verify
        service = container.resolve(IEmbeddingService)
        from app.adapters.outbound.embeddings import LocalEmbeddingService
        assert isinstance(service, LocalEmbeddingService)
    
    @patch('app.infrastructure.container._configured', False)
    def test_embedding_service_selection_fastembed(self):
        """Test that fastembed embedding service is selected from config."""
        # Set up settings for fastembed provider
        settings = AppSettings(
            embedding_provider="fastembed",
            embedding_model="BAAI/bge-small-en-v1.5"
        )
        
        container = Container()
        container.register_instance(AppSettings, settings)
        EmbeddingServiceProvider().configure_services(container)
        
        # Resolve and verify
        service = container.resolve(IEmbeddingService)
        from app.adapters.outbound.embeddings import FastEmbedEmbeddingService
        assert isinstance(service, FastEmbedEmbeddingService)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
