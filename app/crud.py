from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from app import models, schemas
from app.services import ConversationProcessor
import json

class ConversationCRUD:
    def __init__(self, db: Session):
        self.db = db
        self.processor = ConversationProcessor()

    async def create_conversation(self, conversation_data: schemas.ConversationIngest) -> models.Conversation:
        """
        Create a new conversation with chunks and embeddings
        """
        # Process the conversation data
        processed_data = await self.processor.process_conversation_for_ingestion(
            conversation_data.dict()
        )
        
        # Create conversation record
        db_conversation = models.Conversation(
            scenario_title=processed_data.get('scenario_title'),
            original_title=processed_data.get('original_title'),
            url=processed_data.get('url')
        )
        self.db.add(db_conversation)
        self.db.commit()
        self.db.refresh(db_conversation)
        
        # Create conversation chunks
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
        
        self.db.commit()
        self.db.refresh(db_conversation)
        return db_conversation

    def get_conversation(self, conversation_id: int) -> Optional[models.Conversation]:
        """
        Get a conversation by ID
        """
        return self.db.query(models.Conversation).filter(
            models.Conversation.id == conversation_id
        ).first()

    def get_conversations(self, skip: int = 0, limit: int = 100) -> List[models.Conversation]:
        """
        Get all conversations with pagination
        """
        return self.db.query(models.Conversation).offset(skip).limit(limit).all()

    async def search_conversations(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for conversations using vector similarity
        """
        # Generate embedding for the search query
        from app.services import EmbeddingService
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.generate_embedding(query)
        
        # Convert embedding to PostgreSQL array format
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Perform vector similarity search
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
        
        result = self.db.execute(sql_query, {
            'query_embedding': embedding_str,
            'limit': top_k
        })
        
        # Process results
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
                'relevance_score': 1.0 - row.distance  # Convert distance to relevance score
            })
        
        return search_results

    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Delete a conversation and all its chunks
        """
        conversation = self.get_conversation(conversation_id)
        if conversation:
            # Delete chunks first (due to foreign key constraint)
            self.db.query(models.ConversationChunk).filter(
                models.ConversationChunk.conversation_id == conversation_id
            ).delete()
            
            # Delete conversation
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False
