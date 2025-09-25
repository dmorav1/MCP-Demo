from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import Conversation
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/conversations")
def list_conversations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        items = (
            db.query(Conversation)
            .options(selectinload(Conversation.chunks))  # eager-load chunks
            .order_by(Conversation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": c.id,
                "scenario_title": c.scenario_title,
                "original_title": c.original_title,
                "url": c.url,
                "created_at": c.created_at,
                "chunks": [
                    {
                        "id": ch.id,
                        "order_index": ch.order_index,
                        "author_name": ch.author_name,
                        "author_type": ch.author_type,
                        "timestamp": ch.timestamp,
                    }
                    for ch in c.chunks
                ],
            }
            for c in items
        ]
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")