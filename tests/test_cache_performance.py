"""
Performance benchmarks for caching functionality.

Measures the performance improvements from caching embeddings,
search results, and RAG responses.
"""
import pytest
import asyncio
import time
from datetime import timedelta
from unittest.mock import Mock, AsyncMock

from app.adapters.outbound.cache_adapters import InMemoryCacheAdapter
from app.adapters.outbound.embeddings.cached_embedding_service import CachedEmbeddingService
from app.application.cached_search_service import CachedSearchService
from app.application.cached_rag_service import CachedRAGService
from app.domain.value_objects import Embedding


class TestEmbeddingCachePerformance:
    """Performance tests for embedding caching."""
    
    @pytest.fixture
    def mock_slow_embedding_service(self):
        """Create mock embedding service with artificial delay."""
        service = Mock()
        
        async def slow_generate_embedding(text):
            await asyncio.sleep(0.1)  # Simulate API call
            return Embedding(vector=[0.1] * 1536)
        
        async def slow_generate_embeddings(texts):
            await asyncio.sleep(0.1 * len(texts))  # Simulate batch API call
            return [Embedding(vector=[0.1] * 1536) for _ in texts]
        
        service.generate_embedding = slow_generate_embedding
        service.generate_embeddings = slow_generate_embeddings
        return service
    
    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return InMemoryCacheAdapter(max_size=1000)
    
    @pytest.fixture
    def cached_service(self, mock_slow_embedding_service, cache):
        """Create cached embedding service."""
        return CachedEmbeddingService(
            mock_slow_embedding_service,
            cache,
            ttl=timedelta(hours=1)
        )
    
    @pytest.mark.asyncio
    async def test_single_embedding_cache_speedup(self, cached_service):
        """Test speedup from caching single embedding."""
        text = "test text for embedding"
        
        # First call (cache miss)
        start = time.time()
        await cached_service.generate_embedding(text)
        miss_time = time.time() - start
        
        # Second call (cache hit)
        start = time.time()
        await cached_service.generate_embedding(text)
        hit_time = time.time() - start
        
        # Cache hit should be much faster
        speedup = miss_time / hit_time if hit_time > 0 else float('inf')
        print(f"\nSingle embedding speedup: {speedup:.1f}x")
        print(f"Cache miss: {miss_time*1000:.2f}ms, Cache hit: {hit_time*1000:.2f}ms")
        
        assert hit_time < miss_time * 0.1  # Cache should be at least 10x faster
    
    @pytest.mark.asyncio
    async def test_batch_embedding_cache_speedup(self, cached_service):
        """Test speedup from caching batch embeddings."""
        texts = [f"text {i}" for i in range(10)]
        
        # First call (all cache miss)
        start = time.time()
        await cached_service.generate_embeddings(texts)
        miss_time = time.time() - start
        
        # Second call (all cache hit)
        start = time.time()
        await cached_service.generate_embeddings(texts)
        hit_time = time.time() - start
        
        speedup = miss_time / hit_time if hit_time > 0 else float('inf')
        print(f"\nBatch embedding speedup: {speedup:.1f}x")
        print(f"Cache miss: {miss_time*1000:.2f}ms, Cache hit: {hit_time*1000:.2f}ms")
        
        assert hit_time < miss_time * 0.1
    
    @pytest.mark.asyncio
    async def test_partial_cache_hit_performance(self, cached_service):
        """Test performance with partial cache hits."""
        # Cache first 5 texts
        cached_texts = [f"cached {i}" for i in range(5)]
        await cached_service.generate_embeddings(cached_texts)
        
        # Request mix of cached and new texts
        mixed_texts = cached_texts + [f"new {i}" for i in range(5)]
        
        start = time.time()
        await cached_service.generate_embeddings(mixed_texts)
        mixed_time = time.time() - start
        
        # Request all new texts
        new_texts = [f"all new {i}" for i in range(10)]
        start = time.time()
        await cached_service.generate_embeddings(new_texts)
        all_new_time = time.time() - start
        
        print(f"\nPartial cache hit: {mixed_time*1000:.2f}ms")
        print(f"All new: {all_new_time*1000:.2f}ms")
        
        # Partial cache should be faster than all new
        assert mixed_time < all_new_time


