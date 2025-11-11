"""
MCP server that integrates with hexagonal architecture.
This server uses dependency injection and use cases instead of direct API calls.
"""
import os
import logging
from typing import List
from mcp.server.fastmcp import FastMCP, Context

from app.infrastructure.container import initialize_container, get_container
from app.application import (
    SearchConversationRequest,
    SearchConversationResponse,
    IngestConversationRequest,
    IngestConversationResponse,
    GetConversationRequest,
    GetConversationResponse,
    DeleteConversationRequest,
    DeleteConversationResponse,
    MessageDTO,
    SearchConversationsUseCase,
    IngestConversationUseCase,
    GetConversationUseCase,
    ListConversationsUseCase,
    DeleteConversationUseCase
)
from app.application.rag_service import RAGService
from app import schemas


# Set up logging
log_level = os.getenv("LOG_LEVEL", "WARN")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Initialize DI container
logger.info("Initializing DI container for MCP server...")
initialize_container(include_adapters=True)
container = get_container()

# Initialize the MCP application
mcp_app = FastMCP(
    "Conversational Data Server"
)


@mcp_app.tool()
async def search_conversations(context: Context, q: str, top_k: int = 5) -> dict:
    """
    Search for relevant conversations using semantic similarity.
    The search query is converted to a vector embedding and compared against
    stored conversation chunks using cosine similarity.
    
    Args:
        q: Search query string
        top_k: Number of results to return (1-50)
    """
    await context.info(f"🔍 [MCP] Searching conversations with query: '{q}' (top_k={top_k})")
    
    try:
        # Resolve use case from DI container
        search_use_case = container.resolve(SearchConversationsUseCase)
        
        # Create request DTO
        request = SearchConversationRequest(
            query=q,
            top_k=top_k
        )
        
        # Execute use case
        response = await search_use_case.execute(request)
        
        if not response.success:
            await context.error(f"❌ [MCP] Search failed: {response.error_message}")
            raise Exception(f"Search failed: {response.error_message}")
        
        await context.info(f"🎯 [MCP] Found {len(response.results)} search results")
        await context.info(f"✅ [MCP] Search completed successfully for query: '{q}'")
        
        # Convert response to dict format compatible with MCP
        return {
            "query": response.query,
            "total_results": response.total_results,
            "results": [
                {
                    "chunk_id": result.chunk_id,
                    "conversation_id": result.conversation_id,
                    "text": result.text,
                    "score": result.score,
                    "author_name": result.author_name,
                    "author_type": result.author_type,
                    "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                    "order_index": result.order_index,
                    "metadata": result.metadata
                }
                for result in response.results
            ]
        }
        
    except Exception as e:
        await context.error(f"❌ [MCP] Error searching conversations: {str(e)}")
        raise Exception(f"Search failed: {str(e)}")


@mcp_app.tool()
async def ingest_conversation(conversation_data: schemas.ConversationIngest, context: Context) -> dict:
    """
    Ingest a new conversation into the database.
    
    This tool processes the conversation data, chunks it into smaller pieces,
    generates embeddings for each chunk, and stores everything in the database.
    
    Args:
        conversation_data: The conversation data to ingest
    """
    await context.info(f"📥 [MCP] Ingesting conversation: {conversation_data.scenario_title}")

    try:
        # Resolve use case from DI container
        ingest_use_case = container.resolve(IngestConversationUseCase)
        
        # Convert messages to DTOs
        message_dtos = [
            MessageDTO(
                text=msg.get("text", msg.get("content", "")),
                author_name=msg.get("author_name"),
                author_type=msg.get("author_type"),
                timestamp=msg.get("timestamp")
            )
            for msg in conversation_data.messages
        ]
        
        # Create request DTO
        request = IngestConversationRequest(
            messages=message_dtos,
            scenario_title=conversation_data.scenario_title,
            original_title=conversation_data.original_title,
            url=conversation_data.url
        )
        
        # Execute use case
        response = await ingest_use_case.execute(request)
        
        if not response.success:
            await context.error(f"❌ [MCP] Ingestion failed: {response.error_message}")
            raise Exception(f"Ingestion failed: {response.error_message}")
        
        await context.info(f"✅ [MCP] Successfully ingested conversation ID: {response.conversation_id}")
        
        # Return dict format compatible with MCP
        return {
            "id": int(response.conversation_id),
            "scenario_title": response.metadata.scenario_title,
            "original_title": response.metadata.original_title,
            "url": response.metadata.url,
            "created_at": response.metadata.created_at.isoformat(),
            "chunks_created": response.chunks_created
        }
        
    except Exception as e:
        await context.error(f"❌ [MCP] Error ingesting conversation: {str(e)}")
        raise Exception(f"Ingestion failed: {str(e)}")


