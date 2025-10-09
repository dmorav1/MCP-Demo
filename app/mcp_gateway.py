"""
MCP Gateway - Web interface for MCP server interaction
Provides HTTP endpoints that proxy to the MCP server and integrate with LLM
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from openai import AsyncOpenAI

from app.logging_config import get_logger
from app import schemas

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Configuration
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
CHAT_MODEL = os.getenv("CHAT_MODEL", os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"))

# Lazy OpenAI client initialization so that adding the key after container start
# (e.g. `docker compose exec mcp-backend bash` then exporting) or injecting via
# updated environment + reload works without needing a new image build.
_cached_openai_key: Optional[str] = None
_cached_openai_client: Optional[AsyncOpenAI] = None

def get_openai_client() -> Optional[AsyncOpenAI]:
    global _cached_openai_client, _cached_openai_key
    current_key = os.getenv("OPENAI_API_KEY")
    if not current_key:
        return None
    if _cached_openai_client is None or current_key != _cached_openai_key:
        try:
            _cached_openai_client = AsyncOpenAI(api_key=current_key)
            _cached_openai_key = current_key
            logger.info("✅ Initialized OpenAI client (chat model=%s)" % CHAT_MODEL)
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            _cached_openai_client = None
    return _cached_openai_client


class ChatMessage(BaseModel):
    """Chat message from user"""
    content: str
    conversation_history: Optional[List[Dict[str, str]]] = []


class ChatResponse(BaseModel):
    """Response with LLM answer and context"""
    answer: str
    context_used: List[Dict[str, Any]]
    conversation_id: Optional[int] = None


async def search_mcp_context(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search MCP backend for relevant conversation context and normalize shape for frontend.

    The /search endpoint returns chunk-level results with raw distance (stored in 'relevance_score').
    Frontend expects:
      - conversation_id
      - scenario_title
      - matched_content
      - author_info { name, type }
      - relevance_score (similarity 0..1)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/search",
                params={"q": query, "top_k": top_k}
            )
            response.raise_for_status()
            raw = response.json()
            raw_results = raw.get("results", [])
            normalized: List[Dict[str, Any]] = []
            for r in raw_results:
                # Original relevance_score is currently L2 distance. Convert to similarity.
                distance = float(r.get("relevance_score", 0.0) or 0.0)
                similarity = 1.0 / (1.0 + distance)  # in (0,1]
                normalized.append({
                    "conversation_id": r.get("conversation_id"),
                    "scenario_title": r.get("scenario_title") or "Unknown",
                    "matched_content": (r.get("chunk_text") or "")[:800],
                    "author_info": {
                        "name": r.get("author_name") or "Unknown",
                        "type": r.get("author_type") or "unknown"
                    },
                    "relevance_score": similarity
                })
            logger.info(f"🔍 Context mapping produced {len(normalized)} items for query='{query}'")
            return normalized
    except Exception as e:
        logger.error(f"❌ Error searching MCP context: {e}")
        return []


async def generate_llm_response(
    user_question: str,
    context: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]] = None
) -> str:
    """
    Generate LLM response augmented with MCP context
    """
    client = get_openai_client()
    if not client:
        # Fallback: extract answer heuristically from top context
        if not context:
            return ("No OpenAI key configured and no relevant context found. "
                    "Please configure OPENAI_API_KEY for LLM answers or ingest more data.")
        summary_lines = []
        for i, ctx in enumerate(context[:3]):
            snippet = ctx['matched_content'][:160].replace('\n', ' ')
            summary_lines.append(f"{i+1}. [{ctx['scenario_title']}] {snippet}...")
        return ("(Fallback answer) Based on similar historical context:\n" + "\n".join(summary_lines) +
                "\n\nProvide additional details to refine the answer.")
    
    # Build context prompt from MCP search results
    context_text = "\n\n".join([
        f"**Context {i+1}** (from {ctx['scenario_title']}):\n"
        f"Author: {ctx['author_info']['name']} ({ctx['author_info']['type']})\n"
        f"Content: {ctx['matched_content']}\n"
        f"Relevance: {ctx['relevance_score']:.3f}"
        for i, ctx in enumerate(context[:3])  # Limit to top 3 for token efficiency
    ])
    
    # Build system prompt
    system_prompt = f"""You are a technical support assistant with access to historical Slack conversations about technical issues.

