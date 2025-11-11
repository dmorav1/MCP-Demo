"""
Get Conversation Use Case

Retrieves conversation details by ID or lists all conversations with pagination.
"""
import logging
from typing import List, Optional

from app.domain.entities import Conversation
from app.domain.value_objects import ConversationId
from app.domain.repositories import IConversationRepository, RepositoryError, ValidationError

from .dto import (
    GetConversationRequest, GetConversationResponse,
    ConversationChunkDTO
)


logger = logging.getLogger(__name__)


class GetConversationUseCase:
    """
    Use case for retrieving conversation details.
    
    Provides access to conversation data through the repository interface.
    """
    
    def __init__(self, conversation_repository: IConversationRepository):
        self.conversation_repo = conversation_repository
        logger.info("GetConversationUseCase initialized")
    
    async def execute(self, request: GetConversationRequest) -> GetConversationResponse:
        """
        Execute the get conversation use case.
        
        Args:
            request: The get conversation request with ID
            
        Returns:
            Response with conversation details
            
        Raises:
            ValidationError: If conversation ID is invalid
            RepositoryError: If retrieval fails
        """
        try:
            logger.info(f"Retrieving conversation: {request.conversation_id}")
            
            # Create conversation ID value object
            conversation_id = ConversationId(request.conversation_id)
            
            # Retrieve from repository
            conversation = await self.conversation_repo.get_by_id(conversation_id)
            
            if not conversation:
                logger.warning(f"Conversation not found: {request.conversation_id}")
                return GetConversationResponse(
                    conversation_id=request.conversation_id,
                    scenario_title=None,
                    original_title=None,
                    url=None,
                    created_at=None,
                    chunks=[],
                    success=False,
                    error_message=f"Conversation with ID {request.conversation_id} not found"
                )
            
            # Convert to DTO
            return self._build_response(conversation, request.include_chunks, request.include_embeddings)
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return GetConversationResponse(
                conversation_id=request.conversation_id,
                scenario_title=None,
                original_title=None,
                url=None,
                created_at=None,
                chunks=[],
                success=False,
                error_message=f"Validation error: {str(e)}"
            )
        except RepositoryError as e:
            logger.error(f"Repository error: {str(e)}")
            return GetConversationResponse(
                conversation_id=request.conversation_id,
                scenario_title=None,
                original_title=None,
                url=None,
                created_at=None,
                chunks=[],
                success=False,
                error_message=f"Retrieval failed: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")
            return GetConversationResponse(
                conversation_id=request.conversation_id,
                scenario_title=None,
                original_title=None,
                url=None,
                created_at=None,
                chunks=[],
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _build_response(
        self,
        conversation: Conversation,
        include_chunks: bool,
        include_embeddings: bool
    ) -> GetConversationResponse:
        """Build the response DTO from domain entity."""
        chunks = []
        
        if include_chunks and conversation.chunks:
            for chunk in conversation.chunks:
                chunk_dto = ConversationChunkDTO(
                    chunk_id=str(chunk.id.value) if chunk.id else "",
                    text=chunk.text.content,
                    order_index=chunk.metadata.order_index,
                    author_name=chunk.metadata.author_info.name if chunk.metadata.author_info else None,
                    author_type=chunk.metadata.author_info.author_type if chunk.metadata.author_info else None,
                    timestamp=chunk.metadata.timestamp,
                    embedding=chunk.embedding.values if include_embeddings and chunk.embedding else None
                )
                chunks.append(chunk_dto)
        
        return GetConversationResponse(
            conversation_id=str(conversation.id.value),
            scenario_title=conversation.metadata.scenario_title,
            original_title=conversation.metadata.original_title,
            url=conversation.metadata.url,
            created_at=conversation.metadata.created_at,
            chunks=chunks,
            success=True,
            error_message=None
        )


class ListConversationsUseCase:
    """
    Use case for listing conversations with pagination.
    """
    
    def __init__(self, conversation_repository: IConversationRepository):
        self.conversation_repo = conversation_repository
        logger.info("ListConversationsUseCase initialized")
    
    async def execute(self, skip: int = 0, limit: int = 100) -> List[GetConversationResponse]:
        """
        Execute the list conversations use case.
        
        Args:
            skip: Number of conversations to skip
            limit: Maximum number to return
            
        Returns:
            List of conversation responses
        """
        try:
            logger.info(f"Listing conversations (skip={skip}, limit={limit})")
            
            # Retrieve from repository
            conversations = await self.conversation_repo.get_all(skip=skip, limit=limit)
            
            # Convert to DTOs
            responses = []
            for conversation in conversations:
                response = GetConversationResponse(
                    conversation_id=str(conversation.id.value),
                    scenario_title=conversation.metadata.scenario_title,
                    original_title=conversation.metadata.original_title,
                    url=conversation.metadata.url,
                    created_at=conversation.metadata.created_at,
                    chunks=[],  # Don't include chunks in list view
                    success=True,
                    error_message=None
                )
                responses.append(response)
            
            logger.info(f"Retrieved {len(responses)} conversations")
            return responses
            
        except Exception as e:
            logger.exception(f"Error listing conversations: {str(e)}")
            return []
