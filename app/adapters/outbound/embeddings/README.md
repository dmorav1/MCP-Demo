# Embedding Service Adapters

This directory contains outbound adapters that implement the `IEmbeddingService` protocol from the domain layer.

## Architecture

These adapters follow the **Hexagonal Architecture (Ports and Adapters)** pattern:
- **Port (Interface):** `IEmbeddingService` protocol in `app/domain/repositories.py`
- **Adapters (Implementations):** Various embedding providers in this directory

## Available Adapters

### 1. LocalEmbeddingService
**File:** `local_embedding_service.py`

Uses sentence-transformers library with local models.

**Key Features:**
- Lazy model loading
- Device selection (CPU/GPU)
- Automatic padding (384-d → 1536-d)
- Batch processing
- No external API dependencies

**Default Model:** all-MiniLM-L6-v2 (384 dimensions)

### 2. OpenAIEmbeddingService
**File:** `openai_embedding_service.py`

Uses OpenAI's embedding API.

**Key Features:**
- Rate limit handling with exponential backoff
- Request batching (up to 2048 texts)
- Local caching
- Token usage logging
- Retry logic

**Default Model:** text-embedding-ada-002 (1536 dimensions)

### 3. FastEmbedEmbeddingService
**File:** `fastembed_embedding_service.py`

Uses FastEmbed library as a faster alternative.

**Key Features:**
- Optimized CPU inference
- Lower memory footprint
- Automatic padding
- Fast initialization

**Default Model:** BAAI/bge-small-en-v1.5 (384 dimensions)

### 4. LangChainEmbeddingAdapter
**File:** `langchain_embedding_adapter.py`

Wrapper for LangChain embedding providers.

**Key Features:**
- Works with any LangChain Embeddings class
- Dimension normalization
- Async/sync model support

## Factory Pattern

### EmbeddingServiceFactory
**File:** `factory.py`

Creates embedding services based on configuration.

**Usage:**
```python
from app.adapters.outbound.embeddings import create_embedding_service

# Uses settings from environment
service = create_embedding_service()

# Override provider
service = create_embedding_service(provider="openai", api_key="...")
```

## Configuration

All adapters respect the application settings:

```python
# .env
EMBEDDING_PROVIDER=local          # or 'openai', 'fastembed', 'langchain'
EMBEDDING_MODEL=all-MiniLM-L6-v2  # provider-specific
EMBEDDING_DIMENSION=1536          # target dimension
OPENAI_API_KEY=sk-...            # for OpenAI only
```

## Dependency Injection

The embedding service is registered in the DI container via `EmbeddingServiceProvider`:

```python
from app.infrastructure.container import resolve_service
from app.domain.repositories import IEmbeddingService

service = resolve_service(IEmbeddingService)
```

## Protocol Contract

All adapters must implement:

```python
async def generate_embedding(self, text: str) -> Embedding:
    """Generate an embedding for text content."""
    ...

async def generate_embeddings_batch(self, texts: List[str]) -> List[Embedding]:
    """Generate embeddings for multiple texts in batch."""
    ...
```

## Error Handling

All adapters raise `EmbeddingError` from `app.domain.repositories` for:
- Empty text input
- Model loading failures
- API failures
- Network errors

## Testing

### Unit Tests
- `tests/test_local_embedding_service.py`
- `tests/test_openai_embedding_service.py`
- `tests/test_embedding_service_factory.py`

**Run:** `pytest -m unit tests/test_*embedding*.py`

### Integration Tests
- `tests/test_embedding_services_integration.py`

**Run:** `pytest -m slow tests/test_embedding_services_integration.py`

## Adding New Adapters

To add a new embedding provider:

1. Create a new file: `{provider}_embedding_service.py`

2. Implement the protocol:
```python
class MyEmbeddingService:
    async def generate_embedding(self, text: str) -> Embedding:
        # Implementation
        pass
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Embedding]:
        # Implementation
        pass
```

3. Add to factory (`factory.py`):
```python
elif provider == "myprovider":
    return MyEmbeddingService(**kwargs)
```

4. Export from `__init__.py`

5. Add unit tests

6. Update documentation

## Documentation

- **Configuration Guide:** `docs/embedding-services.md`
- **Performance Benchmarks:** `docs/embedding-performance-benchmarks.md`

## Design Principles

1. **Dependency Inversion:** Adapters depend on domain protocols, not vice versa
2. **Single Responsibility:** Each adapter handles one provider
3. **Open/Closed:** Easy to add new providers without modifying existing code
4. **Interface Segregation:** Minimal protocol with only essential methods
5. **Liskov Substitution:** All adapters are interchangeable

## Common Patterns

### Lazy Loading
Models are loaded on first use to avoid startup delays:
```python
async def _ensure_model_loaded(self):
    if self._model is None:
        # Load model
```

### Dimension Normalization
Embeddings are padded/truncated to match target dimension:
```python
def _pad_vector(self, vector: List[float]) -> List[float]:
    if len(vector) < target:
        return vector + [0.0] * (target - len(vector))
```

### Error Wrapping
Provider-specific errors are wrapped in domain `EmbeddingError`:
```python
try:
    result = await provider_call()
except ProviderError as e:
    raise EmbeddingError(f"Failed: {e}")
```

## Performance Tips

1. **Use batch operations:** `generate_embeddings_batch()` is faster than multiple `generate_embedding()` calls
2. **Choose appropriate provider:** Local for development, OpenAI for quality, FastEmbed for speed
3. **Enable GPU:** For local services, use `device="cuda"` if available
4. **Monitor costs:** For OpenAI, check token usage in logs

## License

Part of the MCP Demo project.
