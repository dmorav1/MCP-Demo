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
    SearchResultDTO,
    GetConversationRequest,
    GetConversationResponse,
    DeleteConversationRequest,
    DeleteConversationResponse
)

from .ingest_conversation import IngestConversationUseCase
from .search_conversations import SearchConversationsUseCase
from .get_conversation import GetConversationUseCase, ListConversationsUseCase
from .delete_conversation import DeleteConversationUseCase

__all__ = [
    # DTOs
    "IngestConversationRequest",
    "IngestConversationResponse",
    "SearchConversationRequest",
    "SearchConversationResponse",
    "ConversationMetadataDTO",
    "SearchResultDTO",
    "GetConversationRequest",
    "GetConversationResponse",
    "DeleteConversationRequest",
    "DeleteConversationResponse",
    # Use Cases
    "IngestConversationUseCase",
    "SearchConversationsUseCase",
    "GetConversationUseCase",
    "ListConversationsUseCase",
    "DeleteConversationUseCase",
]
