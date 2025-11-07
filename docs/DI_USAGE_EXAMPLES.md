# Dependency Injection Usage Examples

This document provides practical examples of using the dependency injection container in the MCP Demo application.

## Basic Container Usage

### Resolving Services

```python
from app.infrastructure.container import get_container
from app.domain.repositories import IEmbeddingService, IConversationRepository

# Get the global container
container = get_container()

# Resolve services
embedding_service = container.resolve(IEmbeddingService)
conversation_repo = container.resolve(IConversationRepository)
```

### Checking Registration

```python
from app.infrastructure.container import get_container
from app.domain.repositories import IEmbeddingService

container = get_container()

if container.is_registered(IEmbeddingService):
    service = container.resolve(IEmbeddingService)
else:
    print("Service not registered")
```

## Using in FastAPI Routes

### Method 1: Dependency Provider Function

```python
from fastapi import Depends, APIRouter
from app.infrastructure.container import get_container
from app.application import IngestConversationUseCase, IngestConversationRequest

router = APIRouter()

def get_ingest_use_case() -> IngestConversationUseCase:
    """Dependency provider for ingest use case."""
    container = get_container()
    return container.resolve(IngestConversationUseCase)

@router.post("/api/v2/ingest")
async def ingest_conversation_v2(
    request: IngestConversationRequest,
    use_case: IngestConversationUseCase = Depends(get_ingest_use_case)
):
    """
    Ingest a conversation using the new hexagonal architecture.
    
    This endpoint demonstrates the new architecture where:
    - Use case orchestrates the workflow
    - Repositories handle persistence
    - Embedding service generates vectors
    - All dependencies are injected automatically
    """
    result = await use_case.execute(request)
    return result
```

### Method 2: Direct Resolution

```python
from fastapi import APIRouter
from app.infrastructure.container import get_container
from app.application import SearchConversationsUseCase

router = APIRouter()

@router.get("/api/v2/search")
async def search_conversations_v2(query: str, top_k: int = 5):
    """
    Search conversations using the new architecture.
    
    Resolves the use case directly in the route handler.
    """
    container = get_container()
    use_case = container.resolve(SearchConversationsUseCase)
    
    # Create request DTO
    from app.application import SearchConversationRequest
    request = SearchConversationRequest(query=query, top_k=top_k)
    
    # Execute use case
    result = await use_case.execute(request)
    return result
```

## Working with Repositories

### Direct Repository Usage

```python
from app.infrastructure.container import get_container
from app.domain.repositories import IConversationRepository
from app.domain.value_objects import ConversationId

async def get_conversation_by_id(conversation_id: int):
    """Get a conversation using repository pattern."""
    container = get_container()
    repo = container.resolve(IConversationRepository)
    
    # Use repository
    conversation = await repo.get_by_id(ConversationId(conversation_id))
    
    if conversation:
        return conversation
    else:
        raise ValueError(f"Conversation {conversation_id} not found")
```

### Repository with Session Management

```python
from sqlalchemy.orm import Session
from app.infrastructure.container import get_container
from app.domain.repositories import IConversationRepository

async def save_conversation_example(conversation_data):
    """
    Example showing repository usage with automatic session management.
    
    The container provides a new session for each repository resolution.
    """
    container = get_container()
    
    # Get repository (gets a new session automatically)
    repo = container.resolve(IConversationRepository)
    
    # Create conversation entity
    from app.domain.entities import Conversation
    from app.domain.value_objects import ConversationMetadata
    
    conversation = Conversation(
        metadata=ConversationMetadata(
            title=conversation_data["title"],
            source=conversation_data["source"]
        ),
        chunks=[]
    )
    
    # Save through repository
    saved_conversation = await repo.save(conversation)
    
    return saved_conversation
```

## Embedding Service Examples

### Generate Single Embedding

```python
from app.infrastructure.container import get_container
from app.domain.repositories import IEmbeddingService

async def generate_embedding_example(text: str):
    """Generate embedding for a single text."""
    container = get_container()
    embedding_service = container.resolve(IEmbeddingService)
    
    # Generate embedding
    embedding = await embedding_service.generate_embedding(text)
    
    print(f"Generated embedding with {len(embedding.vector)} dimensions")
    return embedding
```

