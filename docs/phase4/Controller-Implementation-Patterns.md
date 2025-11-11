# Controller Implementation Patterns

**Version:** 1.0  
**Date:** November 11, 2025  
**Status:** Design Complete  
**Related:** [Inbound Adapters Architecture](./Inbound-Adapters-Architecture.md)

---

## Overview

This document provides detailed implementation patterns and examples for controllers in the inbound adapter layer. These patterns ensure consistency, testability, and maintainability across all API endpoints.

---

## Table of Contents

1. [Base Controller Pattern](#base-controller-pattern)
2. [Search Controller Example](#search-controller-example)
3. [Ingest Controller Example](#ingest-controller-example)
4. [Conversations Controller Example](#conversations-controller-example)
5. [Chat Gateway Controller Example](#chat-gateway-controller-example)
6. [Testing Patterns](#testing-patterns)
7. [Common Pitfalls](#common-pitfalls)

---

## Base Controller Pattern

### Implementation

```python
# app/adapters/inbound/api/controllers/base.py
from abc import ABC
from typing import Optional
from fastapi import HTTPException, status
from app.application.dto import ValidationError
from app.domain.repositories import RepositoryError, EmbeddingError
from app.logging_config import get_logger

logger = get_logger(__name__)

class BaseController(ABC):
    """
    Base controller providing common functionality for all controllers.
    
    Responsibilities:
    - Error handling and HTTP status code mapping
    - Common logging patterns
    - Response formatting helpers
    
    All controllers should inherit from this class to ensure consistent behavior.
    """
    
    def handle_error(self, error: Exception) -> HTTPException:
        """
        Map domain/application errors to HTTP status codes.
        
        This method provides centralized error handling, ensuring consistent
        error responses across all endpoints.
        
        Args:
            error: The exception to handle
            
        Returns:
            HTTPException with appropriate status code and message
            
        Examples:
            >>> try:
            ...     # some operation
            ... except Exception as e:
            ...     raise self.handle_error(e)
        """
        # Log the original error for debugging
        logger.error(f"Error in controller: {type(error).__name__}: {str(error)}")
        
        # Map to appropriate HTTP status
        if isinstance(error, ValidationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": str(error)
                }
            )
        elif isinstance(error, RepositoryError):
            # Check for specific repository error types
            if "not found" in str(error).lower():
                return HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "NOT_FOUND",
                        "message": str(error)
                    }
                )
            elif "duplicate" in str(error).lower() or "already exists" in str(error).lower():
                return HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "CONFLICT",
                        "message": str(error)
                    }
                )
            else:
                return HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "REPOSITORY_ERROR",
                        "message": "Database operation failed"
                    }
                )
        elif isinstance(error, EmbeddingError):
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "EMBEDDING_SERVICE_ERROR",
                    "message": "Embedding service is temporarily unavailable"
                }
            )
        else:
            # Log unexpected errors with full traceback
            logger.exception("Unexpected error in controller")
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                }
            )
    
    def log_request(self, operation: str, **params):
        """
        Log incoming request with parameters.
        
        Args:
            operation: Name of the operation
            **params: Request parameters to log
        """
        logger.info(f"Controller operation: {operation}", extra=params)
    
    def log_response(self, operation: str, success: bool = True, **metrics):
        """
        Log operation result with metrics.
        
        Args:
            operation: Name of the operation
            success: Whether operation succeeded
            **metrics: Metrics to log (e.g., count, duration)
        """
        level = "info" if success else "warning"
        getattr(logger, level)(
            f"Controller operation completed: {operation}",
            extra={"success": success, **metrics}
        )
```

### Usage

```python
# Example controller inheriting from BaseController
class SearchController(BaseController):
    async def search(self, query: str, top_k: int, use_case):
        self.log_request("search", query=query, top_k=top_k)
        try:
            # Delegate to use case
            result = await use_case.execute(...)
            self.log_response("search", success=True, results=len(result))
            return result
        except Exception as e:
            raise self.handle_error(e)
```

---

## Search Controller Example

### Full Implementation

```python
# app/adapters/inbound/api/controllers/search_controller.py
from typing import Optional
from app.application.dto import SearchConversationRequest, SearchFilters
from app.application.search_conversations import SearchConversationsUseCase
from .base import BaseController

class SearchController(BaseController):
    """
    Controller for search-related endpoints.
    
    Responsibilities:
    - Validate search parameters
    - Map parameters to SearchConversationRequest DTO
    - Delegate to SearchConversationsUseCase
    - Return search results
    """
    
    async def search_conversations(
        self,
        query: str,
        top_k: int = 5,
        min_score: Optional[float] = None,
        author_name: Optional[str] = None,
        use_case: SearchConversationsUseCase = None
    ):
        """
        Search for conversations using semantic similarity.
        
        Args:
            query: Search query string
            top_k: Maximum number of results
            min_score: Minimum relevance score (0-1)
            author_name: Filter by author name
            use_case: Injected search use case
            
        Returns:
            SearchConversationResponse with results
            
        Raises:
            HTTPException: If search fails
        """
        self.log_request(
            "search_conversations",
            query=query[:50],  # Log first 50 chars only
            top_k=top_k,
            filters={"min_score": min_score, "author_name": author_name}
        )
        
        try:
            # Build filters if provided
            filters = None
            if min_score is not None or author_name is not None:
                filters = SearchFilters(
                    min_score=min_score,
                    author_name=author_name
                )
            
            # Create request DTO
            request = SearchConversationRequest(
                query=query,
                top_k=top_k,
                filters=filters
            )
            
            # Delegate to use case
            response = await use_case.execute(request)
            
            # Check if search was successful
            if not response.success:
                self.log_response(
                    "search_conversations",
                    success=False,
                    error=response.error_message
                )
                raise ValueError(response.error_message)
            
            # Log success metrics
            self.log_response(
                "search_conversations",
                success=True,
                results=response.total_results,
                execution_time_ms=response.execution_time_ms
            )
            
            return response
            
        except ValueError as e:
            # Domain validation error
            raise self.handle_error(ValidationError(str(e)))
        except Exception as e:
            # Other errors
            raise self.handle_error(e)
```

### Router Integration

```python
# app/adapters/inbound/api/routers/v1/search.py
from fastapi import APIRouter, Depends, Query
from app.adapters.inbound.api.controllers.search_controller import SearchController
from app.adapters.inbound.api.dependencies import get_search_use_case
from app.application.dto import SearchConversationResponse

router = APIRouter(prefix="/v1/search", tags=["search"])

@router.get("", response_model=SearchConversationResponse)
async def search_conversations(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    top_k: int = Query(5, description="Number of results", ge=1, le=50),
    min_score: Optional[float] = Query(None, description="Minimum score", ge=0, le=1),
    author_name: Optional[str] = Query(None, description="Filter by author"),
    use_case = Depends(get_search_use_case)
):
    """Search conversations using semantic similarity."""
    controller = SearchController()
    return await controller.search_conversations(
        query=q,
        top_k=top_k,
        min_score=min_score,
        author_name=author_name,
        use_case=use_case
    )
```

### Unit Test

```python
# tests/unit/adapters/inbound/api/controllers/test_search_controller.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.adapters.inbound.api.controllers.search_controller import SearchController
from app.application.dto import SearchConversationResponse, SearchResultDTO

@pytest.mark.asyncio
async def test_search_conversations_success():
    """Test successful search."""
    # Arrange
    controller = SearchController()
    mock_use_case = Mock()
    mock_response = SearchConversationResponse(
        results=[
            SearchResultDTO(
                chunk_id="1",
                conversation_id="123",
                text="test chunk",
                score=0.95
            )
        ],
        query="test query",
        total_results=1,
        execution_time_ms=100.0,
        success=True
    )
    mock_use_case.execute = AsyncMock(return_value=mock_response)
    
    # Act
    result = await controller.search_conversations(
        query="test query",
        top_k=5,
        use_case=mock_use_case
    )
    
    # Assert
    assert result.success is True
    assert result.total_results == 1
    assert len(result.results) == 1
    assert result.results[0].text == "test chunk"
    mock_use_case.execute.assert_called_once()

@pytest.mark.asyncio
async def test_search_conversations_validation_error():
    """Test search with validation error."""
    # Arrange
    controller = SearchController()
    mock_use_case = Mock()
    mock_response = SearchConversationResponse(
        results=[],
        query="",
        total_results=0,
        execution_time_ms=0,
        success=False,
        error_message="Query cannot be empty"
    )
    mock_use_case.execute = AsyncMock(return_value=mock_response)
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await controller.search_conversations(
            query="",
            top_k=5,
            use_case=mock_use_case
        )
    
    assert exc_info.value.status_code == 400
```

---

## Ingest Controller Example

### Full Implementation

```python
# app/adapters/inbound/api/controllers/ingest_controller.py
from typing import List
from app.application.dto import IngestConversationRequest, MessageDTO
from app.application.ingest_conversation import IngestConversationUseCase
from .base import BaseController

class IngestController(BaseController):
    """
    Controller for conversation ingestion.
    
    Responsibilities:
    - Validate ingestion request
    - Map API model to IngestConversationRequest DTO
    - Delegate to IngestConversationUseCase
    - Return ingestion result
    """
    
    async def ingest_conversation(
        self,
        scenario_title: str,
        original_title: str,
        url: str,
        messages: List[dict],
        use_case: IngestConversationUseCase = None
    ):
        """
        Ingest a new conversation into the system.
        
        Args:
            scenario_title: Title of the scenario
            original_title: Original conversation title
            url: Source URL
            messages: List of message dictionaries
            use_case: Injected ingest use case
            
        Returns:
            IngestConversationResponse with conversation ID
            
        Raises:
            HTTPException: If ingestion fails
        """
        self.log_request(
            "ingest_conversation",
            scenario_title=scenario_title,
            message_count=len(messages)
        )
        
        try:
            # Convert message dicts to DTOs
            message_dtos = [
                MessageDTO(
                    text=msg["text"],
                    author_name=msg.get("author_name"),
                    author_type=msg.get("author_type", "user"),
                    timestamp=msg.get("timestamp")
                )
                for msg in messages
            ]
            
            # Create request DTO
            request = IngestConversationRequest(
                messages=message_dtos,
                scenario_title=scenario_title,
                original_title=original_title,
                url=url
            )
            
            # Delegate to use case
            response = await use_case.execute(request)
            
            # Check if ingestion was successful
            if not response.success:
                self.log_response(
                    "ingest_conversation",
                    success=False,
                    error=response.error_message
                )
                raise ValueError(response.error_message)
            
            # Log success metrics
            self.log_response(
                "ingest_conversation",
                success=True,
                conversation_id=response.conversation_id,
                chunks_created=response.chunks_created
            )
            
            return response
            
        except ValueError as e:
            raise self.handle_error(ValidationError(str(e)))
        except Exception as e:
            raise self.handle_error(e)
```

---

## Conversations Controller Example

### Full Implementation

```python
# app/adapters/inbound/api/controllers/conversations_controller.py
from typing import List
from app.application.dto import (
    GetConversationRequest,
    DeleteConversationRequest
)
from .base import BaseController

class ConversationsController(BaseController):
    """
    Controller for conversation management endpoints.
    
    Responsibilities:
    - List conversations with pagination
    - Get conversation by ID
    - Delete conversation by ID
    """
    
    async def list_conversations(
        self,
        skip: int = 0,
        limit: int = 50,
        use_case = None
    ):
        """
        List all conversations with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            use_case: Injected list use case
            
        Returns:
            List of conversation summaries
        """
        self.log_request("list_conversations", skip=skip, limit=limit)
        
        try:
            # Delegate to use case
            response = await use_case.execute(skip=skip, limit=limit)
            
            self.log_response(
                "list_conversations",
                success=True,
                count=len(response.conversations)
            )
            
            return response
            
        except Exception as e:
            raise self.handle_error(e)
    
    async def get_conversation(
        self,
        conversation_id: int,
        include_chunks: bool = True,
        use_case = None
    ):
        """
        Get a specific conversation by ID.
        
        Args:
            conversation_id: The conversation ID
            include_chunks: Whether to include chunks in response
            use_case: Injected get use case
            
        Returns:
            Conversation details
        """
        self.log_request("get_conversation", conversation_id=conversation_id)
        
        try:
            request = GetConversationRequest(
                conversation_id=str(conversation_id),
                include_chunks=include_chunks
            )
            
            response = await use_case.execute(request)
            
            if not response.success:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            self.log_response(
                "get_conversation",
                success=True,
                conversation_id=conversation_id,
                chunks=len(response.chunks)
            )
            
            return response
            
        except ValueError as e:
            raise self.handle_error(ValidationError(str(e)))
        except Exception as e:
            raise self.handle_error(e)
    
    async def delete_conversation(
        self,
        conversation_id: int,
        use_case = None
    ):
        """
        Delete a conversation and all its chunks.
        
        Args:
            conversation_id: The conversation ID to delete
            use_case: Injected delete use case
            
        Returns:
            Deletion confirmation
        """
        self.log_request("delete_conversation", conversation_id=conversation_id)
        
        try:
            request = DeleteConversationRequest(
                conversation_id=str(conversation_id)
            )
            
            response = await use_case.execute(request)
            
            if not response.success:
                raise ValueError(response.error_message)
            
            self.log_response(
                "delete_conversation",
                success=True,
                conversation_id=conversation_id,
                chunks_deleted=response.chunks_deleted
            )
            
            return response
            
        except ValueError as e:
            raise self.handle_error(ValidationError(str(e)))
        except Exception as e:
            raise self.handle_error(e)
```

---

## Chat Gateway Controller Example

### Full Implementation

```python
# app/adapters/inbound/api/controllers/chat_controller.py
from typing import List, Dict, Any
from app.application.dto import SearchConversationRequest
from app.application.rag_service import RAGService
from .base import BaseController

class ChatController(BaseController):
    """
    Controller for RAG-powered chat endpoints.
    
    Responsibilities:
    - Accept user questions
    - Retrieve relevant context
    - Generate augmented responses
    - Stream responses (WebSocket)
    """
    
    async def ask_question(
        self,
        content: str,
        conversation_history: List[Dict[str, str]],
        search_use_case = None,
        rag_service: RAGService = None
    ):
        """
        Answer a question using RAG (Retrieval-Augmented Generation).
        
        Args:
            content: User's question
            conversation_history: Previous messages
            search_use_case: Injected search use case
            rag_service: Injected RAG service
            
        Returns:
            ChatResponse with answer and context
        """
        self.log_request(
            "ask_question",
            question=content[:50],
            history_length=len(conversation_history)
        )
        
        try:
            # Step 1: Retrieve relevant context
            search_request = SearchConversationRequest(
                query=content,
                top_k=5
            )
            search_response = await search_use_case.execute(search_request)
            
            if not search_response.success:
                raise ValueError("Failed to retrieve context")
            
            # Step 2: Generate answer with RAG
            answer = await rag_service.generate_answer(
                question=content,
                context_chunks=search_response.results,
                conversation_history=conversation_history
            )
            
            # Step 3: Format response
            context_used = [
                {
                    "conversation_id": r.conversation_id,
                    "text": r.text,
                    "score": r.score,
                    "author": r.author_name
                }
                for r in search_response.results[:3]  # Top 3 only
            ]
            
            self.log_response(
                "ask_question",
                success=True,
                context_count=len(context_used),
                answer_length=len(answer)
            )
            
            return {
                "answer": answer,
                "context_used": context_used
            }
            
        except Exception as e:
            raise self.handle_error(e)
```

---

## Testing Patterns

### Unit Test Structure

```python
# tests/unit/adapters/inbound/api/controllers/test_base_controller.py
import pytest
from fastapi import HTTPException, status
from app.adapters.inbound.api.controllers.base import BaseController
from app.application.dto import ValidationError
from app.domain.repositories import RepositoryError, EmbeddingError

class TestController(BaseController):
    """Concrete controller for testing."""
    pass

def test_handle_validation_error():
    """Test mapping of ValidationError to 400 Bad Request."""
    controller = TestController()
    error = ValidationError("Invalid input")
    
    http_exc = controller.handle_error(error)
    
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == status.HTTP_400_BAD_REQUEST
    assert "VALIDATION_ERROR" in str(http_exc.detail)

def test_handle_repository_not_found():
    """Test mapping of RepositoryError (not found) to 404."""
    controller = TestController()
    error = RepositoryError("Conversation not found")
    
    http_exc = controller.handle_error(error)
    
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == status.HTTP_404_NOT_FOUND

def test_handle_embedding_error():
    """Test mapping of EmbeddingError to 503."""
    controller = TestController()
    error = EmbeddingError("Service unavailable")
    
    http_exc = controller.handle_error(error)
    
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
```

### Integration Test with TestClient

```python
# tests/integration/adapters/inbound/api/test_search_endpoint.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_search_endpoint_success(mock_search_use_case):
    """Test search endpoint with successful response."""
    response = client.get("/v1/search?q=test&top_k=5")
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "query" in data
    assert data["query"] == "test"

def test_search_endpoint_validation_error():
    """Test search endpoint with invalid parameters."""
    response = client.get("/v1/search?q=&top_k=5")
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data["detail"]

def test_search_endpoint_not_found():
    """Test search with no results."""
    response = client.get("/v1/search?q=nonexistent&top_k=5")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert len(data["results"]) == 0
```

---

## Common Pitfalls

### ❌ Anti-Pattern: Business Logic in Controller

```python
# DON'T DO THIS
class SearchController(BaseController):
    async def search(self, query: str, top_k: int):
        # ❌ Embedding generation in controller
        embedding = await generate_embedding(query)
        
        # ❌ Database query in controller
        results = db.query(Chunk).filter(...).all()
        
        # ❌ Scoring logic in controller
        scored_results = [
            (r, calculate_score(r, embedding))
            for r in results
        ]
        
        return scored_results
```

**Why it's wrong**:
- Violates single responsibility principle
- Makes controller hard to test
- Business logic duplicated across controllers
- Cannot reuse logic in MCP server

**✅ Correct Approach**: Delegate to Use Case

```python
class SearchController(BaseController):
    async def search(self, query: str, top_k: int, use_case):
        # ✅ Only request/response transformation
        request = SearchConversationRequest(query=query, top_k=top_k)
        response = await use_case.execute(request)
        return response
```

### ❌ Anti-Pattern: Direct Database Access

```python
# DON'T DO THIS
class IngestController(BaseController):
    async def ingest(self, data: dict, db: Session):
        # ❌ Direct database access in controller
        conv = Conversation(**data)
        db.add(conv)
        db.commit()
        return conv
```

**✅ Correct Approach**: Use Repository via Use Case

```python
class IngestController(BaseController):
    async def ingest(self, data: dict, use_case):
        # ✅ Delegate to use case (which uses repository)
        request = IngestConversationRequest(**data)
        response = await use_case.execute(request)
        return response
```

### ❌ Anti-Pattern: Leaking Domain Entities

```python
# DON'T DO THIS
@router.get("/conversations/{id}")
async def get_conversation(id: int, repo):
    # ❌ Returning domain entity directly
    conversation = await repo.get_by_id(id)
    return conversation  # Domain entity exposed!
```

**✅ Correct Approach**: Return DTO

```python
@router.get("/conversations/{id}", response_model=GetConversationResponse)
async def get_conversation(id: int, controller):
    # ✅ Controller returns DTO
    response = await controller.get_conversation(id)
    return response  # GetConversationResponse DTO
```

---

## Summary

### Key Principles

1. **Thin Controllers**: Zero business logic, only coordination
2. **Use Case Delegation**: All business logic in use cases
3. **DTO Transformation**: Map between API and application DTOs
4. **Consistent Error Handling**: BaseController provides standard mapping
5. **Testability**: Easy to mock use cases for unit testing
6. **Separation of Concerns**: HTTP concerns separated from business logic

### Checklist for New Controller

- [ ] Inherits from BaseController
- [ ] Uses dependency injection for use cases
- [ ] Contains zero business logic
- [ ] Maps API models to application DTOs
- [ ] Uses handle_error() for exception handling
- [ ] Logs requests and responses
- [ ] Returns application DTOs (not domain entities)
- [ ] Under 100 lines of code
- [ ] Has corresponding unit tests
- [ ] Has integration tests

---

**Document Status**: Complete  
**Last Updated**: November 11, 2025  
**Maintained By**: Architect Agent
