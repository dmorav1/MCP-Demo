"""
Prometheus metrics for monitoring application performance.
"""

import time
from typing import Callable, Optional
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Centralized Prometheus metrics."""
    
    def __init__(self):
        # Request metrics
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_latency = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency',
            ['method', 'endpoint'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        
        self.request_in_progress = Gauge(
            'http_requests_in_progress',
            'HTTP requests in progress',
            ['method', 'endpoint']
        )
        
        # Error metrics
        self.error_count = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'endpoint']
        )
        
        # Database metrics
        self.db_query_count = Counter(
            'db_queries_total',
            'Total database queries',
            ['operation']
        )
        
        self.db_query_latency = Histogram(
            'db_query_duration_seconds',
            'Database query latency',
            ['operation'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )
        
        # Embedding metrics
        self.embedding_generation_count = Counter(
            'embedding_generations_total',
            'Total embedding generations'
        )
        
        self.embedding_generation_latency = Histogram(
            'embedding_generation_duration_seconds',
            'Embedding generation latency',
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type']
        )
        
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type']
        )
        
        # LLM metrics (for RAG)
        self.llm_requests = Counter(
            'llm_requests_total',
            'Total LLM requests',
            ['provider', 'model']
        )
        
        self.llm_tokens = Counter(
            'llm_tokens_total',
            'Total LLM tokens used',
            ['provider', 'model', 'token_type']
        )
        
        self.llm_latency = Histogram(
            'llm_request_duration_seconds',
            'LLM request latency',
            ['provider', 'model'],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
        )
        
        # Business metrics
        self.conversations_ingested = Counter(
            'conversations_ingested_total',
            'Total conversations ingested'
        )
        
        self.searches_performed = Counter(
            'searches_performed_total',
            'Total searches performed'
        )
        
        self.rag_queries = Counter(
            'rag_queries_total',
            'Total RAG queries',
            ['streaming']
        )
        
        # Application info
        self.app_info = Info(
            'mcp_backend_info',
            'MCP Backend application information'
        )
        
        logger.info("Prometheus metrics initialized")
    
    def track_request(self, method: str, endpoint: str, status: int, duration: float):
        """Track HTTP request metrics."""
        self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_latency.labels(method=method, endpoint=endpoint).observe(duration)
    
    def track_error(self, error_type: str, endpoint: str):
        """Track error occurrence."""
        self.error_count.labels(error_type=error_type, endpoint=endpoint).inc()
    
    def track_db_query(self, operation: str, duration: float):
        """Track database query."""
        self.db_query_count.labels(operation=operation).inc()
        self.db_query_latency.labels(operation=operation).observe(duration)
    
    def track_embedding(self, duration: float):
        """Track embedding generation."""
        self.embedding_generation_count.inc()
        self.embedding_generation_latency.observe(duration)
    
    def track_cache(self, cache_type: str, hit: bool):
        """Track cache hit/miss."""
        if hit:
            self.cache_hits.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type).inc()
    
    def track_llm_request(self, provider: str, model: str, duration: float, 
                         prompt_tokens: int = 0, completion_tokens: int = 0):
        """Track LLM request."""
        self.llm_requests.labels(provider=provider, model=model).inc()
        self.llm_latency.labels(provider=provider, model=model).observe(duration)
        
        if prompt_tokens > 0:
            self.llm_tokens.labels(provider=provider, model=model, token_type='prompt').inc(prompt_tokens)
        if completion_tokens > 0:
            self.llm_tokens.labels(provider=provider, model=model, token_type='completion').inc(completion_tokens)


# Global metrics instance
metrics = PrometheusMetrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        endpoint = request.url.path
        
        # Track in-progress requests
        metrics.request_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            metrics.track_request(method, endpoint, response.status_code, duration)
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            metrics.track_request(method, endpoint, 500, duration)
            metrics.track_error(type(e).__name__, endpoint)
            raise
        finally:
            metrics.request_in_progress.labels(method=method, endpoint=endpoint).dec()


async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def timed(metric: Histogram):
    """Decorator to time function execution."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                metric.observe(time.time() - start)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                metric.observe(time.time() - start)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
