from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Dict, Any, Optional
from app import models, schemas
from app.services import ConversationProcessor
from app.logging_config import get_logger

logger = get_logger(__name__)


class ConversationCRUD:
    def __init__(self, db: AsyncSession, processor: ConversationProcessor):
        self.db = db
        self.processor = processor
        self.embedding_service = processor.embedding_service  # Get from processor
        logger.info("🗄️ ConversationCRUD initialized with injected processor")

    async def create_conversation(
        self, conversation_data: schemas.ConversationIngest
    ) -> models.Conversation:
        logger.info(
            f"💾 Atomically creating new conversation: {conversation_data.scenario_title}"
        )
        processed_data = await self.processor.process_conversation_for_ingestion(
            conversation_data.model_dump()
        )

        db_conversation = models.Conversation(
            scenario_title=processed_data.get("scenario_title"),
            original_title=processed_data.get("original_title"),
            url=processed_data.get("url"),
        )
        self.db.add(db_conversation)

        # Flush to get the conversation ID before creating chunks
        await self.db.flush()

        db_chunks = [
            models.ConversationChunk(
                conversation_id=db_conversation.id,
                order_index=chunk_data["order_index"],
                chunk_text=chunk_data["chunk_text"],
                embedding=chunk_data.get("embedding"),
                author_name=chunk_data.get("author_name"),
                author_type=chunk_data.get("author_type"),
                timestamp=chunk_data.get("timestamp"),
            )
            for chunk_data in processed_data.get("chunks", [])
        ]

        self.db.add_all(db_chunks)
        await self.db.commit()  # A single, atomic commit for conversation and all its chunks
        await self.db.refresh(
            db_conversation
        )  # Refresh to load the .chunks relationship

        logger.info(
            f"✅ Successfully created conversation with {len(db_chunks)} chunks in one transaction."
        )
        return db_conversation

    async def get_conversation(
        self, conversation_id: int
    ) -> Optional[models.Conversation]:
        logger.info(f"🔍 Fetching conversation with ID: {conversation_id}")
        result = await self.db.execute(
            select(models.Conversation).filter(
                models.Conversation.id == conversation_id
            )
        )
        return result.scalars().first()

    async def get_conversations(
        self, skip: int = 0, limit: int = 100
    ) -> List[models.Conversation]:
        logger.info(f"📋 Fetching conversations (skip={skip}, limit={limit})")
        result = await self.db.execute(
            select(models.Conversation).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def search_conversations(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        logger.info(
            f"🔍 Performing ORM-based vector search for query: '{query}' (top_k={top_k})"
        )
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Idiomatic, type-safe vector search query
        stmt = (
            select(
                models.Conversation.id.label("conversation_id"),
                models.Conversation.scenario_title,
                models.Conversation.original_title,
                models.Conversation.url,
                models.Conversation.created_at,
                models.ConversationChunk.id.label("chunk_id"),
                models.ConversationChunk.order_index,
                models.ConversationChunk.chunk_text,
                models.ConversationChunk.author_name,
                models.ConversationChunk.author_type,
                models.ConversationChunk.timestamp,
                models.ConversationChunk.embedding.l2_distance(query_embedding).label(
                    "distance"
                ),
            )
            .join(models.Conversation.chunks)
            .filter(models.ConversationChunk.embedding.is_not(None))
            .order_by(models.ConversationChunk.embedding.l2_distance(query_embedding))
            .limit(top_k)
        )

        result = await self.db.execute(stmt)

        search_results = [
            {
                "conversation_id": row.conversation_id,
                "scenario_title": row.scenario_title,
                "original_title": row.original_title,
                "url": row.url,
                "created_at": row.created_at,
                "chunk_id": row.chunk_id,
                "order_index": row.order_index,
                "chunk_text": row.chunk_text,
                "author_name": row.author_name,
                "author_type": row.author_type,
                "timestamp": row.timestamp,
                "relevance_score": 1.0 - row.distance,
            }
            for row in result.mappings()
        ]

        logger.info(f"✅ ORM search completed: found {len(search_results)} results")
        return search_results

    async def delete_conversation(self, conversation_id: int) -> bool:
        logger.info(f"🗑️ Deleting conversation with ID: {conversation_id}")
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            await self.db.execute(
                delete(models.ConversationChunk).where(
                    models.ConversationChunk.conversation_id == conversation_id
                )
            )
            await self.db.delete(conversation)
            await self.db.commit()
            logger.info(
                f"✅ Successfully deleted conversation: {conversation.scenario_title}"
            )
            return True
        return False
