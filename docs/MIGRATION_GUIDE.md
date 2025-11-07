# Migration Guide: Hexagonal Architecture with Dependency Injection

This guide explains how to migrate from the legacy implementation to the new hexagonal architecture with dependency injection.

## Overview

The application now supports both legacy and new hexagonal architectures side-by-side, allowing for gradual migration. The new architecture provides:

- **Separation of Concerns**: Clear boundaries between domain, application, and infrastructure layers
- **Dependency Injection**: Automatic wiring of dependencies through a DI container
- **Testability**: Easy to mock and test individual components
- **Flexibility**: Switch implementations (e.g., embedding providers) via configuration

## Feature Flag

The migration is controlled by the `USE_NEW_ARCHITECTURE` environment variable:

```bash
# Enable new architecture (default)
USE_NEW_ARCHITECTURE=true

# Use legacy implementation
USE_NEW_ARCHITECTURE=false
```

## Configuration

### Required Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dbname

# Embedding service configuration
EMBEDDING_PROVIDER=local  # Options: local, openai, fastembed
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# OpenAI API key (only if using openai provider)
OPENAI_API_KEY=sk-...
```

### Embedding Provider Options

1. **local** (default): Uses sentence-transformers library
   - No API key required
   - Runs locally
   - Models: `all-MiniLM-L6-v2`, `all-mpnet-base-v2`, etc.

2. **openai**: Uses OpenAI's embedding API
   - Requires `OPENAI_API_KEY`
   - Models: `text-embedding-ada-002`, `text-embedding-3-small`, etc.
   - Costs apply per API call

3. **fastembed**: Uses FastEmbed library
   - No API key required
   - Fast inference
   - Models: `BAAI/bge-small-en-v1.5`, etc.

## Architecture Components

### Dependency Injection Container

The DI container (`app/infrastructure/container.py`) manages service lifetimes and dependencies:

- **Singleton**: One instance for the entire application (e.g., embedding service)
- **Transient**: New instance per resolution (e.g., repositories, use cases)
- **Scoped**: Per-request lifetime (database sessions)

### Service Providers

Service providers configure the DI container:

1. **CoreServiceProvider**: Domain services (chunking, validation)
2. **ApplicationServiceProvider**: Use cases (ingest, search)
3. **EmbeddingServiceProvider**: Embedding service based on config
4. **AdapterServiceProvider**: Repository implementations and database sessions

### Application Startup

The container is initialized during application startup in `app/main.py`:

```python
from app.infrastructure.container import initialize_container

# Initialize DI container at startup
initialize_container(include_adapters=True)
```

## Using the New Architecture

### In Route Handlers

```python
from fastapi import Depends
from app.infrastructure.container import get_container
from app.application import IngestConversationUseCase

def get_ingest_use_case():
    """Dependency provider for ingest use case."""
    container = get_container()
    return container.resolve(IngestConversationUseCase)

@app.post("/api/ingest")
async def ingest_conversation(
    request: IngestConversationRequest,
    use_case: IngestConversationUseCase = Depends(get_ingest_use_case)
):
    """Ingest a conversation using the new architecture."""
    result = await use_case.execute(request)
    return result
```

### Resolving Services Manually

```python
from app.infrastructure.container import get_container
from app.domain.repositories import IEmbeddingService

# Get container
container = get_container()

# Resolve service
embedding_service = container.resolve(IEmbeddingService)

# Use service
embedding = await embedding_service.generate_embedding("Hello world")
```

## Migration Steps

### Phase 1: Validate Setup (Current Phase)

✅ **Completed:**
- DI container configured with all adapters
- Feature flag system in place
- Health check validates adapter registration
- Test suite validates container configuration

### Phase 2: Create New Routes (Optional)

Create parallel routes that use the new architecture:

```python
# New route using DI
@app.post("/api/v2/ingest")
async def ingest_v2(
    request: IngestConversationRequest,
    use_case: IngestConversationUseCase = Depends(get_ingest_use_case)
):
    return await use_case.execute(request)

