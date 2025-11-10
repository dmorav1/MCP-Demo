# Performance Optimization Plan
# Phase 4: RAG System Performance and Scalability

**Version:** 1.0  
**Date:** November 8, 2025  
**Status:** Design Document  
**Architect:** Software Architecture Agent

---

## Table of Contents

1. [Overview](#overview)
2. [Performance Targets](#performance-targets)
3. [Caching Strategy](#caching-strategy)
4. [Token Optimization](#token-optimization)
5. [Parallel Processing](#parallel-processing)
6. [Database Optimization](#database-optimization)
7. [LLM Call Optimization](#llm-call-optimization)
8. [Load Balancing and Scalability](#load-balancing-and-scalability)
9. [Monitoring and Profiling](#monitoring-and-profiling)
10. [Performance Testing](#performance-testing)

---

## Overview

This document outlines the performance optimization strategy for the RAG system, ensuring low latency, high throughput, and cost-effective operation at scale.

### Performance Principles

1. **Cache Aggressively**: Cache at multiple levels
2. **Optimize Tokens**: Minimize token usage without losing quality
3. **Parallelize Work**: Execute independent operations concurrently
4. **Batch Operations**: Group similar requests
5. **Monitor Everything**: Continuous performance tracking
6. **Fail Fast**: Quick error handling with fallbacks

---

## Performance Targets

### Response Time Targets

| Operation | Target | Acceptable | Maximum |
|-----------|--------|------------|---------|
| Simple QA (cached) | < 100ms | < 200ms | 500ms |
| Simple QA (uncached) | < 2s | < 3s | 5s |
| Complex analysis | < 5s | < 8s | 15s |
| Conversational (w/ history) | < 3s | < 5s | 10s |
| Streaming (first token) | < 500ms | < 1s | 2s |

### Throughput Targets

| Metric | Target | Acceptable | Minimum |
|--------|--------|------------|---------|
| Concurrent requests | 50 | 30 | 10 |
| Requests per second | 20 | 10 | 5 |
| Cache hit rate | > 40% | > 30% | > 20% |

### Resource Utilization Targets

| Resource | Target | Warning | Critical |
|----------|--------|---------|----------|
| CPU utilization | < 60% | > 70% | > 85% |
| Memory usage | < 70% | > 80% | > 90% |
| Database connections | < 50% pool | > 70% | > 90% |
| LLM API rate | < 80% limit | > 90% | 100% |

---

## Caching Strategy

### Multi-Level Caching Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Caching Layers                            │
│                                                              │
│  1. In-Memory Cache (Application Level)                    │
│     ├─> LRU cache for hot responses                        │
│     ├─> Size: 100 MB                                       │
│     ├─> TTL: 5 minutes                                     │
│     └─> Hit rate target: 20-30%                            │
│                                                              │
│  2. Redis Cache (Distributed)                              │
│     ├─> Shared across instances                            │
│     ├─> Size: 1 GB                                         │
│     ├─> TTL: 1-24 hours (configurable)                    │
│     └─> Hit rate target: 40-60%                            │
│                                                              │
│  3. Embedding Cache                                         │
│     ├─> Cache generated embeddings                         │
│     ├─> Persistent (database)                              │
│     └─> Never expires (invalidate on reingestion)          │
│                                                              │
│  4. Retrieval Results Cache                                │
│     ├─> Cache vector search results                        │
│     ├─> TTL: 1 hour                                        │
│     └─> Invalidate on new ingestion                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Cache Implementation

```python
from typing import Optional, Any, Callable
import hashlib
import json
from functools import wraps
from datetime import datetime, timedelta

class MultiLevelCache:
    """Multi-level caching system for RAG responses."""
    
    def __init__(
        self,
        memory_cache_size: int = 100,  # MB
        redis_client: Optional[Any] = None,
        default_ttl: int = 3600
    ):
        self.memory_cache = LRUCache(maxsize=memory_cache_size * 1024 * 1024)
        self.redis = redis_client
        self.default_ttl = default_ttl
        
        # Cache statistics
        self.stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "redis_hits": 0,
            "redis_misses": 0,
            "total_requests": 0
        }
    
    def generate_cache_key(
        self,
        query: str,
        context_ids: List[str],
        model: str,
        temperature: float
    ) -> str:
        """Generate deterministic cache key."""
        data = {
            "query": query.lower().strip(),
            "context_ids": sorted(context_ids),
            "model": model,
            "temperature": round(temperature, 2)
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve from cache (checks all levels)."""
        self.stats["total_requests"] += 1
        
        # Level 1: Memory cache
        result = self.memory_cache.get(cache_key)
        if result:
            self.stats["memory_hits"] += 1
            return result
        
        self.stats["memory_misses"] += 1
        
        # Level 2: Redis cache
        if self.redis:
            result = await self._get_from_redis(cache_key)
            if result:
                self.stats["redis_hits"] += 1
                # Promote to memory cache
                self.memory_cache.set(cache_key, result)
                return result
            
            self.stats["redis_misses"] += 1
        
        return None
    
    async def set(
        self,
        cache_key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Store in all cache levels."""
        ttl = ttl or self.default_ttl
        
        # Store in memory cache
        self.memory_cache.set(cache_key, value)
        
        # Store in Redis
        if self.redis:
            await self._set_in_redis(cache_key, value, ttl)
    
    async def _get_from_redis(self, key: str) -> Optional[Dict]:
        """Retrieve from Redis."""
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
        return None
    
    async def _set_in_redis(self, key: str, value: Dict, ttl: int):
        """Store in Redis."""
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.stats["total_requests"]
        if total == 0:
            return self.stats
        
        memory_hit_rate = self.stats["memory_hits"] / total
        redis_hit_rate = self.stats["redis_hits"] / total
        overall_hit_rate = (self.stats["memory_hits"] + self.stats["redis_hits"]) / total
        
        return {
            **self.stats,
            "memory_hit_rate": memory_hit_rate,
            "redis_hit_rate": redis_hit_rate,
            "overall_hit_rate": overall_hit_rate
        }


class LRUCache:
    """Simple LRU cache implementation."""
    
    def __init__(self, maxsize: int):
        from collections import OrderedDict
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.current_size = 0
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = value
        value_size = self._estimate_size(value)
        self.current_size += value_size
        
        # Evict if over capacity
        while self.current_size > self.maxsize and self.cache:
            oldest_key, oldest_value = self.cache.popitem(last=False)
            self.current_size -= self._estimate_size(oldest_value)
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes."""
        import sys
        return sys.getsizeof(json.dumps(obj))


def cached(ttl: int = 3600):
    """Decorator for caching function results."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key from function arguments
            cache_key = self._generate_function_cache_key(
                func.__name__,
                args,
                kwargs
            )
            
            # Try to get from cache
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Store in cache
            await self.cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
```

### Cache Invalidation Strategy

```python
class CacheInvalidator:
    """Manage cache invalidation on data changes."""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.invalidation_log = []
    
    async def invalidate_on_ingestion(self, conversation_id: str):
        """Invalidate caches when new conversation is ingested."""
        patterns = [
            f"*conversation:{conversation_id}*",
            "*retrieval:*",  # Invalidate all retrieval caches
        ]
        
        for pattern in patterns:
            await self._invalidate_pattern(pattern)
        
        self.invalidation_log.append({
            "timestamp": datetime.now(),
            "reason": "new_ingestion",
            "conversation_id": conversation_id
        })
    
    async def invalidate_on_embedding_update(self, chunk_ids: List[str]):
        """Invalidate when embeddings are regenerated."""
        for chunk_id in chunk_ids:
            await self._invalidate_pattern(f"*chunk:{chunk_id}*")
    
    async def _invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        if self.cache.redis:
            keys = await self.cache.redis.keys(pattern)
            if keys:
                await self.cache.redis.delete(*keys)
```

---

## Token Optimization

### Token Counting and Management

```python
import tiktoken

class TokenOptimizer:
    """Optimize token usage to reduce costs and improve performance."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except:
            # Fallback to cl100k_base for unknown models
            self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoder.encode(text))
    
    def truncate_to_token_limit(
        self,
        text: str,
        max_tokens: int,
        preserve_end: bool = False
    ) -> str:
        """
        Truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            preserve_end: If True, keep end of text instead of beginning
        """
        tokens = self.encoder.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        if preserve_end:
            truncated_tokens = tokens[-max_tokens:]
        else:
            truncated_tokens = tokens[:max_tokens]
        
        return self.encoder.decode(truncated_tokens)
    
    def optimize_context_chunks(
        self,
        chunks: List[ConversationChunk],
        max_tokens: int,
        strategy: str = "relevance"
    ) -> List[ConversationChunk]:
        """
        Select and optimize chunks to fit within token budget.
        
        Strategies:
        - relevance: Prioritize by relevance score
        - diversity: Maximize information diversity
        - hybrid: Balance relevance and diversity
        """
        if strategy == "relevance":
            return self._optimize_by_relevance(chunks, max_tokens)
        elif strategy == "diversity":
            return self._optimize_by_diversity(chunks, max_tokens)
        elif strategy == "hybrid":
            return self._optimize_hybrid(chunks, max_tokens)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def _optimize_by_relevance(
        self,
        chunks: List[ConversationChunk],
        max_tokens: int
    ) -> List[ConversationChunk]:
        """Select highest relevance chunks within token budget."""
        sorted_chunks = sorted(
            chunks,
            key=lambda c: c.relevance_score,
            reverse=True
        )
        
        selected = []
        token_count = 0
        
        for chunk in sorted_chunks:
            chunk_tokens = self.count_tokens(chunk.text)
            
            if token_count + chunk_tokens <= max_tokens:
                selected.append(chunk)
                token_count += chunk_tokens
            else:
                # Try to fit a truncated version
                remaining_tokens = max_tokens - token_count
                if remaining_tokens > 100:  # Minimum useful size
                    truncated_text = self.truncate_to_token_limit(
                        chunk.text,
                        remaining_tokens
                    )
                    truncated_chunk = replace(chunk, text=truncated_text)
                    selected.append(truncated_chunk)
                break
        
        return selected
    
    def _optimize_by_diversity(
        self,
        chunks: List[ConversationChunk],
        max_tokens: int
    ) -> List[ConversationChunk]:
        """
        Maximize diversity using MMR (Maximal Marginal Relevance).
        
        MMR balances relevance and diversity:
        MMR = λ * relevance - (1-λ) * max_similarity_to_selected
        """
        lambda_param = 0.7  # Balance factor (0.7 favors relevance)
        
        selected = []
        remaining = list(chunks)
        token_count = 0
        
        # Start with highest relevance
        if remaining:
            best = max(remaining, key=lambda c: c.relevance_score)
            selected.append(best)
            remaining.remove(best)
            token_count += self.count_tokens(best.text)
        
        # Iteratively select diverse chunks
        while remaining and token_count < max_tokens:
            best_mmr_score = -float('inf')
            best_chunk = None
            
            for candidate in remaining:
                # Calculate relevance component
                relevance = candidate.relevance_score
                
                # Calculate diversity component (max similarity to selected)
                max_sim = max(
                    self._calculate_similarity(candidate, sel)
                    for sel in selected
                )
                
                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_chunk = candidate
            
            if best_chunk:
                chunk_tokens = self.count_tokens(best_chunk.text)
                if token_count + chunk_tokens <= max_tokens:
                    selected.append(best_chunk)
                    remaining.remove(best_chunk)
                    token_count += chunk_tokens
                else:
                    break
        
        return selected
    
    def _calculate_similarity(
        self,
        chunk1: ConversationChunk,
        chunk2: ConversationChunk
    ) -> float:
        """Calculate similarity between chunks (cosine similarity of embeddings)."""
        if chunk1.embedding and chunk2.embedding:
            import numpy as np
            vec1 = np.array(chunk1.embedding.values)
            vec2 = np.array(chunk2.embedding.values)
            return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return 0.0
    
    def compress_conversation_history(
        self,
        history: List[Dict[str, str]],
        max_tokens: int,
        llm_provider: Any
    ) -> str:
        """
        Compress conversation history using summarization.
        
        For long conversations, summarize older messages to fit budget.
        """
        total_tokens = sum(
            self.count_tokens(turn["question"]) + self.count_tokens(turn["answer"])
            for turn in history
        )
        
        if total_tokens <= max_tokens:
            return self._format_history(history)
        
        # Keep recent messages, summarize old ones
        recent_count = 3
        recent_history = history[-recent_count:]
        old_history = history[:-recent_count]
        
        # Summarize old history
        summary = self._summarize_history(old_history, llm_provider)
        
        # Format compressed history
        compressed = f"Previous conversation summary:\n{summary}\n\nRecent messages:\n"
        compressed += self._format_history(recent_history)
        
        return compressed
    
    def _summarize_history(
        self,
        history: List[Dict[str, str]],
        llm_provider: Any
    ) -> str:
        """Summarize conversation history."""
        history_text = self._format_history(history)
        prompt = f"Summarize this conversation concisely:\n\n{history_text}\n\nSummary:"
        
        # Use LLM to generate summary
        summary = llm_provider.generate(prompt, max_tokens=200)
        return summary
```

### Context Compression Techniques

```python
class ContextCompressor:
    """Advanced context compression techniques."""
    
    def __init__(self, token_optimizer: TokenOptimizer):
        self.token_optimizer = token_optimizer
    
    def compress_redundant_chunks(
        self,
        chunks: List[ConversationChunk],
        similarity_threshold: float = 0.9
    ) -> List[ConversationChunk]:
        """Remove highly similar (redundant) chunks."""
        compressed = []
        
        for chunk in chunks:
            is_redundant = False
            
            for existing in compressed:
                similarity = self.token_optimizer._calculate_similarity(chunk, existing)
                if similarity > similarity_threshold:
                    is_redundant = True
                    break
            
            if not is_redundant:
                compressed.append(chunk)
        
        return compressed
    
    def extract_key_sentences(
        self,
        text: str,
        max_sentences: int = 5
    ) -> str:
        """Extract most important sentences using extractive summarization."""
        sentences = self._split_sentences(text)
        
        if len(sentences) <= max_sentences:
            return text
        
        # Score sentences by importance
        scored_sentences = self._score_sentences(sentences)
        
        # Select top sentences
        top_sentences = sorted(
            scored_sentences,
            key=lambda x: x[1],
            reverse=True
        )[:max_sentences]
        
        # Return in original order
        selected = sorted(top_sentences, key=lambda x: x[2])  # Sort by position
        return " ".join(s[0] for s in selected)
    
    def _score_sentences(self, sentences: List[str]) -> List[Tuple[str, float, int]]:
        """
        Score sentences by importance.
        
        Heuristics:
        - Length (prefer medium length)
        - Question words (higher importance)
        - Named entities (higher importance)
        - Position (first and last sentences important)
        """
        scored = []
        
        for idx, sentence in enumerate(sentences):
            score = 0.0
            
            # Length score (prefer 10-30 words)
            words = sentence.split()
            word_count = len(words)
            if 10 <= word_count <= 30:
                score += 1.0
            elif word_count < 10:
                score += 0.5
            
            # Question/answer indicators
            if any(kw in sentence.lower() for kw in ["decided", "agreed", "concluded"]):
                score += 2.0
            
            # Position score
            if idx == 0 or idx == len(sentences) - 1:
                score += 1.0
            
            scored.append((sentence, score, idx))
        
        return scored
```

---

## Parallel Processing

### Parallel Retrieval Strategy

```python
import asyncio
from typing import List, Dict, Any

class ParallelRetriever:
    """Execute multiple retrieval strategies in parallel."""
    
    def __init__(
        self,
        vector_search_repo: IVectorSearchRepository,
        embedding_service: IEmbeddingService
    ):
        self.vector_search = vector_search_repo
        self.embedding_service = embedding_service
    
    async def parallel_retrieve(
        self,
        query: str,
        strategies: List[str] = ["semantic", "keyword"],
        top_k: int = 10
    ) -> List[ConversationChunk]:
        """
        Execute multiple retrieval strategies in parallel.
        
        Strategies:
        - semantic: Vector similarity search
        - keyword: Full-text search
        - hybrid: Combined semantic + keyword
        - multi_query: Multiple query variations
        """
        tasks = []
        
        if "semantic" in strategies:
            tasks.append(self._semantic_search(query, top_k))
        
        if "keyword" in strategies:
            tasks.append(self._keyword_search(query, top_k))
        
        if "multi_query" in strategies:
            tasks.append(self._multi_query_search(query, top_k))
        
        # Execute all strategies concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [
            r for r in results
            if not isinstance(r, Exception)
        ]
        
        if not valid_results:
            # All strategies failed
            raise Exception("All retrieval strategies failed")
        
        # Merge results using Reciprocal Rank Fusion
        merged = self._merge_results_rrf(valid_results)
        
        return merged[:top_k]
    
    async def _semantic_search(
        self,
        query: str,
        top_k: int
    ) -> List[Tuple[ConversationChunk, float]]:
        """Semantic vector search."""
        embedding = await self.embedding_service.generate_embedding(query)
        results = await self.vector_search.similarity_search(embedding, top_k * 2)
        return results
    
    async def _keyword_search(
        self,
        query: str,
        top_k: int
    ) -> List[Tuple[ConversationChunk, float]]:
        """Full-text keyword search."""
        # Implement full-text search using PostgreSQL tsvector
        # Placeholder implementation
        return []
    
    async def _multi_query_search(
        self,
        query: str,
        top_k: int
    ) -> List[Tuple[ConversationChunk, float]]:
        """Generate multiple query variations and search."""
        variations = self._generate_query_variations(query)
        
        # Search with all variations in parallel
        tasks = [
            self._semantic_search(var, top_k)
            for var in variations
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Merge all results
        all_results = [item for sublist in results for item in sublist]
        return all_results
    
    def _merge_results_rrf(
        self,
        result_sets: List[List[Tuple[ConversationChunk, float]]],
        k: int = 60
    ) -> List[ConversationChunk]:
        """
        Merge multiple result sets using Reciprocal Rank Fusion.
        
        RRF formula: RRF(d) = Σ (1 / (k + rank_i(d)))
        where rank_i(d) is the rank of document d in result set i
        """
        chunk_scores = {}
        
        for result_set in result_sets:
            for rank, (chunk, score) in enumerate(result_set, 1):
                chunk_id = chunk.id.value
                
                if chunk_id not in chunk_scores:
                    chunk_scores[chunk_id] = {"chunk": chunk, "rrf_score": 0.0}
                
                chunk_scores[chunk_id]["rrf_score"] += 1.0 / (k + rank)
        
        # Sort by RRF score
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        return [item["chunk"] for item in sorted_chunks]
    
    def _generate_query_variations(self, query: str) -> List[str]:
        """Generate query variations for multi-query retrieval."""
        variations = [query]
        
        # Add variations (simple heuristics, can be enhanced with LLM)
        # Question to statement
        if query.strip().endswith("?"):
            variations.append(query.strip()[:-1])
        
        # Add synonyms, rephrasings, etc.
        # (Implementation omitted for brevity)
        
        return variations[:3]  # Limit to 3 variations
```

### Batch Processing

```python
class BatchProcessor:
    """Process multiple requests in batches for efficiency."""
    
    def __init__(
        self,
        batch_size: int = 10,
        max_wait_time: float = 0.5  # seconds
    ):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_requests = []
        self.batch_lock = asyncio.Lock()
    
    async def add_to_batch(
        self,
        request: Dict[str, Any]
    ) -> Any:
        """Add request to batch and wait for result."""
        async with self.batch_lock:
            future = asyncio.Future()
            self.pending_requests.append((request, future))
            
            # Trigger batch processing if batch is full
            if len(self.pending_requests) >= self.batch_size:
                asyncio.create_task(self._process_batch())
        
        # Wait for result
        return await asyncio.wait_for(future, timeout=30.0)
    
    async def _process_batch(self):
        """Process accumulated batch."""
        async with self.batch_lock:
            if not self.pending_requests:
                return
            
            batch = self.pending_requests[:self.batch_size]
            self.pending_requests = self.pending_requests[self.batch_size:]
        
        # Process batch (e.g., batch embedding generation)
        requests = [req for req, _ in batch]
        futures = [fut for _, fut in batch]
        
        try:
            results = await self._execute_batch(requests)
            
            # Set results
            for future, result in zip(futures, results):
                future.set_result(result)
        
        except Exception as e:
            # Set exception for all futures
            for future in futures:
                future.set_exception(e)
```

---

## Database Optimization

### Connection Pooling

```python
from sqlalchemy.pool import QueuePool

# Optimized connection pool configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # Core connections
    max_overflow=20,  # Additional connections
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,  # Recycle after 1 hour
    echo=False,  # Disable SQL logging in production
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30s query timeout
    }
)
```

### Query Optimization

```python
# Optimized vector similarity search with HNSW index
CREATE_HNSW_INDEX = """
CREATE INDEX IF NOT EXISTS conversation_chunks_embedding_hnsw_idx 
ON conversation_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
"""

# Optimized retrieval query
OPTIMIZED_SEARCH_QUERY = """
SELECT 
    c.id,
    c.conversation_id,
    c.text,
    c.order_index,
    c.author_name,
    c.author_type,
    c.timestamp,
    1 - (c.embedding <=> :query_embedding) AS relevance_score
FROM conversation_chunks c
WHERE c.embedding IS NOT NULL
ORDER BY c.embedding <=> :query_embedding
LIMIT :top_k;
"""
```

### Index Strategy

```sql
-- Conversation chunks indexes
CREATE INDEX idx_chunks_conversation_id ON conversation_chunks(conversation_id);
CREATE INDEX idx_chunks_timestamp ON conversation_chunks(timestamp DESC);
CREATE INDEX idx_chunks_author_type ON conversation_chunks(author_type);

-- Composite index for filtered searches
CREATE INDEX idx_chunks_composite ON conversation_chunks(
    conversation_id, timestamp DESC, author_type
);

-- Full-text search index
CREATE INDEX idx_chunks_text_fts ON conversation_chunks 
USING GIN (to_tsvector('english', text));
```

---

## LLM Call Optimization

### Request Batching

```python
class LLMBatchOptimizer:
    """Optimize LLM API calls through batching."""
    
    def __init__(self, llm_provider: ILLMProvider):
        self.llm_provider = llm_provider
        self.batch_processor = BatchProcessor(batch_size=5)
    
    async def generate_with_batching(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Queue request for batch processing."""
        request = {"prompt": prompt, **kwargs}
        return await self.batch_processor.add_to_batch(request)
```

### Response Streaming

```python
async def stream_response(
    self,
    prompt: str,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    Stream response tokens as they're generated.
    
    Benefits:
    - Lower perceived latency (first token < 500ms)
    - Better user experience
    - Can cancel if needed
    """
    async for token in self.llm_provider.stream_generate(prompt, **kwargs):
        yield token
```

---

## Load Balancing and Scalability

### Horizontal Scaling Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
│                (Nginx / AWS ALB / HAProxy)               │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │   App    │    │   App    │    │   App    │
  │Instance 1│    │Instance 2│    │Instance 3│
  └────┬─────┘    └────┬─────┘    └────┬─────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Redis Cluster  │
              │  (Shared Cache) │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   PostgreSQL    │
              │   (Primary +    │
              │    Replicas)    │
              └─────────────────┘
```

### Auto-Scaling Configuration

```yaml
# Kubernetes HPA example
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
```

---

## Monitoring and Profiling

### Performance Metrics

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
rag_request_duration = Histogram(
    'rag_request_duration_seconds',
    'RAG request duration',
    ['operation', 'model', 'cache_hit']
)

rag_token_usage = Counter(
    'rag_tokens_used_total',
    'Total tokens used',
    ['model', 'type']  # type: input/output
)

rag_cache_hits = Counter(
    'rag_cache_hits_total',
    'Cache hits',
    ['cache_level']  # memory/redis
)

rag_active_requests = Gauge(
    'rag_active_requests',
    'Number of active RAG requests'
)

class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    @contextmanager
    def track_duration(self, operation: str, **labels):
        """Track operation duration."""
        rag_active_requests.inc()
        start_time = time.time()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            rag_request_duration.labels(
                operation=operation,
                **labels
            ).observe(duration)
            rag_active_requests.dec()
    
    def track_tokens(self, model: str, input_tokens: int, output_tokens: int):
        """Track token usage."""
        rag_token_usage.labels(model=model, type="input").inc(input_tokens)
        rag_token_usage.labels(model=model, type="output").inc(output_tokens)
    
    def track_cache_hit(self, cache_level: str):
        """Track cache hit."""
        rag_cache_hits.labels(cache_level=cache_level).inc()
```

### Application Profiling

```python
import cProfile
import pstats
from functools import wraps

def profile(output_file: Optional[str] = None):
    """Decorator to profile function performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()
            
            try:
                result = func(*args, **kwargs)
            finally:
                profiler.disable()
                
                if output_file:
                    profiler.dump_stats(output_file)
                else:
                    stats = pstats.Stats(profiler)
                    stats.sort_stats('cumulative')
                    stats.print_stats(20)
            
            return result
        return wrapper
    return decorator
```

---

## Performance Testing

### Load Testing Plan

```python
import asyncio
from locust import HttpUser, task, between

class RAGLoadTest(HttpUser):
    """Load test for RAG endpoints."""
    
    wait_time = between(1, 3)
    
    @task(3)
    def ask_simple_question(self):
        """Test simple questions (most common)."""
        self.client.post("/api/rag/ask", json={
            "query": "What did John say about the project?",
            "top_k": 5
        })
    
    @task(1)
    def ask_complex_question(self):
        """Test complex analytical questions."""
        self.client.post("/api/rag/ask", json={
            "query": "Analyze the team's concerns about the timeline and provide recommendations.",
            "top_k": 10
        })
    
    @task(2)
    def conversational_query(self):
        """Test conversational queries with history."""
        self.client.post("/api/rag/ask", json={
            "query": "Tell me more about that.",
            "conversation_id": "conv-123",
            "top_k": 5
        })
```

### Performance Benchmarks

```python
class PerformanceBenchmark:
    """Run performance benchmarks."""
    
    async def run_benchmark(self, num_requests: int = 100):
        """Run comprehensive benchmark."""
        results = {
            "simple_qa": [],
            "complex_qa": [],
            "conversational": [],
            "with_cache": [],
            "without_cache": []
        }
        
        # Benchmark simple QA
        for _ in range(num_requests):
            start = time.time()
            await self.rag_service.ask_question("Simple question?")
            duration = time.time() - start
            results["simple_qa"].append(duration)
        
        # ... more benchmarks ...
        
        # Generate report
        return self._generate_report(results)
    
    def _generate_report(self, results: Dict) -> Dict:
        """Generate performance report."""
        import numpy as np
        
        report = {}
        for test_type, durations in results.items():
            report[test_type] = {
                "mean": np.mean(durations),
                "median": np.median(durations),
                "p95": np.percentile(durations, 95),
                "p99": np.percentile(durations, 99),
                "min": np.min(durations),
                "max": np.max(durations)
            }
        
        return report
```

---

## Summary

### Performance Optimization Checklist

- [ ] Implement multi-level caching (memory + Redis)
- [ ] Add token optimization and compression
- [ ] Enable parallel retrieval strategies
- [ ] Configure database connection pooling
- [ ] Create HNSW indexes for vector search
- [ ] Implement batch processing for LLM calls
- [ ] Add response streaming support
- [ ] Set up horizontal scaling with load balancer
- [ ] Configure auto-scaling policies
- [ ] Implement performance monitoring
- [ ] Set up performance profiling
- [ ] Create load testing suite
- [ ] Run performance benchmarks
- [ ] Document performance characteristics

### Expected Performance Improvements

| Optimization | Expected Improvement |
|--------------|---------------------|
| Response caching | 40-60% reduction in LLM API calls |
| Token optimization | 20-30% reduction in costs |
| Parallel retrieval | 30-40% faster retrieval |
| Database indexing | 70-80% faster vector search |
| Connection pooling | 50% reduction in connection overhead |
| Batch processing | 25-35% better throughput |
| Response streaming | 60-70% lower perceived latency |

---

**Document Status**: Complete  
**Next Document**: Cost Analysis and Optimization Guide  
**Owner**: Software Architecture Agent
