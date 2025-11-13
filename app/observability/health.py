"""
Enhanced health check with detailed component status.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['status'] = self.status.value
        return result


class HealthChecker:
    """Comprehensive health checker."""
    
    def __init__(self):
        self.checks: List[ComponentHealth] = []
    
    def check_database(self, db: Session) -> ComponentHealth:
        """Check database connectivity and performance."""
        start = time.time()
        try:
            # Test query
            result = db.execute(text("SELECT 1")).scalar()
            latency = (time.time() - start) * 1000
            
            if result == 1:
                # Check connection pool if available
                metadata = {}
                try:
                    from app.database import engine
                    pool = engine.pool
                    metadata = {
                        "pool_size": pool.size(),
                        "checked_out": pool.checkedout(),
                        "overflow": pool.overflow(),
                    }
                except Exception:
                    pass
                
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    latency_ms=round(latency, 2),
                    metadata=metadata
                )
            else:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database query returned unexpected result",
                    latency_ms=round(latency, 2)
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.error(f"Database health check failed: {e}")
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                latency_ms=round(latency, 2)
            )
    
    def check_embedding_service(self) -> ComponentHealth:
        """Check embedding service availability."""
        try:
            from app.infrastructure.config import get_settings
            settings = get_settings()
            
            metadata = {
                "provider": settings.embedding.provider,
                "model": settings.embedding.model,
                "dimension": settings.embedding.dimension
            }
            
            return ComponentHealth(
                name="embedding_service",
                status=HealthStatus.HEALTHY,
                message=f"Embedding service configured: {settings.embedding.provider}",
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return ComponentHealth(
                name="embedding_service",
                status=HealthStatus.DEGRADED,
                message=f"Embedding service check failed: {str(e)}"
            )
    
    def check_rag_service(self) -> ComponentHealth:
        """Check RAG service availability."""
        try:
            from app.infrastructure.config import get_settings
            settings = get_settings()
            
            # Check if LLM is configured
            if not settings.llm.api_key:
                return ComponentHealth(
                    name="rag_service",
                    status=HealthStatus.DEGRADED,
                    message="RAG service not configured (no API key)"
                )
            
            metadata = {
                "provider": settings.llm.provider,
                "model": settings.llm.model,
                "max_tokens": settings.llm.max_tokens
            }
            
            return ComponentHealth(
                name="rag_service",
                status=HealthStatus.HEALTHY,
                message=f"RAG service configured: {settings.llm.provider}",
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"RAG service health check failed: {e}")
            return ComponentHealth(
                name="rag_service",
                status=HealthStatus.DEGRADED,
                message="RAG service not available"
            )
    
    def check_adapters(self) -> ComponentHealth:
        """Check adapter registrations in DI container."""
        try:
            from app.infrastructure.container import get_container
            from app.domain.repositories import (
                IConversationRepository,
                IChunkRepository,
                IEmbeddingService,
                IVectorSearchRepository
            )
            
            container = get_container()
            
            adapters = {
                "conversation_repository": container.is_registered(IConversationRepository),
                "chunk_repository": container.is_registered(IChunkRepository),
                "embedding_service": container.is_registered(IEmbeddingService),
                "vector_search": container.is_registered(IVectorSearchRepository),
            }
            
            all_registered = all(adapters.values())
            
            return ComponentHealth(
                name="adapters",
                status=HealthStatus.HEALTHY if all_registered else HealthStatus.DEGRADED,
                message="All adapters registered" if all_registered else "Some adapters missing",
                metadata=adapters
            )
        except Exception as e:
            logger.warning(f"Adapter health check failed: {e}")
            return ComponentHealth(
                name="adapters",
                status=HealthStatus.DEGRADED,
                message=f"Adapter check failed: {str(e)}"
            )
    
    def check_all(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Run all health checks.
        
        Args:
            db: Database session for database checks
            
        Returns:
            Dictionary with overall health and component details
        """
        checks = []
        
        # Database check
        if db:
            checks.append(self.check_database(db))
        
        # Embedding service check
        checks.append(self.check_embedding_service())
        
        # RAG service check
        checks.append(self.check_rag_service())
        
        # Adapters check
        checks.append(self.check_adapters())
        
        # Determine overall status
        statuses = [check.status for check in checks]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "components": [check.to_dict() for check in checks]
        }
