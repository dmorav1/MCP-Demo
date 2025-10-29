"""
Dependency injection container for the application.

This module provides a simple dependency injection container that manages
object creation and lifetime. It supports:
- Singleton and transient lifetimes
- Factory functions
- Lazy initialization
- Configuration-based setup
"""
from typing import TypeVar, Type, Callable, Dict, Any, Optional, Union, List
from abc import ABC, abstractmethod
from enum import Enum
import inspect

from app.domain.services import (
    ConversationChunkingService, EmbeddingValidationService,
    SearchRelevanceService, ConversationValidationService,
    ChunkingParameters
)
from .config import AppSettings, get_settings, get_chunking_config


T = TypeVar('T')


class Lifetime(Enum):
    """Service lifetime management."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"  # For future use (per-request scope)


class ServiceDescriptor:
    """Describes how a service should be created and managed."""
    
    def __init__(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
        **kwargs
    ):
        self.service_type = service_type
        self.implementation = implementation or service_type
        self.factory = factory
        self.lifetime = lifetime
        self.kwargs = kwargs
        self._instance: Optional[T] = None
    
    def create_instance(self, container: 'Container') -> T:
        """Create an instance of the service."""
        if self.lifetime == Lifetime.SINGLETON and self._instance is not None:
            return self._instance
        
        if self.factory:
            instance = self.factory()
        else:
            # Use dependency injection for constructor
            instance = container._create_with_injection(self.implementation, **self.kwargs)
        
        if self.lifetime == Lifetime.SINGLETON:
            self._instance = instance
        
        return instance


class Container:
    """
    Simple dependency injection container.
    
    Manages service registration, resolution, and lifetime.
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._setup_core_services()
    
    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        **kwargs
    ) -> 'Container':
        """Register a service with singleton lifetime."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifetime=Lifetime.SINGLETON,
            **kwargs
        )
        self._services[service_type] = descriptor
        return self
    
    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        **kwargs
    ) -> 'Container':
        """Register a service with transient lifetime."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifetime=Lifetime.TRANSIENT,
            **kwargs
        )
        self._services[service_type] = descriptor
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'Container':
        """Register a pre-created instance as a singleton."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            lifetime=Lifetime.SINGLETON
        )
        descriptor._instance = instance
        self._services[service_type] = descriptor
        return self
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance.
        
        Args:
            service_type: The type of service to resolve
            
        Returns:
            An instance of the requested service
            
        Raises:
            KeyError: If service is not registered
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type} not registered")
        
        descriptor = self._services[service_type]
        return descriptor.create_instance(self)
    
    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """
        Try to resolve a service instance.
        
        Args:
            service_type: The type of service to resolve
            
        Returns:
            An instance of the requested service, or None if not registered
        """
        try:
            return self.resolve(service_type)
        except KeyError:
            return None
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services
    
    def _create_with_injection(self, cls: Type[T], **override_kwargs) -> T:
        """Create an instance with constructor dependency injection."""
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        
        # Build constructor arguments
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Check for override
            if param_name in override_kwargs:
                kwargs[param_name] = override_kwargs[param_name]
                continue
            
            # Try to resolve from container
            param_type = param.annotation
            if param_type != inspect.Parameter.empty and self.is_registered(param_type):
                kwargs[param_name] = self.resolve(param_type)
            elif param.default != inspect.Parameter.empty:
                # Use default value
                kwargs[param_name] = param.default
            else:
                # Required parameter without registration - let constructor handle it
                pass
        
        return cls(**kwargs)
    
    def _setup_core_services(self):
        """Setup core domain services."""
        # Configuration
        self.register_singleton(AppSettings, factory=get_settings)
        
        
        # Domain services with configuration
        self.register_singleton(
            ConversationChunkingService,
            factory=lambda: ConversationChunkingService(
                ChunkingParameters(
                    max_chunk_size=get_chunking_config().max_chunk_size,
                    split_on_speaker_change=get_chunking_config().split_on_speaker_change,
                    preserve_message_boundaries=get_chunking_config().preserve_message_boundaries
                )
            )
        )
        
        self.register_singleton(EmbeddingValidationService)
        self.register_singleton(SearchRelevanceService)
        self.register_singleton(ConversationValidationService)


class ServiceProvider(ABC):
    """Abstract base class for service providers."""
    
    @abstractmethod
    def configure_services(self, container: Container) -> None:
        """Configure services in the container."""
        pass


class CoreServiceProvider(ServiceProvider):
    """Service provider for core domain services."""
    
    def configure_services(self, container: Container) -> None:
        """Configure core domain services."""
        # Core services are already configured in Container.__init__
        pass


# Global container instance
_container = Container()


def get_container() -> Container:
    """Get the global dependency injection container."""
    return _container


def configure_container(providers: List[ServiceProvider]) -> Container:
    """
    Configure the container with service providers.
    
    Args:
        providers: List of service providers to configure
        
    Returns:
        The configured container
    """
    container = get_container()
    
    for provider in providers:
        provider.configure_services(container)
    
    return container


def resolve_service(service_type: Type[T]) -> T:
    """
    Convenience function to resolve a service.
    
    Args:
        service_type: The type of service to resolve
        
    Returns:
        An instance of the requested service
    """
    return _container.resolve(service_type)


def register_singleton(
    service_type: Type[T],
    implementation: Optional[Type[T]] = None,
    factory: Optional[Callable[[], T]] = None,
    **kwargs
) -> None:
    """
    Convenience function to register a singleton service.
    
    Args:
        service_type: The service interface type
        implementation: The implementation type (optional)
        factory: Factory function (optional)
        **kwargs: Additional constructor arguments
    """
    _container.register_singleton(service_type, implementation, factory, **kwargs)


def register_transient(
    service_type: Type[T],
    implementation: Optional[Type[T]] = None,
    factory: Optional[Callable[[], T]] = None,
    **kwargs
) -> None:
    """
    Convenience function to register a transient service.
    
    Args:
        service_type: The service interface type
        implementation: The implementation type (optional)
        factory: Factory function (optional)
        **kwargs: Additional constructor arguments
    """
    _container.register_transient(service_type, implementation, factory, **kwargs)