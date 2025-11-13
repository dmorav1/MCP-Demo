"""
Cache adapter implementations.

Provides in-memory and Redis cache implementations following the hexagonal architecture.
"""
import json
import hashlib
import pickle
import time
from typing import Optional, Any, Dict, List, Tuple
from datetime import timedelta, datetime
from collections import OrderedDict
import logging

from app.domain.cache import CachePort

logger = logging.getLogger(__name__)


class InMemoryCacheAdapter(CachePort):
    """
    In-memory cache implementation using an LRU cache with TTL support.
    
    Suitable for development and single-instance deployments.
    Thread-safe for async operations.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[timedelta] = None):
        """
        Initialize in-memory cache.
        
        Args:
            max_size: Maximum number of items to store
            default_ttl: Default time-to-live for items
        """
        self._cache: OrderedDict[str, Tuple[Any, Optional[float]]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        logger.info(f"InMemoryCacheAdapter initialized with max_size={max_size}")
    
    def _is_expired(self, expiry: Optional[float]) -> bool:
        """Check if an entry is expired."""
        if expiry is None:
            return False
        return time.time() > expiry
    
    def _calculate_expiry(self, ttl: Optional[timedelta]) -> Optional[float]:
        """Calculate expiry timestamp from TTL."""
        ttl = ttl or self._default_ttl
        if ttl is None:
            return None
        return time.time() + ttl.total_seconds()
    
    def _evict_if_needed(self):
        """Evict oldest item if cache is full."""
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
            self._evictions += 1
    
    def _cleanup_expired(self):
        """Remove expired entries (lazy cleanup)."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if expiry is not None and current_time > expiry
        ]
        for key in expired_keys:
            del self._cache[key]
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        self._cleanup_expired()
        
        if key not in self._cache:
            self._misses += 1
            logger.debug(f"Cache miss: {key}")
            return None
        
        value, expiry = self._cache[key]
        if self._is_expired(expiry):
            del self._cache[key]
            self._misses += 1
            logger.debug(f"Cache miss (expired): {key}")
            return None
        
        # Move to end (LRU)
        self._cache.move_to_end(key)
        self._hits += 1
        logger.debug(f"Cache hit: {key}")
        return value
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Store a value in cache."""
        try:
            self._evict_if_needed()
            expiry = self._calculate_expiry(ttl)
            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)
            logger.debug(f"Cache set: {key} (ttl={ttl})")
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache delete: {key}")
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        self._cleanup_expired()
        if key not in self._cache:
            return False
        _, expiry = self._cache[key]
        return not self._is_expired(expiry)
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching a pattern."""
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries")
            return count
        
        # Simple pattern matching (supports * as wildcard)
        import re
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(f"^{regex_pattern}$")
        
        keys_to_delete = [key for key in self._cache.keys() if regex.match(key)]
        for key in keys_to_delete:
            del self._cache[key]
        
        logger.info(f"Cache cleared: {len(keys_to_delete)} entries matching '{pattern}'")
        return len(keys_to_delete)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "type": "in-memory",
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Retrieve multiple values from cache."""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    async def set_many(
        self, 
        items: Dict[str, Any], 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Store multiple values in cache."""
        try:
            for key, value in items.items():
                await self.set(key, value, ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to set multiple cache keys: {e}")
            return False


class RedisCacheAdapter(CachePort):
    """
    Redis cache implementation.
    
    Suitable for production deployments with multiple instances.
    Provides distributed caching with persistence options.
    """
    
    def __init__(
        self, 
        redis_url: str = "redis://localhost:6379",
        default_ttl: Optional[timedelta] = None,
        key_prefix: str = "mcp:"
    ):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live for items
            key_prefix: Prefix for all cache keys
        """
        try:
            import redis.asyncio as aioredis
            self._redis = None
            self._redis_url = redis_url
            self._redis_class = aioredis
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            raise ImportError("redis package required for RedisCacheAdapter")
        
        self._default_ttl = default_ttl
        self._key_prefix = key_prefix
        self._hits = 0
        self._misses = 0
        logger.info(f"RedisCacheAdapter initialized with url={redis_url}, prefix={key_prefix}")
    
    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = await self._redis_class.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=False
            )
        return self._redis
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._key_prefix}{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        return pickle.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        try:
            redis = await self._get_redis()
            data = await redis.get(self._make_key(key))
            
            if data is None:
                self._misses += 1
                logger.debug(f"Cache miss: {key}")
                return None
            
            self._hits += 1
            logger.debug(f"Cache hit: {key}")
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Store a value in cache."""
        try:
            redis = await self._get_redis()
            data = self._serialize(value)
            ttl = ttl or self._default_ttl
            
            if ttl:
                await redis.setex(
                    self._make_key(key),
                    int(ttl.total_seconds()),
                    data
                )
            else:
                await redis.set(self._make_key(key), data)
            
            logger.debug(f"Cache set: {key} (ttl={ttl})")
            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        try:
            redis = await self._get_redis()
            result = await redis.delete(self._make_key(key))
            logger.debug(f"Cache delete: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            redis = await self._get_redis()
            return await redis.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching a pattern."""
        try:
            redis = await self._get_redis()
            
            if pattern is None:
                # Clear all keys with our prefix
                pattern = "*"
            
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in redis.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                deleted = await redis.delete(*keys)
                logger.info(f"Cache cleared: {deleted} entries matching '{pattern}'")
                return deleted
            
            return 0
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            redis = await self._get_redis()
            info = await redis.info("stats")
            
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                "type": "redis",
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown")
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "type": "redis",
                "error": str(e)
            }
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Retrieve multiple values from cache."""
        try:
            if not keys:
                return {}
            
            redis = await self._get_redis()
            redis_keys = [self._make_key(key) for key in keys]
            values = await redis.mget(redis_keys)
            
            result = {}
            for key, data in zip(keys, values):
                if data is not None:
                    result[key] = self._deserialize(data)
                    self._hits += 1
                else:
                    self._misses += 1
            
            return result
        except Exception as e:
            logger.error(f"Failed to get multiple cache keys: {e}")
            return {}
    
    async def set_many(
        self, 
        items: Dict[str, Any], 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Store multiple values in cache."""
        try:
            redis = await self._get_redis()
            pipe = redis.pipeline()
            
            ttl = ttl or self._default_ttl
            
            for key, value in items.items():
                data = self._serialize(value)
                redis_key = self._make_key(key)
                
                if ttl:
                    pipe.setex(redis_key, int(ttl.total_seconds()), data)
                else:
                    pipe.set(redis_key, data)
            
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Failed to set multiple cache keys: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")


def create_cache_key(prefix: str, *parts: str) -> str:
    """
    Create a cache key from components.
    
    Args:
        prefix: Key prefix (e.g., "embedding", "search")
        *parts: Key components to join
        
    Returns:
        Cache key string
    """
    return f"{prefix}:{':'.join(str(p) for p in parts)}"


def hash_text(text: str) -> str:
    """
    Create a hash of text for use as cache key.
    
    Args:
        text: Text to hash
        
    Returns:
        SHA256 hash of text
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
