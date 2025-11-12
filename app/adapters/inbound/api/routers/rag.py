"""
RAG API Router.

Provides REST endpoints for Retrieval-Augmented Generation using hexagonal architecture.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging
import json

from app.adapters.inbound.api.dependencies import get_rag_service
from app.application.rag_service import RAGService
from app.observability import metrics


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])


# ============================================================================
# Pydantic Models (API Layer DTOs)
# ============================================================================

class AskRequest(BaseModel):
    """API request model for RAG question."""
    query: str = Field(..., description="Question to ask")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of context chunks to retrieve")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for multi-turn dialogue")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I handle errors in Python?",
                "top_k": 5
            }
        }


class SourceInfo(BaseModel):
    """Information about a source document."""
    chunk_id: str
    conversation_id: str
    text: str
    score: float
    author_name: Optional[str] = None


class AskResponse(BaseModel):
    """API response model for RAG answer."""
    answer: str
    sources: list[SourceInfo]
    confidence: float
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    """RAG service health status."""
    status: str
    provider: Optional[str] = None
    model: Optional[str] = None
    embedding_service: str
    message: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/ask",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question (RAG)",
    description="Ask a question and get an answer with source citations using RAG."
)
async def ask_question(
    request: AskRequest,
    rag_service: RAGService = Depends(get_rag_service)
) -> AskResponse:
    """
    Ask a question using Retrieval-Augmented Generation.
    
    Performs RAG workflow:
    1. Retrieves relevant context from vector store
    2. Generates answer using LLM with context
    3. Returns answer with source citations
    
    Args:
        request: Question request
        rag_service: Injected RAGService
        
    Returns:
        Answer with sources and confidence score
    """
    logger.info(f"RAG ask: query='{request.query[:50]}...', top_k={request.top_k}")
    
    # Execute RAG query
    result = await rag_service.ask(
        query=request.query,
        top_k=request.top_k,
        conversation_id=request.conversation_id
    )
    
    # Track metrics
    metrics.rag_queries.labels(streaming="false").inc()
    
    # Convert sources to API format
    sources = [
        SourceInfo(
            chunk_id=source.get("chunk_id", ""),
            conversation_id=source.get("conversation_id", ""),
            text=source.get("text", ""),
            score=source.get("score", 0.0),
            author_name=source.get("author_name")
        )
        for source in result.get("sources", [])
    ]
    
    return AskResponse(
        answer=result.get("answer", ""),
        sources=sources,
        confidence=result.get("confidence", 0.0),
        metadata=result.get("metadata", {})
    )


@router.post(
    "/ask-stream",
    status_code=status.HTTP_200_OK,
    summary="Ask a question (streaming)",
    description="Ask a question and stream the answer in real-time using Server-Sent Events."
)
async def ask_question_streaming(
    request: AskRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Ask a question with streaming response.
    
    Returns answer as it's being generated using Server-Sent Events (SSE).
    
    Args:
        request: Question request
        rag_service: Injected RAGService
        
    Returns:
        StreamingResponse with answer chunks
    """
    logger.info(f"RAG ask streaming: query='{request.query[:50]}...'")
    
    async def generate_stream():
        """Generator for streaming response."""
        try:
            async for chunk in rag_service.ask_streaming(
                query=request.query,
                top_k=request.top_k
            ):
                # Format as Server-Sent Event
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Send end signal
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable proxy buffering
        }
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="RAG service health check",
    description="Check if RAG service is available and properly configured."
)
async def rag_health_check(
    rag_service: RAGService = Depends(get_rag_service)
) -> HealthResponse:
    """
    Check RAG service health and availability.
    
    Args:
        rag_service: Injected RAGService
        
    Returns:
        Health status with service configuration
    """
    logger.info("RAG health check")
    
    try:
        # Check if RAG service is configured
        if not rag_service.config:
            return HealthResponse(
                status="degraded",
                message="RAG service not configured",
                embedding_service="unknown"
            )
        
        # Try to get LLM (this will fail if provider credentials are missing)
        try:
            llm = rag_service._get_llm()
            provider_status = "healthy"
        except Exception as e:
            provider_status = f"unavailable: {str(e)}"
        
        return HealthResponse(
            status="healthy" if provider_status == "healthy" else "degraded",
            provider=rag_service.config.provider,
            model=rag_service.config.model,
            embedding_service="configured",
            message=provider_status if provider_status != "healthy" else "RAG service is operational"
        )
    
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            message=str(e),
            embedding_service="unknown"
        )
