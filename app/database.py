from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os
import logging
from dotenv import load_dotenv
from app.logging_config import get_logger

load_dotenv()

# Get logger for this module
logger = get_logger(__name__)
logger.info("📄 Environment variables loaded")

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://username:password@localhost:5432/mcp_db")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    class Config:
        env_file = ".env"

settings = Settings()

# Log configuration (mask sensitive data)
masked_db_url = settings.database_url.replace(settings.database_url.split('@')[0].split('://')[1], '****') if '@' in settings.database_url else settings.database_url
logger.info(f"🔧 Database URL: {masked_db_url}")
logger.info(f"🤖 OpenAI API Key: {'Set' if settings.openai_api_key else 'Not Set'}")
logger.info(f"📊 Embedding Model: {settings.embedding_model}")
logger.info(f"📏 Embedding Dimension: {settings.embedding_dimension}")

logger.info("🔄 Creating database engine...")
engine = create_engine(settings.database_url)
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
