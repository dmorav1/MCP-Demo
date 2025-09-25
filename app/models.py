from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config import settings
from pgvector.sqlalchemy import Vector
from app.database import Base
from app.logging_config import get_logger

logger = get_logger(__name__)
logger.info("📋 Loading database models...")

VECTOR_DIM = int(getattr(settings, "embedding_dimension", 1536))

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    scenario_title = Column(Text, nullable=True)
    original_title = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Load chunks in order and cascade deletes
    chunks = relationship(
        "ConversationChunk",
        back_populates="conversation",
        order_by="ConversationChunk.order_index",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class ConversationChunk(Base):
    __tablename__ = "conversation_chunks"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(VECTOR_DIM), nullable=True)
    author_name = Column(Text, nullable=True)
    author_type = Column(String(16), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("Conversation", back_populates="chunks")

    __table_args__ = (
        Index(
            'ix_conversation_chunks_embedding',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_ops={'embedding': 'vector_l2_ops'},
            postgresql_with={'lists': 100}
        ),
        Index('ix_conversation_chunks_conversation_order', 'conversation_id', 'order_index', unique=True),
    )

logger.info("✅ Database models loaded successfully")
