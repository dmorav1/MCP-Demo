"""
SQLAlchemy implementation of IEmbeddingRepository.

This adapter handles embedding storage and retrieval operations.

NOTE: Current implementation uses synchronous SQLAlchemy operations within
async method signatures. This is a known limitation planned for Phase 6
enhancement. Methods are declared as async for API compatibility with
the domain interface, but operations are not truly asynchronous.
See technical debt ticket: Migrate to SQLAlchemy AsyncSession (Phase 6).
"""
from typing import List, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.domain.repositories import IEmbeddingRepository, RepositoryError
from app.domain.value_objects import ChunkId, Embedding
from app.models import ConversationChunk as ConversationChunkModel

logger = logging.getLogger(__name__)


class SqlAlchemyEmbeddingRepository(IEmbeddingRepository):
    """SQLAlchemy implementation of embedding repository."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    async def store_embedding(self, chunk_id: ChunkId, embedding: Embedding) -> bool:
        """
        Store an embedding for a chunk.
        
        Args:
            chunk_id: The chunk identifier
            embedding: The embedding vector
            
        Returns:
            True if stored successfully
            
        Raises:
            RepositoryError: If storage fails
        """
        try:
            stmt = select(ConversationChunkModel).where(ConversationChunkModel.id == chunk_id.value)
            result = self.session.execute(stmt)
            db_chunk = result.scalar_one_or_none()
            
            if db_chunk is None:
                logger.warning(f"Chunk not found for embedding storage: {chunk_id.value}")
                return False
            
            db_chunk.embedding = embedding.vector
            self.session.commit()
            
            logger.info(f"Stored embedding for chunk: {chunk_id.value}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to store embedding for chunk {chunk_id.value}: {e}")
            raise RepositoryError(f"Failed to store embedding: {e}") from e
    
    async def get_embedding(self, chunk_id: ChunkId) -> Optional[Embedding]:
        """
        Retrieve an embedding for a chunk.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            The embedding if found, None otherwise
        """
        try:
            stmt = select(ConversationChunkModel.embedding).where(ConversationChunkModel.id == chunk_id.value)
            result = self.session.execute(stmt)
            embedding_vector = result.scalar_one_or_none()
            
            if embedding_vector is None:
                logger.debug(f"No embedding found for chunk: {chunk_id.value}")
                return None
            
            # Convert numpy array to list of Python floats
            vector = [float(x) for x in embedding_vector]
            logger.debug(f"Retrieved embedding for chunk: {chunk_id.value}")
            return Embedding(vector=vector)
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve embedding for chunk {chunk_id.value}: {e}")
            raise RepositoryError(f"Failed to retrieve embedding: {e}") from e
    
    async def has_embedding(self, chunk_id: ChunkId) -> bool:
        """
        Check if a chunk has an embedding.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            True if chunk has embedding, False otherwise
        """
        try:
            stmt = (
                select(ConversationChunkModel.id)
                .where(ConversationChunkModel.id == chunk_id.value)
                .where(ConversationChunkModel.embedding.isnot(None))
            )
            result = self.session.execute(stmt)
            has_emb = result.scalar_one_or_none() is not None
            
            logger.debug(f"Chunk {chunk_id.value} has embedding: {has_emb}")
            return has_emb
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to check embedding for chunk {chunk_id.value}: {e}")
            raise RepositoryError(f"Failed to check embedding: {e}") from e
    
    async def get_chunks_needing_embeddings(self) -> List[ChunkId]:
        """
        Get chunk IDs that need embeddings generated.
        
        Returns:
            List of chunk IDs without embeddings
        """
        try:
            stmt = (
                select(ConversationChunkModel.id)
                .where(ConversationChunkModel.embedding.is_(None))
            )
            result = self.session.execute(stmt)
            chunk_ids = result.scalars().all()
            
            logger.debug(f"Found {len(chunk_ids)} chunks needing embeddings")
            return [ChunkId(value=chunk_id) for chunk_id in chunk_ids]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve chunks needing embeddings: {e}")
            raise RepositoryError(f"Failed to retrieve chunks needing embeddings: {e}") from e
