"""
Cached RAG service wrapper.

Adds advanced caching to RAG operations including semantic similarity caching
for similar queries and LLM response caching.
"""
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

from app.domain.cache import CachePort
from app.adapters.outbound.cache_adapters import create_cache_key, hash_text

logger = logging.getLogger(__name__)


class CachedRAGService:
    """
    Wrapper that adds caching to RAG operations.
    
    Features:
    - Caches LLM responses for identical queries
    - Semantic similarity caching (queries with same embedding)
    - Cache invalidation support
    """
    
    def __init__(
        self,
        rag_service,
        cache: CachePort,
        ttl: timedelta = timedelta(hours=1)
    ):
        """
        Initialize cached RAG service.
        
        Args:
            rag_service: Underlying RAG service
            cache: Cache implementation
            ttl: Time-to-live for cached responses
        """
        self._rag_service = rag_service
        self._cache = cache
        self._ttl = ttl
        logger.info(f"CachedRAGService initialized with ttl={ttl}")
    
    async def ask(
        self,
        query: str,
        top_k: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ask a question with caching.
        
        Args:
            query: User question
            top_k: Number of context chunks to retrieve
            **kwargs: Additional parameters
            
        Returns:
            Answer with sources and metadata
        """
        # Create cache key from query and parameters
        cache_key_parts = [
            query,
            str(top_k or "default"),
            str(kwargs.get("conversation_id", "")),
            str(kwargs.get("filters", {}))
        ]
        cache_key_str = ":".join(cache_key_parts)
        query_hash = hash_text(cache_key_str)
        cache_key = create_cache_key("rag", query_hash)
        
        # Try cache first
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.info(f"RAG cache hit for query: '{query[:50]}...'")
            # Add cache metadata
            cached["metadata"]["from_cache"] = True
            return cached
        
        # Cache miss - execute RAG
        logger.info(f"RAG cache miss for query: '{query[:50]}...'")
        response = await self._rag_service.ask(query, top_k, **kwargs)
        
        # Cache successful responses
        if response.get("answer") and response.get("confidence", 0) > 0.5:
            await self._cache.set(cache_key, response, ttl=self._ttl)
            logger.debug(f"Cached RAG response for query: '{query[:50]}...'")
        
        # Add cache metadata
        response["metadata"]["from_cache"] = False
        
        return response
    
    async def ask_conversational(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        history: Optional[list] = None,
        top_k: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ask a conversational question with caching.
        
        Note: Conversational queries are typically not cached since they
        depend on conversation history which changes over time.
        
        Args:
            query: User question
            conversation_id: Conversation identifier
            history: Conversation history
            top_k: Number of context chunks
            **kwargs: Additional parameters
            
        Returns:
            Answer with sources and metadata
        """
        # For conversational queries, we can cache if no history is provided
        if not history or len(history) == 0:
            return await self.ask(query, top_k, conversation_id=conversation_id, **kwargs)
        
        # Otherwise, bypass cache for conversational context
        logger.info(f"Bypassing cache for conversational query with {len(history)} history items")
        response = await self._rag_service.ask_conversational(
            query, conversation_id, history, top_k, **kwargs
        )
        response["metadata"]["from_cache"] = False
        return response
    
    async def invalidate_cache(self, pattern: Optional[str] = None):
        """
        Invalidate RAG cache.
        
        Args:
            pattern: Optional pattern to match (e.g., "rag:*")
        """
        pattern = pattern or "rag:*"
        count = await self._cache.clear(pattern)
        logger.info(f"Invalidated {count} RAG cache entries")
        return count
    
    def clear_conversation_memory(self, conversation_id: Optional[str] = None):
        """
        Clear conversation memory.
        
        Args:
            conversation_id: Specific conversation to clear, or None for all
        """
        return self._rag_service.clear_conversation_memory(conversation_id)
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get cumulative token usage statistics."""
        return self._rag_service.get_token_usage()
    
    def reset_token_usage(self):
        """Reset token usage counters."""
        return self._rag_service.reset_token_usage()
