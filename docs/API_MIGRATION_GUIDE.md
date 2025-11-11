# API Migration Guide

## Overview

The MCP Conversational Data Server has been refactored to use hexagonal architecture. New API endpoints have been introduced that follow clean architecture principles with proper separation of concerns.

## Architecture Changes

### Old Architecture (Legacy)
- Direct database access in routes
- Mixed concerns (business logic in API layer)
- Tight coupling between layers

### New Architecture (Hexagonal)
- Use case layer orchestrates business logic
- Domain layer contains pure business rules
- Adapters handle external concerns (API, database, embeddings)
- Dependency injection for loose coupling

## Migration Path

### Enable New Architecture

Set the environment variable to use the new architecture:

```bash
export USE_NEW_ARCHITECTURE=true
```

The application will then expose both legacy and new endpoints during the migration period.

## Endpoint Changes

### Conversation Ingestion

#### Legacy Endpoint (DEPRECATED)
```http
POST /ingest
```

**Request:**
```json
{
  "scenario_title": "Test Scenario",
  "messages": [
    {
      "author_name": "User1",
      "author_type": "human",
      "content": "Hello, this is a test message."
    }
  ]
}
```

**Response:**
```json
{
  "conversation_id": 1,
  "chunks": 2
}
```

#### New Endpoint (RECOMMENDED)
```http
POST /conversations/ingest
```

**Request:**
```json
{
  "messages": [
    {
      "text": "Hello, this is a test message.",
      "author_name": "User1",
      "author_type": "user"
    }
  ],
  "scenario_title": "Test Scenario",
  "original_title": "Original Title",
  "url": "https://example.com/conversation/123"
}
```

**Response:**
```json
{
  "conversation_id": "1",
  "chunks_created": 2,
  "success": true,
  "error_message": null,
  "metadata": {
    "conversation_id": "1",
    "scenario_title": "Test Scenario",
    "original_title": "Original Title",
    "url": "https://example.com/conversation/123",
    "created_at": "2025-11-11T04:00:00Z",
    "total_chunks": 2
  }
}
```

**Key Changes:**
- Message field renamed from `content` to `text`
- Response includes `success` flag and detailed metadata
- Better error handling with `error_message` field
- Status code is now 201 (Created) instead of 200

---

### List Conversations

#### Legacy Endpoint (DEPRECATED)
```http
GET /conversations?skip=0&limit=50
```

#### New Endpoint (RECOMMENDED)
```http
GET /conversations?skip=0&limit=50
```

**Note:** Same endpoint path, but the new version is handled by the hexagonal architecture router with better error handling and consistency.

**Response Format (New):**
```json
[
  {
    "id": 1,
    "scenario_title": "Test Scenario",
    "original_title": "Original Title",
    "url": "https://example.com/conversation/123",
    "created_at": "2025-11-11T04:00:00Z",
    "chunk_count": 5
  }
]
```

---

### Get Conversation

#### Legacy Endpoint (DEPRECATED)
```http
GET /conversations/{id}
```

#### New Endpoint (RECOMMENDED)
```http
GET /conversations/{id}
```

**Response Format (New):**
```json
{
  "id": 1,
  "scenario_title": "Test Scenario",
  "original_title": "Original Title",
  "url": "https://example.com/conversation/123",
  "created_at": "2025-11-11T04:00:00Z",
  "chunks": [
    {
      "id": 1,
      "order_index": 0,
      "text": "Message content",
      "author_name": "User",
      "author_type": "user",
      "timestamp": "2025-11-11T04:00:00Z"
    }
  ]
}
```

---

### Delete Conversation

#### Legacy Endpoint (DEPRECATED)
```http
DELETE /conversations/{id}
```

#### New Endpoint (RECOMMENDED)
```http
DELETE /conversations/{id}
```

**Response Format (New):**
```json
{
  "message": "Conversation 1 deleted successfully",
  "conversation_id": 1,
  "chunks_deleted": 5
}
```

---

### Search Conversations

#### Legacy Endpoint (DEPRECATED)
```http
GET /search?q=query&top_k=5
```

**Response:**
```json
{
  "query": "query",
  "results": [...],
  "total_results": 10
}
```

#### New Endpoints (RECOMMENDED)

**Option 1: POST with filters**
```http
POST /search
```

**Request:**
```json
{
  "query": "Python programming",
  "top_k": 10,
  "filters": {
    "author_type": "user",
    "min_score": 0.7,
    "author_name": "John"
  },
  "include_metadata": true
}
```

