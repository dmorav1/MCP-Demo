# Inbound Adapters Migration Guide

**Version:** 1.0  
**Date:** November 11, 2025  
**Status:** Design Complete  
**Related:** [Inbound Adapters Architecture](./Inbound-Adapters-Architecture.md)

---

## Overview

This guide provides step-by-step instructions for migrating from the current legacy route implementation to the new hexagonal architecture-based inbound adapters.

---

## Table of Contents

1. [Migration Strategy](#migration-strategy)
2. [Before You Begin](#before-you-begin)
3. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
4. [Phase 2: Create Controllers](#phase-2-create-controllers)
5. [Phase 3: Create New Routes](#phase-3-create-new-routes)
6. [Phase 4: Refactor MCP Server](#phase-4-refactor-mcp-server)
7. [Phase 5: Testing](#phase-5-testing)
8. [Phase 6: Deprecate Legacy](#phase-6-deprecate-legacy)
9. [Rollback Plan](#rollback-plan)
10. [FAQ](#faq)

---

## Migration Strategy

### Approach: Gradual Migration with Feature Flags

We use a **strangler fig pattern** to gradually migrate endpoints without breaking existing functionality:

1. **Create new architecture** alongside existing code
2. **Add new versioned endpoints** (/v1/*) using new architecture
3. **Keep legacy endpoints** (/) working with existing code
4. **Test thoroughly** with both endpoint sets
5. **Deprecate legacy** endpoints over time
6. **Remove legacy** code after migration period

### Benefits

✅ Zero downtime during migration  
✅ Easy rollback if issues occur  
✅ Gradual testing and validation  
✅ Backward compatibility maintained  
✅ Clear migration timeline for clients  

---

## Before You Begin

### Prerequisites

- [ ] Phase 3 (Outbound Adapters) complete
- [ ] All tests passing in current implementation
- [ ] Understanding of hexagonal architecture principles
- [ ] Familiarity with FastAPI dependency injection
- [ ] Development environment set up

### Backup Current State

```bash
# Create a backup branch
git checkout -b backup/pre-inbound-migration
git push origin backup/pre-inbound-migration

# Return to main branch
git checkout main
```

### Enable Feature Flag

```bash
# .env
USE_NEW_ARCHITECTURE=true
USE_NEW_API_ROUTES=false  # Start with false, enable after testing
```

---

## Phase 1: Foundation Setup

### Step 1.1: Create Directory Structure

```bash
# Create inbound adapter directories
mkdir -p app/adapters/inbound/api/routers/v1
mkdir -p app/adapters/inbound/api/controllers
mkdir -p app/adapters/inbound/mcp/tools

# Create __init__.py files
touch app/adapters/inbound/__init__.py
touch app/adapters/inbound/api/__init__.py
touch app/adapters/inbound/api/routers/__init__.py
touch app/adapters/inbound/api/routers/v1/__init__.py
touch app/adapters/inbound/api/controllers/__init__.py
touch app/adapters/inbound/mcp/__init__.py
touch app/adapters/inbound/mcp/tools/__init__.py
```

### Step 1.2: Create Base Controller

```python
# app/adapters/inbound/api/controllers/base.py
# See Controller-Implementation-Patterns.md for full implementation
from abc import ABC
from fastapi import HTTPException, status
from app.application.dto import ValidationError
from app.domain.repositories import RepositoryError, EmbeddingError
from app.logging_config import get_logger

logger = get_logger(__name__)

class BaseController(ABC):
    """Base controller with error handling."""
    
    def handle_error(self, error: Exception) -> HTTPException:
        """Map domain errors to HTTP status codes."""
        # Implementation from pattern document
        pass
```

### Step 1.3: Create Dependency Functions

```python
# app/adapters/inbound/api/dependencies.py
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.infrastructure.container import get_container
from app.application.search_conversations import SearchConversationsUseCase
from app.application.ingest_conversation import IngestConversationUseCase

def get_db() -> Generator[Session, None, None]:
    """Provide database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_search_use_case(
    db: Session = Depends(get_db)
) -> SearchConversationsUseCase:
    """Provide search use case with dependencies."""
    container = get_container()
    # Container resolves use case with all dependencies
    return container.resolve(SearchConversationsUseCase)

def get_ingest_use_case(
    db: Session = Depends(get_db)
) -> IngestConversationUseCase:
    """Provide ingest use case with dependencies."""
    container = get_container()
    return container.resolve(IngestConversationUseCase)
```

### Step 1.4: Create Error Handlers

```python
# app/adapters/inbound/api/error_handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.domain.repositories import ValidationError, RepositoryError, EmbeddingError
from app.logging_config import get_logger

logger = get_logger(__name__)

async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_code": "VALIDATION_ERROR"}
    )

# Add other handlers...

def register_error_handlers(app):
    """Register all error handlers."""
    app.add_exception_handler(ValidationError, validation_error_handler)
    # Register other handlers...
```

### Step 1.5: Create Middleware

```python
# app/adapters/inbound/api/middleware.py
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging_config import get_logger

logger = get_logger(__name__)

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        
        return response
```

---

## Phase 2: Create Controllers

### Step 2.1: Search Controller

```python
# app/adapters/inbound/api/controllers/search_controller.py
from app.application.dto import SearchConversationRequest
from app.application.search_conversations import SearchConversationsUseCase
from .base import BaseController

class SearchController(BaseController):
    """Controller for search endpoints."""
    
    async def search_conversations(
        self,
        query: str,
        top_k: int,
        use_case: SearchConversationsUseCase
    ):
        """Search conversations."""
        self.log_request("search", query=query, top_k=top_k)
        
        try:
            request = SearchConversationRequest(query=query, top_k=top_k)
            response = await use_case.execute(request)
            
            if not response.success:
                raise ValueError(response.error_message)
            
            self.log_response("search", success=True, results=response.total_results)
            return response
            
        except Exception as e:
            raise self.handle_error(e)
```

### Step 2.2: Ingest Controller

```python
# app/adapters/inbound/api/controllers/ingest_controller.py
from typing import List
from app.application.dto import IngestConversationRequest, MessageDTO
from app.application.ingest_conversation import IngestConversationUseCase
from .base import BaseController

class IngestController(BaseController):
    """Controller for ingestion endpoints."""
    
    async def ingest_conversation(
        self,
        messages: List[dict],
        scenario_title: str,
        original_title: str,
        url: str,
        use_case: IngestConversationUseCase
    ):
        """Ingest conversation."""
        self.log_request("ingest", message_count=len(messages))
        
        try:
            message_dtos = [
                MessageDTO(
                    text=msg["text"],
                    author_name=msg.get("author_name"),
                    author_type=msg.get("author_type"),
                    timestamp=msg.get("timestamp")
                )
                for msg in messages
            ]
            
            request = IngestConversationRequest(
                messages=message_dtos,
                scenario_title=scenario_title,
                original_title=original_title,
                url=url
            )
            
            response = await use_case.execute(request)
            
            if not response.success:
                raise ValueError(response.error_message)
            
            self.log_response("ingest", success=True, conversation_id=response.conversation_id)
            return response
            
        except Exception as e:
            raise self.handle_error(e)
```

### Step 2.3: Conversations Controller

```python
# app/adapters/inbound/api/controllers/conversations_controller.py
# See Controller-Implementation-Patterns.md for full implementation
from .base import BaseController

class ConversationsController(BaseController):
    """Controller for conversation management."""
    
    async def list_conversations(self, skip: int, limit: int, use_case):
        """List conversations with pagination."""
        # Implementation...
        pass
    
    async def get_conversation(self, conversation_id: int, use_case):
        """Get conversation by ID."""
        # Implementation...
        pass
    
    async def delete_conversation(self, conversation_id: int, use_case):
        """Delete conversation."""
        # Implementation...
        pass
```

---

## Phase 3: Create New Routes

### Step 3.1: Search Routes

```python
# app/adapters/inbound/api/routers/v1/search.py
from fastapi import APIRouter, Depends, Query
from app.adapters.inbound.api.controllers.search_controller import SearchController
from app.adapters.inbound.api.dependencies import get_search_use_case
from app.application.dto import SearchConversationResponse

router = APIRouter(prefix="/v1/search", tags=["search-v1"])

@router.get("", response_model=SearchConversationResponse)
async def search_conversations(
    q: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(5, ge=1, le=50),
    use_case = Depends(get_search_use_case)
):
    """Search conversations using semantic similarity."""
    controller = SearchController()
    return await controller.search_conversations(q, top_k, use_case)
```

### Step 3.2: Ingest Routes

```python
# app/adapters/inbound/api/routers/v1/ingest.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.adapters.inbound.api.controllers.ingest_controller import IngestController
from app.adapters.inbound/api.dependencies import get_ingest_use_case
from app.application.dto import IngestConversationResponse

router = APIRouter(prefix="/v1/ingest", tags=["ingest-v1"])

class IngestMessageRequest(BaseModel):
    """Message in conversation."""
    text: str
    author_name: Optional[str] = None
    author_type: Optional[str] = "user"
    timestamp: Optional[datetime] = None

class IngestRequest(BaseModel):
    """Ingestion request."""
    scenario_title: Optional[str] = None
    original_title: Optional[str] = None
    url: Optional[str] = None
    messages: List[IngestMessageRequest]

@router.post("", response_model=IngestConversationResponse)
async def ingest_conversation(
    request: IngestRequest,
    use_case = Depends(get_ingest_use_case)
):
    """Ingest a new conversation."""
    controller = IngestController()
    return await controller.ingest_conversation(
        messages=[msg.dict() for msg in request.messages],
        scenario_title=request.scenario_title,
        original_title=request.original_title,
        url=request.url,
        use_case=use_case
    )
```

### Step 3.3: Conversations Routes

```python
# app/adapters/inbound/api/routers/v1/conversations.py
from fastapi import APIRouter, Depends, Query
from app.adapters.inbound.api.controllers.conversations_controller import ConversationsController
from app.adapters.inbound.api.dependencies import get_conversations_use_case
from app.application.dto import GetConversationResponse, DeleteConversationResponse

router = APIRouter(prefix="/v1/conversations", tags=["conversations-v1"])

@router.get("", response_model=List[GetConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    use_case = Depends(get_conversations_use_case)
):
    """List all conversations."""
    controller = ConversationsController()
    return await controller.list_conversations(skip, limit, use_case)

@router.get("/{conversation_id}", response_model=GetConversationResponse)
async def get_conversation(
    conversation_id: int,
    use_case = Depends(get_conversations_use_case)
):
    """Get conversation by ID."""
    controller = ConversationsController()
    return await controller.get_conversation(conversation_id, use_case)

@router.delete("/{conversation_id}", response_model=DeleteConversationResponse)
async def delete_conversation(
    conversation_id: int,
    use_case = Depends(get_conversations_use_case)
):
    """Delete conversation."""
    controller = ConversationsController()
    return await controller.delete_conversation(conversation_id, use_case)
```

### Step 3.4: Update main.py

```python
# app/main.py
from fastapi import FastAPI
from app.adapters.inbound.api.routers.v1 import search, ingest, conversations
from app.adapters.inbound.api.error_handlers import register_error_handlers
from app.adapters.inbound.api.middleware import RequestContextMiddleware

app = FastAPI(title="MCP Conversational Data Server", version="2.0.0")

# Add middleware
app.add_middleware(RequestContextMiddleware)

# Register error handlers
register_error_handlers(app)

# Mount v1 routers
app.include_router(search.router)
app.include_router(ingest.router)
app.include_router(conversations.router)

# Keep legacy routers (backward compatibility)
from app.routers import conversations as legacy_conversations
from app.routers import ingest as legacy_ingest
app.include_router(legacy_conversations.router)
app.include_router(legacy_ingest.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "MCP Conversational Data Server",
        "version": "2.0.0",
        "api_version": "v1",
        "documentation": "/docs"
    }
```

---

## Phase 4: Refactor MCP Server

### Step 4.1: Create MCP Tool Base

```python
# app/adapters/inbound/mcp/tools/base.py
from abc import ABC
from mcp.server.fastmcp import Context

class BaseMCPTool(ABC):
    """Base class for MCP tools."""
    
    async def log_info(self, context: Context, message: str):
        await context.info(f"📋 [MCP] {message}")
    
    async def log_error(self, context: Context, message: str):
        await context.error(f"❌ [MCP] {message}")
    
    def handle_error(self, error: Exception) -> Exception:
        return Exception(f"Operation failed: {str(error)}")
```

### Step 4.2: Create Search Tool

```python
# app/adapters/inbound/mcp/tools/search_tool.py
from mcp.server.fastmcp import Context
from app.application.dto import SearchConversationRequest
from app.application.search_conversations import SearchConversationsUseCase
from .base import BaseMCPTool

class SearchTool(BaseMCPTool):
    """MCP tool for search."""
    
    def __init__(self, use_case: SearchConversationsUseCase):
        self.use_case = use_case
    
    async def execute(self, context: Context, q: str, top_k: int = 5) -> dict:
        """Execute search."""
        await self.log_info(context, f"Searching: '{q}'")
        
        try:
            request = SearchConversationRequest(query=q, top_k=top_k)
            response = await self.use_case.execute(request)
            
            if not response.success:
                raise self.handle_error(Exception(response.error_message))
            
            await self.log_info(context, f"Found {response.total_results} results")
            
            return {
                "query": response.query,
                "total_results": response.total_results,
                "results": [
                    {
                        "conversation_id": r.conversation_id,
                        "text": r.text,
                        "score": r.score
                    }
                    for r in response.results
                ]
            }
            
        except Exception as e:
            await self.log_error(context, str(e))
            raise self.handle_error(e)
```

### Step 4.3: Update MCP Server

```python
# app/mcp_server_refactored.py
from mcp.server.fastmcp import FastMCP, Context
from app.infrastructure.container import get_container
from app.application.search_conversations import SearchConversationsUseCase
from app.adapters.inbound.mcp.tools.search_tool import SearchTool

mcp_app = FastMCP("Conversational Data Server")

def get_search_tool() -> SearchTool:
    """Factory for search tool."""
    container = get_container()
    use_case = container.resolve(SearchConversationsUseCase)
    return SearchTool(use_case)

@mcp_app.tool()
async def search_conversations(context: Context, q: str, top_k: int = 5) -> dict:
    """Search conversations (MCP tool)."""
    tool = get_search_tool()
    return await tool.execute(context, q, top_k)

# Add other tools...
```

---

## Phase 5: Testing

### Step 5.1: Unit Tests

```bash
# Test controllers
pytest tests/unit/adapters/inbound/api/controllers/ -v

# Test MCP tools
pytest tests/unit/adapters/inbound/mcp/tools/ -v
```

### Step 5.2: Integration Tests

```bash
# Test v1 API endpoints
pytest tests/integration/api/v1/ -v

# Test backward compatibility
pytest tests/integration/api/legacy/ -v
```

### Step 5.3: End-to-End Tests

```bash
# Test complete workflows
pytest tests/e2e/ -v
```

### Step 5.4: Manual Testing

```bash
# Start server
uvicorn app.main:app --reload

# Test v1 search
curl "http://localhost:8000/v1/search?q=test&top_k=5"

# Test legacy search (backward compatibility)
curl "http://localhost:8000/search?q=test&top_k=5"

# Test v1 ingest
curl -X POST "http://localhost:8000/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"text": "test message"}]}'
```

---

## Phase 6: Deprecate Legacy

### Step 6.1: Add Deprecation Headers

```python
# app/main.py
@app.middleware("http")
async def add_deprecation_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Legacy endpoints
    if not request.url.path.startswith("/v1"):
        if request.url.path in ["/search", "/ingest", "/conversations"]:
            response.headers["X-API-Deprecation"] = \
                "This endpoint is deprecated. Use /v1/* instead."
            response.headers["X-API-Sunset"] = "2026-06-01"
    
    return response
```

### Step 6.2: Update Documentation

Update README.md and API docs to recommend v1 endpoints:

```markdown
## API Endpoints

### Recommended (v1)
- `GET /v1/search` - Search conversations
- `POST /v1/ingest` - Ingest conversation
- `GET /v1/conversations` - List conversations

### Legacy (Deprecated - Sunset: 2026-06-01)
- `GET /search` - Use `/v1/search` instead
- `POST /ingest` - Use `/v1/ingest` instead
- `GET /conversations` - Use `/v1/conversations` instead
```

### Step 6.3: Notify Users

Send migration notice to API users:

```
Subject: API Migration Notice - Action Required

We're upgrading our API to improve performance and maintainability.

Action Required:
- Migrate to /v1/* endpoints by June 1, 2026
- Update your code to use new endpoints
- Test thoroughly before sunset date

Migration Guide:
https://github.com/yourrepo/docs/migration-guide.md

Support:
Contact us if you need help with migration
```

### Step 6.4: Remove Legacy Endpoints

After sunset date (6 months):

```python
# app/main.py
# Remove legacy routers
# app.include_router(legacy_conversations.router)  # REMOVED
# app.include_router(legacy_ingest.router)  # REMOVED

# Add 410 Gone for legacy endpoints
@app.get("/search", status_code=410)
async def legacy_search():
    return {"detail": "This endpoint has been removed. Use /v1/search instead."}
```

---

## Rollback Plan

### If Issues Occur

1. **Immediate Rollback** (< 5 minutes):
   ```bash
   # Disable new routes via feature flag
   export USE_NEW_API_ROUTES=false
   # Restart service
   systemctl restart mcp-backend
   ```

2. **Code Rollback** (< 15 minutes):
   ```bash
   # Revert to backup branch
   git checkout backup/pre-inbound-migration
   git push origin main --force
   # Deploy
   ./deploy.sh
   ```

3. **Investigate and Fix**:
   - Check logs for errors
   - Review monitoring dashboards
   - Fix issues in development
   - Re-test thoroughly
   - Re-attempt migration

---

## FAQ

### Q: Will this break existing API clients?

**A:** No. Legacy endpoints remain functional throughout migration. Clients can migrate at their own pace.

### Q: How long will legacy endpoints be supported?

**A:** 6 months from deprecation announcement. After that, they return 410 Gone.

### Q: Can I use both old and new endpoints?

**A:** Yes. Both work during migration period.

### Q: How do I know which endpoints to use?

**A:** Use v1 endpoints for new code. Migrate existing code gradually.

### Q: What if I find a bug in v1 endpoints?

**A:** Report immediately. We'll fix and may extend deprecation period if needed.

### Q: Will performance change?

**A:** No. New architecture should have same or better performance.

### Q: Do I need to change my MCP client?

**A:** No. MCP protocol remains unchanged. Internal refactoring only.

---

## Summary

### Migration Checklist

- [ ] Phase 1: Foundation setup complete
- [ ] Phase 2: Controllers implemented
- [ ] Phase 3: New routes created
- [ ] Phase 4: MCP server refactored
- [ ] Phase 5: All tests passing
- [ ] Phase 6: Deprecation notices sent
- [ ] Legacy endpoints removed after sunset

### Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1 | Week 1 | Foundation setup |
| Phase 2 | Week 2 | Controller implementation |
| Phase 3 | Week 3 | Route creation |
| Phase 4 | Week 4 | MCP refactoring |
| Phase 5 | Week 5 | Testing |
| Phase 6 | 6 months | Gradual deprecation |

---

**Document Status**: Complete  
**Last Updated**: November 11, 2025  
**Maintained By**: Architect Agent
