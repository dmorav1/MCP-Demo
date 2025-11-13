"""
Cached search service wrapper.

Adds caching to search operations to improve performance for repeated queries.
"""
import logging
from typing import Optional
from datetime import timedelta

from app.application.dto import SearchConversationRequest, SearchConversationResponse
from app.domain.cache import CachePort
from app.adapters.outbound.cache_adapters import create_cache_key, hash_text

logger = logging.getLogger(__name__)


class CachedSearchService:
    """
    Wrapper that adds caching to search operations.
    
    Caches search results based on query text and parameters.
    """
    
    def __init__(
        self,
        search_usecase,
        cache: CachePort,
        ttl: timedelta = timedelta(minutes=30)
    ):
        """
        Initialize cached search service.
        
        Args:
            search_usecase: Underlying search use case
            cache: Cache implementation
            ttl: Time-to-live for cached search results
        """
        self._search_usecase = search_usecase
        self._cache = cache
        self._ttl = ttl
        logger.info(f"CachedSearchService initialized with ttl={ttl}")
    
    async def execute(self, request: SearchConversationRequest) -> SearchConversationResponse:
        """
        Execute search with caching.
        
        Args:
            request: Search request
            
        Returns:
            Search response
        """
        # Create cache key from query and parameters
        cache_key_parts = [
            request.query,
            str(request.top_k),
            str(request.filters.dict() if request.filters else {})
        ]
        cache_key_str = ":".join(cache_key_parts)
        query_hash = hash_text(cache_key_str)
        cache_key = create_cache_key("search", query_hash)
        
        # Try cache first
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.info(f"Search cache hit for query: '{request.query[:50]}...'")
            return cached
        
        # Cache miss - execute search
        logger.info(f"Search cache miss for query: '{request.query[:50]}...'")
        response = await self._search_usecase.execute(request)
        
        # Cache successful results
        if response.success and response.results:
            await self._cache.set(cache_key, response, ttl=self._ttl)
            logger.debug(f"Cached search results for query: '{request.query[:50]}...'")
        
        return response
    
    async def invalidate_cache(self, pattern: Optional[str] = None):
        """
        Invalidate search cache.
        
        Args:
            pattern: Optional pattern to match (e.g., "search:*")
        """
        pattern = pattern or "search:*"
        count = await self._cache.clear(pattern)
        logger.info(f"Invalidated {count} search cache entries")
        return count
