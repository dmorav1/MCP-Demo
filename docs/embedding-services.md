# Embedding Services Configuration

This document describes the embedding service adapters and their configuration options.

## Overview

The MCP Demo application supports multiple embedding providers through a unified `IEmbeddingService` protocol. This allows flexible switching between different embedding models and providers without changing application code.

## Supported Providers

### 1. Local Embeddings (sentence-transformers)

Uses the `sentence-transformers` library with local models. Default model is `all-MiniLM-L6-v2` (384 dimensions, padded to 1536).

**Configuration:**
```bash
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536
```

**Features:**
- No API costs
- Works offline
- Fast inference on CPU/GPU
- Automatic model downloading and caching
- Lazy loading to avoid startup delays
- Automatic padding from 384-d to 1536-d

**Models:**
- `all-MiniLM-L6-v2` (default): 384 dimensions, fast, good quality
- `all-mpnet-base-v2`: 768 dimensions, slower, higher quality
- `all-distilroberta-v1`: 768 dimensions, balanced

### 2. OpenAI Embeddings

Uses OpenAI's API with `text-embedding-ada-002` model (1536 dimensions).

**Configuration:**
```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=your-api-key-here
```

**Features:**
- High-quality embeddings
- Native 1536 dimensions (no padding needed)
- Automatic rate limit handling with exponential backoff
- Request batching (up to 2048 texts per request)
- Local caching to avoid redundant API calls
- Token usage logging for cost monitoring

**Cost:** ~$0.0001 per 1K tokens

**Requirements:**
- Valid OpenAI API key
- Internet connection

### 3. FastEmbed

Uses the `fastembed` library as a faster alternative to sentence-transformers.

**Configuration:**
```bash
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=1536
```

**Features:**
- Optimized for CPU inference
- Faster than sentence-transformers
- Lower memory footprint
- Automatic padding to target dimension

**Note:** Requires `fastembed` package:
```bash
pip install fastembed
```

### 4. LangChain Adapter

Wrapper for any LangChain embedding provider. Useful for future integrations.

**Configuration (programmatic):**
```python
from langchain.embeddings import HuggingFaceEmbeddings
from app.adapters.outbound.embeddings import create_embedding_service

langchain_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
service = create_embedding_service(
    provider="langchain",
    langchain_embeddings=langchain_embeddings
)
```

**Features:**
- Works with any LangChain Embeddings class
- Automatic dimension normalization
- Supports both sync and async LangChain models

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `EMBEDDING_PROVIDER` | Embedding provider to use | `local` | No |
| `EMBEDDING_MODEL` | Model name (provider-specific) | `all-MiniLM-L6-v2` | No |
| `EMBEDDING_DIMENSION` | Target embedding dimension | `1536` | No |
| `OPENAI_API_KEY` | OpenAI API key | None | Only for OpenAI provider |

## Usage Examples

### Using the Factory

```python
from app.adapters.outbound.embeddings import create_embedding_service

# Create local service
service = create_embedding_service(provider="local")

# Create OpenAI service
service = create_embedding_service(
    provider="openai",
    api_key="your-key"
)

# Generate embeddings
embedding = await service.generate_embedding("Hello world")
embeddings = await service.generate_embeddings_batch([
    "First text",
    "Second text",
    "Third text"
])
```

### Using DI Container

The embedding service is automatically registered in the DI container based on configuration:

```python
from app.infrastructure.container import resolve_service
from app.domain.repositories import IEmbeddingService

# Resolve from container
service = resolve_service(IEmbeddingService)

# Use the service
embedding = await service.generate_embedding("Hello world")
```

## Performance Considerations

### Local (sentence-transformers)
- **Speed:** ~100-500 texts/second on CPU
- **Memory:** ~500MB for model
- **Startup:** 2-5 seconds for model loading (lazy)
- **Cost:** Free

### OpenAI
- **Speed:** Rate limited by API (varies)
- **Memory:** Minimal (~10MB)
- **Startup:** Instant
- **Cost:** ~$0.0001 per 1K tokens