@mcp_app.tool()
async def get_conversations(context: Context, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    Get all conversations with pagination.
    
    Args:
        skip: Number of conversations to skip
        limit: Maximum number of conversations to return (1-1000)
    """
    await context.info(f"📋 [MCP] Fetching conversations (skip={skip}, limit={limit})")

    try:
        # Resolve use case from DI container
        list_use_case = container.resolve(ListConversationsUseCase)
        
        # Execute use case
        responses = await list_use_case.execute(skip=skip, limit=limit)
        
        await context.info(f"✅ [MCP] Retrieved {len(responses)} conversations")
        
        # Convert to dict format
        return [
            {
                "id": int(resp.conversation_id),
                "scenario_title": resp.scenario_title,
                "original_title": resp.original_title,
                "url": resp.url,
                "created_at": resp.created_at.isoformat() if resp.created_at else None
            }
            for resp in responses
        ]
        
    except Exception as e:
        await context.error(f"❌ [MCP] Error retrieving conversations: {str(e)}")
        raise Exception(f"Retrieval failed: {str(e)}")


@mcp_app.tool()
async def get_conversation(conversation_id: int, context: Context) -> dict:
    """
    Get a specific conversation by ID.
    
    Args:
        conversation_id: The ID of the conversation to retrieve
    """
    await context.info(f"🔍 [MCP] Fetching conversation with ID: {conversation_id}")

    try:
        # Resolve use case from DI container
        get_use_case = container.resolve(GetConversationUseCase)
        
        # Create request DTO
        request = GetConversationRequest(
            conversation_id=str(conversation_id),
            include_chunks=True,
            include_embeddings=False
        )
        
        # Execute use case
        response = await get_use_case.execute(request)
        
        if not response.success:
            if "not found" in response.error_message.lower():
                await context.warning(f"⚠️ [MCP] Conversation not found: {conversation_id}")
            else:
                await context.error(f"❌ [MCP] Error retrieving conversation: {response.error_message}")
            raise Exception(response.error_message)
        
        await context.info(f"✅ [MCP] Retrieved conversation: {response.scenario_title}")
        
        # Convert to dict format
        return {
            "id": int(response.conversation_id),
            "scenario_title": response.scenario_title,
            "original_title": response.original_title,
            "url": response.url,
            "created_at": response.created_at.isoformat() if response.created_at else None,
            "chunks": [
                {
                    "id": int(chunk.chunk_id) if chunk.chunk_id.isdigit() else chunk.chunk_id,
                    "text": chunk.text,
                    "order_index": chunk.order_index,
                    "author_name": chunk.author_name,
                    "author_type": chunk.author_type,
                    "timestamp": chunk.timestamp.isoformat() if chunk.timestamp else None
                }
                for chunk in response.chunks
            ]
        }
        
    except Exception as e:
        await context.error(f"❌ [MCP] Error retrieving conversation: {str(e)}")
        raise Exception(f"Retrieval failed: {str(e)}")


@mcp_app.tool()
async def delete_conversation(conversation_id: int, context: Context) -> dict:
    """
    Delete a conversation and all its chunks.
    
    Args:
        conversation_id: The ID of the conversation to delete
    """
    await context.info(f"🗑️ [MCP] Deleting conversation with ID: {conversation_id}")

    try:
        # Resolve use case from DI container
        delete_use_case = container.resolve(DeleteConversationUseCase)
        
        # Create request DTO
        request = DeleteConversationRequest(
            conversation_id=str(conversation_id)
        )
        
        # Execute use case
        response = await delete_use_case.execute(request)
        
        if not response.success:
            if "not found" in response.error_message.lower():
                await context.warning(f"⚠️ [MCP] Conversation not found for deletion: {conversation_id}")
            else:
                await context.error(f"❌ [MCP] Error deleting conversation: {response.error_message}")
            raise Exception(response.error_message)
        
        await context.info(f"✅ [MCP] Successfully deleted conversation: {conversation_id}")
        
        return {
            "conversation_id": int(response.conversation_id),
            "chunks_deleted": response.chunks_deleted,
            "message": "Conversation deleted successfully"
        }
        
    except Exception as e:
        await context.error(f"❌ [MCP] Error deleting conversation: {str(e)}")
        raise Exception(f"Deletion failed: {str(e)}")


@mcp_app.tool()
async def health_check(context: Context) -> dict:
    """
    Check the health status of the MCP server and its dependencies.
    """
    await context.info("💚 [MCP] Health check endpoint accessed")

    try:
        # Check if DI container is working
        container = get_container()
        
        # Try to resolve a use case to verify DI is working
        search_use_case = container.resolve(SearchConversationsUseCase)
        
        await context.info("✅ [MCP] MCP server and dependencies are healthy")
        return {
            "status": "healthy",
            "message": "MCP server is operational",
            "di_container": "operational"
        }
        
    except Exception as e:
        await context.error(f"❌ [MCP] Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": str(e),
            "di_container": "error"
        }


if __name__ == "__main__":
    mcp_app.run()
