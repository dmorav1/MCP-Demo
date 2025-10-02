from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.services import EmbeddingService
from app.logging_config import get_logger

logger = get_logger(__name__)

class ConversationCRUD:
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
        logger.info(f"🔍 Starting search for query: '{query}', top_k: {top_k}")
        q = (query or "").strip()
        if not q:
            return []

        # 1) Embed query (local model → 384, padded to 1536 by service)
        logger.info(f"🔍 Generating embedding for query...")
        try:
            qvec = await self._embed.generate_embedding(q)
            logger.info(f"🔍 Generated embedding with {len(qvec)} dimensions")
        except Exception as e:
            logger.error(f"🔍 Error generating embedding: {e}")
            raise

        # 2) Vector search (L2). Use <-> since your index uses vector_l2_ops.
        sql = text("""
            SELECT
              ch.id              AS chunk_id,
              ch.conversation_id AS conversation_id,
              ch.order_index     AS order_index,
              ch.chunk_text      AS chunk_text,
              ch.author_name     AS author_name,
              ch.author_type     AS author_type,
              ch.timestamp       AS timestamp,
              conv.scenario_title AS scenario_title,
              conv.original_title AS original_title,
              conv.url            AS url,
              (ch.embedding <-> CAST(:qvec AS vector)) AS score
            FROM conversation_chunks ch
            JOIN conversations conv ON conv.id = ch.conversation_id
            ORDER BY ch.embedding <-> CAST(:qvec AS vector)
            LIMIT :k
        """)
        rows = self.db.execute(sql, {"qvec": qvec, "k": int(top_k)}).mappings().all()
        
        logger.info(f"🔍 Query returned {len(rows)} rows")
        if rows:
            logger.info(f"🔍 First row keys: {list(rows[0].keys()) if rows else 'None'}")

        results = []
        for r in rows:
            results.append({
                "score": float(r["score"]),
                "chunk": {
                    "id": r["chunk_id"],
                    "conversation_id": r["conversation_id"],
                    "order_index": r["order_index"],
                    "author_name": r["author_name"],
                    "author_type": r["author_type"],
                    "timestamp": r["timestamp"],
                    "text": r["chunk_text"],
                },
                "conversation": {
                    "id": r["conversation_id"],
                    "scenario_title": r["scenario_title"],
                    "original_title": r["original_title"],
                    "url": r["url"],
                }
            })
        logger.info(f"🔎 search '{q}' → {len(results)} hits")
        return results
