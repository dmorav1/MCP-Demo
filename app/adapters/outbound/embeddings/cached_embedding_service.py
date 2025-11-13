"""
Cached embedding service wrapper.

Wraps any embedding service with caching capabilities to reduce API calls
and improve performance.
"""
import logging
from typing import List
from datetime import timedelta

from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding
from app.domain.cache import CachePort
from app.adapters.outbound.cache_adapters import create_cache_key, hash_text

logger = logging.getLogger(__name__)


class CachedEmbeddingService:
    """
    Wrapper that adds caching to any embedding service.
    
    Uses a hash of the input text as the cache key to handle
    identical text inputs efficiently.
    """
    
    def __init__(
        self,
        embedding_service,
        cache: CachePort,
        ttl: timedelta = timedelta(hours=24)
    ):
        """
        Initialize cached embedding service.
        
        Args:
            embedding_service: Underlying embedding service to wrap
            cache: Cache implementation
            ttl: Time-to-live for cached embeddings
        """
        self._embedding_service = embedding_service
        self._cache = cache
        self._ttl = ttl
        logger.info(f"CachedEmbeddingService initialized with ttl={ttl}")
    
    async def generate_embedding(self, text: str) -> Embedding:
        """
        Generate embedding with caching.
        
        Args:
            text: Input text
            
        Returns:
            Embedding object
        """
        # Create cache key from text hash
        text_hash = hash_text(text)
        cache_key = create_cache_key("embedding", text_hash)
        
        # Try cache first
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Embedding cache hit for text (hash={text_hash[:8]}...)")
            return cached
        
        # Cache miss - generate embedding
        logger.debug(f"Embedding cache miss for text (hash={text_hash[:8]}...)")
        try:
            embedding = await self._embedding_service.generate_embedding(text)
            
            # Store in cache
            await self._cache.set(cache_key, embedding, ttl=self._ttl)
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")
    
    async def generate_embeddings(self, texts: List[str]) -> List[Embedding]:
        """
        Generate embeddings for multiple texts with caching.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of Embedding objects
        """
        # Create cache keys for all texts
        text_hashes = [hash_text(text) for text in texts]
        cache_keys = [create_cache_key("embedding", h) for h in text_hashes]
        
        # Try to get all from cache
        cached_results = await self._cache.get_many(cache_keys)
        
        # Identify which texts need generation
        results = [None] * len(texts)
        texts_to_generate = []
        indices_to_generate = []
        
        for i, (text, cache_key) in enumerate(zip(texts, cache_keys)):
            if cache_key in cached_results:
                results[i] = cached_results[cache_key]
                logger.debug(f"Embedding cache hit for text {i} (hash={text_hashes[i][:8]}...)")
            else:
                texts_to_generate.append(text)
                indices_to_generate.append(i)
                logger.debug(f"Embedding cache miss for text {i} (hash={text_hashes[i][:8]}...)")
        
        # Generate missing embeddings
        if texts_to_generate:
            try:
                generated = await self._embedding_service.generate_embeddings(texts_to_generate)
                
                # Store in cache and fill results
                cache_items = {}
                for idx, embedding in zip(indices_to_generate, generated):
                    results[idx] = embedding
                    cache_key = cache_keys[idx]
                    cache_items[cache_key] = embedding
                
                await self._cache.set_many(cache_items, ttl=self._ttl)
                
                logger.info(f"Generated and cached {len(generated)} embeddings, hit {len(cached_results)} from cache")
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
                raise EmbeddingError(f"Batch embedding generation failed: {e}")
        else:
            logger.info(f"All {len(texts)} embeddings retrieved from cache")
        
        return results
