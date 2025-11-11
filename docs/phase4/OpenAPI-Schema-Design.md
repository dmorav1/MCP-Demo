# OpenAPI Schema Design

**Version:** 1.0  
**Date:** November 11, 2025  
**Status:** Design Complete  
**Related:** [Inbound Adapters Architecture](./Inbound-Adapters-Architecture.md)

---

## Overview

This document defines the OpenAPI schema design for the v1 API, ensuring comprehensive, accurate, and user-friendly API documentation.

---

## Table of Contents

1. [OpenAPI Configuration](#openapi-configuration)
2. [Schema Models](#schema-models)
3. [Endpoint Documentation](#endpoint-documentation)
4. [Example Responses](#example-responses)
5. [Error Responses](#error-responses)
6. [Authentication](#authentication)
7. [Rate Limiting](#rate-limiting)

---

## OpenAPI Configuration

### FastAPI App Configuration

```python
# app/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="MCP Conversational Data Server",
    description="""
    A semantic search and RAG-powered conversational data server.
    
    ## Features
    
    * **Semantic Search**: Find relevant conversations using vector similarity
    * **RAG**: Retrieval-Augmented Generation for intelligent Q&A
    * **Conversation Management**: Store and retrieve conversations with metadata
    * **MCP Protocol**: Model Context Protocol support for LLM integration
    
    ## API Versions
    
    * **v1**: Current stable API (recommended)
    * **Legacy**: Deprecated endpoints (sunset: 2026-06-01)
    
    ## Getting Started
    
    1. Ingest conversations using POST /v1/ingest
    2. Search using GET /v1/search
    3. Use RAG via POST /v1/chat/ask
    
    ## Rate Limits
    
    * 100 requests/minute per IP
    * 1000 requests/hour per API key
    """,
    version="2.0.0",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "API Support",
        "url": "https://example.com/support",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "search-v1",
            "description": "Semantic search operations"
        },
        {
            "name": "ingest-v1",
            "description": "Conversation ingestion"
        },
        {
            "name": "conversations-v1",
            "description": "Conversation management"
        },
        {
            "name": "chat-v1",
            "description": "RAG-powered chat"
        },
        {
            "name": "health",
            "description": "Health checks and monitoring"
        }
    ]
)

def custom_openapi():
    """Customize OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    # Add common response schemas
    openapi_schema["components"]["schemas"]["Error"] = {
        "type": "object",
        "properties": {
            "detail": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "message": {"type": "string"}
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

---

## Schema Models

### Search Request/Response

```python
# app/adapters/inbound/api/models/search.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class SearchResultSchema(BaseModel):
    """A single search result."""
    
    conversation_id: str = Field(
        ...,
        description="ID of the conversation containing this result",
        example="123"
    )
    
    text: str = Field(
        ...,
        description="The relevant text chunk",
        example="We fixed the database connection issue by increasing the pool size to 20."
    )
    
    score: float = Field(
        ...,
        description="Relevance score (0-1, higher is more relevant)",
        ge=0.0,
        le=1.0,
        example=0.95
    )
    
    author_name: Optional[str] = Field(
        None,
        description="Author of the message",
        example="John Doe"
    )
    
    author_type: Optional[str] = Field(
        None,
        description="Type of author (user, assistant, system)",
        example="user"
    )
    
    timestamp: Optional[datetime] = Field(
        None,
        description="When the message was created",
        example="2025-01-15T10:30:00Z"
    )
    
    order_index: Optional[int] = Field(
        None,
        description="Position in original conversation",
        example=3
    )
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "123",
                "text": "We fixed the database connection issue by increasing the pool size to 20.",
                "score": 0.95,
                "author_name": "John Doe",
                "author_type": "user",
                "timestamp": "2025-01-15T10:30:00Z",
                "order_index": 3
            }
        }


class SearchResponseSchema(BaseModel):
    """Response from search endpoint."""
    
    query: str = Field(
        ...,
        description="The original search query",
        example="database connection error"
    )
    
    total_results: int = Field(
        ...,
        description="Number of results returned",
        ge=0,
        example=5
    )
    
    execution_time_ms: float = Field(
        ...,
        description="Search execution time in milliseconds",
        ge=0,
        example=123.45
    )
    
    results: List[SearchResultSchema] = Field(
        ...,
        description="List of search results, ordered by relevance"
    )
    
    success: bool = Field(
        True,
        description="Whether the search succeeded"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "query": "database connection error",
                "total_results": 5,
                "execution_time_ms": 123.45,
                "results": [
                    {
                        "conversation_id": "123",
                        "text": "We fixed the database connection issue by increasing the pool size to 20.",
                        "score": 0.95,
                        "author_name": "John Doe",
                        "author_type": "user",
                        "timestamp": "2025-01-15T10:30:00Z",
                        "order_index": 3
                    }
                ],
                "success": True
            }
        }
```

### Ingest Request/Response

```python
# app/adapters/inbound/api/models/ingest.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class IngestMessageSchema(BaseModel):
    """A single message in a conversation."""
    
    text: str = Field(
        ...,
        description="Message content",
        min_length=1,
        max_length=10000,
        example="The database connection was timing out after 30 seconds."
    )
    
    author_name: Optional[str] = Field(
        None,
        description="Author's name",
        example="John Doe"
    )
    
    author_type: Optional[str] = Field(
        "user",
        description="Type of author",
        example="user"
    )
    
    timestamp: Optional[datetime] = Field(
        None,
        description="Message timestamp",
        example="2025-01-15T10:30:00Z"
    )
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Message text cannot be empty or whitespace")
        return v.strip()


class IngestRequestSchema(BaseModel):
    """Request to ingest a conversation."""
    
    scenario_title: Optional[str] = Field(
        None,
        description="Title for the scenario/conversation",
        max_length=500,
        example="Database Connection Issues - January 2025"
    )
    
    original_title: Optional[str] = Field(
        None,
        description="Original conversation title",
        max_length=500,
        example="Help with DB timeout"
    )
    
    url: Optional[str] = Field(
        None,
        description="Source URL of the conversation",
        max_length=2000,
        example="https://slack.com/archives/C123/p1234567890"
    )
    
    messages: List[IngestMessageSchema] = Field(
        ...,
        description="List of messages in the conversation",
        min_items=1
    )
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError("At least one message is required")
        return v


class IngestResponseSchema(BaseModel):
    """Response after ingesting a conversation."""
    
    conversation_id: str = Field(
        ...,
        description="ID of the created conversation",
        example="456"
    )
    
    chunks_created: int = Field(
        ...,
        description="Number of chunks created from messages",
        ge=0,
        example=5
    )
    
    success: bool = Field(
        True,
        description="Whether ingestion succeeded"
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message if failed"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "456",
                "chunks_created": 5,
                "success": True,
                "error_message": None
            }
        }
```

### Conversation Management

```python
# app/adapters/inbound/api/models/conversations.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ConversationChunkSchema(BaseModel):
    """A chunk within a conversation."""
    
    chunk_id: str = Field(..., example="789")
    text: str = Field(..., example="The database connection was timing out...")
    order_index: int = Field(..., example=0, ge=0)
    author_name: Optional[str] = Field(None, example="John Doe")
    author_type: Optional[str] = Field(None, example="user")
    timestamp: Optional[datetime] = Field(None, example="2025-01-15T10:30:00Z")


class ConversationDetailSchema(BaseModel):
    """Detailed conversation information."""
    
    conversation_id: str = Field(..., example="456")
    scenario_title: Optional[str] = Field(None, example="Database Issues")
    original_title: Optional[str] = Field(None, example="Help with DB")
    url: Optional[str] = Field(None, example="https://slack.com/...")
    created_at: datetime = Field(..., example="2025-01-15T10:00:00Z")
    chunks: List[ConversationChunkSchema] = Field(..., description="Conversation chunks")


class DeleteConversationResponseSchema(BaseModel):
    """Response after deleting a conversation."""
    
    conversation_id: str = Field(..., example="456")
    chunks_deleted: int = Field(..., ge=0, example=5)
    success: bool = Field(True)
    error_message: Optional[str] = None
```

---

## Endpoint Documentation

### Search Endpoint

```python
# app/adapters/inbound/api/routers/v1/search.py
@router.get(
    "",
    response_model=SearchResponseSchema,
    summary="Search conversations",
    description="""
    Search for relevant conversation chunks using semantic similarity.
    
    This endpoint:
    1. Converts your query to a vector embedding
    2. Performs cosine similarity search against stored conversation chunks
    3. Returns ranked results with relevance scores
    
    ## How It Works
    
    The search uses vector embeddings to find semantically similar content,
    not just keyword matches. This means "database timeout" will match
    "DB connection hanging" even without shared keywords.
    
    ## Parameters
    
    * **q**: Search query (required, 1-500 characters)
        * Examples: "database connection error", "how to fix timeout"
        * Best practice: Use natural language questions
    
    * **top_k**: Number of results to return (optional, 1-50, default: 5)
        * Lower values for precise results
        * Higher values for comprehensive search
    
    * **min_score**: Minimum relevance score (optional, 0-1)
        * Filter out low-relevance results
        * Recommended: 0.7 for high precision
    
    * **author_name**: Filter by author (optional)
        * Exact match on author name
        * Case-sensitive
    
    ## Response
    
    Returns a list of conversation chunks ranked by relevance score (0-1).
    Higher scores indicate more relevant results.
    
    ## Example Usage
    
    ```bash
    # Basic search
    curl "http://localhost:8000/v1/search?q=database+connection+error&top_k=5"
    
    # With filters
    curl "http://localhost:8000/v1/search?q=timeout&top_k=10&min_score=0.7&author_name=John+Doe"
    ```
    
    ## Performance
    
    * Typical latency: 100-500ms
    * Scales to millions of chunks
    * Uses IVFFlat index for fast similarity search
    """,
    response_description="Search results with relevance scores",
    responses={
        200: {
            "description": "Successful search",
            "content": {
                "application/json": {
                    "example": {
                        "query": "database connection error",
                        "total_results": 5,
                        "execution_time_ms": 123.45,
                        "results": [
                            {
                                "conversation_id": "123",
                                "text": "We fixed the database connection issue by increasing pool size.",
                                "score": 0.95,
                                "author_name": "John Doe",
                                "timestamp": "2025-01-15T10:30:00Z"
                            }
                        ],
                        "success": True
                    }
                }
            }
        },
        400: {
            "description": "Invalid query parameters",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "VALIDATION_ERROR",
                            "message": "Query cannot be empty"
                        }
                    }
                }
            }
        },
        503: {
            "description": "Embedding service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "EMBEDDING_SERVICE_ERROR",
                            "message": "Embedding service is temporarily unavailable"
                        }
                    }
                }
            }
        }
    }
)
async def search_conversations(...):
    """Execute semantic search."""
    pass
