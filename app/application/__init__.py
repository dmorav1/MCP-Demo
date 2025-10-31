"""
Application Layer - Use Cases and DTOs

This layer orchestrates domain operations and defines the application's use cases.
It depends on domain interfaces (ports) but is independent of infrastructure details.

Key responsibilities:
- Define use cases (application services)
- Create DTOs for data transfer
- Orchestrate domain services and repositories
- Handle cross-cutting concerns (transactions, logging)
"""

from .dto import (
    IngestConversationRequest,
    IngestConversationResponse,
    SearchConversationRequest,
    SearchConversationResponse,
    ConversationMetadataDTO,
    SearchResultDTO
)

from .ingest_conversation import IngestConversationUseCase
from .search_conversations import SearchConversationsUseCase

__all__ = [
    # DTOs
    "IngestConversationRequest",
    "IngestConversationResponse",
    "SearchConversationRequest",
    "SearchConversationResponse",
    "ConversationMetadataDTO",
    "SearchResultDTO",
    # Use Cases
    "IngestConversationUseCase",
    "SearchConversationsUseCase",
]
