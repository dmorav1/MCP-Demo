# app/dependencies.py (New File)
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app import crud
from app.services import EmbeddingService, ConversationProcessor
from app.database import get_db, settings


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Returns a singleton instance of the EmbeddingService."""
    return EmbeddingService(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
    )


@lru_cache()
def get_conversation_processor(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> ConversationProcessor:
    """Returns a singleton instance of the ConversationProcessor."""
    return ConversationProcessor(embedding_service=embedding_service)


def get_conversation_crud(
    db: AsyncSession = Depends(get_db),
    processor: ConversationProcessor = Depends(get_conversation_processor),
) -> crud.ConversationCRUD:
    """Returns a new ConversationCRUD instance for each request."""
    return crud.ConversationCRUD(db=db, processor=processor)
