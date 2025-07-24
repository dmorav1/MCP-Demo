from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    scenario_title = Column(Text, nullable=True)
    original_title = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to conversation chunks
    chunks = relationship("ConversationChunk", back_populates="conversation")

class ConversationChunk(Base):
    __tablename__ = "conversation_chunks"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)  # Dimension for text-embedding-ada-002
    author_name = Column(Text, nullable=True)
    author_type = Column(String(10), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)

    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="chunks")

    __table_args__ = (
        Index('ix_conversation_chunks_embedding', 'embedding', postgresql_using='ivfflat', postgresql_ops={'embedding': 'vector_l2_ops'}, postgresql_with={'lists': 100}),
        Index('ix_conversation_chunks_conversation_order', 'conversation_id', 'order_index', unique=True),
    )
