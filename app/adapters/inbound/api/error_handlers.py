"""
Error handlers for mapping domain exceptions to HTTP responses.

Maps domain-level exceptions to appropriate HTTP status codes and error formats.
"""
from typing import Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

from app.domain.repositories import (
    ValidationError, RepositoryError, EmbeddingError
)


logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a resource is not found."""
    pass


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_type: Type of error (e.g., "ValidationError")
        message: Human-readable error message
        details: Optional additional error details
        
    Returns:
        JSONResponse with standardized error format
    """
    error_data = {
        "error": {
            "type": error_type,
            "message": message,
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=error_data
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle ValidationError exceptions."""
    logger.warning(f"Validation error: {str(exc)}")
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_type="ValidationError",
        message=str(exc),
        details={"path": str(request.url.path)}
    )


async def repository_error_handler(request: Request, exc: RepositoryError) -> JSONResponse:
    """Handle RepositoryError exceptions."""
    logger.error(f"Repository error: {str(exc)}")
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type="RepositoryError",
        message="An internal error occurred while accessing the database",
        details={"path": str(request.url.path)}
    )


async def embedding_error_handler(request: Request, exc: EmbeddingError) -> JSONResponse:
    """Handle EmbeddingError exceptions."""
    logger.error(f"Embedding error: {str(exc)}")
    return create_error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        error_type="EmbeddingError",
        message="The embedding service is currently unavailable",
        details={"path": str(request.url.path)}
    )


async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle NotFoundError exceptions."""
    logger.info(f"Not found error: {str(exc)}")
    return create_error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        error_type="NotFoundError",
        message=str(exc),
        details={"path": str(request.url.path)}
    )


def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(RepositoryError, repository_error_handler)
    app.add_exception_handler(EmbeddingError, embedding_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    
    logger.info("Error handlers registered")
