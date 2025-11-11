# Phase 4 Architecture - Inbound Adapters Design

**Version:** 1.0  
**Date:** November 11, 2025  
**Status:** Design Complete  
**Previous Phase:** [Phase 3 - Outbound Adapters](../Phase3-Architecture.md)  
**Related Documents:**
- [Phase 3 Architecture](../Phase3-Architecture.md)
- [Migration Guide](./Inbound-Adapters-Migration-Guide.md)
- [Controller Patterns](./Controller-Implementation-Patterns.md)
- [OpenAPI Documentation](./OpenAPI-Schema-Design.md)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [REST API Inbound Adapters](#rest-api-inbound-adapters)
4. [MCP Server Inbound Adapters](#mcp-server-inbound-adapters)
5. [Controller Design Pattern](#controller-design-pattern)
6. [Route Organization](#route-organization)
7. [Dependency Injection in FastAPI](#dependency-injection-in-fastapi)
8. [Error Handling Strategy](#error-handling-strategy)
9. [Request/Response DTOs](#requestresponse-dtos)
10. [API Versioning Strategy](#api-versioning-strategy)
11. [Backward Compatibility](#backward-compatibility)
12. [OpenAPI Documentation](#openapi-documentation)
13. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

Phase 4 completes the hexagonal architecture migration by refactoring inbound adapters (REST API routes and MCP server) to use the clean architecture established in Phase 3. This design maintains 100% backward compatibility while improving internal structure, testability, and maintainability.

### Design Goals

✅ **Thin Controllers**: Controllers delegate to use cases, contain zero business logic  
✅ **Dependency Injection**: FastAPI integration with DI container for request-scoped services  
✅ **Clean DTOs**: Separate request/response models from domain entities  
✅ **Error Handling**: Consistent error mapping and status codes across all endpoints  
✅ **API Versioning**: Future-proof strategy with support for multiple API versions  
✅ **Backward Compatible**: All existing API contracts maintained  
✅ **Testability**: Controllers easily testable with mocked use cases  
✅ **Documentation**: Automatic OpenAPI schema generation from DTOs  

### Architecture Quality Goals

- **Maintainability**: Controllers under 100 lines, single responsibility
- **Testability**: 100% of controllers testable without infrastructure
- **Performance**: Zero overhead compared to current implementation
- **Reliability**: Consistent error handling with proper HTTP status codes
- **Extensibility**: Easy to add new endpoints and versions

---

## Architecture Overview

### Hexagonal Architecture - Complete Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INBOUND ADAPTERS (Phase 4)                    │
│                                                                      │
│  ┌──────────────────────────────┐   ┌───────────────────────────┐  │
│  │      REST API ADAPTERS        │   │   MCP SERVER ADAPTERS     │  │
│  │                               │   │                           │  │
│  │  • ConversationsController    │   │  • SearchToolAdapter      │  │
│  │  • IngestController           │   │  • IngestToolAdapter      │  │
│  │  • SearchController           │   │  • ConversationToolAdapter│  │
│  │  • ChatGatewayController      │   │  • HealthToolAdapter      │  │
│  │                               │   │                           │  │
│  │  [Request DTOs] → [Response DTOs] │  [Tool Definitions]       │  │
│  │  [Error Mapping] → [Status Codes] │  [Streaming Handlers]     │  │
│  └──────────────────────────────┘   └───────────────────────────┘  │
└────────────────────────┬──────────────────────────────────────────┘
                         │ (Calls Use Cases)
┌────────────────────────▼──────────────────────────────────────────┐
│                     APPLICATION LAYER (Phase 2)                     │
│                                                                      │
│  ┌─────────────────┐  ┌───────────────────┐  ┌─────────────────┐  │
│  │ IngestConversation│ │SearchConversations │ │   RAGService    │  │
│  │   Use Case       │  │    Use Case        │  │   Use Case      │  │
│  └─────────────────┘  └───────────────────┘  └─────────────────┘  │
│                                                                      │
│  [Application DTOs] ↔ [Domain Entities]                             │
└────────────────────────┬──────────────────────────────────────────┘
                         │ (Uses Domain Services & Repositories)
┌────────────────────────▼──────────────────────────────────────────┐
│                        DOMAIN LAYER (Phase 1)                        │
│                                                                      │
│  [Entities] [Value Objects] [Domain Services] [Port Interfaces]     │
└────────────────────────┬──────────────────────────────────────────┘
                         │ (Implemented by Outbound Adapters)
┌────────────────────────▼──────────────────────────────────────────┐
│                   OUTBOUND ADAPTERS (Phase 3)                        │
│                                                                      │
│  [Repositories] [Embedding Services] [External APIs]                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow - Complete Request Cycle

```
┌─────────────┐
│ HTTP Request│
│ (FastAPI)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Controller (Inbound)    │  ← Phase 4
│ • Validate request      │
│ • Map to Request DTO    │
│ • Call Use Case         │
│ • Map to Response DTO   │
│ • Handle errors         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Use Case (Application)  │  ← Phase 2
│ • Orchestrate workflow  │
│ • Use domain services   │
│ • Call repositories     │
│ • Return result         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Domain Layer            │  ← Phase 1
│ • Business rules        │
│ • Entity validation     │
│ • Value objects         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Repository (Outbound)   │  ← Phase 3
│ • Data access           │
│ • External APIs         │
│ • Persistence           │
└──────┬──────────────────┘
       │
       ▼
┌─────────────┐
│ Database    │
│ External API│
└─────────────┘
```

---

## REST API Inbound Adapters

### Controller Design Principles

1. **Thin Controllers**: No business logic, only request/response transformation
2. **Single Responsibility**: Each controller handles one resource type
3. **Dependency Injection**: Use cases injected via FastAPI dependencies
4. **Error Handling**: Consistent error mapping to HTTP status codes
5. **Validation**: Pydantic models for automatic request validation
6. **Documentation**: FastAPI auto-generates OpenAPI from type hints

### Controller Structure

```python
# app/adapters/inbound/api/controllers/base.py
from abc import ABC
from typing import TypeVar, Generic
from fastapi import HTTPException, status
from app.application.dto import ValidationError
from app.domain.repositories import RepositoryError, EmbeddingError

T = TypeVar('T')

class BaseController(ABC):
    """
    Base controller with common error handling and response mapping.
    
    All controllers inherit from this to ensure consistent behavior.
    """
    
    def handle_error(self, error: Exception) -> HTTPException:
        """
        Map domain/application errors to HTTP status codes.
        
        Args:
            error: The exception to handle
            
        Returns:
            HTTPException with appropriate status code and message
        """
        if isinstance(error, ValidationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error)
            )
        elif isinstance(error, RepositoryError):
            if "not found" in str(error).lower():
                return HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(error)
                )
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Repository error occurred"
            )
        elif isinstance(error, EmbeddingError):
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Embedding service unavailable"
            )
        else:
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
```

### Example Controller Implementation

```python
# app/adapters/inbound/api/controllers/conversations_controller.py
from typing import List
from fastapi import Depends, HTTPException, status
from app.application.dto import (
    GetConversationRequest, GetConversationResponse,
    SearchConversationRequest, SearchConversationResponse,
    DeleteConversationRequest, DeleteConversationResponse
)
from app.application.search_conversations import SearchConversationsUseCase
from .base import BaseController
from .dependencies import get_search_use_case

class ConversationsController(BaseController):
    """
    Controller for conversation-related endpoints.
    
    Responsibilities:
    - Validate incoming requests
    - Transform requests to application DTOs
    - Delegate to use cases
    - Transform use case responses to API responses
    - Handle errors with appropriate HTTP status codes
    """
    
    async def search_conversations(
        self,
        q: str,
        top_k: int = 5,
        use_case: SearchConversationsUseCase = Depends(get_search_use_case)
    ) -> SearchConversationResponse:
        """
        Search for conversations using semantic similarity.
        
        Args:
            q: Search query string
            top_k: Number of results to return (1-50)
            use_case: Injected search use case
            
        Returns:
            Search results with relevance scores
            
        Raises:
            HTTPException: If validation fails or search errors
        """
        try:
            # Create request DTO
            request = SearchConversationRequest(
                query=q,
                top_k=top_k
            )
            
            # Delegate to use case
            response = await use_case.execute(request)
            
            # Return response (already a DTO)
            return response
            
        except Exception as e:
            raise self.handle_error(e)
    
    async def get_conversation(
        self,
        conversation_id: int,
        use_case = Depends(get_get_conversation_use_case)
    ) -> GetConversationResponse:
        """
        Get a specific conversation by ID.
        
        Args:
            conversation_id: The conversation ID
            use_case: Injected use case
            
        Returns:
            Conversation details
        """
        try:
            request = GetConversationRequest(
                conversation_id=str(conversation_id),
                include_chunks=True
            )
            
            response = await use_case.execute(request)
            
            if not response.success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found"
                )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise self.handle_error(e)
    
    async def delete_conversation(
        self,
        conversation_id: int,
        use_case = Depends(get_delete_conversation_use_case)
    ) -> DeleteConversationResponse:
        """
        Delete a conversation and all its chunks.
        
        Args:
            conversation_id: The conversation ID to delete
            use_case: Injected use case
            
        Returns:
            Deletion confirmation
        """
        try:
            request = DeleteConversationRequest(
                conversation_id=str(conversation_id)
            )
            
            response = await use_case.execute(request)
            
            if not response.success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=response.error_message
                )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise self.handle_error(e)
```

---

## MCP Server Inbound Adapters

### MCP Tool Adapter Pattern

MCP tools are refactored to use the same use cases as REST endpoints, ensuring consistency and DRY principles.

```python
# app/adapters/inbound/mcp/tools/base.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from mcp.server.fastmcp import Context

T = TypeVar('T')

class BaseMCPTool(ABC):
    """
    Base class for MCP tool adapters.
    
    All MCP tools inherit from this to ensure consistent patterns:
    - Use case delegation
    - Error handling
    - Logging via MCP context
    """
    
    async def log_info(self, context: Context, message: str):
        """Log info message via MCP context."""
        await context.info(f"📋 [MCP] {message}")
    
    async def log_error(self, context: Context, message: str):
        """Log error message via MCP context."""
        await context.error(f"❌ [MCP] {message}")
    
    async def log_success(self, context: Context, message: str):
        """Log success message via MCP context."""
        await context.info(f"✅ [MCP] {message}")
    
    def handle_error(self, error: Exception) -> Exception:
        """
        Map domain/application errors to MCP-friendly exceptions.
        
        Args:
            error: The exception to handle
            
        Returns:
            Exception with user-friendly message
        """
        # Return exceptions with user-friendly messages
        # MCP protocol will handle error serialization
        return Exception(f"Operation failed: {str(error)}")
```

### MCP Tool Implementation

```python
# app/adapters/inbound/mcp/tools/search_tool.py
from mcp.server.fastmcp import Context
from app.application.dto import SearchConversationRequest
from app.application.search_conversations import SearchConversationsUseCase
from .base import BaseMCPTool

class SearchTool(BaseMCPTool):
    """
    MCP tool adapter for conversation search.
    
    This adapter:
    - Accepts MCP tool parameters
    - Maps to application DTOs
    - Delegates to SearchConversationsUseCase
    - Returns MCP-compatible responses
    """
    
    def __init__(self, search_use_case: SearchConversationsUseCase):
        self.search_use_case = search_use_case
    
    async def execute(
        self, 
        context: Context, 
        q: str, 
        top_k: int = 5
    ) -> dict:
        """
        Execute search tool.
        
        Args:
            context: MCP context for logging
            q: Search query
            top_k: Number of results
            
        Returns:
            Search results as dictionary
        """
        await self.log_info(context, f"Searching: '{q}' (top_k={top_k})")
        
        try:
            # Create request DTO
            request = SearchConversationRequest(
                query=q,
                top_k=top_k
            )
            
            # Delegate to use case
            response = await self.search_use_case.execute(request)
            
            if not response.success:
                await self.log_error(context, response.error_message)
                raise self.handle_error(Exception(response.error_message))
            
            await self.log_success(
                context, 
                f"Found {response.total_results} results"
            )
            
            # Convert to MCP response format
            return {
                "query": response.query,
                "total_results": response.total_results,
                "results": [
                    {
                        "conversation_id": r.conversation_id,
                        "text": r.text,
                        "score": r.score,
                        "author": r.author_name,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None
                    }
                    for r in response.results
                ]
            }
            
        except Exception as e:
            await self.log_error(context, str(e))
            raise self.handle_error(e)
```

### MCP Server Integration

```python
# app/adapters/inbound/mcp/server.py
from mcp.server.fastmcp import FastMCP, Context
from app.infrastructure.container import get_container
from app.application.search_conversations import SearchConversationsUseCase
from app.application.ingest_conversation import IngestConversationUseCase
from .tools.search_tool import SearchTool
from .tools.ingest_tool import IngestTool

# Initialize MCP application
mcp_app = FastMCP("Conversational Data Server")

# Register tools with dependency injection
def get_search_tool() -> SearchTool:
    """Factory function to create search tool with dependencies."""
    container = get_container()
    use_case = container.resolve(SearchConversationsUseCase)
    return SearchTool(use_case)

def get_ingest_tool() -> IngestTool:
    """Factory function to create ingest tool with dependencies."""
    container = get_container()
    use_case = container.resolve(IngestConversationUseCase)
    return IngestTool(use_case)

# Register MCP tools
@mcp_app.tool()
async def search_conversations(context: Context, q: str, top_k: int = 5) -> dict:
    """
    Search for relevant conversations using semantic similarity.
    
    Args:
        q: Search query string
        top_k: Number of results to return (1-50)
    """
    tool = get_search_tool()
    return await tool.execute(context, q, top_k)

@mcp_app.tool()
async def ingest_conversation(context: Context, conversation_data: dict) -> dict:
    """
    Ingest a new conversation into the database.
    
    Args:
        conversation_data: Conversation data with messages
    """
    tool = get_ingest_tool()
    return await tool.execute(context, conversation_data)
```

---

## Controller Design Pattern

### Pattern: Thin Controller with Use Case Delegation

**Intent**: Keep controllers focused on HTTP concerns, delegate business logic to use cases

**Structure**:
```
Controller (Inbound Adapter)
    ├── Request Validation (Pydantic)
    ├── DTO Mapping (Request → Application DTO)
    ├── Use Case Invocation
    ├── DTO Mapping (Application DTO → Response)
    └── Error Handling (Exceptions → HTTP Status)
```

**Benefits**:
- Controllers are easy to test (mock use cases)
- Business logic isolated in use cases
- HTTP concerns separated from business logic
- Consistent error handling across endpoints

### Pattern: Dependency Injection via FastAPI

**Intent**: Inject use cases into controllers at request time

**Implementation**:
```python
# app/adapters/inbound/api/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.infrastructure.container import get_container
from app.application.search_conversations import SearchConversationsUseCase
from app.database import get_db

def get_search_use_case(
    db: Session = Depends(get_db)
) -> SearchConversationsUseCase:
    """
    Dependency function to provide SearchConversationsUseCase.
    
    FastAPI calls this for each request, providing a fresh use case
    instance with a request-scoped database session.
    """
    container = get_container()
    
    # Use case will be created with fresh repository instances
    # that use the request-scoped database session
    use_case = container.resolve(SearchConversationsUseCase)
    
    return use_case
```

**Benefits**:
- Request-scoped dependencies (new DB session per request)
- Easy to mock for testing
- Automatic cleanup (session closed after request)
- Type-safe dependency resolution

---

## Route Organization

### Directory Structure

```
app/
├── adapters/
│   ├── __init__.py
│   ├── inbound/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── v1/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── conversations.py      # Conversation endpoints
│   │   │   │   │   ├── search.py             # Search endpoints
│   │   │   │   │   ├── ingest.py             # Ingest endpoints
│   │   │   │   │   ├── health.py             # Health check
│   │   │   │   │   └── chat.py               # Chat gateway
│   │   │   ├── controllers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py                   # BaseController
│   │   │   │   ├── conversations_controller.py
│   │   │   │   ├── search_controller.py
│   │   │   │   ├── ingest_controller.py
│   │   │   │   └── chat_controller.py
│   │   │   ├── dependencies.py               # FastAPI dependency functions
│   │   │   ├── middleware.py                 # Request/response middleware
│   │   │   └── error_handlers.py             # Global error handlers
│   │   └── mcp/
│   │       ├── __init__.py
│   │       ├── server.py                     # MCP server setup
│   │       └── tools/
│   │           ├── __init__.py
│   │           ├── base.py                   # BaseMCPTool
│   │           ├── search_tool.py
│   │           ├── ingest_tool.py
│   │           ├── conversation_tool.py
│   │           └── health_tool.py
│   └── outbound/                             # (Phase 3 - existing)
│       ├── persistence/
│       └── embeddings/
├── application/                               # (Phase 2 - existing)
│   ├── dto.py
│   ├── search_conversations.py
│   └── ingest_conversation.py
├── domain/                                    # (Phase 1 - existing)
│   ├── entities.py
│   ├── value_objects.py
│   └── repositories.py
└── main.py                                    # FastAPI app setup
```

### Router Organization

Each router file handles a specific resource with versioned endpoints:

```python
# app/adapters/inbound/api/routers/v1/conversations.py
from fastapi import APIRouter, Depends, Query
from app.adapters.inbound.api.controllers.conversations_controller import (
    ConversationsController
)
from app.adapters.inbound.api.dependencies import (
    get_conversations_controller
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])

# GET /v1/conversations - List all conversations
@router.get("", response_model=List[GetConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    controller: ConversationsController = Depends(get_conversations_controller)
):
    """List all conversations with pagination."""
    return await controller.list_conversations(skip, limit)

# GET /v1/conversations/{id} - Get specific conversation
@router.get("/{conversation_id}", response_model=GetConversationResponse)
async def get_conversation(
    conversation_id: int,
    controller: ConversationsController = Depends(get_conversations_controller)
):
    """Get a specific conversation by ID."""
    return await controller.get_conversation(conversation_id)

# DELETE /v1/conversations/{id} - Delete conversation
@router.delete("/{conversation_id}", response_model=DeleteConversationResponse)
async def delete_conversation(
    conversation_id: int,
    controller: ConversationsController = Depends(get_conversations_controller)
):
    """Delete a conversation and all its chunks."""
    return await controller.delete_conversation(conversation_id)
```

### Naming Conventions

- **Routers**: Plural resource names (conversations.py, searches.py)
- **Controllers**: Singular with Controller suffix (ConversationsController)
- **Endpoints**: REST verbs (GET, POST, DELETE) with resource paths
- **Dependencies**: get_* prefix (get_search_use_case)
- **Response Models**: *Response suffix (SearchConversationResponse)
- **Request Models**: *Request suffix (IngestConversationRequest)

---

## Dependency Injection in FastAPI

### Request-Scoped Service Resolution

FastAPI's dependency injection system provides request-scoped services automatically:

```python
# app/adapters/inbound/api/dependencies.py
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.infrastructure.container import get_container
from app.application.search_conversations import SearchConversationsUseCase

def get_db() -> Generator[Session, None, None]:
    """
    Provide database session for request scope.
    
    Session is created per request and closed after response.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_search_use_case(
    db: Session = Depends(get_db)
) -> SearchConversationsUseCase:
    """
    Provide SearchConversationsUseCase with request-scoped dependencies.
    
    This ensures each request gets:
    - Fresh database session
    - Fresh use case instance
    - Proper cleanup after request
    """
    container = get_container()
    
    # Temporarily register request-scoped session
    # (Alternative: use scoped container per request)
    container.register_instance(Session, db)
    
    # Resolve use case (will use registered session)
    use_case = container.resolve(SearchConversationsUseCase)
    
    return use_case
```

### Middleware for Request Context

```python
# app/adapters/inbound/api/middleware.py
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging_config import get_logger

logger = get_logger(__name__)

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context and logging.
    
    Adds:
    - Request ID (X-Request-ID header)
    - Request timing
    - Request/response logging
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        
        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration_ms:.2f}ms",
            extra={"request_id": request_id}
        )
        
        return response
```

---

## Error Handling Strategy

### Error Mapping Table

| Domain/Application Error | HTTP Status Code | Response Example |
|-------------------------|------------------|------------------|
| `ValidationError` | 400 Bad Request | `{"detail": "query cannot be empty"}` |
| `RepositoryError` (not found) | 404 Not Found | `{"detail": "Conversation 123 not found"}` |
| `RepositoryError` (other) | 500 Internal Server Error | `{"detail": "Database error occurred"}` |
| `EmbeddingError` | 503 Service Unavailable | `{"detail": "Embedding service unavailable"}` |
| `Exception` (uncaught) | 500 Internal Server Error | `{"detail": "Internal server error"}` |

### Global Error Handlers

```python
# app/adapters/inbound/api/error_handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.domain.repositories import RepositoryError, EmbeddingError, ValidationError
from app.logging_config import get_logger

logger = get_logger(__name__)

async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors from domain layer."""
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_code": "VALIDATION_ERROR"}
    )

async def repository_error_handler(request: Request, exc: RepositoryError):
    """Handle repository errors."""
    logger.error(f"Repository error: {str(exc)}")
    
    # Check if it's a not found error
    if "not found" in str(exc).lower():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "error_code": "NOT_FOUND"}
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Repository error occurred", "error_code": "REPOSITORY_ERROR"}
    )

async def embedding_error_handler(request: Request, exc: EmbeddingError):
    """Handle embedding service errors."""
    logger.error(f"Embedding error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Embedding service unavailable", "error_code": "EMBEDDING_ERROR"}
    )

async def generic_error_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}
    )

def register_error_handlers(app):
    """Register all error handlers with FastAPI app."""
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(RepositoryError, repository_error_handler)
    app.add_exception_handler(EmbeddingError, embedding_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
```

---

## Request/Response DTOs

### DTO Design Pattern

**Separation of Concerns**:
- **API DTOs**: FastAPI request/response models (Pydantic)
- **Application DTOs**: Use case input/output (dataclasses)
- **Domain Entities**: Business objects (not exposed directly)

### API Request/Response Models

```python
# app/adapters/inbound/api/models/requests.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class SearchRequest(BaseModel):
    """API request model for search endpoint."""
    q: str = Field(..., description="Search query", min_length=1)
    top_k: int = Field(5, description="Number of results", ge=1, le=50)
    
    @validator('q')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()

class IngestMessageRequest(BaseModel):
    """Individual message in conversation."""
    text: str = Field(..., description="Message text")
    author_name: Optional[str] = Field(None, description="Author name")
    author_type: Optional[str] = Field("user", description="Author type")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")

class IngestConversationAPIRequest(BaseModel):
    """API request model for ingest endpoint."""
    scenario_title: Optional[str] = Field(None, description="Scenario title")
    original_title: Optional[str] = Field(None, description="Original title")
    url: Optional[str] = Field(None, description="Source URL")
    messages: List[IngestMessageRequest] = Field(..., description="Messages")
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError("At least one message is required")
        return v
```

```python
# app/adapters/inbound/api/models/responses.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchResultResponse(BaseModel):
    """Single search result in API response."""
    conversation_id: str
    text: str
    score: float
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    order_index: Optional[int] = None

class SearchAPIResponse(BaseModel):
    """API response model for search endpoint."""
    query: str
    total_results: int
    execution_time_ms: float
    results: List[SearchResultResponse]
    success: bool = True

class ConversationChunkResponse(BaseModel):
    """Chunk within conversation response."""
    chunk_id: str
    text: str
    order_index: int
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    timestamp: Optional[datetime] = None

class ConversationDetailResponse(BaseModel):
    """API response model for conversation detail."""
    conversation_id: str
    scenario_title: Optional[str]
    original_title: Optional[str]
    url: Optional[str]
    created_at: datetime
    chunks: List[ConversationChunkResponse]

class IngestAPIResponse(BaseModel):
    """API response model for ingest endpoint."""
    conversation_id: str
    chunks_created: int
    success: bool = True
    error_message: Optional[str] = None
```

### DTO Mapping Functions

```python
# app/adapters/inbound/api/mappers.py
from app.application.dto import (
    SearchConversationRequest as AppSearchRequest,
    SearchConversationResponse as AppSearchResponse,
    IngestConversationRequest as AppIngestRequest,
    MessageDTO
)
from .models.requests import SearchRequest, IngestConversationAPIRequest
from .models.responses import SearchAPIResponse, IngestAPIResponse

class DTOMapper:
    """Maps between API models and application DTOs."""
    
    @staticmethod
    def to_search_app_request(api_request: SearchRequest) -> AppSearchRequest:
        """Map API search request to application DTO."""
        return AppSearchRequest(
            query=api_request.q,
            top_k=api_request.top_k
        )
    
    @staticmethod
    def to_search_api_response(app_response: AppSearchResponse) -> SearchAPIResponse:
        """Map application search response to API response."""
        return SearchAPIResponse(
            query=app_response.query,
            total_results=app_response.total_results,
            execution_time_ms=app_response.execution_time_ms,
            results=[
                SearchResultResponse(
                    conversation_id=r.conversation_id,
                    text=r.text,
                    score=r.score,
                    author_name=r.author_name,
                    author_type=r.author_type,
                    timestamp=r.timestamp,
                    order_index=r.order_index
                )
                for r in app_response.results
            ],
            success=app_response.success
        )
    
    @staticmethod
    def to_ingest_app_request(
        api_request: IngestConversationAPIRequest
    ) -> AppIngestRequest:
        """Map API ingest request to application DTO."""
        messages = [
            MessageDTO(
                text=msg.text,
                author_name=msg.author_name,
                author_type=msg.author_type,
                timestamp=msg.timestamp
            )
            for msg in api_request.messages
        ]
        
        return AppIngestRequest(
            messages=messages,
            scenario_title=api_request.scenario_title,
            original_title=api_request.original_title,
            url=api_request.url
        )
```

---

## API Versioning Strategy

### Strategy: URL Path Versioning

**Chosen Approach**: `/v1/resource` pattern

**Benefits**:
- Clear and explicit versioning
- Easy to understand for clients
- Works well with OpenAPI documentation
- Allows complete API rewrites per version

### Implementation

```python
# app/main.py
from fastapi import FastAPI
from app.adapters.inbound.api.routers.v1 import (
    conversations as v1_conversations,
    search as v1_search,
    ingest as v1_ingest,
    chat as v1_chat
)

app = FastAPI(title="MCP Conversational Data Server", version="2.0.0")

# Mount v1 routers
app.include_router(v1_conversations.router, prefix="/v1")
app.include_router(v1_search.router, prefix="/v1")
app.include_router(v1_ingest.router, prefix="/v1")
app.include_router(v1_chat.router, prefix="/v1")

# Root redirect to latest version
@app.get("/")
async def root():
    return {
        "message": "MCP Conversational Data Server",
        "version": "2.0.0",
        "latest_api_version": "v1",
        "documentation": "/docs"
    }
```

### Version Migration Path

```python
# Future v2 API (example)
# app/adapters/inbound/api/routers/v2/search.py
from fastapi import APIRouter

router = APIRouter(prefix="/v2/search", tags=["search-v2"])

@router.post("", response_model=SearchAPIResponseV2)
async def search_v2(request: SearchRequestV2):
    """
    Version 2 of search API with enhanced features:
    - Semantic filters
    - Result reranking
    - Faceted search
    """
    # New implementation with backward-incompatible changes
    pass
```

**Version Deprecation Strategy**:
1. Announce deprecation in v1 responses (X-API-Deprecation header)
2. Maintain v1 for at least 6 months after v2 launch
3. Return 410 Gone after deprecation period
4. Document migration guide in API docs

---

## Backward Compatibility

### Strategy: Maintain Existing Contracts

**Goal**: Zero breaking changes to existing API

**Approach**:
1. Keep existing endpoints at current paths (/, /search, /conversations, /ingest)
2. Add v1 prefixed endpoints with new architecture
3. Phase out legacy endpoints over time (with deprecation warnings)

### Legacy Endpoint Preservation

```python
# app/main.py
from app.adapters.inbound.api.routers.v1 import search as v1_search
from app.adapters.inbound.api.routers.legacy import search as legacy_search

app = FastAPI()

# New v1 endpoints (recommended)
app.include_router(v1_search.router, prefix="/v1")

# Legacy endpoints (backward compatibility)
app.include_router(legacy_search.router)  # /search endpoint

# Add deprecation headers to legacy endpoints
@app.middleware("http")
async def add_deprecation_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Check if legacy endpoint
    if not request.url.path.startswith("/v1") and request.url.path in ["/search", "/ingest", "/conversations"]:
        response.headers["X-API-Deprecation"] = "This endpoint is deprecated. Use /v1/* endpoints instead."
        response.headers["X-API-Sunset"] = "2026-06-01"  # 6 months from now
    
    return response
```

### Gradual Migration Plan

**Phase 1: Dual Operation** (Months 1-2)
- Both legacy and v1 endpoints active
- V1 endpoints documented as recommended
- Legacy endpoints marked as "stable"

**Phase 2: Deprecation** (Months 3-4)
- Legacy endpoints return deprecation headers
- Documentation updated to recommend v1
- Sunset date announced

**Phase 3: Warning** (Months 5-6)
- Legacy endpoints return warning messages
- Clients encouraged to migrate
- Support available for migration

**Phase 4: Removal** (Month 7+)
- Legacy endpoints return 410 Gone
- Only v1 endpoints supported
- Migration guide archived

---

## OpenAPI Documentation

### Auto-Generated Documentation

FastAPI automatically generates OpenAPI schemas from:
- Pydantic request/response models
- Type hints on endpoint functions
- Docstrings on endpoints and models
- Example values in Field definitions

### Enhanced Documentation

```python
# app/adapters/inbound/api/routers/v1/search.py
from fastapi import APIRouter, Query
from pydantic import Field

router = APIRouter(prefix="/v1/search", tags=["search"])

@router.get(
    "",
    response_model=SearchAPIResponse,
    summary="Search conversations",
    description="""
    Search for relevant conversation chunks using semantic similarity.
    
    This endpoint:
    1. Converts your query to a vector embedding
    2. Performs similarity search against stored chunks
    3. Returns ranked results with relevance scores
    
    ## Parameters
    - **q**: Search query (required, 1-500 characters)
    - **top_k**: Number of results to return (default: 5, max: 50)
    
    ## Response
    Returns a list of conversation chunks ranked by relevance score (0-1).
    Higher scores indicate more relevant results.
    
    ## Example
    ```
    GET /v1/search?q=database connection error&top_k=10
    ```
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
                                "text": "Fixed database connection timeout...",
                                "score": 0.95,
                                "author_name": "John Doe",
                                "author_type": "user",
                                "timestamp": "2025-01-15T10:30:00Z"
                            }
                        ]
                    }
                }
            }
        },
        400: {"description": "Invalid query parameters"},
        503: {"description": "Embedding service unavailable"}
    }
)
async def search_conversations(
    q: str = Query(
        ...,
        description="Search query string",
        min_length=1,
        max_length=500,
        example="database connection error"
    ),
    top_k: int = Query(
        5,
        description="Number of results to return",
        ge=1,
        le=50,
        example=10
    ),
    controller = Depends(get_search_controller)
):
    """Execute semantic search over conversations."""
    return await controller.search(q, top_k)
```

### Schema Examples

```python
# app/adapters/inbound/api/models/responses.py
from pydantic import BaseModel, Field

class SearchResultResponse(BaseModel):
    """Single search result."""
    conversation_id: str = Field(..., example="123")
    text: str = Field(..., example="Fixed database connection timeout by increasing pool size")
    score: float = Field(..., example=0.95, ge=0, le=1)
    author_name: Optional[str] = Field(None, example="John Doe")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "123",
                "text": "Fixed database connection timeout by increasing pool size",
                "score": 0.95,
                "author_name": "John Doe",
                "author_type": "user",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }
```

---

## Implementation Roadmap

### Phase 4.1: Foundation (Week 1)
- [x] Create directory structure
- [ ] Implement BaseController
- [ ] Implement BaseMCPTool
- [ ] Create dependency injection functions
- [ ] Set up error handlers
- [ ] Create middleware

### Phase 4.2: REST API Controllers (Week 2)
- [ ] Implement SearchController
- [ ] Implement IngestController
- [ ] Implement ConversationsController
- [ ] Implement ChatGatewayController
- [ ] Create API request/response models
- [ ] Implement DTO mappers

### Phase 4.3: REST API Routers (Week 3)
- [ ] Create v1/search router
- [ ] Create v1/ingest router
- [ ] Create v1/conversations router
- [ ] Create v1/chat router
- [ ] Create v1/health router
- [ ] Update main.py with new routers

### Phase 4.4: MCP Server Refactor (Week 4)
- [ ] Implement SearchTool adapter
- [ ] Implement IngestTool adapter
- [ ] Implement ConversationTool adapter
- [ ] Implement HealthTool adapter
- [ ] Update MCP server integration
- [ ] Test MCP protocol compatibility

### Phase 4.5: Testing (Week 5)
- [ ] Unit tests for controllers
- [ ] Unit tests for MCP tools
- [ ] Integration tests for API endpoints
- [ ] Integration tests for MCP tools
- [ ] End-to-end tests
- [ ] Performance tests

### Phase 4.6: Documentation (Week 6)
- [ ] Update README with new architecture
- [ ] Create API migration guide
- [ ] Update OpenAPI documentation
- [ ] Create MCP usage examples
- [ ] Document deployment process

### Phase 4.7: Backward Compatibility (Week 7)
- [ ] Create legacy endpoint wrappers
- [ ] Test backward compatibility
- [ ] Add deprecation warnings
- [ ] Update client libraries

### Phase 4.8: Deployment (Week 8)
- [ ] Feature flag for new architecture
- [ ] Gradual rollout plan
- [ ] Monitoring and alerting
- [ ] Rollback strategy

---

## Success Criteria

### Technical Metrics
- ✅ All controllers under 100 lines
- ✅ Zero business logic in controllers
- ✅ 100% test coverage for controllers
- ✅ All endpoints documented in OpenAPI
- ✅ Zero breaking changes to existing API
- ✅ Request latency unchanged or improved
- ✅ All use cases reused between REST and MCP

### Code Quality
- ✅ No circular dependencies
- ✅ All dependencies injected
- ✅ Consistent error handling
- ✅ Comprehensive logging
- ✅ Type hints on all functions
- ✅ Docstrings on all public APIs

### User Experience
- ✅ API documentation clear and complete
- ✅ Error messages user-friendly
- ✅ Migration path well-documented
- ✅ Deprecation warnings clear
- ✅ No service disruption during rollout

---

## Related Documents

- **Next**: [Controller Implementation Patterns](./Controller-Implementation-Patterns.md)
- **Next**: [Migration Guide](./Inbound-Adapters-Migration-Guide.md)
- **Next**: [OpenAPI Schema Design](./OpenAPI-Schema-Design.md)
- **Previous**: [Phase 3 Architecture](../Phase3-Architecture.md)

---

**Document Status**: Complete  
**Last Updated**: November 11, 2025  
**Maintained By**: Architect Agent
