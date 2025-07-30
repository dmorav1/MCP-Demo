from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete
from typing import List, Dict, Any, Optional
from app import models, schemas
from app.services import ConversationProcessor
from app.logging_config import get_logger
import numpy as np

logger = get_logger(__name__)

class ConversationCRUD:
    def __init__(self, db: AsyncSession, processor: ConversationProcessor):
        self.db = db
        self.processor = processor
        self.embedding_service = processor.embedding_service # Get from processor
        logger.info("🗄️ ConversationCRUD initialized with injected processor")

    async def create_conversation(self, conversation_data: schemas.ConversationIngest) -> models.Conversation:
        # This will be fully refactored in Phase 3 for atomicity
        logger.info(f"💾 Creating new conversation: {conversation_data.scenario_title}")
        processed_data = await self.processor.process_conversation_for_ingestion(conversation_data.model_dump())
        db_conversation = models.Conversation(
            scenario_title=processed_data.get('scenario_title'),
            original_title=processed_data.get('original_title'),
            url=processed_data.get('url')
        )
        self.db.add(db_conversation)
        await self.db.commit()
        await self.db.refresh(db_conversation)
        
        for chunk_data in processed_data.get('chunks', []):
            db_chunk = models.ConversationChunk(
                conversation_id=db_conversation.id,
                order_index=chunk_data['order_index'],
                chunk_text=chunk_data['chunk_text'],
                embedding=chunk_data.get('embedding'),
                author_name=chunk_data.get('author_name'),
                author_type=chunk_data.get('author_type'),
                timestamp=chunk_data.get('timestamp')
            )
            self.db.add(db_chunk)
        await self.db.commit()
        await self.db.refresh(db_conversation)
        return db_conversation

    async def get_conversation(self, conversation_id: int) -> Optional[models.Conversation]:
        logger.info(f"🔍 Fetching conversation with ID: {conversation_id}")
        result = await self.db.execute(
            select(models.Conversation).filter(models.Conversation.id == conversation_id)
        )
        return result.scalars().first()

    async def get_conversations(self, skip: int = 0, limit: int = 100) -> List[models.Conversation]:
        logger.info(f"📋 Fetching conversations (skip={skip}, limit={limit})")
        result = await self.db.execute(
            select(models.Conversation).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def search_conversations(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # This will be fully refactored in Phase 3 for safety and performance
        logger.info(f"🔍 Searching conversations for query: '{query}' (top_k={top_k})")
        # REMOVE manual instantiation of EmbeddingService
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # Using l2_distance is preferred, but we'll stick to the raw query for now and fix in Phase 3
        sql_query = text("""
            SELECT 
                c.id as conversation_id,
                c.scenario_title,
                c.original_title,
                c.url,
                c.created_at,
                cc.id as chunk_id,
                cc.order_index,
                cc.chunk_text,
                cc.author_name,
                cc.author_type,
                cc.timestamp,
                cc.embedding <=> :query_embedding as distance
            FROM conversations c
            JOIN conversation_chunks cc ON c.id = cc.conversation_id
            WHERE cc.embedding IS NOT NULL
            ORDER BY cc.embedding <=> :query_embedding
            LIMIT :limit
        """)
        
        result = await self.db.execute(sql_query, {
            'query_embedding': str(list(query_embedding)), # Pass as string representation of list
            'limit': top_k
        })
        
        search_results = []
        for row in result:
            search_results.append({
                'conversation_id': row.conversation_id,
                'scenario_title': row.scenario_title,
                'original_title': row.original_title,
                'url': row.url,
                'created_at': row.created_at,
                'chunk_id': row.chunk_id,
                'order_index': row.order_index,
                'chunk_text': row.chunk_text,
                'author_name': row.author_name,
                'author_type': row.author_type,
                'timestamp': row.timestamp,
                'relevance_score': 1.0 - row.distance
            })
        
        logger.info(f"✅ Search completed: found {len(search_results)} results")
        return search_results

    async def delete_conversation(self, conversation_id: int) -> bool:
        logger.info(f"🗑️ Deleting conversation with ID: {conversation_id}")
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            await self.db.execute(
                delete(models.ConversationChunk).where(models.ConversationChunk.conversation_id == conversation_id)
            )
            await self.db.delete(conversation)
            await self.db.commit()
            logger.info(f"✅ Successfully deleted conversation: {conversation.scenario_title}")
            return True
        return False
