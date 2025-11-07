# SQLAlchemy Persistence Adapters

This directory contains SQLAlchemy implementations of the repository interfaces defined in the domain layer, following the hexagonal architecture pattern.

## Implemented Adapters

### SqlAlchemyConversationRepository
Implements `IConversationRepository` for conversation persistence operations.

**Features:**
- Save/update conversations with upsert behavior (using `merge()`)
- Retrieve conversations by ID with eager loading of chunks
- Pagination support for `get_all()`
- Delete operations with cascade to chunks
- Existence checks and counting

**Usage:**
```python
from sqlalchemy.orm import Session
from app.adapters.outbound.persistence import SqlAlchemyConversationRepository

# Assuming you have a SQLAlchemy session
repository = SqlAlchemyConversationRepository(session)

# Save a conversation
saved_conversation = await repository.save(conversation)

# Retrieve by ID
conversation = await repository.get_by_id(ConversationId(1))

# Get all with pagination
conversations = await repository.get_all(skip=0, limit=10)
```

### SqlAlchemyChunkRepository
Implements `IChunkRepository` for chunk persistence operations.

**Features:**
- Batch save operations for multiple chunks
- Retrieve chunks by conversation ID (ordered by order_index)
- Update embeddings for existing chunks
- Find chunks without embeddings

**Usage:**
```python
from app.adapters.outbound.persistence import SqlAlchemyChunkRepository

repository = SqlAlchemyChunkRepository(session)

# Batch save chunks
saved_chunks = await repository.save_chunks([chunk1, chunk2, chunk3])

# Get chunks for a conversation
chunks = await repository.get_by_conversation(conversation_id)

# Update embedding
success = await repository.update_embedding(chunk_id, embedding)
```

### SqlAlchemyVectorSearchRepository
Implements `IVectorSearchRepository` for vector similarity search using pgvector.

**Features:**
- L2 distance-based similarity search using pgvector's `<=>` operator
- Relevance score normalization (0.0 to 1.0)
- Threshold-based filtering
- Top-K result limiting

**Usage:**
```python
from app.adapters.outbound.persistence import SqlAlchemyVectorSearchRepository

repository = SqlAlchemyVectorSearchRepository(session)

# Perform similarity search
results = await repository.similarity_search(query_embedding, top_k=10)

# Search with threshold
results = await repository.similarity_search_with_threshold(
    query_embedding, 
    threshold=0.7, 
    top_k=10
)

# Process results
for chunk, score in results:
    print(f"Chunk {chunk.id.value}: relevance {score.value}")
```

### SqlAlchemyEmbeddingRepository
Implements `IEmbeddingRepository` for embedding storage and retrieval.

**Features:**
- Store embeddings for chunks
- Retrieve embeddings by chunk ID
- Check if chunks have embeddings
- Find chunks needing embeddings

**Usage:**
```python
from app.adapters.outbound.persistence import SqlAlchemyEmbeddingRepository

repository = SqlAlchemyEmbeddingRepository(session)

# Store embedding
await repository.store_embedding(chunk_id, embedding)

# Get embedding
embedding = await repository.get_embedding(chunk_id)

# Check if has embedding
has_embedding = await repository.has_embedding(chunk_id)

# Get chunks needing embeddings
chunk_ids = await repository.get_chunks_needing_embeddings()
```

## Key Features

### Type Conversion
All adapters handle conversion between:
- Domain entities (pure business objects) ↔ SQLAlchemy models
- Python lists ↔ numpy arrays (for embeddings)
- Domain value objects ↔ primitive types

### Error Handling
All adapters catch `SQLAlchemyError` and convert to `RepositoryError` to prevent infrastructure errors from leaking into the domain layer.

### Transaction Management
- All write operations use `session.commit()` and handle rollback on errors
- Proper exception handling ensures database consistency

### Logging
Comprehensive logging at appropriate levels:
- INFO: Successful operations with counts
- DEBUG: Individual operations and queries
- ERROR: Failures with context

## Integration with Container

To use these adapters with the dependency injection container, register them in your application setup:

```python
from app.infrastructure.container import Container
from app.adapters.outbound.persistence import (
    SqlAlchemyConversationRepository,
    SqlAlchemyChunkRepository,
    SqlAlchemyVectorSearchRepository,
    SqlAlchemyEmbeddingRepository
)
from app.domain.repositories import (
    IConversationRepository,
    IChunkRepository,
    IVectorSearchRepository,
    IEmbeddingRepository
)

def configure_persistence(container: Container, session_factory):
    """Configure persistence layer in the container."""
    
    # Register repositories as singletons with session factory
    container.register_singleton(
        IConversationRepository,
        factory=lambda: SqlAlchemyConversationRepository(session_factory())
    )
    
    container.register_singleton(
        IChunkRepository,
        factory=lambda: SqlAlchemyChunkRepository(session_factory())
    )
    
    container.register_singleton(
        IVectorSearchRepository,
        factory=lambda: SqlAlchemyVectorSearchRepository(session_factory())
    )
    
    container.register_singleton(
        IEmbeddingRepository,
        factory=lambda: SqlAlchemyEmbeddingRepository(session_factory())
    )
```

## Testing

Comprehensive unit tests are provided in `/tests/test_sqlalchemy_*.py`:

- `test_sqlalchemy_conversation_repository.py`: 14 tests covering all conversation operations
- `test_sqlalchemy_chunk_repository.py`: 12 tests covering chunk operations
- `test_sqlalchemy_embedding_repository.py`: 11 tests covering embedding operations
- `test_sqlalchemy_vector_search_repository.py`: Integration tests (require PostgreSQL with pgvector)

Run tests:
```bash
# Run all adapter tests
pytest tests/test_sqlalchemy_*.py -v

# Run specific adapter tests
pytest tests/test_sqlalchemy_conversation_repository.py -v
```

## Requirements

- SQLAlchemy 2.0+
- psycopg3 (psycopg) for PostgreSQL connectivity
- pgvector extension for vector operations (required for vector search)
- PostgreSQL 11+ with pgvector extension installed

## Architecture Notes

These adapters follow the hexagonal architecture (ports and adapters) pattern:
- **Zero infrastructure leakage**: Domain layer has no knowledge of SQLAlchemy
- **Clean boundaries**: All conversions happen in the adapter layer
- **Testability**: Adapters can be tested with in-memory SQLite (except vector search)
- **Flexibility**: Easy to swap implementations without changing domain logic

## Future Enhancements

Potential improvements for production use:
- Connection pooling configuration
- Retry logic for transient errors
- Query optimization with proper indexes
- Caching layer for frequently accessed data
- Bulk operations optimization
- Read replicas support
