"""
SQLAlchemy implementation of IVectorSearchRepository.

This adapter performs vector similarity search using pgvector operators.
"""
from typing import List, Tuple
import logging
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from app.domain.repositories import IVectorSearchRepository, RepositoryError
from app.domain.entities import ConversationChunk
from app.domain.value_objects import Embedding, RelevanceScore, ConversationId, ChunkId, ChunkText, ChunkMetadata, AuthorInfo
from app.models import ConversationChunk as ConversationChunkModel

logger = logging.getLogger(__name__)


class SqlAlchemyVectorSearchRepository(IVectorSearchRepository):
    """SQLAlchemy implementation of vector search repository using pgvector."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    async def similarity_search(
        self, 
        query_embedding: Embedding, 
        top_k: int = 10
    ) -> List[Tuple[ConversationChunk, RelevanceScore]]:
        """
        Perform vector similarity search using L2 distance.
        
        Uses pgvector's <=> operator for L2 distance calculation.
        
        Args:
            query_embedding: The query vector
            top_k: Maximum number of results to return
            
        Returns:
            List of (chunk, relevance_score) tuples ordered by relevance
            
        Raises:
            RepositoryError: If search fails
        """
        try:
            # Convert L2 distance to relevance score (0.0 to 1.0)
            # Distance of 0 = perfect match (score 1.0)
            # We use 1 / (1 + distance) for normalization
            distance = ConversationChunkModel.embedding.l2_distance(query_embedding.vector)
            
            stmt = (
                select(ConversationChunkModel, distance)
                .where(ConversationChunkModel.embedding.isnot(None))
                .order_by(distance)
                .limit(top_k)
            )
            
            result = self.session.execute(stmt)
            rows = result.all()
            
            logger.debug(f"Vector search returned {len(rows)} results")
            
            # Convert to domain entities with relevance scores
            results = []
            for db_chunk, dist in rows:
                chunk = self._to_entity(db_chunk)
                # Convert distance to relevance score (0.0 to 1.0)
                # Use 1 / (1 + distance) for normalization
                relevance = 1.0 / (1.0 + float(dist))
                results.append((chunk, RelevanceScore(value=relevance)))
            
            return results
            
        except SQLAlchemyError as e:
            logger.error(f"Vector similarity search failed: {e}")
            raise RepositoryError(f"Vector similarity search failed: {e}") from e
    
    async def similarity_search_with_threshold(
        self, 
        query_embedding: Embedding, 
        threshold: float = 0.7,
        top_k: int = 10
    ) -> List[Tuple[ConversationChunk, RelevanceScore]]:
        """
        Perform vector similarity search with relevance threshold.
        
        Args:
            query_embedding: The query vector
            threshold: Minimum relevance score (0.0 to 1.0)
            top_k: Maximum number of results to return
            
        Returns:
            List of (chunk, relevance_score) tuples above threshold
            
        Raises:
            RepositoryError: If search fails
        """
        try:
            # Get all results first
            all_results = await self.similarity_search(query_embedding, top_k * 2)
            
            # Filter by threshold
            filtered_results = [
                (chunk, score) for chunk, score in all_results
                if score.value >= threshold
            ]
            
            # Limit to top_k
            results = filtered_results[:top_k]
            
            logger.debug(f"Vector search with threshold {threshold} returned {len(results)} results")
            return results
            
        except RepositoryError:
            raise
        except Exception as e:
            logger.error(f"Vector similarity search with threshold failed: {e}")
            raise RepositoryError(f"Vector similarity search with threshold failed: {e}") from e
    
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
            # Convert numpy array to list of Python floats
            vector = [float(x) for x in db_chunk.embedding]
            embedding = Embedding(vector=vector)
        
        return ConversationChunk(
            id=ChunkId(db_chunk.id) if db_chunk.id else None,
            conversation_id=ConversationId(db_chunk.conversation_id),
            text=ChunkText(content=db_chunk.chunk_text),
            metadata=chunk_metadata,
            embedding=embedding,
        )
