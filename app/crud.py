"""
CRUD operations for conversations and chunks.
Handles database operations with proper error handling and logging.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.services import EmbeddingService
from app.logging_config import get_logger

logger = get_logger(__name__)

class ConversationCRUD:
    """
    CRUD operations for conversations and chunks.
    Encapsulates all database operations with proper session management.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._embed = EmbeddingService()

    def get_conversations(self, skip: int = 0, limit: int = 100) -> List[models.Conversation]:
        logger.info(f"Fetching conversations skip={skip} limit={limit}")
        # Eager-load chunks to avoid empty lists caused by lazy-load timing
        q = (
            self.db.query(models.Conversation)
            .options(selectinload(models.Conversation.chunks))
            .order_by(models.Conversation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = q.all()
        logger.info(f"Fetched conversations={len(items)}")
        return items

    async def create_conversation(self, data: schemas.ConversationIngest) -> models.Conversation:
        logger.info("Creating conversation in DB")
        conv = models.Conversation(
            scenario_title=data.scenario_title,
            original_title=data.original_title,
            url=data.url,
        )
        self.db.add(conv)
        self.db.flush()
        self.db.commit()
        logger.info(f"Created conversation id={conv.id}")
        return conv

    def get_conversation(self, conversation_id: int) -> Optional[models.Conversation]:
        logger.info(f"Fetching conversation id={conversation_id}")
        return self.db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()

    def delete_conversation(self, conversation_id: int) -> bool:
        logger.info(f"Deleting conversation id={conversation_id}")
        obj = self.get_conversation(conversation_id)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True

    async def search_conversations(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []

        # 1) Embed query (local model → 384, padded to 1536 by service)
        qvec = await self._embed.generate_embedding(q)

        # 2) Vector search (L2). Use <-> with proper casting for pgvector
        sql = text("""
            SELECT
                ch.id              AS id,
                ch.conversation_id AS conversation_id,
                ch.order_index     AS order_index,
                ch.chunk_text      AS chunk_text,
                ch.author_name     AS author_name,
                ch.author_type     AS author_type,
                ch.timestamp       AS timestamp,
                conv.scenario_title AS scenario_title,
                conv.original_title AS original_title,
                conv.url            AS url,
                conv.created_at     AS created_at,
                (ch.embedding <-> CAST(:qvec AS vector)) AS score
            FROM conversation_chunks ch
            JOIN conversations conv ON conv.id = ch.conversation_id
            WHERE ch.embedding IS NOT NULL
            ORDER BY ch.embedding <-> CAST(:qvec AS vector)
            LIMIT :k
        """)
        rows = self.db.execute(sql, {"qvec": str(qvec), "k": int(top_k)}).mappings().all()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "conversation_id": r["conversation_id"],
                "order_index": r["order_index"],
                "chunk_text": r["chunk_text"],
                "author_name": r["author_name"],
                "author_type": r["author_type"],
                "timestamp": r["timestamp"],
                "scenario_title": r["scenario_title"],
                "original_title": r["original_title"],
                "url": r["url"],
                "created_at": r["created_at"],
                "relevance_score": float(r["score"])
            })
        logger.info(f"🔎 search '{q}' → {len(results)} hits")
        return results
    
    def create_conversation(
        self,
        scenario_title: str,
        chunks_data: List[dict]
    ) -> models.Conversation:
        """
        Create a new conversation with associated chunks.
        
        Args:
            scenario_title: Title of the conversation scenario
            chunks_data: List of dicts containing chunk content and metadata
            
        Returns:
            Created Conversation object with chunks loaded
        """
        logger.info(f"📝 Creating conversation: '{scenario_title}' with {len(chunks_data)} chunks")
        
        try:
            # Create conversation
            conversation = models.Conversation(scenario_title=scenario_title)
            self.db.add(conversation)
            self.db.flush()  # Get conversation_id without committing
            
            # Create chunks
            for idx, chunk_data in enumerate(chunks_data):
                chunk = models.ConversationChunk(
                    conversation_id=conversation.id,
                    order_index=idx,
                    chunk_text=chunk_data["content"],
                    author_name=chunk_data.get("author_name"),
                    author_type=chunk_data.get("author_type", "human"),
                    embedding=chunk_data.get("embedding")
                )
                self.db.add(chunk)
            
            self.db.commit()
            self.db.refresh(conversation)
            
            logger.info(f"✅ Created conversation {conversation.id}")
            return conversation
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to create conversation: {e}")
            raise
    
    def get_conversation(self, conversation_id: int) -> Optional[schemas.ConversationResponse]:
        """
        Get a single conversation with all chunks by ID.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            ConversationResponse with chunks, or None if not found
        """
        logger.info(f"🔍 Fetching conversation {conversation_id}")
        
        try:
            conversation = (
                self.db.query(models.Conversation)
                .options(selectinload(models.Conversation.chunks))
                .filter(models.Conversation.id == conversation_id)
                .first()
            )
            
            if not conversation:
                logger.warning(f"⚠️ Conversation {conversation_id} not found")
                return None
            
            # Convert to response schema
            chunks = []
            for chunk in sorted(conversation.chunks, key=lambda c: c.order_index):
                chunks.append(schemas.ConversationChunkResponse(
                    id=chunk.id,
                    conversation_id=chunk.conversation_id,
                    order_index=chunk.order_index,
                    chunk_text=chunk.chunk_text,
                    author_name=chunk.author_name,
                    author_type=chunk.author_type,
                    timestamp=chunk.timestamp
                ))
            
            response = schemas.ConversationResponse(
                id=conversation.id,
                scenario_title=conversation.scenario_title,
                created_at=conversation.created_at,
                chunks=chunks
            )
            
            logger.info(f"✅ Found conversation {conversation_id} with {len(chunks)} chunks")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversation: {e}")
            raise
    
    def get_conversations(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> List[schemas.ConversationResponse]:
        """
        Get list of conversations with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of ConversationResponse objects
        """
        logger.info(f"📋 Fetching conversations: skip={skip}, limit={limit}")
        
        try:
            conversations = (
                self.db.query(models.Conversation)
                .options(selectinload(models.Conversation.chunks))
                .order_by(models.Conversation.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            response = []
            for conv in conversations:
                chunk_responses = []
                for chunk in sorted(conv.chunks, key=lambda c: c.order_index):
                    chunk_responses.append(schemas.ConversationChunkResponse(
                        id=chunk.id,
                        conversation_id=chunk.conversation_id,
                        order_index=chunk.order_index,
                        chunk_text=chunk.chunk_text,
                        author_name=chunk.author_name,
                        author_type=chunk.author_type,
                        timestamp=chunk.timestamp
                    ))
                response.append(schemas.ConversationResponse(
                    id=conv.id,
                    scenario_title=conv.scenario_title,
                    created_at=conv.created_at,
                    chunks=chunk_responses
                ))
            
            logger.info(f"✅ Retrieved {len(response)} conversations")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to get conversations: {e}")
            raise
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Delete a conversation and all associated chunks.
        
        Args:
            conversation_id: ID of the conversation to delete
            
        Returns:
            True if deleted, False if not found
        """
        logger.info(f"🗑️ Deleting conversation {conversation_id}")
        
        try:
            conversation = (
                self.db.query(models.Conversation)
                .filter(models.Conversation.id == conversation_id)
                .first()
            )
            
            if not conversation:
                logger.warning(f"⚠️ Conversation {conversation_id} not found")
                return False
            
            # Delete conversation (chunks deleted via CASCADE)
            self.db.delete(conversation)
            self.db.commit()
            
            logger.info(f"✅ Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to delete conversation: {e}")
            raise
    
    async def search_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[schemas.SearchResult]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query vector (1536 dimensions)
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects ranked by similarity
        """
        logger.info(f"🔍 Vector search: top_k={top_k}, embedding_dim={len(query_embedding)}")
        
        try:
            # Use pgvector L2 distance operator
            results = (
                self.db.query(
                    models.ConversationChunk,
                    models.Conversation,
                    models.ConversationChunk.embedding.l2_distance(query_embedding).label("distance")
                )
                .join(models.Conversation)
                .order_by(text("distance"))
                .limit(top_k)
                .all()
            )
            
            search_results = []
            for chunk, conversation, distance in results:
                # Convert L2 distance to similarity score (0-1 range)
                # Lower distance = higher similarity
                similarity = max(0.0, 1.0 - (distance / 2.0))
                
                search_results.append(schemas.SearchResult(
                    chunk_id=chunk.chunk_id,
                    conversation_id=chunk.conversation_id,
                    scenario_title=conversation.scenario_title,
                    matched_content=chunk.content,
                    author_info={
                        "name": chunk.author_name,
                        "type": chunk.author_type
                    },
                    relevance_score=similarity
                ))
            
            logger.info(f"✅ Found {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            raise


# Legacy function wrappers for backward compatibility
async def search_conversations(
    db: Session,
    query: str,
    top_k: int = 5
) -> List[schemas.SearchResult]:
    """Wrapper now delegates to ConversationCRUD.search_conversations which handles embedding + vector SQL."""
    crud_instance = ConversationCRUD(db)
    return await crud_instance.search_conversations(query, top_k)


def get_conversation(db: Session, conversation_id: int) -> Optional[schemas.ConversationResponse]:
    """Legacy wrapper for get_conversation."""
    crud = ConversationCRUD(db)
    return crud.get_conversation(conversation_id)


def get_conversations(
    db: Session,
    skip: int = 0,
    limit: int = 50
) -> List[schemas.ConversationResponse]:
    """Legacy wrapper for get_conversations."""
    crud = ConversationCRUD(db)
    return crud.get_conversations(skip, limit)


def delete_conversation(db: Session, conversation_id: int) -> bool:
    """Legacy wrapper for delete_conversation."""
    crud = ConversationCRUD(db)
    return crud.delete_conversation(conversation_id)