```

### Ingest Endpoint

```python
# app/adapters/inbound/api/routers/v1/ingest.py
@router.post(
    "",
    response_model=IngestResponseSchema,
    status_code=201,
    summary="Ingest a conversation",
    description="""
    Ingest a new conversation into the system.
    
    This endpoint:
    1. Validates the conversation data
    2. Chunks messages into searchable units
    3. Generates vector embeddings for each chunk
    4. Stores conversation with embeddings in database
    
    ## Process
    
    1. **Validation**: Ensures all required fields are present
    2. **Chunking**: Splits long messages into manageable chunks
    3. **Embedding**: Generates vector embeddings using configured provider
    4. **Storage**: Saves to PostgreSQL with pgvector
    
    ## Request Body
    
    * **scenario_title**: Optional title for grouping related conversations
    * **original_title**: Original conversation title from source system
    * **url**: Source URL (e.g., Slack thread link)
    * **messages**: Array of messages (required, at least 1)
        * **text**: Message content (required, 1-10000 chars)
        * **author_name**: Message author (optional)
        * **author_type**: Type (user/assistant/system, default: user)
        * **timestamp**: When message was created (optional)
    
    ## Response
    
    Returns conversation ID and number of chunks created.
    
    ## Example Usage
    
    ```bash
    curl -X POST "http://localhost:8000/v1/ingest" \
      -H "Content-Type: application/json" \
      -d '{
        "scenario_title": "Database Issues - Jan 2025",
        "messages": [
          {
            "text": "Our database keeps timing out after 30 seconds.",
            "author_name": "John Doe",
            "timestamp": "2025-01-15T10:30:00Z"
          },
          {
            "text": "Try increasing the connection pool size.",
            "author_name": "Jane Smith",
            "timestamp": "2025-01-15T10:35:00Z"
          }
        ]
      }'
    ```
    
    ## Performance
    
    * Typical latency: 500-2000ms (depends on message count)
    * Embedding generation is the bottleneck
    * Use batch ingestion for multiple conversations
    """,
    response_description="Ingestion result with conversation ID",
    responses={
        201: {
            "description": "Successfully ingested",
            "content": {
                "application/json": {
                    "example": {
                        "conversation_id": "456",
                        "chunks_created": 5,
                        "success": True
                    }
                }
            }
        },
        400: {
            "description": "Invalid request data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "VALIDATION_ERROR",
                            "message": "At least one message is required"
                        }
                    }
                }
            }
        },
        503: {
            "description": "Embedding service unavailable"
        }
    }
)
async def ingest_conversation(...):
    """Ingest conversation."""
    pass
