"""
Cache port interface for the domain layer.

Defines the contract for caching operations in the application.
"""
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
from datetime import timedelta


class CachePort(ABC):
    """
    Port interface for caching operations.
    
    This abstract interface defines caching capabilities required by the domain,
    allowing different implementations (Redis, in-memory, etc.) to be plugged in.
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Store a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (expiration time)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key existed and was deleted
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        pass
    
    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries matching a pattern.
        
        Args:
            pattern: Optional key pattern (e.g., "embeddings:*")
                    If None, clears all entries
            
        Returns:
            Number of entries cleared
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats (hits, misses, size, etc.)
        """
        pass
    
    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Retrieve multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary mapping keys to values (missing keys excluded)
        """
        pass
    
    @abstractmethod
    async def set_many(
        self, 
        items: Dict[str, Any], 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Store multiple values in cache.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time-to-live for all items
            
        Returns:
            True if all successful
        """
        pass
