"""
Search API Router.

Provides REST endpoints for semantic search using hexagonal architecture.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.adapters.inbound.api.dependencies import get_search_use_case
from app.application.search_conversations import SearchConversationsUseCase
from app.application.dto import (
    SearchConversationRequest, SearchConversationResponse,
    SearchFilters, SearchResultDTO
)
from app.observability import metrics


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


# ============================================================================
# Pydantic Models (API Layer DTOs)
# ============================================================================

class SearchFiltersRequest(BaseModel):
    """API request model for search filters."""
    scenario_title: Optional[str] = Field(None, description="Filter by scenario title")
    author_name: Optional[str] = Field(None, description="Filter by author name")
    author_type: Optional[str] = Field(None, description="Filter by author type")
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum relevance score")
    date_from: Optional[datetime] = Field(None, description="Filter by start date")
    date_to: Optional[datetime] = Field(None, description="Filter by end date")


class SearchRequest(BaseModel):
    """API request model for search."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, ge=1, le=100, description="Maximum number of results")
    filters: Optional[SearchFiltersRequest] = Field(None, description="Optional search filters")
    include_metadata: bool = Field(True, description="Include full metadata in results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I install Python packages?",
                "top_k": 5,
                "filters": {
                    "author_type": "assistant",
                    "min_score": 0.7
                }
            }
        }


class SearchResultResponse(BaseModel):
    """API response model for a single search result."""
    chunk_id: str
    conversation_id: str
    text: str
    score: float
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    order_index: Optional[int] = None
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    """API response model for search results."""
    results: List[SearchResultResponse]
    query: str
    total_results: int
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search conversations",
    description="Perform semantic search on conversation chunks using vector similarity.",
    operation_id="search_conversations_post"
)
async def search_conversations(
    request: SearchRequest,
    use_case: SearchConversationsUseCase = Depends(get_search_use_case)
) -> SearchResponse:
    """
    Search conversations using semantic similarity.
    
    Performs vector similarity search on conversation chunks:
    1. Generates query embedding
    2. Performs vector search
    3. Applies filters
    4. Ranks results by relevance
    
    Args:
        request: Search request with query and filters
        use_case: Injected SearchConversationsUseCase
        
    Returns:
        Search results with relevance scores and metadata
    """
    logger.info(f"Searching conversations: query='{request.query[:50]}...', top_k={request.top_k}")
    
    # Convert API filters to application filters
    app_filters = None
    if request.filters:
        app_filters = SearchFilters(
            scenario_title=request.filters.scenario_title,
            author_name=request.filters.author_name,
            author_type=request.filters.author_type,
            min_score=request.filters.min_score,
            date_from=request.filters.date_from,
            date_to=request.filters.date_to
        )
    
    # Create application request
    app_request = SearchConversationRequest(
        query=request.query,
        top_k=request.top_k,
        filters=app_filters,
        include_metadata=request.include_metadata
    )
    
    # Execute use case
    result = await use_case.execute(app_request)
    
    # Track metrics
    metrics.searches_performed.inc()
    
    # Convert application DTOs to API response
    api_results = [
        SearchResultResponse(
            chunk_id=r.chunk_id,
            conversation_id=r.conversation_id,
            text=r.text,
            score=r.score,
            author_name=r.author_name,
            author_type=r.author_type,
            timestamp=r.timestamp,
            order_index=r.order_index,
            metadata=r.metadata
        )
        for r in result.results
    ]
    
    return SearchResponse(
        results=api_results,
        query=result.query,
        total_results=result.total_results,
        execution_time_ms=result.execution_time_ms,
        success=result.success,
        error_message=result.error_message
    )


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search conversations (GET)",
    description="Perform semantic search using query parameters (simplified version).",
    operation_id="search_conversations_get_v2"
)
async def search_conversations_get(
    q: str = Query(..., description="Search query text"),
    top_k: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    author_name: Optional[str] = Query(None, description="Filter by author name"),
    author_type: Optional[str] = Query(None, description="Filter by author type"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum relevance score"),
    use_case: SearchConversationsUseCase = Depends(get_search_use_case)
) -> SearchResponse:
    """
    Search conversations using GET request with query parameters.
    
    This is a simplified version of the POST endpoint that accepts filters
    via query parameters instead of a JSON body.
    
    Args:
        q: Search query text
        top_k: Maximum number of results
        author_name: Filter by author name
        author_type: Filter by author type
        min_score: Minimum relevance score filter
        use_case: Injected SearchConversationsUseCase
        
    Returns:
        Search results with relevance scores and metadata
    """
    logger.info(f"GET search: query='{q[:50]}...', top_k={top_k}")
    
    # Create filters if any are specified
    app_filters = None
    if author_name or author_type or min_score is not None:
        app_filters = SearchFilters(
            author_name=author_name,
            author_type=author_type,
            min_score=min_score
        )
    
    # Create application request
    app_request = SearchConversationRequest(
        query=q,
        top_k=top_k,
        filters=app_filters,
        include_metadata=True
    )
    
    # Execute use case
    result = await use_case.execute(app_request)
    
    # Convert application DTOs to API response
    api_results = [
        SearchResultResponse(
            chunk_id=r.chunk_id,
            conversation_id=r.conversation_id,
            text=r.text,
            score=r.score,
            author_name=r.author_name,
            author_type=r.author_type,
            timestamp=r.timestamp,
            order_index=r.order_index,
            metadata=r.metadata
        )
        for r in result.results
    ]
    
    return SearchResponse(
        results=api_results,
        query=result.query,
        total_results=result.total_results,
        execution_time_ms=result.execution_time_ms,
        success=result.success,
        error_message=result.error_message
    )
