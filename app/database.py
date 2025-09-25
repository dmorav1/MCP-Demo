from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)
Base = declarative_base()

def _normalize_db_url(u: str) -> str:
    u = (u or "").strip().strip("'").strip('"')
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    if u.startswith("postgresql://"):
        u = "postgresql+psycopg://" + u[len("postgresql://"):]
    return u

raw_url = settings.database_url or os.getenv("DATABASE_URL", "")
db_url = _normalize_db_url(raw_url)
logger.info(f"Using DATABASE_URL={db_url}")

engine = create_engine(db_url, pool_pre_ping=True, future=True)

# Avoid attribute expiration during response building
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ensure pgvector is available on fresh DBs
try:
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("✅ pgvector extension is ready")
except Exception as ex:
    logger.warning(f"⚠️ Could not ensure pgvector extension: {ex}")