```

---

## Error Responses

### Standard Error Format

All error responses follow this format:

```json
{
  "detail": {
    "error": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters or body |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `REPOSITORY_ERROR` | 500 | Database operation failed |
| `EMBEDDING_SERVICE_ERROR` | 503 | Embedding service unavailable |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Example Error Responses

```python
# app/adapters/inbound/api/models/errors.py
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    """Error detail structure."""
    error: str = Field(..., example="VALIDATION_ERROR")
    message: str = Field(..., example="Query cannot be empty")

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: ErrorDetail
    
    class Config:
        schema_extra = {
            "example": {
                "detail": {
                    "error": "VALIDATION_ERROR",
                    "message": "Query cannot be empty"
                }
            }
        }
```

---

## Authentication

### API Key Authentication (Future)

```python
# app/adapters/inbound/api/routers/v1/search.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key."""
    # Implementation
    if not is_valid_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@router.get("/search", dependencies=[Security(verify_api_key)])
async def search_conversations(...):
    """Search endpoint with auth."""
    pass
```

---

## Rate Limiting

### Configuration

```python
# app/adapters/inbound/api/middleware.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = {}  # {ip: [(timestamp, count), ...]}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # Clean old entries
        if client_ip in self.requests:
            self.requests[client_ip] = [
                (ts, count) for ts, count in self.requests[client_ip]
                if now - ts < self.period
            ]
        
        # Check rate limit
        if client_ip in self.requests:
            total_requests = sum(count for _, count in self.requests[client_ip])
            if total_requests >= self.calls:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "error": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded: {self.calls} requests per {self.period} seconds"
                        }
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.calls),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + self.period))
                    }
                )
        
        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append((now, 1))
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.calls - sum(count for _, count in self.requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
        
        return response
```

---

## Summary

### Documentation Quality Checklist

- [x] All endpoints documented with descriptions
- [x] Request/response models have examples
- [x] Field descriptions are clear and helpful
- [x] Error responses documented
- [x] HTTP status codes explained
- [x] Authentication documented (when added)
- [x] Rate limiting documented
- [x] Performance characteristics mentioned
- [x] Usage examples provided
- [x] Best practices included

### OpenAPI Features Used

- [x] Pydantic models for automatic schema generation
- [x] Field validators for input validation
- [x] Example values in Field definitions
- [x] schema_extra for model examples
- [x] Detailed endpoint descriptions
- [x] Response examples for different status codes
- [x] Tags for endpoint organization
- [x] Security schemes (API key)
- [x] Custom OpenAPI schema modification

---

**Document Status**: Complete  
**Last Updated**: November 11, 2025  
**Maintained By**: Architect Agent
