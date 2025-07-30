from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import logging
import os
from app import models, schemas, crud, dependencies
from app.database import engine, get_db
from app.services import ContextFormatter
from app.logging_config import setup_logging, get_logger

# Set up comprehensive logging
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(log_level)
logger = get_logger(__name__)

# Note: Database schema creation is now handled by Alembic migrations
# See Phase 4 of the refactoring plan for migration setup

app = FastAPI(
    title="MCP Backend API",
    description="Model Context Protocol Backend for Conversational Data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("✅ FastAPI application initialized")

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🌟 Application startup completed")
    logger.info("🔗 API endpoints registered:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            logger.info(f"   {methods} {route.path}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 Application shutdown initiated")
    logger.info("👋 MCP Backend API stopped")

@app.get("/")
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

@app.post("/ingest", response_model=schemas.Conversation, status_code=status.HTTP_201_CREATED)
async def ingest_conversation(
    conversation_data: schemas.ConversationIngest,
    conversation_crud: crud.ConversationCRUD = Depends(dependencies.get_conversation_crud)
):
    """
    Ingest a new conversation into the database.
    
    This endpoint processes the conversation data, chunks it into smaller pieces,
    generates embeddings for each chunk, and stores everything in the database.
    """
    logger.info(f"📥 Ingesting conversation: {conversation_data.scenario_title}")
    try:
        db_conversation = await conversation_crud.create_conversation(conversation_data)
        logger.info(f"✅ Successfully ingested conversation ID: {db_conversation.id}")
        return db_conversation
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error during ingestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred during ingestion."
        )
    except Exception as e:  # Keep a general one as a fallback
        logger.error(f"❌ An unexpected error occurred during ingestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )

@app.get("/search", response_model=schemas.SearchResponse)
async def search_conversations(
    q: str = Query(..., description="Search query string"),
    top_k: int = Query(5, ge=1, le=50, description="Number of results to return"),
    conversation_crud: crud.ConversationCRUD = Depends(dependencies.get_conversation_crud)
):
    """
    Search for relevant conversations using semantic similarity.
    
    The search query is converted to a vector embedding and compared against
    stored conversation chunks using cosine similarity.
    """
    logger.info(f"🔍 Searching conversations with query: '{q}' (top_k={top_k})")
    try:
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
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error during search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred during search."
        )
    except Exception as e:  # Keep a general one as a fallback
        logger.error(f"❌ An unexpected error occurred during search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )

@app.get("/conversations", response_model=List[schemas.Conversation])
async def get_conversations(
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of conversations to return"),
    conversation_crud: crud.ConversationCRUD = Depends(dependencies.get_conversation_crud)
):
    """
    Get all conversations with pagination.
    """
    logger.info(f"📋 Fetching conversations (skip={skip}, limit={limit})")
    try:
        conversations = await conversation_crud.get_conversations(skip=skip, limit=limit)
        logger.info(f"✅ Retrieved {len(conversations)} conversations")
        return conversations
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error retrieving conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving conversations."
        )
    except Exception as e:  # Keep a general one as a fallback
        logger.error(f"❌ An unexpected error occurred retrieving conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )

@app.get("/conversations/{conversation_id}", response_model=schemas.Conversation)
async def get_conversation(
    conversation_id: int,
    conversation_crud: crud.ConversationCRUD = Depends(dependencies.get_conversation_crud)
):
    """
    Get a specific conversation by ID.
    """
    logger.info(f"🔍 Fetching conversation with ID: {conversation_id}")
    try:
        conversation = await conversation_crud.get_conversation(conversation_id)
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
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error retrieving conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving the conversation."
        )
    except Exception as e:  # Keep a general one as a fallback
        logger.error(f"❌ An unexpected error occurred retrieving conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    conversation_crud: crud.ConversationCRUD = Depends(dependencies.get_conversation_crud)
):
    """
    Delete a conversation and all its chunks.
    """
    logger.info(f"🗑️ Deleting conversation with ID: {conversation_id}")
    try:
        success = await conversation_crud.delete_conversation(conversation_id)
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
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while deleting the conversation."
        )
    except Exception as e:  # Keep a general one as a fallback
        logger.error(f"❌ An unexpected error occurred deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    logger.info("💚 Health check endpoint accessed")
    return {"status": "healthy", "service": "mcp-backend"}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting application server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