### Batch Embedding Generation

```python
from app.infrastructure.container import get_container
from app.domain.repositories import IEmbeddingService

async def generate_embeddings_batch_example(texts: list[str]):
    """Generate embeddings for multiple texts."""
    container = get_container()
    embedding_service = container.resolve(IEmbeddingService)
    
    # Generate embeddings in batch
    embeddings = await embedding_service.generate_embeddings_batch(texts)
    
    print(f"Generated {len(embeddings)} embeddings")
    return embeddings
```

## Use Case Examples

### Complete Ingestion Workflow

```python
from app.infrastructure.container import get_container
from app.application import IngestConversationUseCase, IngestConversationRequest
from app.application.dto import MessageDTO

async def ingest_conversation_example():
    """
    Complete example of ingesting a conversation using the use case.
    
    This demonstrates the full workflow:
    1. Resolve use case from container
    2. Create request DTO
    3. Execute use case
    4. Handle response
    """
    container = get_container()
    use_case = container.resolve(IngestConversationUseCase)
    
    # Create request
    request = IngestConversationRequest(
        title="Team Standup",
        source="slack",
        messages=[
            MessageDTO(
                speaker="Alice",
                content="Good morning team! What's everyone working on today?",
                timestamp="2024-01-15T09:00:00Z"
            ),
            MessageDTO(
                speaker="Bob",
                content="I'm finishing up the authentication feature.",
                timestamp="2024-01-15T09:01:00Z"
            ),
            MessageDTO(
                speaker="Charlie",
                content="Working on database migrations.",
                timestamp="2024-01-15T09:02:00Z"
            )
        ]
    )
    
    # Execute use case
    result = await use_case.execute(request)
    
    # Handle result
    if result.success:
        print(f"✅ Conversation ingested successfully!")
        print(f"   ID: {result.conversation_id}")
        print(f"   Chunks created: {result.chunks_created}")
        print(f"   Embeddings generated: {result.embeddings_generated}")
    else:
        print(f"❌ Ingestion failed: {result.error}")
    
    return result
```

### Search Workflow

```python
from app.infrastructure.container import get_container
from app.application import SearchConversationsUseCase, SearchConversationRequest

async def search_conversations_example(query: str):
    """
    Example of searching conversations using the use case.
    """
    container = get_container()
    use_case = container.resolve(SearchConversationsUseCase)
    
    # Create request
    request = SearchConversationRequest(
        query=query,
        top_k=10,
        min_relevance=0.7
    )
    
    # Execute search
    result = await use_case.execute(request)
    
    # Process results
    print(f"Found {len(result.results)} relevant chunks")
    for i, search_result in enumerate(result.results, 1):
        print(f"\n{i}. Relevance: {search_result.relevance_score:.2f}")
        print(f"   Speaker: {search_result.speaker}")
        print(f"   Content: {search_result.content[:100]}...")
    
    return result
```

## Testing with DI

### Mock Dependencies for Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.infrastructure.container import Container
from app.domain.repositories import IEmbeddingService, IConversationRepository
from app.application import IngestConversationUseCase

@pytest.fixture
def test_container():
    """Create a test container with mock dependencies."""
    container = Container()
    
    # Create mocks
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    mock_conversation_repo = AsyncMock(spec=IConversationRepository)
    mock_chunk_repo = AsyncMock()
    
    # Configure mock behaviors
    mock_embedding_service.generate_embedding.return_value = Mock(
        vector=[0.1] * 384
    )
    
    # Register mocks
    container.register_instance(IEmbeddingService, mock_embedding_service)
    container.register_instance(IConversationRepository, mock_conversation_repo)
    
    return container

async def test_ingest_with_mocks(test_container):
    """Test ingestion with mocked dependencies."""
    # Resolve use case with mocked dependencies
    use_case = test_container.resolve(IngestConversationUseCase)
    
    # Execute test
    # ... test logic ...
```

### Integration Test with Real Dependencies

```python
import pytest
from app.infrastructure.container import initialize_container
from app.application import IngestConversationUseCase

@pytest.mark.integration
async def test_full_ingestion_workflow():
    """Integration test with real implementations."""
    # Initialize container with real adapters
    container = initialize_container(include_adapters=True)
    
    # Resolve use case
    use_case = container.resolve(IngestConversationUseCase)
    
    # Execute real workflow
    # ... test logic ...
