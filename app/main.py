from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
import sys
from contextlib import asynccontextmanager

from app import models, schemas, crud
from app.database import engine, get_db, test_connection
from app.routers.ingest import router as ingest_router
from app.routers.cache import router as cache_router
from app.services import ContextFormatter

# Observability imports
from app.observability import (
    setup_structured_logging,
    get_logger,
    metrics,
    setup_tracing,
    instrument_fastapi,
    instrument_sqlalchemy,
    setup_error_tracking,
    HealthChecker,
)
from app.observability.middleware import ObservabilityMiddleware, PerformanceLoggingMiddleware
from app.observability.metrics import MetricsMiddleware, metrics_endpoint

# Import new hexagonal architecture routers
from app.adapters.inbound.api.routers.conversations import router as conversations_router
from app.adapters.inbound.api.routers.search import router as search_router
from app.adapters.inbound.api.routers.rag import router as rag_router
from app.adapters.inbound.api.error_handlers import register_error_handlers

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

# Setup observability
log_level = os.getenv("LOG_LEVEL", "INFO")
use_json_logs = os.getenv("USE_JSON_LOGS", "true").lower() in ("true", "1", "yes")
log_file = os.getenv("LOG_FILE", "logs/mcp-backend.log")

setup_structured_logging(
    log_level=log_level,
    use_json=use_json_logs,
    log_file=log_file
)
logger = get_logger(__name__)

# Setup tracing
jaeger_host = os.getenv("JAEGER_HOST")
otlp_endpoint = os.getenv("OTLP_ENDPOINT")
console_tracing = os.getenv("ENABLE_CONSOLE_TRACING", "false").lower() in ("true", "1", "yes")

if jaeger_host or otlp_endpoint or console_tracing:
    setup_tracing(
        jaeger_host=jaeger_host,
        otlp_endpoint=otlp_endpoint,
        console_export=console_tracing
    )

# Setup error tracking
sentry_dsn = os.getenv("SENTRY_DSN")
sentry_env = os.getenv("SENTRY_ENVIRONMENT", "development")
if sentry_dsn:
    setup_error_tracking(
        dsn=sentry_dsn,
        environment=sentry_env,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
    )

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
    
    # Instrument SQLAlchemy for tracing
    try:
        instrument_sqlalchemy(engine)
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")
    
    # Set application info in metrics
    metrics.app_info.info({
        'version': '1.0.0',
        'architecture': 'hexagonal' if USE_NEW_ARCHITECTURE else 'legacy',
        'python_version': os.sys.version
    })
    
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

# Add observability middleware
slow_request_threshold = float(os.getenv("SLOW_REQUEST_THRESHOLD", "1.0"))
app.add_middleware(PerformanceLoggingMiddleware, slow_request_threshold=slow_request_threshold)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(MetricsMiddleware)

# Instrument FastAPI for tracing
try:
    instrument_fastapi(app)
except Exception as e:
    logger.warning(f"Failed to instrument FastAPI: {e}")

# Register error handlers for domain exceptions
register_error_handlers(app)

# Mount new hexagonal architecture routers
if USE_NEW_ARCHITECTURE:
    app.include_router(conversations_router)
    app.include_router(search_router)
    app.include_router(rag_router)
    logger.info("✅ New hexagonal architecture routers mounted")

# Mount cache management router
app.include_router(cache_router, tags=["cache"])
logger.info("✅ Cache management router mounted")

# Mount legacy routers (with deprecation warnings)
app.include_router(ingest_router, tags=["ingest", "legacy"])
if CHAT_ROUTER_AVAILABLE:
    app.include_router(chat_router, tags=["chat"])
    logger.info("✅ Chat gateway router mounted")

logger.info("✅ FastAPI application initialized")


@app.get("/", tags=["root"])
async def read_root():
    """Root endpoint with API information."""
    endpoints = {
        "health": "/health",
        "docs": "/docs",
    }
    
    if USE_NEW_ARCHITECTURE:
        endpoints.update({
            "conversations": {
                "ingest": "POST /conversations/ingest",
                "list": "GET /conversations",
                "get": "GET /conversations/{id}",
                "delete": "DELETE /conversations/{id}"
            },
            "search": {
                "post": "POST /search",
                "get": "GET /search?q={query}"
            },
            "rag": {
                "ask": "POST /rag/ask",
                "stream": "POST /rag/ask-stream",
                "health": "GET /rag/health"
            }
        })
        endpoints["ingest"] = "/ingest (DEPRECATED - use POST /conversations/ingest)"
        endpoints["legacy_search"] = "/search (DEPRECATED - use POST /search or GET /search)"
        endpoints["legacy_conversations"] = "/conversations (DEPRECATED - use new conversation endpoints)"
    else:
        endpoints.update({
            "ingest": "/ingest",
            "search": "/search",
            "conversations": "/conversations",
        })
    
    if CHAT_ROUTER_AVAILABLE:
        endpoints["chat"] = "/chat/ask"
    
    return {
        "message": "MCP Conversational Data Server",
        "version": "1.0.0",
        "architecture": "hexagonal" if USE_NEW_ARCHITECTURE else "legacy",
        "endpoints": endpoints
    }


@app.get("/metrics", tags=["monitoring"])
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus format for scraping.
    """
    return await metrics_endpoint()


@app.get("/health", tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Enhanced health check endpoint with detailed component status.
    Returns service status, database connectivity, and all component health.
    """
    try:
        health_checker = HealthChecker()
        health_result = health_checker.check_all(db=db)
        
        # Add basic service info
        health_result["service"] = "mcp-conversational-data-server"
        health_result["version"] = "1.0.0"
        health_result["architecture"] = "hexagonal" if USE_NEW_ARCHITECTURE else "legacy"
        
        # Add conversation count
        try:
            conversation_count = db.query(models.Conversation).count()
            health_result["conversation_count"] = conversation_count
        except Exception:
            pass
        
        # Determine HTTP status based on health
        if health_result["status"] == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_result
            )
        
        return health_result
        
    except HTTPException:
        raise
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
    
    DEPRECATED: This endpoint is deprecated. Use POST /search or GET /search instead.
    """
    if USE_NEW_ARCHITECTURE:
        logger.warning("⚠️  Legacy /search endpoint called - use POST /search or GET /search instead")
    
    logger.info(f"🔍 Search request: query='{q}', top_k={top_k}")
    
    try:
        # Perform search
        results = await crud.search_conversations(db, query=q, top_k=top_k)
        logger.info(f"✅ Found {len(results)} results")
        
        # Track metrics
        metrics.searches_performed.inc()
        
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
    
    DEPRECATED: This endpoint is deprecated. Use GET /conversations instead.
    """
    if USE_NEW_ARCHITECTURE:
        logger.warning("⚠️  Legacy GET /conversations endpoint called - use new conversation router instead")
    
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
    
    DEPRECATED: This endpoint is deprecated. Use GET /conversations/{id} on the new router instead.
    """
    if USE_NEW_ARCHITECTURE:
        logger.warning(f"⚠️  Legacy GET /conversations/{conversation_id} endpoint called - use new conversation router instead")
    
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
    
    DEPRECATED: This endpoint is deprecated. Use DELETE /conversations/{id} on the new router instead.
    """
    if USE_NEW_ARCHITECTURE:
        logger.warning(f"⚠️  Legacy DELETE /conversations/{conversation_id} endpoint called - use new conversation router instead")
    
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
