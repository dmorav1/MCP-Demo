from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import Conversation, ConversationChunk
from app.services import ConversationProcessor
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MessageIn(BaseModel):
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    content: str
    timestamp: Optional[datetime] = None

class ConversationIn(BaseModel):
    scenario_title: Optional[str] = None
    original_title: Optional[str] = None
    url: Optional[str] = None
    messages: List[MessageIn] = Field(default_factory=list)

@router.post("/ingest")
async def ingest_conversation(payload: ConversationIn, db: Session = Depends(get_db)):
    try:
        processor = ConversationProcessor()
        prepared = await processor.process_conversation_for_ingestion(payload.model_dump())
        chunks = prepared.get("chunks", [])
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks to ingest")

        conv = Conversation(
            scenario_title=prepared.get("scenario_title"),
            original_title=prepared.get("original_title"),
            url=prepared.get("url"),
        )
        db.add(conv)
        db.flush()  # ensures conv.id is available

        # Insert chunks
        objects = []
        for ch in chunks:
            objects.append(ConversationChunk(
                conversation_id=conv.id,
                order_index=ch["order_index"],
                chunk_text=ch["chunk_text"],
                author_name=ch.get("author_name"),
                author_type=ch.get("author_type"),
                timestamp=ch.get("timestamp"),
                embedding=ch.get("embedding"),
            ))
        if objects:
            db.add_all(objects)

        db.commit()

        # Refresh conv with chunks eagerly for any immediate responses
        db.refresh(conv)
        conv = (
            db.query(Conversation)
            .options(selectinload(Conversation.chunks))
            .filter(Conversation.id == conv.id)
            .first()
        )
        logger.info(f"💾 Ingested conversation id={conv.id} chunks={len(conv.chunks)}")
        return {"conversation_id": conv.id, "chunks": len(conv.chunks)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Use logger.exception to include traceback for debugging
        logger.exception(f"❌ Error ingesting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest conversation")
