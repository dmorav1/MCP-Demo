from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict 
from typing import Optional
import os
import logging
from dotenv import load_dotenv
from app.logging_config import get_logger

load_dotenv()

# Get logger for this module
logger = get_logger(__name__)
logger.info("📄 Environment variables loaded")

class Settings(BaseSettings):
    """
    Manages application configuration using Pydantic's environment variable loading.
    It automatically reads from .env files and the system environment.
    """
    # Pydantic will automatically map these uppercase field names to
    # environment variables of the same name.
    database_url: str = "postgresql+psycopg://username:password@localhost:5432/mcp_db"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimension: int = 1536

    mcp_transport: Optional[str] = None

    # This is the Pydantic V2 way to configure settings.
    # It tells Pydantic to look for a .env file and to forbid extra fields.
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

settings = Settings()

# Log configuration (mask sensitive data)
masked_db_url = settings.database_url.replace(settings.database_url.split('@')[0].split('://')[1], '****') if '@' in settings.database_url else settings.database_url
logger.info(f"🔧 Database URL: {masked_db_url}")
logger.info(f"🤖 OpenAI API Key: {'Set' if settings.openai_api_key else 'Not Set'}")
logger.info(f"📊 Embedding Model: {settings.embedding_model}")
logger.info(f"📏 Embedding Dimension: {settings.embedding_dimension}")

raw_url = settings.database_url or os.getenv("DATABASE_URL", "")
db_url = raw_url.strip().strip("'").strip('"')
if not db_url:
    raise RuntimeError("DATABASE_URL is not set")
logger = get_logger(__name__) if "get_logger" in globals() else None
if logger:
    logger.info(f"Using DATABASE_URL={db_url}")
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("✅ Database engine created successfully")

Base = declarative_base()

def get_db():
    logger.debug("🔌 Creating database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("🔒 Closing database session")
        db.close()
