# MCP Server Hexagonal Architecture

## Overview

The MCP server has been refactored to use hexagonal architecture principles, integrating with the application's dependency injection container and use cases instead of making direct REST API calls.

## Architecture

### Previous Design (REST API Proxy)
```
MCP Tools → httpx → FastAPI Endpoints → CRUD Operations → Database
```

### Current Design (Hexagonal Architecture)
```
MCP Tools → DI Container → Use Cases → Domain Services → Repositories → Database
```

## Key Components

### 1. MCP Server (`app/mcp_server.py`)
- **Responsibility**: MCP protocol implementation and tool definitions
- **Dependencies**: Uses DI container to resolve use cases
- **Key Changes**:
  - Removed httpx dependency
  - Added DI container initialization at module level
  - All tools now resolve and use use cases from the container
  - Proper error handling with domain exception catching

### 2. Use Cases (Application Layer)
- **SearchConversationsUseCase**: Semantic search over conversation chunks
- **IngestConversationUseCase**: Process and store new conversations
- **GetConversationUseCase**: Retrieve conversation by ID with chunks
- **ListConversationsUseCase**: List conversations with pagination
- **DeleteConversationUseCase**: Delete conversation and associated chunks

### 3. Dependency Injection Container
- **Location**: `app/infrastructure/container.py`
- **Responsibilities**: 
  - Register all use cases as transient
  - Register repositories and services
  - Provide automatic constructor injection
- **Initialization**: Container is initialized once at module load time

## MCP Tools

### search_conversations
```python
async def search_conversations(context: Context, q: str, top_k: int = 5) -> dict
```
- Uses `SearchConversationsUseCase`
- Converts query to embedding and searches vector database
- Returns ranked results with relevance scores

### ingest_conversation
```python
async def ingest_conversation(conversation_data: schemas.ConversationIngest, context: Context) -> dict
```
- Uses `IngestConversationUseCase`
- Chunks messages, generates embeddings, stores in database
- Returns conversation ID and chunk count

### get_conversation
```python
async def get_conversation(conversation_id: int, context: Context) -> dict
```
- Uses `GetConversationUseCase`
- Retrieves conversation with all chunks
- Returns 404 if not found

### get_conversations
```python
async def get_conversations(context: Context, skip: int = 0, limit: int = 100) -> List[dict]
```
- Uses `ListConversationsUseCase`
- Lists conversations with pagination
- Does not include chunks (metadata only)

### delete_conversation
```python
async def delete_conversation(conversation_id: int, context: Context) -> dict
```
- Uses `DeleteConversationUseCase`
- Deletes conversation and all associated chunks
- Returns 404 if not found

### health_check
```python
async def health_check(context: Context) -> dict
```
- Verifies DI container and use case resolution
- Returns health status

## Data Flow Example: Search

1. **MCP Tool receives request**
   ```python
   search_conversations(context, q="hello world", top_k=5)
   ```

2. **Resolve use case from container**
   ```python
   search_use_case = container.resolve(SearchConversationsUseCase)
   ```

3. **Create DTO request**
   ```python
   request = SearchConversationRequest(query="hello world", top_k=5)
   ```

4. **Execute use case**
   ```python
   response = await search_use_case.execute(request)
   ```

5. **Use case orchestrates**:
   - Validates query
   - Generates embedding via `IEmbeddingService`
   - Searches via `IVectorSearchRepository`
   - Applies filters and ranking
   - Returns DTOs

6. **MCP tool converts response**
   ```python
   return {
       "query": response.query,
       "total_results": response.total_results,
       "results": [...]
   }
   ```

## Error Handling

### Domain Exceptions
- `ValidationError`: Invalid input data
- `RepositoryError`: Database operation failures
- `EmbeddingError`: Embedding generation failures

### MCP Error Handling
- All domain exceptions are caught in use cases
- Use cases return DTOs with `success=False` and `error_message`
- MCP tools log errors using context (info/warning/error)
- MCP tools raise exceptions for MCP client to handle

### Example
```python
try:
    response = await use_case.execute(request)
    if not response.success:
        await context.error(f"❌ [MCP] Operation failed: {response.error_message}")
        raise Exception(response.error_message)
    # ... success path
except Exception as e:
    await context.error(f"❌ [MCP] Unexpected error: {str(e)}")
    raise Exception(f"Operation failed: {str(e)}")
```

## Configuration

### Environment Variables
- `LOG_LEVEL`: Logging level for MCP server (default: "WARN")
- `DATABASE_URL`: PostgreSQL connection string (inherited from main app)
- `EMBEDDING_PROVIDER`: Embedding service to use (local, openai, etc.)

### DI Container Setup
The container is initialized automatically when the module is imported:
```python
logger.info("Initializing DI container for MCP server...")
initialize_container(include_adapters=True)
container = get_container()
```

## Benefits of Hexagonal Architecture

1. **Separation of Concerns**: MCP server is a thin adapter layer
2. **Testability**: Use cases can be tested independently
3. **Reusability**: Same use cases used by FastAPI and MCP
4. **Maintainability**: Business logic centralized in domain/application layers
5. **Flexibility**: Easy to swap implementations via DI
6. **No Duplication**: Avoid duplicate REST API and direct DB access logic

## Running the MCP Server

### Standalone Mode
```bash
python app/mcp_server.py
```

### With Claude Desktop
Configure in Claude Desktop's MCP settings to point to the server script.

## Testing

The MCP tools are tested indirectly through:
1. **Use Case Tests**: Unit tests for each use case with mocked dependencies
2. **Integration Tests**: End-to-end tests with real database (e2e tests)
3. **DI Container Tests**: Verify proper registration and resolution

## Future Enhancements

1. **RAG Tool**: Add `rag_ask` tool using `RAGService` from Phase 4
2. **Streaming**: Support streaming responses for long operations
3. **Batch Operations**: Support batch ingest/delete operations
4. **Filters**: Enhanced search filters (date range, author, etc.)
5. **Metrics**: Track tool usage and performance metrics

## Troubleshooting

### Container Resolution Fails
- Ensure all dependencies are registered in `ApplicationServiceProvider`
- Check that `initialize_container()` is called before use

### Use Case Execution Fails
- Check logs for domain exception details
- Verify database connectivity
- Confirm embedding service is configured correctly

### MCP Client Connection Issues
- Verify MCP server is running
- Check firewall/network settings
- Review MCP client configuration