### FastEmbed
- **Speed:** ~200-1000 texts/second on CPU
- **Memory:** ~300MB for model
- **Startup:** 1-3 seconds for model loading
- **Cost:** Free

## Dimension Handling

All services normalize embeddings to the configured `EMBEDDING_DIMENSION` (default 1536):

- **Native 1536-d models** (OpenAI): No transformation needed
- **Smaller dimensions** (384-d, 768-d): Padded with zeros
- **Larger dimensions**: Truncated (rare)

This ensures compatibility with the database vector column.

## Caching

### Local Services
Local services (sentence-transformers, FastEmbed) don't implement caching as model inference is fast enough. Consider adding application-level caching if needed.

### OpenAI Service
Built-in caching prevents redundant API calls:
- Cache key: exact text string
- Cache scope: per service instance
- Memory: grows with unique texts (consider limits for production)

To disable caching:
```python
service = OpenAIEmbeddingService(
    api_key="your-key",
    enable_cache=False
)
```

## Error Handling

All services implement comprehensive error handling:

- **Empty text**: Raises `EmbeddingError`
- **Model loading failure**: Raises `EmbeddingError` with details
- **API errors**: Raises `EmbeddingError` with error message
- **Rate limits**: Automatic retry with exponential backoff (OpenAI)
- **Network issues**: Propagates as `EmbeddingError`

## Testing

### Unit Tests
Run unit tests with mocked dependencies:
```bash
pytest -m unit tests/test_*embedding*.py
```

### Integration Tests
Run integration tests with real models/APIs (slow):
```bash
pytest -m slow tests/test_embedding_services_integration.py
```

Skip tests requiring API keys:
```bash
pytest -m "slow and not skipif"
```

## Migration Guide

### From Hardcoded Service

Before:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
vector = model.encode("text")
```

After:
```python
from app.adapters.outbound.embeddings import create_embedding_service
service = create_embedding_service()
embedding = await service.generate_embedding("text")
vector = embedding.vector
```

### Switching Providers

1. Update environment variables in `.env`:
   ```bash
   EMBEDDING_PROVIDER=openai
   OPENAI_API_KEY=your-key
   ```

2. Restart application

3. No code changes needed!

## Troubleshooting

### "Failed to load embedding model"
- Check model name is correct
- Ensure sufficient disk space for model download
- Check internet connection for first-time download

### "OpenAI API key required"
- Set `OPENAI_API_KEY` environment variable
- Verify key is valid on OpenAI dashboard

### "Rate limit exceeded"
- OpenAI API has rate limits
- Service automatically retries with backoff
- Consider upgrading OpenAI plan or reducing batch sizes

### "Embedding dimension mismatch"
- Check `EMBEDDING_DIMENSION` matches database vector column
- Services automatically pad/truncate as needed

## Best Practices

1. **Choose provider based on needs:**
   - Development: `local` (fast, free)
   - Production (quality): `openai` (best quality, cost)
   - Production (cost): `local` or `fastembed` (free, good quality)

2. **Use batch operations:**
   ```python
   # Good: batch processing
   embeddings = await service.generate_embeddings_batch(texts)
   
   # Bad: one by one
   embeddings = [await service.generate_embedding(t) for t in texts]
   ```

3. **Cache at application level:**
   Store embeddings in database to avoid regeneration

4. **Monitor costs:**
   - Check logs for token usage (OpenAI)
   - Set up billing alerts on OpenAI dashboard

5. **Test with integration tests:**
   Verify embedding quality before deploying changes

## Future Enhancements

Potential improvements:

- [ ] Vector quantization for reduced storage
- [ ] Multi-language model support
- [ ] Custom model fine-tuning
- [ ] Embedding similarity metrics
- [ ] Batch processing optimizations
- [ ] Redis caching for distributed systems
- [ ] A/B testing framework for comparing providers
