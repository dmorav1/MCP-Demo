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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


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
    """
    Search MCP backend for relevant conversation context
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FASTAPI_BASE_URL}/search",
                params={"q": query, "top_k": top_k}
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"🔍 Found {len(result.get('results', []))} context items for query: '{query}'")
            return result.get("results", [])
            
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
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
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
        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        
        answer = response.choices[0].message.content
        logger.info(f"✅ LLM response generated successfully")
        return answer
        
    except Exception as e:
        logger.error(f"❌ Error generating LLM response: {e}")
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")


@router.post("/ask", response_model=ChatResponse)
async def ask_question(message: ChatMessage):
    """
    Ask a question and get an LLM response augmented with MCP context
    
    This endpoint:
    1. Searches the MCP backend for relevant historical conversations
    2. Uses those conversations as context for the LLM
    3. Generates an informed response
    """
    logger.info(f"📥 Received question: '{message.content}'")
    
    # Step 1: Search for relevant context
    context = await search_mcp_context(message.content, top_k=5)
    
    # Step 2: Generate LLM response with context
    answer = await generate_llm_response(
        message.content,
        context,
        message.conversation_history
    )
    
    return ChatResponse(
        answer=answer,
        context_used=context
    )


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
            if openai_client:
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
                stream = await openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
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
        "openai_configured": openai_client is not None,
        "mcp_backend": FASTAPI_BASE_URL
    }