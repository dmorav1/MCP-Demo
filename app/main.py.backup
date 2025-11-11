from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
from contextlib import asynccontextmanager

from app import models, schemas, crud
from app.database import engine, get_db, test_connection
from app.routers.ingest import router as ingest_router
from app.services import ContextFormatter
from app.logging_config import setup_logging, get_logger

# Import DI container
from app.infrastructure.container import initialize_container, get_container
from app.infrastructure.config import get_settings

# Import chat gateway if it exists
try:
    from app.mcp_gateway import router as chat_router
    CHAT_ROUTER_AVAILABLE = True
except ImportError:
    CHAT_ROUTER_AVAILABLE = False
    chat_router = None

# Setup logging first
setup_logging()
logger = get_logger(__name__)

logger.info("🚀 Initializing FastAPI application...")

# Feature flag for using new hexagonal architecture
USE_NEW_ARCHITECTURE = os.getenv("USE_NEW_ARCHITECTURE", "true").lower() in ("true", "1", "yes")

logger.info(f"📐 Architecture mode: {'NEW (Hexagonal)' if USE_NEW_ARCHITECTURE else 'LEGACY'}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🔧 Application startup...")
    
    # Create database tables
    try:
        logger.info("📊 Creating database tables...")
        models.Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise
    
    # Test database connection
    logger.info("🔍 Testing database connection...")
    if not test_connection():
        logger.error("❌ Database connection test failed - application may not work correctly")
    else:
        logger.info("✅ Database connection verified")
    
    # Initialize DI container if using new architecture
    if USE_NEW_ARCHITECTURE:
        try:
            logger.info("🔌 Initializing dependency injection container...")
            initialize_container(include_adapters=True)
            logger.info("✅ DI container initialized with all adapters")
            
            # Validate configuration
            settings = get_settings()
            logger.info(f"✅ Configuration loaded: provider={settings.embedding.provider}, model={settings.embedding.model}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize DI container: {e}")
            raise
    
    logger.info("✅ Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("👋 Application shutdown...")


app = FastAPI(
    title="MCP Conversational Data Server",
    description="Ingest, search, and serve conversational data via REST and MCP protocol",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(ingest_router, tags=["ingest"])
if CHAT_ROUTER_AVAILABLE:
    app.include_router(chat_router, tags=["chat"])
    logger.info("✅ Chat gateway router mounted")

logger.info("✅ FastAPI application initialized")


@app.get("/", tags=["root"])
async def read_root():
    """Root endpoint with API information."""
    return {
        "message": "MCP Conversational Data Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "ingest": "/ingest",
            "search": "/search",
            "conversations": "/conversations",
            "chat": "/chat/ask" if CHAT_ROUTER_AVAILABLE else "not available"
        }
    }


@app.get("/health", tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Returns service status and database connectivity.
    Validates all adapters when using new architecture.
    """
    try:
        # Test database query
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        
        # Count conversations
        conversation_count = db.query(models.Conversation).count()
        
        health_info = {
            "status": "healthy",
            "service": "mcp-conversational-data-server",
            "database": db_status,
            "conversation_count": conversation_count,
            "architecture": "hexagonal" if USE_NEW_ARCHITECTURE else "legacy",
            "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "local"),
            "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", 1536)),
            "chat_gateway": "available" if CHAT_ROUTER_AVAILABLE else "not available"
        }
        
        # If using new architecture, validate adapter registrations
        if USE_NEW_ARCHITECTURE:
            try:
                from app.domain.repositories import (
                    IConversationRepository, IChunkRepository,
                    IEmbeddingService, IVectorSearchRepository
                )
                
                container = get_container()
                
                # Check if all required services are registered
                adapters_status = {
                    "conversation_repository": container.is_registered(IConversationRepository),
                    "chunk_repository": container.is_registered(IChunkRepository),
                    "embedding_service": container.is_registered(IEmbeddingService),
                    "vector_search_repository": container.is_registered(IVectorSearchRepository),
                }
                
                health_info["adapters"] = adapters_status
                health_info["di_container"] = "configured"
                
                # Check if all adapters are registered
                if not all(adapters_status.values()):
                    health_info["status"] = "degraded"
                    health_info["warning"] = "Some adapters not registered"
                    
            except Exception as e:
                logger.warning(f"Failed to validate adapters: {e}")
                health_info["di_container"] = f"error: {str(e)}"
                health_info["status"] = "degraded"
        
        return health_info
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.get("/search", response_model=schemas.ChunkSearchResponse, tags=["search"])
async def search_conversations(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search for relevant conversation chunks using vector similarity.
    Returns chunks ranked by relevance with metadata.
    """
    logger.info(f"🔍 Search request: query='{q}', top_k={top_k}")
    
    try:
        # Perform search
        results = await crud.search_conversations(db, query=q, top_k=top_k)
        logger.info(f"✅ Found {len(results)} results")
        chunk_results = [schemas.ChunkSearchResult(**r) for r in results]
        return schemas.ChunkSearchResponse(
            query=q,
            results=chunk_results,
            total_results=len(chunk_results)
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@app.get("/conversations", response_model=List[schemas.ConversationResponse], tags=["conversations"])
async def list_conversations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """
    List all conversations with pagination.
    Returns conversation metadata and statistics.
    """
    logger.info(f"📋 List conversations: skip={skip}, limit={limit}")
    
    try:
        conversations = crud.get_conversations(db, skip=skip, limit=limit)
        
        logger.info(f"✅ Retrieved {len(conversations)} conversations")
        return conversations
        
    except Exception as e:
        logger.error(f"❌ Failed to list conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversations: {str(e)}"
        )


@app.get("/conversations/{conversation_id}", response_model=schemas.ConversationResponse, tags=["conversations"])
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation by ID with all chunks.
    """
    logger.info(f"🔍 Get conversation: id={conversation_id}")
    
    try:
        conversation = crud.get_conversation(db, conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        logger.info(f"✅ Retrieved conversation {conversation_id}")
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation: {str(e)}"
        )


@app.delete("/conversations/{conversation_id}", tags=["conversations"])
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its chunks.
    """
    logger.info(f"🗑️ Delete conversation: id={conversation_id}")
    
    try:
        result = crud.delete_conversation(db, conversation_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        logger.info(f"✅ Deleted conversation {conversation_id}")
        return {"message": f"Conversation {conversation_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting server with uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
