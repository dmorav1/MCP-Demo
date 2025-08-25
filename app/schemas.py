from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging
from app.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)
logger.info("📦 Loading Pydantic schemas...")

class ConversationChunkBase(BaseModel):
    order_index: int
    chunk_text: str
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    timestamp: Optional[datetime] = None

class ConversationChunkCreate(ConversationChunkBase):
    pass

class ConversationChunk(ConversationChunkBase):
    id: int
    conversation_id: int
    embedding: Optional[List[float]] = None

    class Config:
        from_attributes = True

# Response-only schemas (without embeddings)
class ConversationChunkResponse(ConversationChunkBase):
    id: int
    conversation_id: int

    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    scenario_title: Optional[str] = None
    original_title: Optional[str] = None
    url: Optional[str] = None

class ConversationCreate(ConversationBase):
    chunks: List[ConversationChunkCreate] = []

class Conversation(ConversationBase):
    id: int
    created_at: datetime
    chunks: List[ConversationChunk] = []

    class Config:
        from_attributes = True

class ConversationResponse(ConversationBase):
    id: int
    created_at: datetime
    chunks: List[ConversationChunkResponse] = []

    class Config:
        from_attributes = True

class ConversationIngest(BaseModel):
    scenario_title: Optional[str] = None
    original_title: Optional[str] = None
    url: Optional[str] = None
    messages: List[dict] = Field(..., description="List of conversation messages")

class SearchResult(BaseModel):
    conversation: Conversation
    relevance_score: float
    matched_chunks: List[ConversationChunk]

class SearchResultResponse(BaseModel):
    conversation: ConversationResponse
    relevance_score: float
    matched_chunks: List[ConversationChunkResponse]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total_results: int

class SearchResponseNew(BaseModel):
    results: List[SearchResultResponse]
    query: str
    total_results: int

logger.info("✅ Pydantic schemas loaded successfully")
