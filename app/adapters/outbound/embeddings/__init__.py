"""
Embedding service adapters - Outbound adapters implementing IEmbeddingService protocol.

These adapters integrate with various embedding providers and normalize their outputs
to match the domain's IEmbeddingService protocol.
"""
from .local_embedding_service import LocalEmbeddingService
from .openai_embedding_service import OpenAIEmbeddingService
from .fastembed_embedding_service import FastEmbedEmbeddingService
from .langchain_embedding_adapter import LangChainEmbeddingAdapter
from .factory import EmbeddingServiceFactory, create_embedding_service

__all__ = [
    'LocalEmbeddingService',
    'OpenAIEmbeddingService',
    'FastEmbedEmbeddingService',
    'LangChainEmbeddingAdapter',
    'EmbeddingServiceFactory',
    'create_embedding_service',
]
