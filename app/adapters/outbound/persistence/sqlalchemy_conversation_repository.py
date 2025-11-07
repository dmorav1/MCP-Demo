"""
SQLAlchemy implementation of IConversationRepository.

This adapter converts between domain entities and SQLAlchemy models,
implementing the repository interface without leaking infrastructure details
into the domain layer.
"""
from typing import List, Optional
import logging
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.domain.repositories import IConversationRepository, RepositoryError
from app.domain.entities import Conversation
from app.domain.value_objects import ConversationId, ConversationMetadata, ChunkId, ChunkText, ChunkMetadata, AuthorInfo, Embedding
from app.models import Conversation as ConversationModel, ConversationChunk as ConversationChunkModel

logger = logging.getLogger(__name__)


class SqlAlchemyConversationRepository(IConversationRepository):
    """SQLAlchemy implementation of conversation repository."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    async def save(self, conversation: Conversation) -> Conversation:
        """
        Persist a conversation and return it with assigned ID.
        
        Uses merge() for upsert behavior - creates new or updates existing.
        Handles transaction commit/rollback properly.
        
        Args:
            conversation: The conversation to save
            
        Returns:
            The saved conversation with ID assigned
            
        Raises:
            RepositoryError: If save operation fails
        """
        try:
            # Convert domain entity to SQLAlchemy model
            db_conversation = self._to_model(conversation)
            
            # Use merge for upsert behavior
            db_conversation = self.session.merge(db_conversation)
            self.session.commit()
            self.session.refresh(db_conversation)
            
            logger.info(f"Saved conversation with ID: {db_conversation.id}")
            
            # Convert back to domain entity
            return self._to_entity(db_conversation)
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to save conversation: {e}")
            raise RepositoryError(f"Failed to save conversation: {e}") from e
    
    async def get_by_id(self, conversation_id: ConversationId) -> Optional[Conversation]:
        """
        Retrieve a conversation by ID with eager loading of chunks.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            The conversation if found, None otherwise
        """
        try:
            # Use selectinload for efficient eager loading of chunks
            stmt = (
                select(ConversationModel)
                .where(ConversationModel.id == conversation_id.value)
                .options(selectinload(ConversationModel.chunks))
            )
            
            result = self.session.execute(stmt)
            db_conversation = result.scalar_one_or_none()
            
            if db_conversation is None:
                logger.debug(f"Conversation not found: {conversation_id.value}")
                return None
            
            logger.debug(f"Retrieved conversation: {conversation_id.value}")
            return self._to_entity(db_conversation)
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve conversation {conversation_id.value}: {e}")
            raise RepositoryError(f"Failed to retrieve conversation: {e}") from e
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        Retrieve conversations with pagination.
        
        Args:
            skip: Number of conversations to skip
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversations ordered by creation date (newest first)
        """
        try:
            stmt = (
                select(ConversationModel)
                .options(selectinload(ConversationModel.chunks))
                .order_by(ConversationModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            
            result = self.session.execute(stmt)
            db_conversations = result.scalars().all()
            
            logger.debug(f"Retrieved {len(db_conversations)} conversations (skip={skip}, limit={limit})")
            return [self._to_entity(db_conv) for db_conv in db_conversations]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve conversations: {e}")
            raise RepositoryError(f"Failed to retrieve conversations: {e}") from e
    
    async def delete(self, conversation_id: ConversationId) -> bool:
        """
        Delete a conversation and all its chunks (cascade).
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: If deletion fails
        """
        try:
            stmt = select(ConversationModel).where(ConversationModel.id == conversation_id.value)
            result = self.session.execute(stmt)
            db_conversation = result.scalar_one_or_none()
            
            if db_conversation is None:
                logger.debug(f"Conversation not found for deletion: {conversation_id.value}")
                return False
            
            self.session.delete(db_conversation)
            self.session.commit()
            
            logger.info(f"Deleted conversation: {conversation_id.value}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to delete conversation {conversation_id.value}: {e}")
            raise RepositoryError(f"Failed to delete conversation: {e}") from e
    
    async def exists(self, conversation_id: ConversationId) -> bool:
        """
        Check if a conversation exists.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            True if conversation exists, False otherwise
        """
        try:
            stmt = select(ConversationModel.id).where(ConversationModel.id == conversation_id.value)
            result = self.session.execute(stmt)
            exists = result.scalar_one_or_none() is not None
            
            logger.debug(f"Conversation {conversation_id.value} exists: {exists}")
            return exists
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to check conversation existence: {e}")
            raise RepositoryError(f"Failed to check conversation existence: {e}") from e
    
    async def count(self) -> int:
        """
        Get total number of conversations.
        
        Returns:
            Total conversation count
        """
        try:
            stmt = select(ConversationModel)
            result = self.session.execute(stmt)
            count = len(result.scalars().all())
            
            logger.debug(f"Total conversations: {count}")
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to count conversations: {e}")
            raise RepositoryError(f"Failed to count conversations: {e}") from e
    
    def _to_model(self, conversation: Conversation) -> ConversationModel:
        """
        Convert domain entity to SQLAlchemy model.
        
        Args:
            conversation: Domain conversation entity
            
        Returns:
            SQLAlchemy conversation model
        """
        db_conversation = ConversationModel(
            id=conversation.id.value if conversation.id else None,
            scenario_title=conversation.metadata.scenario_title,
            original_title=conversation.metadata.original_title,
            url=conversation.metadata.url,
            created_at=conversation.metadata.created_at,
        )
        
        # Convert chunks if present
        db_conversation.chunks = [
            self._chunk_to_model(chunk) for chunk in conversation.chunks
        ]
        
        return db_conversation
    
    def _chunk_to_model(self, chunk) -> ConversationChunkModel:
        """Convert domain chunk to SQLAlchemy model."""
        return ConversationChunkModel(
            id=chunk.id.value if chunk.id else None,
            conversation_id=chunk.conversation_id.value,
            order_index=chunk.metadata.order_index,
            chunk_text=chunk.text.content,
            embedding=chunk.embedding.vector if chunk.embedding else None,
            author_name=chunk.metadata.author_info.name,
            author_type=chunk.metadata.author_info.author_type,
            timestamp=chunk.metadata.timestamp,
        )
    
    def _to_entity(self, db_conversation: ConversationModel) -> Conversation:
        """
        Convert SQLAlchemy model to domain entity.
        
        Args:
            db_conversation: SQLAlchemy conversation model
            
        Returns:
            Domain conversation entity
        """
        from app.domain.entities import Conversation, ConversationChunk
        
        # Create conversation metadata
        metadata = ConversationMetadata(
            scenario_title=db_conversation.scenario_title,
            original_title=db_conversation.original_title,
            url=db_conversation.url,
            created_at=db_conversation.created_at,
        )
        
        # Convert chunks
        chunks = [
            self._chunk_to_entity(db_chunk, ConversationId(db_conversation.id))
            for db_chunk in db_conversation.chunks
        ]
        
        return Conversation(
            id=ConversationId(db_conversation.id),
            metadata=metadata,
            chunks=chunks,
        )
    
    def _chunk_to_entity(self, db_chunk: ConversationChunkModel, conversation_id: ConversationId):
        """Convert SQLAlchemy chunk model to domain entity."""
        from app.domain.entities import ConversationChunk
        
        # Create chunk metadata
        chunk_metadata = ChunkMetadata(
            order_index=db_chunk.order_index,
            author_info=AuthorInfo(
                name=db_chunk.author_name,
                author_type=db_chunk.author_type or "human",
            ),
            timestamp=db_chunk.timestamp,
        )
        
        # Create embedding if present
        embedding = None
        if db_chunk.embedding is not None:
            # Convert numpy array to list of Python floats
            vector = [float(x) for x in db_chunk.embedding]
            embedding = Embedding(vector=vector)
        
        return ConversationChunk(
            id=ChunkId(db_chunk.id) if db_chunk.id else None,
            conversation_id=conversation_id,
            text=ChunkText(content=db_chunk.chunk_text),
            metadata=chunk_metadata,
            embedding=embedding,
        )
