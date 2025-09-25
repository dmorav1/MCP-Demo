from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.logging_config import get_logger

logger = get_logger(__name__)

class ConversationCRUD:
    def __init__(self, db: Session):
        self.db = db

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
