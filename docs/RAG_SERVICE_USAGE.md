# RAG Service Usage Guide

This guide explains how to use the RAG (Retrieval-Augmented Generation) service for question answering with LangChain integration.

## Overview

The RAG service provides intelligent question answering by:
1. Retrieving relevant context from your conversation database
2. Generating natural language answers using LLMs (OpenAI, Anthropic, or local models)
3. Including source citations in answers
4. Supporting multi-turn conversations with memory
5. Streaming responses in real-time

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# RAG Provider Selection
RAG__PROVIDER=openai  # Options: openai, anthropic, local

# Model Configuration
RAG__MODEL=gpt-3.5-turbo
RAG__TEMPERATURE=0.7
RAG__MAX_TOKENS=2000

# API Keys
RAG__OPENAI_API_KEY=sk-your-openai-api-key
# RAG__ANTHROPIC_API_KEY=your-anthropic-api-key

# Retrieval Configuration
RAG__TOP_K=5
RAG__SCORE_THRESHOLD=0.7

# Features
RAG__ENABLE_STREAMING=true
RAG__ENABLE_CONVERSATION_MEMORY=true
RAG__ENABLE_CACHE=true
RAG__CACHE_TTL_SECONDS=3600

# Context Management
RAG__MAX_CONTEXT_TOKENS=3500
RAG__MAX_HISTORY_MESSAGES=10

# Performance
RAG__MAX_RETRIES=3
RAG__TIMEOUT_SECONDS=60

# Observability
RAG__ENABLE_TOKEN_TRACKING=true
RAG__ENABLE_LATENCY_TRACKING=true
```

### Python Configuration

```python
from app.infrastructure.config import get_rag_config

# Get configuration
config = get_rag_config()

# Access settings
print(f"Provider: {config.provider}")
print(f"Model: {config.model}")
print(f"Temperature: {config.temperature}")
```

## Basic Usage

### Simple Question Answering

```python
from app.application.rag_service import RAGService
from app.infrastructure.config import get_rag_config
from app.infrastructure.container import container

# Initialize service (or get from DI container)
rag_service = RAGService(
    vector_search_repository=container.vector_search_repository(),
    embedding_service=container.embedding_service(),
    config=get_rag_config()
)

# Ask a question
result = await rag_service.ask(
    query="What is Python used for?",
    top_k=5  # Optional: number of context chunks to retrieve
)

# Access the response
print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Sources used: {len(result['sources'])}")
print(f"Latency: {result['metadata']['latency_ms']:.2f}ms")

# View sources
for i, source in enumerate(result['sources'], 1):
    print(f"\n[Source {i}]")
    print(f"  Score: {source['score']:.2f}")
    print(f"  Text: {source['text'][:100]}...")
    print(f"  Author: {source['author']}")
```

### Conversational Question Answering

```python
# Start a conversation
conversation_id = "user-session-123"

# First question
result1 = await rag_service.ask_with_context(
    query="What is Python?",
    conversation_id=conversation_id
)
print(result1['answer'])

# Follow-up question (context is maintained)
result2 = await rag_service.ask_with_context(
    query="Who created it?",
    conversation_id=conversation_id
)
print(result2['answer'])

# Another follow-up
result3 = await rag_service.ask_with_context(
    query="When was it first released?",
    conversation_id=conversation_id
)
print(result3['answer'])

# Clear conversation when done
rag_service.clear_conversation_memory(conversation_id)
```

### Streaming Responses

```python
# Stream the answer in real-time
async for chunk in rag_service.ask_streaming(
    query="Explain Python's key features",
    top_k=5
):
    print(chunk, end='', flush=True)
```

## Advanced Usage

### Custom Parameters

```python
# Override default parameters
result = await rag_service.ask(
    query="What are Python's advantages?",
    top_k=10,  # Retrieve more context
    temperature=0.3,  # More focused responses
    max_tokens=1000,  # Limit response length
    provider="anthropic",  # Override provider
    model="claude-3-sonnet-20240229"  # Specific model
)
```

### Token Usage Tracking

```python
# Reset counters at start of session
rag_service.reset_token_usage()

