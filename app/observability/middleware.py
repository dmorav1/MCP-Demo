"""
Observability middleware for FastAPI.
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .logger import set_request_context, clear_request_context
from .tracing import add_span_attributes

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds observability context to requests.
    
    - Generates request IDs
    - Sets logging context
    - Adds trace attributes
    - Logs request/response details
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Set logging context
        set_request_context(request_id=request_id)
        
        # Add trace attributes if tracing is enabled
        try:
            add_span_attributes(
                request_id=request_id,
                http_method=request.method,
                http_url=str(request.url),
                http_user_agent=request.headers.get("user-agent", ""),
            )
        except Exception:
            pass
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "http_method": request.method,
                "http_url": str(request.url),
                "http_path": request.url.path,
                "client_host": request.client.host if request.client else None,
            }
        )
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "http_status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            # Add trace attributes
            try:
                add_span_attributes(
                    http_status_code=response.status_code,
                    duration_seconds=duration,
                )
            except Exception:
                pass
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True
            )
            
            # Add trace attributes
            try:
                add_span_attributes(
                    error=True,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            except Exception:
                pass
            
            raise
        finally:
            # Clear request context
            clear_request_context()


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs slow requests.
    """
    
    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "threshold_ms": round(self.slow_request_threshold * 1000, 2),
                }
            )
        
        return response
