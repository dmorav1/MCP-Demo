"""
Cache management endpoints.

Provides API endpoints for cache statistics and management.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.cache_factory import get_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    stats: Dict[str, Any]
    message: str


class CacheClearRequest(BaseModel):
    """Request model for cache clear operation."""
    pattern: Optional[str] = None


class CacheClearResponse(BaseModel):
    """Response model for cache clear operation."""
    cleared: int
    message: str


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get cache statistics.
    
    Returns statistics about cache usage including:
    - Hit rate
    - Total requests
    - Cache size
    - Backend type
    """
    try:
        cache = get_cache()
        stats = await cache.get_stats()
        
        logger.info(f"Cache stats requested: {stats}")
        
        return CacheStatsResponse(
            stats=stats,
            message="Cache statistics retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.post("/clear", response_model=CacheClearResponse)
async def clear_cache(request: CacheClearRequest):
    """
    Clear cache entries.
    
    Args:
        request: Clear request with optional pattern
        
    Returns:
        Number of entries cleared
    """
    try:
        cache = get_cache()
        cleared = await cache.clear(request.pattern)
        
        pattern_info = f" matching pattern '{request.pattern}'" if request.pattern else ""
        message = f"Cleared {cleared} cache entries{pattern_info}"
        
        logger.info(message)
        
        return CacheClearResponse(
            cleared=cleared,
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.delete("/key/{key}")
async def delete_cache_key(key: str):
    """
    Delete a specific cache key.
    
    Args:
        key: Cache key to delete
        
    Returns:
        Success status
    """
    try:
        cache = get_cache()
        deleted = await cache.delete(key)
        
        if deleted:
            logger.info(f"Deleted cache key: {key}")
            return {"message": f"Cache key '{key}' deleted successfully", "deleted": True}
        else:
            logger.warning(f"Cache key not found: {key}")
            return {"message": f"Cache key '{key}' not found", "deleted": False}
    except Exception as e:
        logger.error(f"Failed to delete cache key {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete cache key: {str(e)}")
