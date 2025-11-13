"""
Cache factory for creating cache instances.

Provides a centralized way to create and configure cache instances
based on application settings.
"""
import logging
from datetime import timedelta
from typing import Optional

from app.domain.cache import CachePort
from app.adapters.outbound.cache_adapters import InMemoryCacheAdapter, RedisCacheAdapter
from app.config import settings

logger = logging.getLogger(__name__)


class CacheFactory:
    """Factory for creating cache instances."""
    
    _instance: Optional[CachePort] = None
    
    @classmethod
    def create_cache(cls, backend: Optional[str] = None) -> CachePort:
        """
        Create a cache instance based on configuration.
        
        Args:
            backend: Cache backend type ("memory" or "redis")
                    If None, uses settings.cache_backend
        
        Returns:
            Cache implementation
        """
        if not settings.cache_enabled:
            logger.warning("Cache is disabled in settings, using in-memory cache anyway")
        
        backend = backend or settings.cache_backend
        default_ttl = timedelta(seconds=settings.cache_default_ttl)
        
        if backend == "redis":
            try:
                logger.info(f"Creating Redis cache with URL: {settings.cache_redis_url}")
                return RedisCacheAdapter(
                    redis_url=settings.cache_redis_url,
                    default_ttl=default_ttl,
                    key_prefix="mcp:"
                )
            except ImportError as e:
                logger.warning(f"Redis not available: {e}. Falling back to in-memory cache")
                backend = "memory"
        
        if backend == "memory":
            logger.info(f"Creating in-memory cache with max_size: {settings.cache_max_size}")
            return InMemoryCacheAdapter(
                max_size=settings.cache_max_size,
                default_ttl=default_ttl
            )
        
        raise ValueError(f"Unknown cache backend: {backend}")
    
    @classmethod
    def get_cache(cls) -> CachePort:
        """
        Get singleton cache instance.
        
        Returns:
            Shared cache instance
        """
        if cls._instance is None:
            cls._instance = cls.create_cache()
        return cls._instance
    
    @classmethod
    def reset_cache(cls):
        """Reset the singleton cache instance."""
        cls._instance = None


def get_cache() -> CachePort:
    """
    Convenience function to get the default cache instance.
    
    Returns:
        Cache implementation
    """
    return CacheFactory.get_cache()
