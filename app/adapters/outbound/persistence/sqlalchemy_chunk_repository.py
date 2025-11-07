"""
SQLAlchemy implementation of IChunkRepository.

This adapter handles conversation chunk persistence with batch operations
and embedding updates.
"""
from typing import List, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.domain.repositories import IChunkRepository, RepositoryError
from app.domain.entities import ConversationChunk
from app.domain.value_objects import ConversationId, ChunkId, ChunkText, ChunkMetadata, AuthorInfo, Embedding
from app.models import ConversationChunk as ConversationChunkModel

logger = logging.getLogger(__name__)


class SqlAlchemyChunkRepository(IChunkRepository):
    """SQLAlchemy implementation of chunk repository."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    async def save_chunks(self, chunks: List[ConversationChunk]) -> List[ConversationChunk]:
        """
        Save multiple chunks in a batch operation.
        
        Uses bulk_save_objects for efficient batch inserts.
        
        Args:
            chunks: List of chunks to save
            
        Returns:
            Saved chunks with IDs assigned
            
        Raises:
            RepositoryError: If batch save fails
        """
        try:
            if not chunks:
                return []
            
            # Convert domain entities to SQLAlchemy models
            db_chunks = [self._to_model(chunk) for chunk in chunks]
            
            # Use merge for each chunk to handle updates
            saved_chunks = []
            for db_chunk in db_chunks:
                merged_chunk = self.session.merge(db_chunk)
                saved_chunks.append(merged_chunk)
            
            self.session.commit()
            
            # Refresh to get IDs
            for db_chunk in saved_chunks:
                self.session.refresh(db_chunk)
            
            logger.info(f"Saved {len(saved_chunks)} chunks in batch")
            
            # Convert back to domain entities
            return [self._to_entity(db_chunk) for db_chunk in saved_chunks]
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to save chunks in batch: {e}")
            raise RepositoryError(f"Failed to save chunks: {e}") from e
    
    async def get_by_conversation(self, conversation_id: ConversationId) -> List[ConversationChunk]:
        """
        Get all chunks for a conversation.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            List of chunks ordered by order_index
        """
        try:
            stmt = (
                select(ConversationChunkModel)
                .where(ConversationChunkModel.conversation_id == conversation_id.value)
                .order_by(ConversationChunkModel.order_index)
            )
            
            result = self.session.execute(stmt)
            db_chunks = result.scalars().all()
            
            logger.debug(f"Retrieved {len(db_chunks)} chunks for conversation {conversation_id.value}")
            return [self._to_entity(db_chunk) for db_chunk in db_chunks]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve chunks for conversation {conversation_id.value}: {e}")
            raise RepositoryError(f"Failed to retrieve chunks: {e}") from e
    
    async def get_by_id(self, chunk_id: ChunkId) -> Optional[ConversationChunk]:
        """
        Retrieve a chunk by ID.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            The chunk if found, None otherwise
        """
        try:
            stmt = select(ConversationChunkModel).where(ConversationChunkModel.id == chunk_id.value)
            result = self.session.execute(stmt)
            db_chunk = result.scalar_one_or_none()
            
            if db_chunk is None:
                logger.debug(f"Chunk not found: {chunk_id.value}")
                return None
            
            logger.debug(f"Retrieved chunk: {chunk_id.value}")
            return self._to_entity(db_chunk)
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve chunk {chunk_id.value}: {e}")
            raise RepositoryError(f"Failed to retrieve chunk: {e}") from e
    
    async def update_embedding(self, chunk_id: ChunkId, embedding: Embedding) -> bool:
        """
        Update the embedding for a specific chunk.
        
        Args:
            chunk_id: The chunk identifier
            embedding: The new embedding
            
        Returns:
            True if updated successfully, False if chunk not found
            
        Raises:
            RepositoryError: If update fails
        """
        try:
            stmt = select(ConversationChunkModel).where(ConversationChunkModel.id == chunk_id.value)
            result = self.session.execute(stmt)
            db_chunk = result.scalar_one_or_none()
            
            if db_chunk is None:
                logger.debug(f"Chunk not found for embedding update: {chunk_id.value}")
                return False
            
            db_chunk.embedding = embedding.vector
            self.session.commit()
            
            logger.info(f"Updated embedding for chunk: {chunk_id.value}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to update embedding for chunk {chunk_id.value}: {e}")
            raise RepositoryError(f"Failed to update embedding: {e}") from e
    
    async def get_chunks_without_embeddings(self) -> List[ConversationChunk]:
        """
        Get all chunks that don't have embeddings yet.
        
        Returns:
            List of chunks without embeddings
        """
        try:
            stmt = select(ConversationChunkModel).where(ConversationChunkModel.embedding.is_(None))
            result = self.session.execute(stmt)
            db_chunks = result.scalars().all()
            
            logger.debug(f"Found {len(db_chunks)} chunks without embeddings")
            return [self._to_entity(db_chunk) for db_chunk in db_chunks]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve chunks without embeddings: {e}")
            raise RepositoryError(f"Failed to retrieve chunks without embeddings: {e}") from e
    
    def _to_model(self, chunk: ConversationChunk) -> ConversationChunkModel:
        """
        Convert domain entity to SQLAlchemy model.
        
        Args:
            chunk: Domain chunk entity
            
        Returns:
            SQLAlchemy chunk model
        """
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
    
    def _to_entity(self, db_chunk: ConversationChunkModel) -> ConversationChunk:
        """
        Convert SQLAlchemy model to domain entity.
        
        Args:
            db_chunk: SQLAlchemy chunk model
            
        Returns:
            Domain chunk entity
        """
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
            embedding = Embedding(vector=db_chunk.embedding)
        
        return ConversationChunk(
            id=ChunkId(db_chunk.id) if db_chunk.id else None,
            conversation_id=ConversationId(db_chunk.conversation_id),
            text=ChunkText(content=db_chunk.chunk_text),
            metadata=chunk_metadata,
            embedding=embedding,
        )
