from fastapi import FastAPI, Depends, HTTPException, status, Query
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List
import logging
import os
import math
import json
import asyncio # Add this import
from mcp.server.fastmcp import FastMCP
from collections.abc import AsyncIterator

from app.database import SessionLocal
from app import models, schemas, crud
from app.database import engine, get_db
from app.services import ContextFormatter
from app.logging_config import setup_logging, get_logger

# Set up comprehensive logging
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(log_level)
logger = get_logger(__name__)

# Create database tables
logger.info("🚀 Creating database tables...")
models.Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables created successfully")

# Shared State and Lifespan (NEW & IMPORTANT)
# This dataclass will hold our shared resources, like the DB session factory.
class AppState:
    def __init__(self):
        self.db_session_factory = SessionLocal

app_state = AppState()

logger.info("🚀 Initializing MCP...")

mcp_app = FastMCP(
    "Conversational Data Server",
    description="Exposes conversation ingestion and search via MCP."
)
# Initialize the MCP application
logger.info("✅  MCP application initialized")


@mcp_app.tool()
async def search(q: str, top_k: int = 5) -> schemas.SearchResponse:
    """
    Search for relevant conversations using semantic similarity.
    The search query is converted to a vector embedding and compared against
    stored conversation chunks using cosine similarity.
    """
    logger.info(f"🔍 [MCP] Searching conversations with query: '{q}' (top_k={top_k})")
    
    # Manually get a DB session from our shared state.
    db: Session = app_state.db_session_factory()
    try:
        conversation_crud = crud.ConversationCRUD(db)
        search_results = await conversation_crud.search_conversations(q, top_k)
        logger.info(f"🎯 [MCP] Found {len(search_results)} search results")
        
        # The MCP SDK expects a Pydantic model, which we already have!
        response = schemas.SearchResponse(
            results=[
                schemas.SearchResult(
                    conversation=schemas.Conversation(
                        id=result['conversation_id'],
                        scenario_title=result['scenario_title'],
                        original_title=result['original_title'],
                        url=result['url'],
                        created_at=result['created_at'],
                        chunks=[]
                    ),
                    relevance_score=result['relevance_score'],
                    matched_chunks=[
                        schemas.ConversationChunk(
                            id=result['chunk_id'],
                            conversation_id=result['conversation_id'],
                            order_index=result['order_index'],
                            chunk_text=result['chunk_text'],
                            author_name=result['author_name'],
                            author_type=result['author_type'],
                            timestamp=result['timestamp']
                        )
                    ]
                ) for result in search_results
            ],
            query=q,
            total_results=len(search_results)
        )
        logger.info(f"✅ [MCP] Search completed successfully for query: '{q}'")
        return response
    except Exception as e:
        logger.error(f"❌ [MCP] Error searching conversations: {str(e)}")
        # For tools, it's often better to return an error within the protocol
        # rather than raising an exception that kills the connection.
        # However, for simplicity, we'll let it raise for now.
        # A more robust implementation might return a SearchResponse with an error field.
        raise
    finally:
        db.close()

# --- INITIALIZATION ---
logger.info("🚀 Initializing FastAPI application...")
fastapi_app = FastAPI(
    title="MCP Backend API",
    description="Model Context Protocol Backend for Conversational Data",
    version="1.0.0"
)

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("✅ FastAPI application initialized")


def safe_json_encode(obj):
    """
    Custom JSON encoder that handles NaN and infinity values
    """
    def default(o):
        if isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return 0.0
        return o
    
    return json.loads(json.dumps(obj, default=default))


@fastapi_app.get("/")
async def root():
    """
    Root endpoint
    """
    logger.info("📍 Root endpoint accessed")
    return {
        "message": "MCP Backend API",
        "version": "1.0.0",
        "endpoints": {
            "ingest": "POST /ingest - Ingest a new conversation",
            "search": "GET /search - Search conversations",
            "conversations": "GET /conversations - List all conversations",
            "conversation": "GET /conversations/{id} - Get a specific conversation"
        }
    }

@fastapi_app.post("/ingest", response_model=schemas.Conversation, status_code=status.HTTP_201_CREATED)
async def ingest_conversation(
    conversation_data: schemas.ConversationIngest,
    db: Session = Depends(get_db)
):
    """
    Ingest a new conversation into the database.
    
    This endpoint processes the conversation data, chunks it into smaller pieces,
    generates embeddings for each chunk, and stores everything in the database.
    """
    logger.info(f"📥 Ingesting conversation: {conversation_data.scenario_title}")
    try:
        conversation_crud = crud.ConversationCRUD(db)
        db_conversation = await conversation_crud.create_conversation(conversation_data)
        logger.info(f"✅ Successfully ingested conversation ID: {db_conversation.id}")
        return db_conversation
    except Exception as e:
        logger.error(f"❌ Error ingesting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting conversation: {str(e)}"
        )

