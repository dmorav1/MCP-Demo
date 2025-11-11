"""
Conversations API Router.

Provides REST endpoints for conversation management using hexagonal architecture.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.adapters.inbound.api.dependencies import get_ingest_use_case, get_db
from app.adapters.inbound.api.error_handlers import NotFoundError
from app.application.ingest_conversation import IngestConversationUseCase
from app.application.dto import (
    IngestConversationRequest, IngestConversationResponse,
    MessageDTO, ConversationMetadataDTO
)
from sqlalchemy.orm import Session
from app import models


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


# ============================================================================
# Pydantic Models (API Layer DTOs)
# ============================================================================

class MessageRequest(BaseModel):
    """API request model for a message."""
    text: str = Field(..., description="Message content")
    author_name: Optional[str] = Field(None, description="Author name")
    author_type: Optional[str] = Field(None, description="Author type (user, assistant, system)")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")


class IngestRequest(BaseModel):
    """API request model for ingesting a conversation."""
    messages: List[MessageRequest] = Field(..., description="List of messages")
    scenario_title: Optional[str] = Field(None, description="Scenario title")
    original_title: Optional[str] = Field(None, description="Original conversation title")
    url: Optional[str] = Field(None, description="Source URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "text": "Hello, I need help with Python.",
                        "author_name": "User",
                        "author_type": "user"
                    },
                    {
                        "text": "I'd be happy to help! What do you need?",
                        "author_name": "Assistant",
                        "author_type": "assistant"
                    }
                ],
                "scenario_title": "Python Help Session",
                "url": "https://example.com/conversation/123"
            }
        }


class IngestResponse(BaseModel):
    """API response model for conversation ingestion."""
    conversation_id: str = Field(..., description="Created conversation ID")
    chunks_created: int = Field(..., description="Number of chunks created")
    success: bool = Field(..., description="Whether ingestion succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[dict] = Field(None, description="Conversation metadata")


class ConversationResponse(BaseModel):
    """API response model for a conversation."""
    id: int
    scenario_title: Optional[str]
    original_title: Optional[str]
    url: Optional[str]
    created_at: Optional[datetime]
    chunk_count: int
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """API response model for conversation details with chunks."""
    id: int
    scenario_title: Optional[str]
    original_title: Optional[str]
    url: Optional[str]
    created_at: Optional[datetime]
    chunks: List[dict]
    
    class Config:
        from_attributes = True


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new conversation",
    description="Ingest a conversation with messages, chunk them, and generate embeddings."
)
async def ingest_conversation(
    request: IngestRequest,
    use_case: IngestConversationUseCase = Depends(get_ingest_use_case)
) -> IngestResponse:
    """
    Ingest a new conversation.
    
    Processes messages through the ingestion pipeline:
    1. Validates input
    2. Chunks messages
    3. Generates embeddings
    4. Persists to database
    
    Args:
        request: Conversation ingestion request
        use_case: Injected IngestConversationUseCase
        
    Returns:
        Ingestion response with conversation ID and metadata
    """
    logger.info(f"Ingesting conversation with {len(request.messages)} messages")
    
    # Convert API DTOs to application DTOs
    message_dtos = [
        MessageDTO(
            text=msg.text,
            author_name=msg.author_name,
            author_type=msg.author_type,
            timestamp=msg.timestamp
        )
        for msg in request.messages
    ]
    
    app_request = IngestConversationRequest(
        messages=message_dtos,
        scenario_title=request.scenario_title,
        original_title=request.original_title,
        url=request.url
    )
    
    # Execute use case
    result = await use_case.execute(app_request)
    
    # Convert application DTO to API response
    metadata_dict = None
    if result.metadata:
        metadata_dict = {
            "conversation_id": result.metadata.conversation_id,
            "scenario_title": result.metadata.scenario_title,
            "original_title": result.metadata.original_title,
            "url": result.metadata.url,
            "created_at": result.metadata.created_at.isoformat() if result.metadata.created_at else None,
            "total_chunks": result.metadata.total_chunks
        }
    
    return IngestResponse(
        conversation_id=result.conversation_id,
        chunks_created=result.chunks_created,
        success=result.success,
        error_message=result.error_message,
        metadata=metadata_dict
    )


@router.get(
    "",
    response_model=List[ConversationResponse],
    summary="List conversations",
    description="List all conversations with pagination.",
    operation_id="list_conversations_v2"
)
async def list_conversations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
) -> List[ConversationResponse]:
    """
    List conversations with pagination.
    
    Args:
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of conversation summaries
    """
    logger.info(f"Listing conversations: skip={skip}, limit={limit}")
    
    conversations = db.query(models.Conversation)\
        .order_by(models.Conversation.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    results = []
    for conv in conversations:
        chunk_count = db.query(models.ConversationChunk)\
            .filter(models.ConversationChunk.conversation_id == conv.id)\
            .count()
        
        results.append(ConversationResponse(
            id=conv.id,
            scenario_title=conv.scenario_title,
            original_title=conv.original_title,
            url=conv.url,
            created_at=conv.created_at,
            chunk_count=chunk_count
        ))
    
    logger.info(f"Retrieved {len(results)} conversations")
    return results


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation by ID",
    description="Retrieve a specific conversation with all its chunks.",
    operation_id="get_conversation_v2"
)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
) -> ConversationDetailResponse:
    """
    Get a specific conversation by ID.
    
    Args:
        conversation_id: Conversation ID
        db: Database session
        
    Returns:
        Conversation details with chunks
        
    Raises:
        NotFoundError: If conversation not found
    """
    logger.info(f"Retrieving conversation: id={conversation_id}")
    
    conversation = db.query(models.Conversation)\
        .filter(models.Conversation.id == conversation_id)\
        .first()
    
    if not conversation:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    
    # Get chunks
    chunks = db.query(models.ConversationChunk)\
        .filter(models.ConversationChunk.conversation_id == conversation_id)\
        .order_by(models.ConversationChunk.order_index)\
        .all()
    
    chunk_dicts = [
        {
            "id": chunk.id,
            "order_index": chunk.order_index,
            "text": chunk.chunk_text,
            "author_name": chunk.author_name,
            "author_type": chunk.author_type,
            "timestamp": chunk.timestamp.isoformat() if chunk.timestamp else None
        }
        for chunk in chunks
    ]
    
    logger.info(f"Retrieved conversation {conversation_id} with {len(chunk_dicts)} chunks")
    
    return ConversationDetailResponse(
        id=conversation.id,
        scenario_title=conversation.scenario_title,
        original_title=conversation.original_title,
        url=conversation.url,
        created_at=conversation.created_at,
        chunks=chunk_dicts
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete conversation",
    description="Delete a conversation and all its chunks.",
    operation_id="delete_conversation_v2"
)
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete a conversation and all its chunks.
    
    Args:
        conversation_id: Conversation ID to delete
        db: Database session
        
    Returns:
        Success message with deletion details
        
    Raises:
        NotFoundError: If conversation not found
    """
    logger.info(f"Deleting conversation: id={conversation_id}")
    
    conversation = db.query(models.Conversation)\
        .filter(models.Conversation.id == conversation_id)\
        .first()
    
    if not conversation:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    
    # Count chunks before deletion
    chunk_count = db.query(models.ConversationChunk)\
        .filter(models.ConversationChunk.conversation_id == conversation_id)\
        .count()
    
    # Delete chunks (cascade should handle this, but explicit is better)
    db.query(models.ConversationChunk)\
        .filter(models.ConversationChunk.conversation_id == conversation_id)\
        .delete()
    
    # Delete conversation
    db.delete(conversation)
    db.commit()
    
    logger.info(f"Deleted conversation {conversation_id} and {chunk_count} chunks")
    
    return {
        "message": f"Conversation {conversation_id} deleted successfully",
        "conversation_id": conversation_id,
        "chunks_deleted": chunk_count
    }
