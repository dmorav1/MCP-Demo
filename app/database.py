"""
Database configuration and session management.
Uses psycopg 3 with SQLAlchemy 2.0+ for PostgreSQL + pgvector support.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

from app.logging_config import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://mcp_user:mcp_password@localhost:5432/mcp_db"
)

# Validate URL format for psycopg3
if DATABASE_URL.startswith("postgresql://"):
    logger.warning("⚠️ DATABASE_URL uses 'postgresql://' - converting to 'postgresql+psycopg://'")
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

logger.info(f"🔗 Connecting to database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL query logging
    future=True  # SQLAlchemy 2.0 style
)

# Create sessionmaker with expire_on_commit=False for better performance
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Keep objects usable after commit
)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI to get database sessions.
    Yields a session and ensures cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    Test database connection and pgvector extension.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as connection:
            # Test basic connectivity
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"✅ Database connected: {version[:50]}...")
            
            # Test pgvector extension
            result = connection.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector';"))
            if result.fetchone():
                logger.info("✅ pgvector extension is installed")
            else:
                logger.warning("⚠️ pgvector extension not found")
            
            connection.commit()
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


# Test connection on import
if __name__ != "__main__":
    test_connection()
