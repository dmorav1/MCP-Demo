from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, crud
from app.database import engine, get_db
from app.services import ContextFormatter

# Create database tables
models.Base.metadata.create_all(bind=engine)

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

@app.get("/")
async def root():
    """
    Root endpoint
    """
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
    db: Session = Depends(get_db)
):
    """
    Ingest a new conversation into the database.
    
    This endpoint processes the conversation data, chunks it into smaller pieces,
    generates embeddings for each chunk, and stores everything in the database.
    """
    try:
        conversation_crud = crud.ConversationCRUD(db)
        db_conversation = await conversation_crud.create_conversation(conversation_data)
        return db_conversation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting conversation: {str(e)}"
        )

@app.get("/search", response_model=schemas.SearchResponse)
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
    try:
        conversation_crud = crud.ConversationCRUD(db)
        search_results = await conversation_crud.search_conversations(q, top_k)
        
        # Format results using ContextFormatter
        formatted_results = ContextFormatter.format_search_results(search_results, q)
        
        return schemas.SearchResponse(
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching conversations: {str(e)}"
        )

@app.get("/conversations", response_model=List[schemas.Conversation])
async def get_conversations(
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of conversations to return"),
    db: Session = Depends(get_db)
):
    """
    Get all conversations with pagination.
    """
    try:
        conversation_crud = crud.ConversationCRUD(db)
        conversations = conversation_crud.get_conversations(skip=skip, limit=limit)
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving conversations: {str(e)}"
        )

@app.get("/conversations/{conversation_id}", response_model=schemas.Conversation)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation by ID.
    """
    try:
        conversation_crud = crud.ConversationCRUD(db)
        conversation = conversation_crud.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving conversation: {str(e)}"
        )

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its chunks.
    """
    try:
        conversation_crud = crud.ConversationCRUD(db)
        success = conversation_crud.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "mcp-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
