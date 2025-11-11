"""
Delete Conversation Use Case

Deletes a conversation and all associated chunks.
"""
import logging

from app.domain.value_objects import ConversationId
from app.domain.repositories import IConversationRepository, RepositoryError, ValidationError

from .dto import DeleteConversationRequest, DeleteConversationResponse


logger = logging.getLogger(__name__)


class DeleteConversationUseCase:
    """
    Use case for deleting conversations.
    
    Removes a conversation and all its associated chunks from the system.
    """
    
    def __init__(
        self,
        conversation_repository: IConversationRepository
    ):
        self.conversation_repo = conversation_repository
        logger.info("DeleteConversationUseCase initialized")
    
    async def execute(self, request: DeleteConversationRequest) -> DeleteConversationResponse:
        """
        Execute the delete conversation use case.
        
        Args:
            request: The delete request with conversation ID
            
        Returns:
            Response with deletion status
            
        Raises:
            ValidationError: If conversation ID is invalid
            RepositoryError: If deletion fails
        """
        try:
            logger.info(f"Deleting conversation: {request.conversation_id}")
            
            # Create conversation ID value object
            conversation_id = ConversationId(request.conversation_id)
            
            # Check if conversation exists
            exists = await self.conversation_repo.exists(conversation_id)
            
            if not exists:
                logger.warning(f"Conversation not found: {request.conversation_id}")
                return DeleteConversationResponse(
                    conversation_id=request.conversation_id,
                    chunks_deleted=0,
                    success=False,
                    error_message=f"Conversation with ID {request.conversation_id} not found"
                )
            
            # Get conversation to count chunks before deletion
            conversation = await self.conversation_repo.get_by_id(conversation_id)
            chunks_count = len(conversation.chunks) if conversation and conversation.chunks else 0
            
            # Delete conversation (should cascade to chunks)
            deleted = await self.conversation_repo.delete(conversation_id)
            
            if not deleted:
                logger.error(f"Failed to delete conversation: {request.conversation_id}")
                return DeleteConversationResponse(
                    conversation_id=request.conversation_id,
                    chunks_deleted=0,
                    success=False,
                    error_message="Failed to delete conversation"
                )
            
            logger.info(f"Successfully deleted conversation: {request.conversation_id} with {chunks_count} chunks")
            
            return DeleteConversationResponse(
                conversation_id=request.conversation_id,
                chunks_deleted=chunks_count,
                success=True,
                error_message=None
            )
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return DeleteConversationResponse(
                conversation_id=request.conversation_id,
                chunks_deleted=0,
                success=False,
                error_message=f"Validation error: {str(e)}"
            )
        except RepositoryError as e:
            logger.error(f"Repository error: {str(e)}")
            return DeleteConversationResponse(
                conversation_id=request.conversation_id,
                chunks_deleted=0,
                success=False,
                error_message=f"Deletion failed: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")
            return DeleteConversationResponse(
                conversation_id=request.conversation_id,
                chunks_deleted=0,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
