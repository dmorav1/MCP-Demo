"""
Standalone MCP server that communicates with the FastAPI application via REST API calls.
This server implements MCP tools that proxy requests to the FastAPI endpoints.
"""
import asyncio
import os
from typing import Any, Dict, List
import httpx
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent


# FastAPI server configuration
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

# Initialize the MCP server
server = Server("mcp-demo")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_conversations",
            description="Search for conversations using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Number of results to return", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="ingest_conversation",
            description="Ingest a new conversation into the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Conversation title"},
                    "content": {"type": "string", "description": "Conversation content"},
                    "scenario_title": {"type": "string", "description": "Scenario title", "default": ""},
                    "url": {"type": "string", "description": "Source URL", "default": ""}
                },
                "required": ["title", "content"]
            }
        ),
        Tool(
            name="get_conversations",
            description="Get a list of conversations from the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of conversations to return", "default": 10},
                    "offset": {"type": "integer", "description": "Number of conversations to skip", "default": 0}
                }
            }
        ),
        Tool(
            name="get_conversation_chunks",
            description="Get all chunks for a specific conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "integer", "description": "Conversation ID"}
                },
                "required": ["conversation_id"]
            }
        ),
        Tool(
            name="health_check",
            description="Check the health of the FastAPI backend",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_conversations":
            return await search_conversations(**arguments)
        elif name == "ingest_conversation":
            return await ingest_conversation(**arguments)
        elif name == "get_conversations":
            return await get_conversations(**arguments)
        elif name == "get_conversation_chunks":
            return await get_conversation_chunks(**arguments)
        elif name == "health_check":
            return await health_check(**arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error calling tool {name}: {str(e)}")]


async def search_conversations(query: str, top_k: int = 5) -> List[TextContent]:
    """Search for conversations using semantic similarity."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/search",
                params={"q": query, "top_k": top_k}
            )
            response.raise_for_status()
            result = response.json()
            return [TextContent(type="text", text=f"Search results: {result}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Failed to search conversations: {str(e)}")]


async def ingest_conversation(
    title: str,
    content: str,
    scenario_title: str = "",
    url: str = ""
) -> List[TextContent]:
    """Ingest a new conversation into the database."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/ingest",
                json={
                    "original_title": title,
                    "scenario_title": scenario_title,
                    "url": url,
                    "messages": [
                        {
                            "content": content,
                            "author_name": "user",
                            "author_type": "user"
                        }
                    ]
                }
            )
            response.raise_for_status()
            result = response.json()
            return [TextContent(type="text", text=f"Conversation ingested: {result}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Failed to ingest conversation: {str(e)}")]


async def get_conversations(limit: int = 10, offset: int = 0) -> List[TextContent]:
    """Get a list of conversations from the database."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/conversations",
                params={"limit": limit, "skip": offset}
            )
            response.raise_for_status()
            result = response.json()
            return [TextContent(type="text", text=f"Conversations: {result}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Failed to get conversations: {str(e)}")]


async def get_conversation_chunks(conversation_id: int) -> List[TextContent]:
    """Get all chunks for a specific conversation."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/conversations/{conversation_id}"
            )
            response.raise_for_status()
            result = response.json()
            return [TextContent(type="text", text=f"Conversation with chunks: {result}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Failed to get conversation: {str(e)}")]


async def health_check() -> List[TextContent]:
    """Check the health of the FastAPI backend."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{FASTAPI_BASE_URL}/health")
            response.raise_for_status()
            result = response.json()
            return [TextContent(type="text", text=f"Health check: {result}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Failed to check health: {str(e)}")]


async def main():
    """Main function to run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())