class TestSearchCachePerformance:
    """Performance tests for search caching."""
    
    @pytest.fixture
    def mock_slow_search_usecase(self):
        """Create mock search use case with artificial delay."""
        usecase = Mock()
        
        async def slow_execute(request):
            await asyncio.sleep(0.2)  # Simulate vector search
            from app.application.dto import SearchConversationResponse
            return SearchConversationResponse(
                results=[],
                query=request.query,
                total_results=0,
                execution_time_ms=200.0,
                success=True
            )
        
        usecase.execute = slow_execute
        return usecase
    
    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return InMemoryCacheAdapter(max_size=1000)
    
    @pytest.fixture
    def cached_search(self, mock_slow_search_usecase, cache):
        """Create cached search service."""
        return CachedSearchService(
            mock_slow_search_usecase,
            cache,
            ttl=timedelta(minutes=30)
        )
    
    @pytest.mark.asyncio
    async def test_search_cache_speedup(self, cached_search):
        """Test speedup from caching search results."""
        from app.application.dto import SearchConversationRequest
        
        request = SearchConversationRequest(query="test query", top_k=5)
        
        # First call (cache miss)
        start = time.time()
        await cached_search.execute(request)
        miss_time = time.time() - start
        
        # Second call (cache hit)
        start = time.time()
        await cached_search.execute(request)
        hit_time = time.time() - start
        
        speedup = miss_time / hit_time if hit_time > 0 else float('inf')
        print(f"\nSearch cache speedup: {speedup:.1f}x")
        print(f"Cache miss: {miss_time*1000:.2f}ms, Cache hit: {hit_time*1000:.2f}ms")
        
        assert hit_time < miss_time * 0.1


class TestCacheStatistics:
    """Tests for cache statistics and monitoring."""
    
    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return InMemoryCacheAdapter(max_size=100)
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_tracking(self, cache):
        """Test tracking of cache hit rate."""
        # Perform some operations
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Hit
        await cache.get("key1")
        await cache.get("key1")
        await cache.get("key2")
        
        # Miss
        await cache.get("missing1")
        await cache.get("missing2")
        
        stats = await cache.get_stats()
        
        print(f"\nCache statistics:")
        print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
        print(f"Hit rate: {stats['hit_rate']}%")
        
        assert stats['hits'] == 3
        assert stats['misses'] == 2
        assert stats['hit_rate'] == 60.0
    
    @pytest.mark.asyncio
    async def test_cache_memory_usage(self, cache):
        """Test cache memory usage tracking."""
        # Add items
        for i in range(50):
            await cache.set(f"key{i}", f"value{i}")
        
        stats = await cache.get_stats()
        
        print(f"\nCache memory usage:")
        print(f"Size: {stats['size']}/{stats['max_size']}")
        
        assert stats['size'] == 50
        assert stats['max_size'] == 100
    
    @pytest.mark.asyncio
    async def test_cache_eviction_tracking(self, cache):
        """Test tracking of cache evictions."""
        # Fill cache beyond capacity
        for i in range(150):
            await cache.set(f"key{i}", f"value{i}")
        
        stats = await cache.get_stats()
        
        print(f"\nCache eviction stats:")
        print(f"Evictions: {stats['evictions']}")
        print(f"Current size: {stats['size']}")
        
        assert stats['evictions'] == 50
        assert stats['size'] == 100


class TestCacheImpact:
    """High-level tests showing overall cache impact."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance_improvement(self):
        """Test overall performance improvement with caching."""
        cache = InMemoryCacheAdapter(max_size=1000)
        
        # Simulate a typical workflow
        print("\n=== Simulating typical workflow ===")
        
        # 1. Generate embedding (simulated delay)
        async def slow_embedding(text):
            await asyncio.sleep(0.05)
            return Embedding(vector=[0.1] * 1536)
        
        # Without cache
        start = time.time()
        for _ in range(10):
            await slow_embedding("test query")
        no_cache_time = time.time() - start
        
        # With cache
        start = time.time()
        # First call - miss
        embedding = await slow_embedding("test query")
        await cache.set("emb:test", embedding)
        # Rest - hits
        for _ in range(9):
            await cache.get("emb:test")
        with_cache_time = time.time() - start
        
        improvement = (1 - with_cache_time / no_cache_time) * 100
        
        print(f"Without cache: {no_cache_time*1000:.2f}ms")
        print(f"With cache: {with_cache_time*1000:.2f}ms")
        print(f"Improvement: {improvement:.1f}%")
        
        assert with_cache_time < no_cache_time * 0.3  # At least 70% improvement