@fastapi_app.get("/search", response_model=schemas.SearchResponse)
async def search_conversations(
    q: str = Query(..., description="Search query string"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search for relevant conversations using semantic similarity.
    
    The search query is converted to a vector embedding and compared against
    stored conversation chunks using cosine similarity.
    """
    logger.info(f"🔍 Searching conversations with query: '{q}' (top_k={top_k})")
    try:
        conversation_crud = crud.ConversationCRUD(db)
        search_results = await conversation_crud.search_conversations(q, top_k)
        logger.info(f"🎯 Found {len(search_results)} search results")
        
        # Format results using ContextFormatter
        formatted_results = ContextFormatter.format_search_results(search_results, q)
        
        response = schemas.SearchResponse(
            results=[
                schemas.SearchResult(
                    conversation=schemas.Conversation(
                        id=result['conversation_id'],
                        scenario_title=result['scenario_title'],
                        original_title=result['original_title'],
                        url=result['url'],
                        created_at=result['created_at'],
                        chunks=[]
                    ),
                    relevance_score=result['relevance_score'],
                    matched_chunks=[
                        schemas.ConversationChunk(
                            id=result['chunk_id'],
                            conversation_id=result['conversation_id'],
                            order_index=result['order_index'],
                            chunk_text=result['chunk_text'],
                            author_name=result['author_name'],
                            author_type=result['author_type'],
                            timestamp=result['timestamp']
                        )
                    ]
                ) for result in search_results
            ],
            query=q,
            total_results=len(search_results)
        )
        logger.info(f"✅ Search completed successfully for query: '{q}'")
        return response
    except Exception as e:
        logger.error(f"❌ Error searching conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching conversations: {str(e)}"
        )

@fastapi_app.get("/conversations", response_model=List[schemas.Conversation])
async def get_conversations(
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of conversations to return"),
    db: Session = Depends(get_db)
):
    """
    Get all conversations with pagination.
    """
    logger.info(f"📋 Fetching conversations (skip={skip}, limit={limit})")
    try:
        conversation_crud = crud.ConversationCRUD(db)
        conversations = conversation_crud.get_conversations(skip=skip, limit=limit)
        logger.info(f"✅ Retrieved {len(conversations)} conversations")
        return conversations
    except Exception as e:
        logger.error(f"❌ Error retrieving conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving conversations: {str(e)}"
        )

@fastapi_app.get("/conversations/{conversation_id}", response_model=schemas.Conversation)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation by ID.
    """
    logger.info(f"🔍 Fetching conversation with ID: {conversation_id}")
    try:
        conversation_crud = crud.ConversationCRUD(db)
        conversation = conversation_crud.get_conversation(conversation_id)
        if conversation is None:
            logger.warning(f"⚠️ Conversation not found: {conversation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        logger.info(f"✅ Retrieved conversation: {conversation.scenario_title}")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving conversation: {str(e)}"
        )

@fastapi_app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its chunks.
    """
    logger.info(f"🗑️ Deleting conversation with ID: {conversation_id}")
    try:
        conversation_crud = crud.ConversationCRUD(db)
        success = conversation_crud.delete_conversation(conversation_id)
        if not success:
            logger.warning(f"⚠️ Conversation not found for deletion: {conversation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        logger.info(f"✅ Successfully deleted conversation: {conversation_id}")
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )

@fastapi_app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    logger.info("💚 Health check endpoint accessed")
    return {"status": "healthy", "service": "mcp-backend"}

if __name__ == "__main__":
    import uvicorn
    import asyncio

    # Specification 1.3: Concurrent asyncio runner
    async def main():
        
        # Configure Uvicorn task
        uvicorn_config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=8000
        )
        uvicorn_server = uvicorn.Server(uvicorn_config)

        # Configure MCP stdio task
        mcp_stdio_task = mcp_app.run_stdio_async()

        logger.info("🚀 Starting concurrent servers...")
        logger.info("   - HTTP API running on http://0.0.0.0:8000 (logs in fastapi_server.log)")
        logger.info("   - MCP server running on stdio")

        # Run both tasks
        await asyncio.gather(
            uvicorn_server.serve(),
            mcp_stdio_task
        )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Shutdown logic from old lifespan
        logger.info("🛑 Application shutdown initiated by user.")
        logger.info("🛑 Application shutdown: Lifespan manager is cleaning up.")
        logger.info("🛑 Application shutdown initiated")
        logger.info("👋 MCP Backend API stopped")
