from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings  # <— use centralized settings
from typing import Optional
from dotenv import load_dotenv
from app.logging_config import get_logger
import os

load_dotenv()
logger = get_logger(__name__)
logger.info("📄 Environment variables loaded")

# Normalize DATABASE_URL and prefer psycopg (v3)
raw_url = settings.database_url or os.getenv("DATABASE_URL", "")
db_url = raw_url.strip().strip("'").strip('"')
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
if not db_url:
    raise RuntimeError("DATABASE_URL is not set")

logger.info(f"Using DATABASE_URL={db_url}")
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData()

def get_db():
    logger.debug("🔌 Creating database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("🔒 Closing database session")
        db.close()
