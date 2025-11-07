"""
Embedding service factory.

Factory pattern implementation for creating embedding services based on configuration.
"""
from typing import Optional
import logging

from app.config import settings
from app.domain.repositories import EmbeddingError
from .local_embedding_service import LocalEmbeddingService
from .openai_embedding_service import OpenAIEmbeddingService
from .fastembed_embedding_service import FastEmbedEmbeddingService
from .langchain_embedding_adapter import LangChainEmbeddingAdapter

logger = logging.getLogger(__name__)


class EmbeddingServiceFactory:
    """
    Factory for creating embedding service instances.
    
    Supports multiple providers:
    - local: sentence-transformers
    - openai: OpenAI API
    - fastembed: FastEmbed library
    - langchain: LangChain wrapper (requires external setup)
    """
    
    @staticmethod
    def create(
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        dimension: Optional[int] = None,
        **kwargs
    ):
        """
        Create an embedding service instance based on provider.
        
        Args:
            provider: Provider name ('local', 'openai', 'fastembed', 'langchain')
            model: Model name (provider-specific)
            api_key: API key (for openai)
            dimension: Target embedding dimension
            **kwargs: Additional provider-specific arguments
            
        Returns:
            An embedding service instance implementing IEmbeddingService protocol
            
        Raises:
            EmbeddingError: If provider is invalid or configuration is missing
        """
        # Use settings as defaults
        provider = provider or settings.embedding_provider
        model = model or settings.embedding_model
        dimension = dimension or settings.embedding_dimension
        
        logger.info(f"Creating embedding service: provider={provider}, model={model}")
        
        if provider == "local":
            return LocalEmbeddingService(
                model_name=model,
                target_dimension=dimension,
                **kwargs
            )
        
        elif provider == "openai":
            api_key = api_key or settings.openai_api_key
            if not api_key:
                raise EmbeddingError(
                    "OpenAI API key required for 'openai' provider. "
                    "Set OPENAI_API_KEY environment variable."
                )
            
            return OpenAIEmbeddingService(
                api_key=api_key,
                model=model,
                **kwargs
            )
        
        elif provider == "fastembed":
            return FastEmbedEmbeddingService(
                model_name=model,
                target_dimension=dimension,
                **kwargs
            )
        
        elif provider == "langchain":
            # LangChain requires external setup - user must provide embeddings instance
            langchain_embeddings = kwargs.get('langchain_embeddings')
            if not langchain_embeddings:
                raise EmbeddingError(
                    "LangChain provider requires 'langchain_embeddings' parameter. "
                    "Create a LangChain Embeddings instance and pass it to the factory."
                )
            
            return LangChainEmbeddingAdapter(
                langchain_embeddings=langchain_embeddings,
                target_dimension=dimension
            )
        
        else:
            raise EmbeddingError(
                f"Unknown embedding provider: {provider}. "
                f"Supported: 'local', 'openai', 'fastembed', 'langchain'"
            )


def create_embedding_service(
    provider: Optional[str] = None,
    **kwargs
):
    """
    Convenience function to create an embedding service.
    
    Args:
        provider: Provider name
        **kwargs: Additional arguments passed to factory
        
    Returns:
        An embedding service instance
    """
    return EmbeddingServiceFactory.create(provider=provider, **kwargs)
