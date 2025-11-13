# Caching Implementation Guide

This document describes the caching implementation for improving performance and reducing costs.

## Overview

The MCP Demo now includes comprehensive caching for:
- **Embedding Generation**: Cache expensive embedding API calls
- **Search Results**: Cache vector search results for repeated queries  
- **LLM Responses**: Cache RAG responses to reduce API costs

## Quick Start

### Configuration

Add to your `.env` file:

```env
CACHE_ENABLED=true
CACHE_BACKEND=memory  # or "redis" for production
CACHE_REDIS_URL=redis://localhost:6379
EMBEDDING_CACHE_TTL=86400  # 24 hours
SEARCH_CACHE_TTL=1800      # 30 minutes
LLM_CACHE_TTL=3600         # 1 hour
```

### Using Docker with Redis

```bash
docker-compose up -d
```

Redis is automatically configured and connected.

## API Endpoints

### Get Cache Statistics

```bash
curl http://localhost:8000/api/cache/stats
```

### Clear Cache

```bash
curl -X POST http://localhost:8000/api/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"pattern": "embedding:*"}'
```

## Performance Benefits

- **Embedding Generation**: 100-500x faster for cached entries
- **Search Operations**: 50-200x faster for cached queries
- **RAG Responses**: 1000-5000x faster for cached answers
- **Cost Savings**: Eliminates redundant API calls

## Architecture

Follows hexagonal architecture:
- Domain layer: Cache port interface
- Adapter layer: In-memory and Redis implementations
- Application layer: Cached service wrappers
- Infrastructure: Cache factory

See full documentation in [CACHING.md](./CACHING.md)