# Perform multiple queries
await rag_service.ask("Question 1")
await rag_service.ask("Question 2")
await rag_service.ask("Question 3")

# Check token usage
usage = rag_service.get_token_usage()
print(f"Prompt tokens: {usage['prompt_tokens']}")
print(f"Completion tokens: {usage['completion_tokens']}")
print(f"Total tokens: {usage['prompt_tokens'] + usage['completion_tokens']}")

# Estimate costs (example for OpenAI)
prompt_cost = usage['prompt_tokens'] * 0.0015 / 1000  # $0.0015 per 1K tokens
completion_cost = usage['completion_tokens'] * 0.002 / 1000  # $0.002 per 1K tokens
total_cost = prompt_cost + completion_cost
print(f"Estimated cost: ${total_cost:.4f}")
```

### Error Handling

```python
try:
    result = await rag_service.ask("What is Python?")
    
    if "error" in result["metadata"]:
        print(f"Error occurred: {result['metadata']['error']}")
        print(f"Fallback answer: {result['answer']}")
    else:
        print(f"Success! Answer: {result['answer']}")
        
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Response Format

### Standard Response

```python
{
    "answer": "Python is a high-level programming language according to [Source 1]...",
    "sources": [
        {
            "chunk_id": "chunk-123",
            "text": "Python is a high-level programming language...",
            "score": 0.95,
            "author": "Alice"
        },
        # ... more sources
    ],
    "confidence": 0.85,  # 0.0 to 1.0
    "metadata": {
        "query": "What is Python?",
        "chunks_retrieved": 5,
        "citations": [1, 2],  # Which sources were cited
        "latency_ms": 1234.56,
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "cached": false,
        "tokens": {
            "prompt": 150,
            "completion": 50,
            "total": 200
        }
    }
}
```

### Error Response

```python
{
    "answer": "I encountered an error while processing your question: ...",
    "sources": [],
    "confidence": 0.0,
    "metadata": {
        "query": "What is Python?",
        "error": "API rate limit exceeded",
        "latency_ms": 100.0
    }
}
```

## Best Practices

### 1. Query Formulation

```python
# Good: Clear, specific questions
result = await rag_service.ask("What are the main features of Python 3.9?")

# Good: Natural language
result = await rag_service.ask("Can you explain how Python's GIL works?")

# Avoid: Very short or vague queries
# result = await rag_service.ask("Python?")  # Too vague
```

### 2. Conversation Management

```python
# Use unique conversation IDs per user/session
conversation_id = f"user-{user_id}-{session_id}"

# Clear memory when conversation ends
rag_service.clear_conversation_memory(conversation_id)

# Or periodically clear all memories
if hour == 0 and minute == 0:  # Daily cleanup
    rag_service.clear_conversation_memory()
```

### 3. Caching Strategy

```python
# Cache is enabled by default with 1-hour TTL
# For frequently asked questions, this saves API calls

# Disable cache for sensitive/real-time queries
config.enable_cache = False
result = await rag_service.ask("What's the current stock price?")

# Re-enable cache
config.enable_cache = True
```

### 4. Context Tuning

```python
# More context for complex questions
result = await rag_service.ask(
    query="Compare Python and JavaScript for web development",
    top_k=10  # More context
)

# Less context for simple questions
result = await rag_service.ask(
    query="What is Python?",
    top_k=3  # Quick answer
)
```

## Integration Examples

### FastAPI Endpoint

```python
from fastapi import APIRouter, Depends
from app.infrastructure.container import container
from app.infrastructure.config import get_rag_config

router = APIRouter()

@router.post("/ask")
async def ask_question(
    query: str,
    conversation_id: Optional[str] = None,
    rag_service: RAGService = Depends(lambda: RAGService(
        vector_search_repository=container.vector_search_repository(),
        embedding_service=container.embedding_service(),
        config=get_rag_config()
    ))
):
    """Ask a question and get an AI-generated answer."""
    if conversation_id:
        result = await rag_service.ask_with_context(
            query=query,
            conversation_id=conversation_id
        )
    else:
        result = await rag_service.ask(query=query)
    
    return result
```