**Option 2: GET with query parameters**
```http
GET /search?q=Python programming&top_k=10&author_type=user&min_score=0.7
```

**Response Format (Both):**
```json
{
  "results": [
    {
      "chunk_id": "123",
      "conversation_id": "456",
      "text": "Python programming is great...",
      "score": 0.95,
      "author_name": "User",
      "author_type": "user",
      "timestamp": "2025-11-11T04:00:00Z",
      "order_index": 0,
      "metadata": {}
    }
  ],
  "query": "Python programming",
  "total_results": 1,
  "execution_time_ms": 45.2,
  "success": true,
  "error_message": null
}
```

**Key Changes:**
- POST endpoint supports more advanced filtering
- Response includes execution time and success flag
- Better error messages

---

### RAG (NEW Feature)

The new architecture introduces RAG (Retrieval-Augmented Generation) endpoints:

#### Ask a Question
```http
POST /rag/ask
```

**Request:**
```json
{
  "query": "How do I install Python packages?",
  "top_k": 5,
  "conversation_id": "optional-conversation-id"
}
```

**Response:**
```json
{
  "answer": "To install Python packages, you can use pip...",
  "sources": [
    {
      "chunk_id": "123",
      "conversation_id": "456",
      "text": "Source text...",
      "score": 0.95,
      "author_name": "User"
    }
  ],
  "confidence": 0.85,
  "metadata": {
    "query": "How do I install Python packages?",
    "latency_ms": 1250.5,
    "provider": "openai",
    "model": "gpt-3.5-turbo"
  }
}
```

#### Ask with Streaming Response
```http
POST /rag/ask-stream
```

Returns a Server-Sent Events (SSE) stream with real-time answer generation.

**Request:**
```json
{
  "query": "Explain Python decorators",
  "top_k": 5
}
```

**Response:** (SSE stream)
```
data: {"chunk": "Python "}
data: {"chunk": "decorators "}
data: {"chunk": "are..."}
data: [DONE]
```

#### RAG Health Check
```http
GET /rag/health
```

**Response:**
```json
{
  "status": "healthy",
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "embedding_service": "configured",
  "message": "RAG service is operational"
}
```

---

## Error Handling

### Legacy Errors
Legacy endpoints return inconsistent error formats.

### New Error Format
All new endpoints return standardized error responses:

```json
{
  "error": {
    "type": "ValidationError",
    "message": "Invalid input data",
    "details": {
      "path": "/conversations/ingest"
    }
  }
}
```

**Error Types:**
- `ValidationError` (400) - Invalid input data
- `NotFoundError` (404) - Resource not found
- `RepositoryError` (500) - Database error
- `EmbeddingError` (503) - Embedding service unavailable

---

## Migration Timeline

### Phase 1: Dual Support (Current)
- Both legacy and new endpoints are available
- Legacy endpoints show deprecation warnings in logs
- Recommended to test new endpoints

### Phase 2: Deprecation Notice (Future)
- Legacy endpoints will return deprecation headers
- Documentation will strongly recommend new endpoints

### Phase 3: Legacy Removal (Future)
- Legacy endpoints will be removed
- Only new hexagonal architecture endpoints available

---

## Testing Your Migration

### 1. Test Basic Ingestion
```bash
# New endpoint
curl -X POST http://localhost:8000/conversations/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"text": "Test message", "author_name": "User"}
    ],
    "scenario_title": "Test"
  }'
```

### 2. Test Search
```bash
# New GET endpoint
curl "http://localhost:8000/search?q=test&top_k=5"

# New POST endpoint
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test",
    "top_k": 5
  }'
```

### 3. Test RAG
```bash
# Ask a question
curl -X POST http://localhost:8000/rag/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does this work?",
    "top_k": 5
  }'

# Check RAG health
curl http://localhost:8000/rag/health
```

---

## Benefits of New Architecture

1. **Better Error Handling**: Consistent error responses across all endpoints
2. **Improved Validation**: Input validation at multiple layers
3. **Testability**: Use cases can be tested independently
4. **Maintainability**: Clean separation of concerns
5. **Extensibility**: Easy to add new features without breaking existing code
6. **Performance**: Better resource management with dependency injection
7. **New Features**: RAG capabilities for question answering

---

## Support

If you encounter issues during migration:

1. Check the logs for deprecation warnings
2. Review the API documentation at `/docs`
3. Compare your requests with the examples in this guide
4. Test with the new endpoints in a development environment first

---

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Both provide detailed information about:
- Request/response schemas
- Required/optional fields
- Example requests
- Error responses