```

## Configuration-Based Selection

### Switching Embedding Providers

The embedding service provider is selected based on configuration:

```python
# Environment: EMBEDDING_PROVIDER=local
from app.infrastructure.container import get_container
from app.domain.repositories import IEmbeddingService
from app.adapters.outbound.embeddings import LocalEmbeddingService

container = get_container()
service = container.resolve(IEmbeddingService)

# service is instance of LocalEmbeddingService
assert isinstance(service, LocalEmbeddingService)
```

```python
# Environment: EMBEDDING_PROVIDER=openai
from app.infrastructure.container import get_container
from app.domain.repositories import IEmbeddingService
from app.adapters.outbound.embeddings import OpenAIEmbeddingService

container = get_container()
service = container.resolve(IEmbeddingService)

# service is instance of OpenAIEmbeddingService
assert isinstance(service, OpenAIEmbeddingService)
```

## Advanced Patterns

### Custom Factory Function

```python
from app.infrastructure.container import get_container

def create_custom_service():
    """Custom factory for complex service creation."""
    container = get_container()
    
    # Resolve dependencies
    repo = container.resolve(IConversationRepository)
    embedding = container.resolve(IEmbeddingService)
    
    # Create service with custom logic
    return MyCustomService(
        repository=repo,
        embedding=embedding,
        custom_config={"option": "value"}
    )

# Register custom factory
container = get_container()
container.register_singleton(MyCustomService, factory=create_custom_service)
```

### Conditional Service Registration

```python
from app.infrastructure.container import get_container
from app.infrastructure.config import get_settings

def configure_conditional_services():
    """Register services based on configuration."""
    container = get_container()
    settings = get_settings()
    
    # Register different implementations based on environment
    if settings.is_production:
        # Use production-grade implementation
        container.register_singleton(ICacheService, factory=create_redis_cache)
    else:
        # Use simple in-memory cache for development
        container.register_singleton(ICacheService, factory=create_memory_cache)
```

## Best Practices

1. **Use Dependency Providers**: Create dedicated functions for FastAPI dependencies
2. **Resolve at Runtime**: Don't store resolved services globally; resolve when needed
3. **Mock for Testing**: Use test containers with mocked dependencies
4. **Check Registration**: Use `is_registered()` to avoid errors
5. **Follow Lifetimes**: Understand singleton vs transient lifetimes
6. **Clean Up Sessions**: Ensure database sessions are properly closed
7. **Use Protocols**: Depend on interfaces (protocols), not concrete implementations

## Common Pitfalls

### ❌ Don't Store Resolved Services Globally

```python
# BAD - Don't do this
embedding_service = get_container().resolve(IEmbeddingService)

@app.get("/endpoint")
async def handler():
    # Using global service
    await embedding_service.generate_embedding("text")
```

### ✅ Do Resolve in Route or Use Dependency

```python
# GOOD - Resolve in handler
@app.get("/endpoint")
async def handler():
    container = get_container()
    service = container.resolve(IEmbeddingService)
    await service.generate_embedding("text")

# BETTER - Use dependency injection
def get_embedding_service():
    return get_container().resolve(IEmbeddingService)

@app.get("/endpoint")
async def handler(service: IEmbeddingService = Depends(get_embedding_service)):
    await service.generate_embedding("text")
```

### ❌ Don't Share Sessions Across Requests

```python
# BAD - Session might be stale
session = get_container().resolve(Session)

@app.get("/endpoint1")
async def handler1():
    repo = IConversationRepository(session)  # Reusing session
```

### ✅ Do Get Fresh Sessions

```python
# GOOD - New session per request
@app.get("/endpoint1")
async def handler1():
    container = get_container()
    repo = container.resolve(IConversationRepository)  # Fresh session
```

## Summary

The dependency injection container provides:
- **Automatic dependency resolution**: No manual wiring needed
- **Configuration-based selection**: Switch implementations via env vars
- **Testability**: Easy to mock and test
- **Flexibility**: Add new implementations without changing code
- **Clear architecture**: Separation of concerns and loose coupling

For more information, see the [Migration Guide](MIGRATION_GUIDE.md).
