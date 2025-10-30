"""
Data Transfer Objects (DTOs) for the application layer.

DTOs decouple the domain model from external interfaces (REST API, MCP, Slack).
They define the contract for data exchange between layers.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# Conversation Ingestion DTOs
# ============================================================================

@dataclass
class MessageDTO:
    """DTO representing a single message in a conversation."""
    text: str
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class IngestConversationRequest:
    """
    Request to ingest a new conversation.
    
    Attributes:
        messages: List of messages to ingest
        scenario_title: Optional title for the scenario
        original_title: Optional original conversation title
        url: Optional source URL
        metadata: Optional additional metadata
    """
    messages: List[MessageDTO]
    scenario_title: Optional[str] = None
    original_title: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.messages:
            raise ValueError("messages cannot be empty")


@dataclass
class ConversationMetadataDTO:
    """Metadata about a conversation."""
    conversation_id: str
    scenario_title: Optional[str]
    original_title: Optional[str]
    url: Optional[str]
    created_at: datetime
    total_chunks: int


@dataclass
class IngestConversationResponse:
    """
    Response after ingesting a conversation.
    
    Attributes:
        conversation_id: ID of the created conversation
        chunks_created: Number of chunks created
        metadata: Conversation metadata
        success: Whether ingestion succeeded
        error_message: Optional error message if failed
    """
    conversation_id: str
    chunks_created: int
    metadata: ConversationMetadataDTO
    success: bool = True
    error_message: Optional[str] = None


# ============================================================================
# Conversation Search DTOs
# ============================================================================

@dataclass
class SearchFilters:
    """Filters for conversation search."""
    scenario_title: Optional[str] = None
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    min_score: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@dataclass
class SearchConversationRequest:
    """
    Request to search conversations.
    
    Attributes:
        query: Search query text
        top_k: Maximum number of results to return
        filters: Optional search filters
        include_metadata: Whether to include full metadata
    """
    query: str
    top_k: int = 10
    filters: Optional[SearchFilters] = None
    include_metadata: bool = True
    
    def __post_init__(self):
        if not self.query or not self.query.strip():
            raise ValueError("query cannot be empty")
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")
        if self.top_k > 100:
            raise ValueError("top_k cannot exceed 100")


@dataclass
class SearchResultDTO:
    """
    A single search result.
    
    Attributes:
        chunk_id: ID of the matched chunk
        conversation_id: ID of the conversation
        text: The chunk text
        score: Relevance score (0-1)
        author_name: Optional author name
        author_type: Optional author type
        timestamp: Optional timestamp
        order_index: Position in original conversation
    """
    chunk_id: str
    conversation_id: str
    text: str
    score: float
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    order_index: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchConversationResponse:
    """
    Response from conversation search.
    
    Attributes:
        results: List of search results
        query: The original query
        total_results: Total number of results found
        execution_time_ms: Search execution time in milliseconds
        success: Whether search succeeded
        error_message: Optional error message if failed
    """
    results: List[SearchResultDTO]
    query: str
    total_results: int
    execution_time_ms: float
    success: bool = True
    error_message: Optional[str] = None


# ============================================================================
# Conversation Management DTOs
# ============================================================================

@dataclass
class DeleteConversationRequest:
    """Request to delete a conversation."""
    conversation_id: str


@dataclass
class DeleteConversationResponse:
    """Response after deleting a conversation."""
    conversation_id: str
    chunks_deleted: int
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class GetConversationRequest:
    """Request to retrieve a conversation."""
    conversation_id: str
    include_chunks: bool = True
    include_embeddings: bool = False


@dataclass
class ConversationChunkDTO:
    """DTO for a conversation chunk."""
    chunk_id: str
    text: str
    order_index: int
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    embedding: Optional[List[float]] = None


@dataclass
class GetConversationResponse:
    """Response with conversation details."""
    conversation_id: str
    scenario_title: Optional[str]
    original_title: Optional[str]
    url: Optional[str]
    created_at: datetime
    chunks: List[ConversationChunkDTO]
    success: bool = True
    error_message: Optional[str] = None


# ============================================================================
# Validation and Error DTOs
# ============================================================================

@dataclass
class ValidationError:
    """Validation error details."""
    field: str
    message: str
    error_code: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool
    errors: List[ValidationError]
    
    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True, errors=[])
    
    @classmethod
    def failure(cls, errors: List[ValidationError]) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, errors=errors)