**Available Context from Past Conversations:**
{context_text if context_text else "No relevant historical context found."}

Use this context to provide informed, accurate answers. If the context contains similar issues and solutions, reference them. If the context isn't relevant, provide general technical guidance."""

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history[-5:])  # Last 5 messages for context
    
    # Add current user question
    messages.append({"role": "user", "content": user_question})
    
    try:
        logger.info(f"🤖 Generating LLM response for: '{user_question}'")
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        
        answer = response.choices[0].message.content
        logger.info(f"✅ LLM response generated successfully")
        return answer
        
    except Exception as e:
        # Graceful fallback: log and return context-derived summary instead of failing hard
        logger.error(f"❌ Error generating LLM response: {e}")
        if context:
            summary = []
            for i, ctx in enumerate(context[:3]):
                snippet = ctx['matched_content'][:160].replace('\n', ' ')
                summary.append(f"{i+1}. [{ctx['scenario_title']}] {snippet}...")
            return (
                "(Fallback answer due to LLM error) Related context snippets:\n" +
                "\n".join(summary) +
                f"\n\nOriginal question: {user_question}\nError: {e}" )
        return (
            "(Fallback answer) LLM unavailable and no context found. "
            "Please configure OPENAI_API_KEY or ingest more data." )


@router.post("/ask", response_model=ChatResponse)
async def ask_question(message: ChatMessage):
    """Question answering endpoint with graceful fallback when no OpenAI key is configured."""
    logger.info(f"📥 Received question: '{message.content}'")
    # Step 1: Retrieve context
    context = await search_mcp_context(message.content, top_k=5)
    # Step 2: Answer generation (LLM or fallback)
    answer = await generate_llm_response(
        message.content,
        context,
        message.conversation_history
    )
    return ChatResponse(answer=answer, context_used=context)


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with streaming responses
    """
    await websocket.accept()
    logger.info("🔌 WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            question = data.get("content", "")
            history = data.get("conversation_history", [])
            
            logger.info(f"📨 WebSocket question: '{question}'")
            
            # Search context
            context = await search_mcp_context(question, top_k=5)
            
            # Send context to client
            await websocket.send_json({
                "type": "context",
                "data": context
            })
            
            # Generate streaming response
            client = get_openai_client()
            if client:
                # Build messages (same as ask_question)
                context_text = "\n\n".join([
                    f"**Context {i+1}**: {ctx['matched_content'][:200]}..."
                    for i, ctx in enumerate(context[:3])
                ])
                
                system_prompt = f"""You are a technical support assistant.

**Context from past conversations:**
{context_text if context_text else "No relevant context found."}

Provide helpful, informed answers based on this context."""

                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(history[-5:])
                messages.append({"role": "user", "content": question})
                
                # Stream response
                stream = await client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    temperature=0.7,
                    stream=True
                )
                
                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        await websocket.send_json({
                            "type": "token",
                            "data": content
                        })
                
                # Send completion
                await websocket.send_json({
                    "type": "complete",
                    "data": {
                        "answer": full_response,
                        "context_used": context
                    }
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "data": "OpenAI API key not configured"
                })
                
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await websocket.close()


@router.get("/conversations")
async def get_all_conversations(skip: int = 0, limit: int = 50):
    """
    Get list of all conversations for browsing
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/conversations",
                params={"skip": skip, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"❌ Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chat_health_check():
    """
    Health check for chat gateway
    """
    return {
        "status": "healthy",
        "service": "mcp-chat-gateway",
        "openai_configured": get_openai_client() is not None,
        "mcp_backend": FASTAPI_BASE_URL
    }