### Streaming Endpoint

```python
from fastapi.responses import StreamingResponse

@router.post("/ask/stream")
async def ask_streaming(
    query: str,
    rag_service: RAGService = Depends(...)
):
    """Stream the answer as it's generated."""
    async def generate():
        async for chunk in rag_service.ask_streaming(query=query):
            yield chunk
    
    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
```

### MCP Tool Integration

```python
from mcp.server.stdio import server

@server.list_tools()
async def list_tools():
    return [
        {
            "name": "ask_question",
            "description": "Ask a question about your conversations",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "conversation_id": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "ask_question":
        result = await rag_service.ask_with_context(
            query=arguments["query"],
            conversation_id=arguments.get("conversation_id")
        )
        return {"content": [{"type": "text", "text": result["answer"]}]}
```

## Troubleshooting

### Issue: API Key Errors

```python
# Ensure API keys are set
import os
assert os.getenv("RAG__OPENAI_API_KEY"), "OpenAI API key not set"

# Or check config
config = get_rag_config()
assert config.openai_api_key, "OpenAI API key not configured"
```

### Issue: Slow Responses

```python
# Check latency
result = await rag_service.ask("Question")
latency_ms = result["metadata"]["latency_ms"]

if latency_ms > 5000:  # 5 seconds
    # Consider:
    # 1. Reducing top_k (less context to process)
    # 2. Enabling cache
    # 3. Using a faster model (gpt-3.5-turbo vs gpt-4)
    pass
```

### Issue: Poor Answer Quality

```python
result = await rag_service.ask("Question")

if result["confidence"] < 0.5:
    # Try:
    # 1. Increase top_k for more context
    # 2. Check if relevant data exists in database
    # 3. Rephrase the question
    # 4. Increase temperature for more creative answers
    pass

# Check citations
if not result["metadata"]["citations"]:
    print("Warning: Answer not grounded in sources")
```

## Performance Optimization

### 1. Batch Queries

```python
# For multiple queries, reuse the service instance
queries = ["Question 1", "Question 2", "Question 3"]
results = []

for query in queries:
    result = await rag_service.ask(query)
    results.append(result)

# Check total token usage
usage = rag_service.get_token_usage()
```

### 2. Cache Warming

```python
# Pre-cache common questions
common_questions = [
    "What is Python?",
    "How do I install Python?",
    "What are Python's key features?"
]

for question in common_questions:
    await rag_service.ask(question)  # Warm the cache
```

### 3. Memory Management

```python
# Periodically clear old conversations
MAX_CONVERSATIONS = 100

if len(rag_service._conversation_memory) > MAX_CONVERSATIONS:
    # Clear oldest conversations
    # (In production, use Redis with TTL for this)
    rag_service.clear_conversation_memory()
```

## Security Considerations

1. **API Key Management**: Never commit API keys to version control
2. **Input Validation**: Queries are automatically sanitized
3. **Rate Limiting**: Implement rate limiting at the API level
4. **Cost Control**: Monitor token usage and set budget limits
5. **Content Filtering**: Enable content filtering in LLM provider settings

## Monitoring and Observability

```python
# Log all queries for audit
import logging
logger = logging.getLogger(__name__)

result = await rag_service.ask(query)
logger.info(
    "RAG query",
    extra={
        "query": query,
        "confidence": result["confidence"],
        "latency_ms": result["metadata"]["latency_ms"],
        "tokens": result["metadata"].get("tokens", {})
    }
)
```

## Next Steps

- Explore prompt template customization
- Implement custom citation formatting
- Add support for images in context
- Integrate with external knowledge bases
- Add semantic caching with embeddings
- Implement query rewriting for better retrieval
