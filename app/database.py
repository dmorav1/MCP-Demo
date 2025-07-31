# app/database.py (New Content)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv
from app.logging_config import get_logger

load_dotenv()
logger = get_logger(__name__)


class Settings(BaseSettings):
    # IMPORTANT: The driver is now postgresql+asyncpg
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://mcp_user:mcp_password@localhost:5433/mcp_db",
    )
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    class Config:
        env_file = ".env"


settings = Settings()

# Log configuration (mask sensitive data)
masked_db_url = (
    settings.database_url.replace(
        settings.database_url.split("@")[0].split("://")[1], "****"
    )
    if "@" in settings.database_url
    else settings.database_url
)
logger.info(f"🔧 Database URL: {masked_db_url}")

logger.info("🔄 Creating ASYNC database engine...")
engine = create_async_engine(
    settings.database_url, echo=False
)  # Set echo=True for debugging SQL

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Required for FastAPI background tasks and dependencies
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# Async dependency to get a DB session
async def get_db() -> AsyncSession:
    logger.debug("🔌 Creating new ASYNC database session")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            logger.debug("🔒 Closing ASYNC database session")
