"""
Standalone MCP server that communicates with the FastAPI application via REST API calls.
This server implements MCP tools that proxy requests to the FastAPI endpoints.
"""
import os
from typing import List
import httpx
from mcp.server.fastmcp import FastMCP, Context

from app import schemas


# Set up logging
log_level = os.getenv("LOG_LEVEL", "WARN")


# FastAPI server configuration
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

# Initialize the MCP application
mcp_app = FastMCP(
    "Conversational Data Server",
    description="Exposes conversation ingestion and search via MCP."
)


@mcp_app.tool()
async def search_conversations(context: Context, q: str, top_k: int = 5) -> schemas.SearchResponse:
    """
    Search for relevant conversations using semantic similarity.
    The search query is converted to a vector embedding and compared against
    stored conversation chunks using cosine similarity.
    
    Args:
        q: Search query string
        top_k: Number of results to return (1-50)
    """
    await context.info(f"🔍 [MCP] Searching conversations with query: '{q}' (top_k={top_k})")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/search",
                params={"q": q, "top_k": top_k}
            )
            response.raise_for_status()
            
            result_data = response.json()
            search_response = schemas.SearchResponse(**result_data)

            await context.info(f"🎯 [MCP] Found {len(search_response.results)} search results")
            await context.info(f"✅ [MCP] Search completed successfully for query: '{q}'")

            return search_response
            
        except httpx.HTTPStatusError as e:
            await context.error(f"❌ [MCP] HTTP error searching conversations: {e}")
            raise Exception(f"Search failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            await context.error(f"❌ [MCP] Error searching conversations: {str(e)}")
            raise Exception(f"Search failed: {str(e)}")


@mcp_app.tool()
async def ingest_conversation(conversation_data: schemas.ConversationIngest, context: Context) -> schemas.Conversation:
    """
    Ingest a new conversation into the database.
    
    This tool processes the conversation data, chunks it into smaller pieces,
    generates embeddings for each chunk, and stores everything in the database.
    
    Args:
        conversation_data: The conversation data to ingest
    """
    await context.info(f"📥 [MCP] Ingesting conversation: {conversation_data.scenario_title}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/ingest",
                json=conversation_data.model_dump()
            )
            response.raise_for_status()
            
            result_data = response.json()
            conversation = schemas.Conversation(**result_data)

            await context.info(f"✅ [MCP] Successfully ingested conversation ID: {conversation.id}")
            return conversation
            
        except httpx.HTTPStatusError as e:
            await context.error(f"❌ [MCP] HTTP error ingesting conversation: {e}")
            raise Exception(f"Ingestion failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            await context.error(f"❌ [MCP] Error ingesting conversation: {str(e)}")
            raise Exception(f"Ingestion failed: {str(e)}")


@mcp_app.tool()
async def get_conversations(context: Context, skip: int = 0, limit: int = 100) -> List[schemas.Conversation]:
    """
    Get all conversations with pagination.
    
    Args:
        skip: Number of conversations to skip
        limit: Maximum number of conversations to return (1-1000)
    """
    await context.info(f"📋 [MCP] Fetching conversations (skip={skip}, limit={limit})")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/conversations",
                params={"skip": skip, "limit": limit}
            )
            response.raise_for_status()
            
            result_data = response.json()
            conversations = [schemas.Conversation(**conv) for conv in result_data]

            await context.info(f"✅ [MCP] Retrieved {len(conversations)} conversations")
            return conversations
            
        except httpx.HTTPStatusError as e:
            await context.error(f"❌ [MCP] HTTP error retrieving conversations: {e}")
            raise Exception(f"Retrieval failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            await context.error(f"❌ [MCP] Error retrieving conversations: {str(e)}")
            raise Exception(f"Retrieval failed: {str(e)}")


@mcp_app.tool()
async def get_conversation(conversation_id: int, context: Context) -> schemas.Conversation:
    """
    Get a specific conversation by ID.
    
    Args:
        conversation_id: The ID of the conversation to retrieve
    """
    await context.info(f"🔍 [MCP] Fetching conversation with ID: {conversation_id}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FASTAPI_BASE_URL}/conversations/{conversation_id}")
            response.raise_for_status()
            
            result_data = response.json()
            conversation = schemas.Conversation(**result_data)

            await context.info(f"✅ [MCP] Retrieved conversation: {conversation.scenario_title}")
            return conversation
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await context.warning(f"⚠️ [MCP] Conversation not found: {conversation_id}")
                raise Exception(f"Conversation with ID {conversation_id} not found")
            await context.error(f"❌ [MCP] HTTP error retrieving conversation: {e}")
            raise Exception(f"Retrieval failed with status {e.response.status_code}: {e.response.text}")
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

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{FASTAPI_BASE_URL}/conversations/{conversation_id}")
            response.raise_for_status()
            
            result_data = response.json()

            await context.info(f"✅ [MCP] Successfully deleted conversation: {conversation_id}")
            return result_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await context.warning(f"⚠️ [MCP] Conversation not found for deletion: {conversation_id}")
                raise Exception(f"Conversation with ID {conversation_id} not found")
            await context.error(f"❌ [MCP] HTTP error deleting conversation: {e}")
            raise Exception(f"Deletion failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            await context.error(f"❌ [MCP] Error deleting conversation: {str(e)}")
            raise Exception(f"Deletion failed: {str(e)}")


@mcp_app.tool()
async def health_check(context: Context) -> dict:
    """
    Check the health status of the FastAPI backend service.
    """
    await context.info("💚 [MCP] Health check endpoint accessed")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FASTAPI_BASE_URL}/health")
            response.raise_for_status()
            
            result_data = response.json()
            await context.info("✅ [MCP] Backend service is healthy")
            return result_data
            
        except httpx.HTTPStatusError as e:
            await context.error(f"❌ [MCP] Backend service health check failed: {e}")
            raise Exception(f"Health check failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            await context.error(f"❌ [MCP] Error checking backend health: {str(e)}")
            raise Exception(f"Health check failed: {str(e)}")


if __name__ == "__main__":
    mcp_app.run()