# Keep legacy route
@app.post("/ingest")
async def ingest_legacy(data: dict, db: Session = Depends(get_db)):
    return crud.create_conversation(db, data)
```

### Phase 3: Update Existing Routes

Gradually update existing routes to use DI-resolved services:

1. Add dependency provider functions
2. Update route handlers to use use cases
3. Add feature flag checks for backward compatibility
4. Test thoroughly

### Phase 4: Remove Legacy Code

Once all routes are migrated and tested:

1. Remove `USE_NEW_ARCHITECTURE` feature flag
2. Delete legacy CRUD functions
3. Clean up unused imports
4. Update documentation

## Testing

### Unit Tests

Test individual components in isolation:

```python
from app.infrastructure.container import Container
from app.domain.repositories import IConversationRepository

def test_repository():
    # Create test container
    container = Container()
    
    # Register mock repository
    mock_repo = MockConversationRepository()
    container.register_instance(IConversationRepository, mock_repo)
    
    # Test with mock
    repo = container.resolve(IConversationRepository)
    assert repo is mock_repo
```

### Integration Tests

Test with actual implementations:

```python
from app.infrastructure.container import initialize_container

def test_full_workflow():
    # Initialize with real adapters
    container = initialize_container(include_adapters=True)
    
    # Resolve use case
    use_case = container.resolve(IngestConversationUseCase)
    
    # Execute workflow
    result = await use_case.execute(request)
    assert result.success
```

### Health Check

Verify the container is properly configured:

```bash
curl http://localhost:8000/health
```

Response when using new architecture:

```json
{
  "status": "healthy",
  "architecture": "hexagonal",
  "di_container": "configured",
  "adapters": {
    "conversation_repository": true,
    "chunk_repository": true,
    "embedding_service": true,
    "vector_search_repository": true
  }
}
```

## Troubleshooting

### Container Not Initialized

**Symptom**: `KeyError: Service not registered`

**Solution**: Ensure `initialize_container()` is called at startup:

```python
# In app/main.py lifespan function
initialize_container(include_adapters=True)
```

### Wrong Embedding Provider

**Symptom**: Unexpected embedding service type

**Solution**: Check environment variables:

```bash
echo $EMBEDDING_PROVIDER
echo $EMBEDDING_MODEL
```

Update `.env` file if needed.

### Session Management Issues

**Symptom**: Database connection errors or stale sessions

**Solution**: Repositories get new sessions from the container. Ensure proper cleanup:

```python
# Sessions are transient - new per resolution
session = container.resolve(Session)
try:
    # Use session
    pass
finally:
    session.close()
```

### Tests Interfering with Each Other

**Symptom**: Tests fail when run together but pass individually

**Solution**: Reset container state between tests:

```python
import app.infrastructure.container as container_module

def setup_test():
    container_module._configured = False
    container_module._container = Container()
```

## Benefits of New Architecture

1. **Loose Coupling**: Components depend on interfaces, not implementations
2. **Testability**: Easy to inject mocks and test in isolation
3. **Flexibility**: Switch implementations via configuration
4. **Maintainability**: Clear separation of concerns
5. **Scalability**: Add new features without modifying existing code

## Next Steps

1. ✅ Validate container configuration
2. ✅ Run test suite
3. ✅ Check health endpoint
4. 🔄 Update existing routes to use DI (optional)
5. 🔄 Add more adapters as needed
6. 🔄 Eventually remove legacy implementation

## Support

For issues or questions:
- Check test suite: `pytest tests/test_di_container.py -v`
- Review health endpoint: `/health`
- Check logs for container initialization messages
- Refer to architecture documentation in `docs/`

## References

- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Dependency Injection Patterns](https://en.wikipedia.org/wiki/Dependency_injection)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
