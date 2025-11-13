"""
Tests for caching functionality.

Tests cache implementations, embedding caching, search caching,
and cache statistics.
"""
import pytest
import asyncio
from datetime import timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.domain.cache import CachePort
from app.adapters.outbound.cache_adapters import (
    InMemoryCacheAdapter,
    RedisCacheAdapter,
    create_cache_key,
    hash_text
)
from app.adapters.outbound.embeddings.cached_embedding_service import CachedEmbeddingService
from app.application.cached_search_service import CachedSearchService
from app.infrastructure.cache_factory import CacheFactory
from app.domain.value_objects import Embedding


class TestInMemoryCacheAdapter:
    """Tests for in-memory cache adapter."""
    
    @pytest.fixture
    def cache(self):
        """Create in-memory cache instance."""
        return InMemoryCacheAdapter(max_size=10, default_ttl=timedelta(seconds=60))
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_get_missing_key(self, cache):
        """Test getting a non-existent key."""
        result = await cache.get("missing")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test delete operation."""
        await cache.set("key1", "value1")
        deleted = await cache.delete("key1")
        assert deleted is True
        
        result = await cache.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test exists operation."""
        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True
        assert await cache.exists("missing") is False
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test TTL expiration."""
        await cache.set("key1", "value1", ttl=timedelta(milliseconds=100))
        
        # Should exist immediately
        assert await cache.exists("key1") is True
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired
        result = await cache.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_clear_all(self, cache):
        """Test clearing all cache entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        cleared = await cache.clear()
        assert cleared == 3
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_clear_with_pattern(self, cache):
        """Test clearing cache entries matching a pattern."""
        await cache.set("user:1", "value1")
        await cache.set("user:2", "value2")
        await cache.set("post:1", "value3")
        
        cleared = await cache.clear("user:*")
        assert cleared == 2
        
        assert await cache.get("user:1") is None
        assert await cache.get("user:2") is None
        assert await cache.get("post:1") == "value3"
    
    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Test getting cache statistics."""
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("missing")  # Miss
        
        stats = await cache.get_stats()
        assert stats["type"] == "in-memory"
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 50.0
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to max
        for i in range(10):
            await cache.set(f"key{i}", f"value{i}")
        
        # Add one more - should evict oldest
        await cache.set("key10", "value10")
        
        stats = await cache.get_stats()
        assert stats["size"] == 10
        assert stats["evictions"] == 1
        
        # First key should be evicted
        assert await cache.get("key0") is None
    
    @pytest.mark.asyncio
    async def test_get_many(self, cache):
        """Test getting multiple values."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        results = await cache.get_many(["key1", "key3", "missing"])
        assert results == {"key1": "value1", "key3": "value3"}
    
    @pytest.mark.asyncio
    async def test_set_many(self, cache):
        """Test setting multiple values."""
        items = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        success = await cache.set_many(items)
        assert success is True
        
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"


class TestCacheKeyHelpers:
    """Tests for cache key helper functions."""
    
    def test_create_cache_key(self):
        """Test creating cache keys."""
        key = create_cache_key("embedding", "text_hash")
        assert key == "embedding:text_hash"
        
        key = create_cache_key("search", "query_hash", "10", "filters")
        assert key == "search:query_hash:10:filters"
    
    def test_hash_text(self):
        """Test text hashing."""
        hash1 = hash_text("test text")
        hash2 = hash_text("test text")
        hash3 = hash_text("different text")
        
        # Same text produces same hash
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Different text produces different hash
        assert hash1 != hash3


