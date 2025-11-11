"""
FastAPI dependency functions.

Provides dependency injection for use cases, services, and database sessions.
"""
from typing import Generator, Any
from fastapi import Depends
from sqlalchemy.orm import Session
import logging

from app.database import SessionLocal
from app.infrastructure.container import get_container
from app.application.ingest_conversation import IngestConversationUseCase
from app.application.search_conversations import SearchConversationsUseCase
from app.application.rag_service import RAGService


logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Provides a database session that is automatically closed after the request.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ingest_use_case() -> IngestConversationUseCase:
    """
    Get IngestConversationUseCase from DI container.
    
    Returns:
        IngestConversationUseCase instance
    """
    container = get_container()
    return container.resolve(IngestConversationUseCase)


def get_search_use_case() -> SearchConversationsUseCase:
    """
    Get SearchConversationsUseCase from DI container.
    
    Returns:
        SearchConversationsUseCase instance
    """
    container = get_container()
    return container.resolve(SearchConversationsUseCase)


def get_rag_service() -> RAGService:
    """
    Get RAGService from DI container.
    
    Returns:
        RAGService instance
    """
    container = get_container()
    return container.resolve(RAGService)


async def log_request(request: Any) -> None:
    """
    Request logging dependency.
    
    Logs incoming requests for monitoring and debugging.
    
    Args:
        request: FastAPI request object
    """
    logger.info(f"Request: {request.method} {request.url.path}")