class TestCachedEmbeddingService:
    """Tests for cached embedding service."""
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = Mock()
        service.generate_embedding = AsyncMock()
        service.generate_embeddings = AsyncMock()
        return service
    
    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return InMemoryCacheAdapter(max_size=100)
    
    @pytest.fixture
    def cached_service(self, mock_embedding_service, cache):
        """Create cached embedding service."""
        return CachedEmbeddingService(
            mock_embedding_service,
            cache,
            ttl=timedelta(hours=1)
        )
    
    @pytest.mark.asyncio
    async def test_cache_miss_generates_embedding(
        self, cached_service, mock_embedding_service, cache
    ):
        """Test cache miss generates embedding."""
        embedding = Embedding(vector=[0.1] * 1536)
        mock_embedding_service.generate_embedding.return_value = embedding
        
        result = await cached_service.generate_embedding("test text")
        
        assert result == embedding
        mock_embedding_service.generate_embedding.assert_called_once_with("test text")
    
    @pytest.mark.asyncio
    async def test_cache_hit_skips_generation(
        self, cached_service, mock_embedding_service, cache
    ):
        """Test cache hit skips embedding generation."""
        embedding = Embedding(vector=[0.1] * 1536)
        mock_embedding_service.generate_embedding.return_value = embedding
        
        # First call - cache miss
        await cached_service.generate_embedding("test text")
        assert mock_embedding_service.generate_embedding.call_count == 1
        
        # Second call - cache hit
        result = await cached_service.generate_embedding("test text")
        assert result == embedding
        assert mock_embedding_service.generate_embedding.call_count == 1
    
    @pytest.mark.asyncio
    async def test_batch_embeddings_partial_cache(
        self, cached_service, mock_embedding_service, cache
    ):
        """Test batch embeddings with partial cache hits."""
        # Pre-cache one embedding
        cached_embedding = Embedding(vector=[0.1] * 1536)
        text_hash = hash_text("text1")
        cache_key = create_cache_key("embedding", text_hash)
        await cache.set(cache_key, cached_embedding)
        
        # Mock service for uncached text
        new_embedding = Embedding(vector=[0.2] * 1536)
        mock_embedding_service.generate_embeddings.return_value = [new_embedding]
        
        # Request both texts
        results = await cached_service.generate_embeddings(["text1", "text2"])
        
        assert len(results) == 2
        assert results[0] == cached_embedding  # From cache
        assert results[1] == new_embedding  # Generated
        
        # Should only generate for uncached text
        mock_embedding_service.generate_embeddings.assert_called_once_with(["text2"])


class TestCachedSearchService:
    """Tests for cached search service."""
    
    @pytest.fixture
    def mock_search_usecase(self):
        """Create mock search use case."""
        usecase = Mock()
        usecase.execute = AsyncMock()
        return usecase
    
    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return InMemoryCacheAdapter(max_size=100)
    
    @pytest.fixture
    def cached_search(self, mock_search_usecase, cache):
        """Create cached search service."""
        return CachedSearchService(
            mock_search_usecase,
            cache,
            ttl=timedelta(minutes=30)
        )
    
    @pytest.mark.asyncio
    async def test_cache_miss_executes_search(
        self, cached_search, mock_search_usecase
    ):
        """Test cache miss executes search."""
        from app.application.dto import SearchConversationRequest, SearchConversationResponse
        
        request = SearchConversationRequest(query="test query", top_k=5)
        response = SearchConversationResponse(
            results=[],
            query="test query",
            total_results=0,
            execution_time_ms=10.0,
            success=True
        )
        mock_search_usecase.execute.return_value = response
        
        result = await cached_search.execute(request)
        
        assert result == response
        mock_search_usecase.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_hit_skips_search(
        self, cached_search, mock_search_usecase
    ):
        """Test cache hit skips search execution."""
        from app.application.dto import SearchConversationRequest, SearchConversationResponse
        
        request = SearchConversationRequest(query="test query", top_k=5)
        response = SearchConversationResponse(
            results=[],
            query="test query",
            total_results=0,
            execution_time_ms=10.0,
            success=True
        )
        mock_search_usecase.execute.return_value = response
        
        # First call - cache miss
        await cached_search.execute(request)
        assert mock_search_usecase.execute.call_count == 1
        
        # Second call - cache hit
        result = await cached_search.execute(request)
        assert result.query == "test query"
        assert mock_search_usecase.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_invalidate_cache(self, cached_search, cache):
        """Test cache invalidation."""
        from app.application.dto import SearchConversationRequest, SearchConversationResponse
        
        # Add some cached searches
        await cache.set("search:hash1", "result1")
        await cache.set("search:hash2", "result2")
        await cache.set("other:hash3", "result3")
        
        # Invalidate search cache
        count = await cached_search.invalidate_cache("search:*")
        
        assert count == 2
        assert await cache.get("other:hash3") == "result3"


class TestCacheFactory:
    """Tests for cache factory."""
    
    def test_create_memory_cache(self):
        """Test creating in-memory cache."""
        cache = CacheFactory.create_cache("memory")
        assert isinstance(cache, InMemoryCacheAdapter)
    
    def test_singleton_pattern(self):
        """Test cache factory singleton pattern."""
        CacheFactory.reset_cache()
        
        cache1 = CacheFactory.get_cache()
        cache2 = CacheFactory.get_cache()
        
        assert cache1 is cache2
    
    def test_reset_cache(self):
        """Test resetting cache instance."""
        cache1 = CacheFactory.get_cache()
        CacheFactory.reset_cache()
        cache2 = CacheFactory.get_cache()
        
        assert cache1 is not cache2
