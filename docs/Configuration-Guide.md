# Configuration Guide - MCP RAG Demo

**Version:** 1.0  
**Date:** November 7, 2025  
**Status:** Complete  
**Related Documents:**
- [Phase 3 Architecture](Phase3-Architecture.md)
- [Phase 3 Migration Guide](Phase3-Migration-Guide.md)
- [Operations Guide](Operations-Guide.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Environment Variables Reference](#environment-variables-reference)
3. [Configuration by Environment](#configuration-by-environment)
4. [Embedding Provider Configuration](#embedding-provider-configuration)
5. [Database Configuration](#database-configuration)
6. [Performance Tuning](#performance-tuning)
7. [Configuration Validation](#configuration-validation)
8. [Security Considerations](#security-considerations)

---

## Overview

The MCP RAG Demo application is configured entirely through environment variables. This guide provides comprehensive documentation of all configuration options and recommended settings for different deployment scenarios.

### Configuration Sources

Configuration is loaded in this order (later sources override earlier ones):

1. **Default values** in `app/infrastructure/config.py`
2. **Environment variables** from shell
3. **`.env` file** in project root (development only)
4. **External secret managers** (production)

### Configuration File

**File:** `.env` (development) or environment variables (production)

**Location:** Project root directory

**Format:**
```bash
# Comments start with #
VARIABLE_NAME=value
ANOTHER_VARIABLE=another_value

# No quotes needed (unless value contains spaces/special chars)
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db

# Quotes for values with spaces
APP_TITLE="MCP RAG Demo Application"
```

---

## Environment Variables Reference

### Core Application Settings

#### `USE_NEW_ARCHITECTURE`
- **Type:** Boolean
- **Default:** `true`
- **Required:** No
- **Description:** Enable new hexagonal architecture with adapters
- **Values:**
  - `true` - Use new adapter-based architecture (recommended)
  - `false` - Use legacy implementation
- **Example:** `USE_NEW_ARCHITECTURE=true`

#### `APP_TITLE`
- **Type:** String
- **Default:** `"MCP Backend"`
- **Required:** No
- **Description:** Application title shown in API documentation
- **Example:** `APP_TITLE="MCP RAG Demo"`

#### `LOG_LEVEL`
- **Type:** String
- **Default:** `INFO`
- **Required:** No
- **Description:** Logging verbosity level
- **Values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Example:** `LOG_LEVEL=INFO`

#### `ENVIRONMENT`
- **Type:** String
- **Default:** `development`
- **Required:** No
- **Description:** Deployment environment name
- **Values:** `development`, `staging`, `production`
- **Example:** `ENVIRONMENT=production`

### Database Configuration

#### `DATABASE_URL`
- **Type:** String (Connection URL)
- **Default:** `postgresql+psycopg://postgres:postgres@localhost:5432/mcp_db`
- **Required:** Yes
- **Description:** PostgreSQL connection string with psycopg3 driver
- **Format:** `postgresql+psycopg://user:password@host:port/database`
- **Example:** `DATABASE_URL=postgresql+psycopg://admin:secret@db.example.com:5432/mcp_prod`
- **Note:** Must use `psycopg` (not `psycopg2`) for Python 3.13 compatibility

#### `DB_POOL_SIZE`
- **Type:** Integer
- **Default:** `5`
- **Required:** No
- **Description:** Number of persistent database connections in pool
- **Example:** `DB_POOL_SIZE=10`

#### `DB_MAX_OVERFLOW`
- **Type:** Integer
- **Default:** `10`
- **Required:** No
- **Description:** Additional connections when pool is full
- **Example:** `DB_MAX_OVERFLOW=20`

#### `DB_POOL_TIMEOUT`
- **Type:** Integer (seconds)
- **Default:** `30`
- **Required:** No
- **Description:** Timeout waiting for connection from pool
- **Example:** `DB_POOL_TIMEOUT=60`

#### `DB_POOL_RECYCLE`
- **Type:** Integer (seconds)
- **Default:** `3600`
- **Required:** No
- **Description:** Recycle connections after this time
- **Example:** `DB_POOL_RECYCLE=7200`

### Embedding Service Configuration

#### `EMBEDDING_PROVIDER`
- **Type:** String (Enum)
- **Default:** `local`
- **Required:** Yes
- **Description:** Embedding service provider
- **Values:**
  - `local` - sentence-transformers (free, offline)
  - `openai` - OpenAI API (requires API key, costs apply)
  - `fastembed` - FastEmbed library (free, offline)
  - `langchain` - LangChain wrapper (flexible)
- **Example:** `EMBEDDING_PROVIDER=local`

#### `EMBEDDING_MODEL`
- **Type:** String
- **Default:** Depends on provider
- **Required:** Yes
- **Description:** Model name for embedding generation
- **Examples:**
  - Local: `all-MiniLM-L6-v2`, `all-mpnet-base-v2`
  - OpenAI: `text-embedding-ada-002`, `text-embedding-3-small`
  - FastEmbed: `BAAI/bge-small-en-v1.5`
- **Example:** `EMBEDDING_MODEL=all-MiniLM-L6-v2`

#### `EMBEDDING_DIMENSION`
- **Type:** Integer
- **Default:** `1536`
- **Required:** Yes
- **Description:** Target embedding vector dimension
- **Note:** Must match database schema `vector(1536)`
- **Example:** `EMBEDDING_DIMENSION=1536`

#### `OPENAI_API_KEY`
- **Type:** String (Secret)
- **Default:** None
- **Required:** Yes (if `EMBEDDING_PROVIDER=openai`)
- **Description:** OpenAI API key for embeddings
- **Format:** `sk-...` (starts with "sk-")
- **Example:** `OPENAI_API_KEY=sk-proj-...`
- **Security:** Never commit to git, use secret manager in production

#### `EMBEDDING_BATCH_SIZE`
- **Type:** Integer
- **Default:** `32`
- **Required:** No
- **Description:** Number of texts to embed in one batch
- **Example:** `EMBEDDING_BATCH_SIZE=64`

### Chunking Configuration

#### `CHUNK_MAX_CHARS`
- **Type:** Integer
- **Default:** `1000`
- **Required:** No
- **Description:** Maximum characters per conversation chunk
- **Example:** `CHUNK_MAX_CHARS=1500`

#### `CHUNK_OVERLAP_CHARS`
- **Type:** Integer
- **Default:** `100`
- **Required:** No
- **Description:** Character overlap between consecutive chunks
- **Example:** `CHUNK_OVERLAP_CHARS=150`

#### `CHUNK_BY_SPEAKER`
- **Type:** Boolean
- **Default:** `true`
- **Required:** No
- **Description:** Break chunks on speaker change
- **Example:** `CHUNK_BY_SPEAKER=true`

### Vector Search Configuration

#### `VECTOR_SEARCH_TOP_K`
- **Type:** Integer
- **Default:** `10`
- **Required:** No
- **Description:** Default number of results to return
- **Example:** `VECTOR_SEARCH_TOP_K=20`

#### `VECTOR_SIMILARITY_THRESHOLD`
- **Type:** Float (0.0 to 1.0)
- **Default:** `0.7`
- **Required:** No
- **Description:** Minimum similarity score for results
- **Example:** `VECTOR_SIMILARITY_THRESHOLD=0.75`

### MCP Server Configuration

#### `MCP_TRANSPORT`
- **Type:** String (Enum)
- **Default:** `stdio`
- **Required:** No
- **Description:** MCP server transport protocol
- **Values:**
  - `stdio` - Standard input/output (for Claude Desktop)
  - `sse` - Server-Sent Events (for HTTP clients)
- **Example:** `MCP_TRANSPORT=stdio`

#### `MCP_PORT`
- **Type:** Integer
- **Default:** `3000`
- **Required:** No (only for SSE transport)
- **Description:** Port for MCP server (SSE mode)
- **Example:** `MCP_PORT=3000`

#### `FASTAPI_BASE_URL`
- **Type:** String (URL)
- **Default:** `http://localhost:8000`
- **Required:** No
- **Description:** Base URL for FastAPI backend
- **Example:** `FASTAPI_BASE_URL=http://mcp-backend:8000`

### Slack Integration (Optional)

#### `ENABLE_SLACK_INGEST`
- **Type:** Boolean
- **Default:** `false`
- **Required:** No
- **Description:** Enable automatic Slack message ingestion
- **Example:** `ENABLE_SLACK_INGEST=true`

#### `SLACK_BOT_TOKEN`
- **Type:** String (Secret)
- **Default:** None
- **Required:** Yes (if Slack enabled)
- **Description:** Slack Bot User OAuth Token
- **Format:** `xoxb-...`
- **Example:** `SLACK_BOT_TOKEN=xoxb-1234-5678-...`

#### `SLACK_CHANNEL`
- **Type:** String
- **Default:** None
- **Required:** Yes (if Slack enabled)
- **Description:** Slack channel ID to monitor
- **Example:** `SLACK_CHANNEL=C1234567890`

---

## Configuration by Environment

### Local Development

**File:** `.env` (project root)

```bash
# Architecture
USE_NEW_ARCHITECTURE=true

# Database (Docker container)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/mcp_db

# Embedding (local, no API key needed)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536

# Chunking
CHUNK_MAX_CHARS=1000
CHUNK_OVERLAP_CHARS=100

# Logging (verbose for debugging)
LOG_LEVEL=DEBUG

# MCP Server
MCP_TRANSPORT=stdio

# Slack (optional, for testing)
ENABLE_SLACK_INGEST=false
# SLACK_BOT_TOKEN=xoxb-...
# SLACK_CHANNEL=C...
```

**Starting Development:**
```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env

# Start services
./start-dev.sh all
```

### Staging Environment

**Source:** Environment variables (from CI/CD or secret manager)

```bash
# Architecture
USE_NEW_ARCHITECTURE=true

# Database (staging server)
DATABASE_URL=postgresql+psycopg://mcp_user:$DB_PASSWORD@staging-db.internal:5432/mcp_staging

# Embedding (OpenAI for quality testing)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=$OPENAI_API_KEY_STAGING

# Connection pooling (moderate)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Chunking (same as production)
CHUNK_MAX_CHARS=1000
CHUNK_OVERLAP_CHARS=100

# Logging (info level)
LOG_LEVEL=INFO
ENVIRONMENT=staging

# MCP Server (SSE for web clients)
MCP_TRANSPORT=sse
MCP_PORT=3000
FASTAPI_BASE_URL=http://mcp-backend:8000

# Slack (enabled for integration testing)
ENABLE_SLACK_INGEST=true
SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN_STAGING
SLACK_CHANNEL=$SLACK_CHANNEL_STAGING
```

### Production Environment

**Source:** Kubernetes secrets, AWS Secrets Manager, or similar

```bash
# Architecture
USE_NEW_ARCHITECTURE=true

# Database (production RDS or managed PostgreSQL)
DATABASE_URL=postgresql+psycopg://mcp_prod:$DB_PASSWORD@prod-db.rds.amazonaws.com:5432/mcp_production

# Embedding (OpenAI for best quality)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=$OPENAI_API_KEY_PROD  # From secret manager

# Connection pooling (higher for production load)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=60
DB_POOL_RECYCLE=3600

# Chunking (optimized)
CHUNK_MAX_CHARS=1000
CHUNK_OVERLAP_CHARS=100

# Logging (info level, structured JSON)
LOG_LEVEL=INFO
ENVIRONMENT=production

# MCP Server (SSE for web clients)
MCP_TRANSPORT=sse
MCP_PORT=3000
FASTAPI_BASE_URL=http://mcp-backend-service:8000

# Slack (enabled)
ENABLE_SLACK_INGEST=true
SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN_PROD  # From secret manager
SLACK_CHANNEL=$SLACK_CHANNEL_PROD
```

### Testing Environment

**File:** `.env.test` or test-specific variables

```bash
# Architecture
USE_NEW_ARCHITECTURE=true

# Database (test database)
DATABASE_URL=postgresql+psycopg://test:test@localhost:5432/mcp_test

# Embedding (local for speed)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536

# Minimal pooling for tests
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=5

# Chunking (same as production)
CHUNK_MAX_CHARS=1000
CHUNK_OVERLAP_CHARS=100

# Logging (debug for test failures)
LOG_LEVEL=DEBUG
ENVIRONMENT=test

# Slack (disabled for unit tests)
ENABLE_SLACK_INGEST=false
```

**Running Tests:**
```bash
# Load test environment
export $(cat .env.test | xargs)

# Run tests
pytest tests/ -v
```

---

## Embedding Provider Configuration

### Local Provider (sentence-transformers)

**Best for:** Development, cost-sensitive deployments, offline requirements

**Configuration:**
```bash
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2  # or all-mpnet-base-v2
EMBEDDING_DIMENSION=1536
```

**Models:**

| Model | Native Dim | Quality | Speed | Size |
|-------|-----------|---------|-------|------|
| all-MiniLM-L6-v2 | 384 | Good (0.58) | Fast | 90 MB |
| all-mpnet-base-v2 | 768 | Better (0.61) | Medium | 420 MB |
| multi-qa-mpnet-base-dot-v1 | 768 | Best (0.63) | Medium | 420 MB |

**Notes:**
- Vectors are padded from native dimension to 1536 (database requirement)
- Models downloaded on first use (~100-400 MB)
- CPU or GPU supported (auto-detected)
- No API costs

**Installation:**
```bash
pip install sentence-transformers torch
```

### OpenAI Provider

**Best for:** Production, best quality, consistent with other OpenAI services

**Configuration:**
```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002  # or text-embedding-3-small
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-proj-...
```

**Models:**

| Model | Dimension | Cost (per 1M tokens) | Quality |
|-------|-----------|----------------------|---------|
| text-embedding-ada-002 | 1536 | $0.10 | Excellent |
| text-embedding-3-small | 1536 | $0.02 | Very Good |
| text-embedding-3-large | 3072 | $0.13 | Best |

**Notes:**
- Requires internet connection
- Rate limits apply (check OpenAI dashboard)
- Automatic retry with exponential backoff
- Native 1536-d (no padding needed)

**Cost Estimation:**
```
Average conversation: 500 tokens
1000 conversations/day: 500K tokens/day
Monthly cost: ~$1.50 (with ada-002)
```

### FastEmbed Provider

**Best for:** Fast inference, lightweight deployment

**Configuration:**
```bash
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=1536
```

**Models:**

| Model | Native Dim | Speed | Quality |
|-------|-----------|-------|---------|
| BAAI/bge-small-en-v1.5 | 384 | Fastest | Good |
| BAAI/bge-base-en-v1.5 | 768 | Fast | Better |

**Notes:**
- Optimized CPU inference
- Lower memory footprint than sentence-transformers
- No GPU required
- Vectors padded to 1536

**Installation:**
```bash
pip install fastembed
```

### LangChain Provider

**Best for:** Integration with LangChain ecosystem

**Configuration:**
```bash
EMBEDDING_PROVIDER=langchain
EMBEDDING_MODEL=openai  # or huggingface, cohere, etc.
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-...  # if using OpenAI via LangChain
```

**Notes:**
- Wraps any LangChain Embeddings class
- Flexible but adds dependency overhead
- Useful for future RAG enhancements

**Installation:**
```bash
pip install langchain langchain-openai
```

### Provider Selection Decision Tree

```
Do you need offline capability?
├─ Yes → Use "local" or "fastembed"
│   ├─ Need fastest inference? → "fastembed"
│   └─ Need better quality? → "local" with all-mpnet-base-v2
│
└─ No (internet available)
    ├─ Budget priority? → "openai" with text-embedding-3-small
    ├─ Quality priority? → "openai" with text-embedding-ada-002
    └─ LangChain integration? → "langchain"
```

---

## Database Configuration

### Connection String Format

**Correct format (psycopg3):**
```
postgresql+psycopg://user:password@host:port/database
```

**Common mistakes:**
```
# Wrong - missing driver
postgresql://user:password@host:port/database

# Wrong - old driver (psycopg2)
postgresql+psycopg2://user:password@host:port/database

# Wrong - special characters not encoded
postgresql+psycopg://user:p@ss:word@host:5432/db
# Should be: postgresql+psycopg://user:p%40ss%3Aword@host:5432/db
```

### Connection Pool Configuration

**Low-traffic (development):**
```bash
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
```

**Medium-traffic (staging):**
```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

**High-traffic (production):**
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=60
```

**Calculation:**
```
DB_POOL_SIZE = (Expected concurrent requests) / (Average request duration in seconds)
DB_MAX_OVERFLOW = DB_POOL_SIZE * 2

Example: 50 requests/sec, 0.2s duration
DB_POOL_SIZE = 50 * 0.2 = 10
DB_MAX_OVERFLOW = 20
```

### SSL/TLS Configuration

**For AWS RDS:**
```bash
DATABASE_URL=postgresql+psycopg://user:pass@db.rds.amazonaws.com:5432/mcp?sslmode=require&sslrootcert=/path/to/rds-ca-bundle.pem
```

**For self-signed certificates:**
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db?sslmode=verify-ca&sslcert=/path/to/client.crt&sslkey=/path/to/client.key
```

### Read Replicas (Advanced)

For read-heavy workloads, configure read replicas:

```python
# app/infrastructure/config.py
class AppSettings:
    database_url: str  # Primary (write)
    database_read_url: Optional[str]  # Read replica

# Use read replica for queries
read_engine = create_engine(settings.database_read_url)
```

---

## Performance Tuning

### Embedding Generation

**Batch Processing:**
```bash
# Process multiple texts in one call
EMBEDDING_BATCH_SIZE=32  # Local
EMBEDDING_BATCH_SIZE=2048  # OpenAI (max)
```

**GPU Acceleration (Local provider):**
```bash
# Auto-detected, or force:
EMBEDDING_DEVICE=cuda  # Use GPU if available
EMBEDDING_DEVICE=cpu   # Force CPU
```

### Database Performance

**Vector Index Tuning:**
```sql
-- Adjust IVFFlat lists parameter based on data size
-- Rule of thumb: lists = sqrt(total_rows)

-- For 10K chunks:
CREATE INDEX idx_embedding ON conversation_chunks 
USING ivfflat (embedding vector_l2_ops) 
WITH (lists = 100);

-- For 100K chunks:
CREATE INDEX idx_embedding ON conversation_chunks 
USING ivfflat (embedding vector_l2_ops) 
WITH (lists = 316);

-- For 1M chunks:
CREATE INDEX idx_embedding ON conversation_chunks 
USING ivfflat (embedding vector_l2_ops) 
WITH (lists = 1000);
```

**Query Optimization:**
```bash
# Limit results for faster queries
VECTOR_SEARCH_TOP_K=10  # vs 100

# Higher threshold = fewer results
VECTOR_SIMILARITY_THRESHOLD=0.75  # vs 0.5
```

### Chunking Optimization

**For short messages:**
```bash
CHUNK_MAX_CHARS=500  # Smaller chunks
CHUNK_OVERLAP_CHARS=50
CHUNK_BY_SPEAKER=true  # Important for conversations
```

**For long documents:**
```bash
CHUNK_MAX_CHARS=2000  # Larger chunks
CHUNK_OVERLAP_CHARS=200
CHUNK_BY_SPEAKER=false  # May not apply
```

### API Server Performance

**FastAPI Workers:**
```bash
# In start script or Docker
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

**Number of workers:**
```
CPU-bound (local embeddings): workers = (CPU cores * 2) + 1
I/O-bound (OpenAI embeddings): workers = CPU cores * 4
```

---

## Configuration Validation

### Validation Checklist

Before deployment, verify:

**Database:**
- [ ] `DATABASE_URL` is correct and accessible
- [ ] Database has pgvector extension installed
- [ ] Tables exist with correct schema
- [ ] Vector column is `vector(1536)`
- [ ] Indexes are created

**Embedding Service:**
- [ ] `EMBEDDING_PROVIDER` is set
- [ ] `EMBEDDING_MODEL` is appropriate for provider
- [ ] `EMBEDDING_DIMENSION` is 1536
- [ ] `OPENAI_API_KEY` is set (if using OpenAI)
- [ ] API key is valid and has sufficient quota

**Architecture:**
- [ ] `USE_NEW_ARCHITECTURE` is set (true recommended)
- [ ] DI container initializes successfully
- [ ] All adapters are registered

**Optional Features:**
- [ ] Slack credentials set (if `ENABLE_SLACK_INGEST=true`)
- [ ] MCP transport configured correctly
- [ ] Logging level appropriate for environment

### Automated Validation

**Script:** `scripts/validate_config.py`

```bash
# Validate configuration
python scripts/validate_config.py

# Output:
# ✅ Database connection successful
# ✅ Embedding service configured
# ✅ DI container initializes
# ❌ OPENAI_API_KEY not set (required for provider=openai)
```

**Health Check Endpoint:**
```bash
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "database": "connected",
  "embedding_service": "local (all-MiniLM-L6-v2)",
  "architecture": "new (adapters)",
  "version": "1.0.0"
}
```

### Common Validation Errors

**Error:** `ValueError: OPENAI_API_KEY is required`
**Fix:** Set `OPENAI_API_KEY` in environment or `.env`

**Error:** `OperationalError: could not connect to server`
**Fix:** Verify `DATABASE_URL` and ensure database is running

**Error:** `ModuleNotFoundError: No module named 'sentence_transformers'`
**Fix:** `pip install sentence-transformers`

**Error:** `EmbeddingError: Model not found`
**Fix:** Verify `EMBEDDING_MODEL` name is correct for provider

---

## Security Considerations

### Secret Management

**Development (Local):**
```bash
# .env file (excluded from git via .gitignore)
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/db
```

**Production (Recommended):**

**Option 1: Environment Variables**
```bash
# Set in deployment platform (Kubernetes, Docker, etc.)
kubectl create secret generic mcp-secrets \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=DB_PASSWORD=...
```

**Option 2: AWS Secrets Manager**
```bash
# Store in Secrets Manager
aws secretsmanager create-secret \
  --name mcp/prod/openai-key \
  --secret-string "sk-..."

# Retrieve in application
OPENAI_API_KEY=$(aws secretsmanager get-secret-value --secret-id mcp/prod/openai-key --query SecretString --output text)
```

**Option 3: HashiCorp Vault**
```bash
# Store in Vault
vault kv put secret/mcp/prod openai_key=sk-...

# Retrieve in application
export OPENAI_API_KEY=$(vault kv get -field=openai_key secret/mcp/prod)
```

### Credential Rotation

**OpenAI API Key:**
```bash
# 1. Generate new key in OpenAI dashboard
# 2. Update secret in secret manager
# 3. Rolling restart of application
# 4. Verify new key works
# 5. Delete old key from OpenAI dashboard
```

**Database Password:**
```bash
# 1. Create new database user or change password
# 2. Update DATABASE_URL with new credentials
# 3. Rolling restart of application
# 4. Verify connectivity
# 5. Delete old user or expire old password
```

### Access Control

**Database:**
```sql
-- Create restricted user
CREATE USER mcp_app WITH PASSWORD '...';
GRANT CONNECT ON DATABASE mcp_db TO mcp_app;
GRANT USAGE ON SCHEMA public TO mcp_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO mcp_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mcp_app;

-- Revoke unnecessary privileges
REVOKE CREATE ON SCHEMA public FROM mcp_app;
```

**API Keys:**
- Use separate keys for dev/staging/prod
- Rotate regularly (every 90 days)
- Monitor usage for anomalies
- Implement rate limiting

### Configuration Auditing

**Track configuration changes:**
```bash
# Git commit .env.example (without secrets)
git add .env.example
git commit -m "Update configuration template"

# Log configuration changes in deployment
echo "$(date): Updated EMBEDDING_PROVIDER from local to openai" >> /var/log/mcp-config-changes.log
```

---

## Examples and Templates

### Complete `.env` Template

```bash
# =============================================================================
# MCP RAG Demo - Configuration Template
# =============================================================================
# Copy to .env and update with your values
# NEVER commit .env to git (already in .gitignore)
# =============================================================================

# -----------------------------------------------------------------------------
# Architecture Settings
# -----------------------------------------------------------------------------
USE_NEW_ARCHITECTURE=true
ENVIRONMENT=development
LOG_LEVEL=INFO

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/mcp_db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# -----------------------------------------------------------------------------
# Embedding Service Configuration
# -----------------------------------------------------------------------------
# Provider: local (free), openai (paid), fastembed (free), langchain (flexible)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536

# OpenAI API Key (required if EMBEDDING_PROVIDER=openai)
# Get from: https://platform.openai.com/api-keys
# OPENAI_API_KEY=sk-proj-...

# -----------------------------------------------------------------------------
# Chunking Configuration
# -----------------------------------------------------------------------------
CHUNK_MAX_CHARS=1000
CHUNK_OVERLAP_CHARS=100
CHUNK_BY_SPEAKER=true

# -----------------------------------------------------------------------------
# Vector Search Configuration
# -----------------------------------------------------------------------------
VECTOR_SEARCH_TOP_K=10
VECTOR_SIMILARITY_THRESHOLD=0.7

# -----------------------------------------------------------------------------
# MCP Server Configuration
# -----------------------------------------------------------------------------
# Transport: stdio (Claude Desktop) or sse (HTTP clients)
MCP_TRANSPORT=stdio
MCP_PORT=3000
FASTAPI_BASE_URL=http://localhost:8000

# -----------------------------------------------------------------------------
# Slack Integration (Optional)
# -----------------------------------------------------------------------------
ENABLE_SLACK_INGEST=false
# SLACK_BOT_TOKEN=xoxb-...
# SLACK_CHANNEL=C...

# =============================================================================
# End of Configuration
# =============================================================================
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-backend:
    build: .
    environment:
      # Load from .env file
      - USE_NEW_ARCHITECTURE=${USE_NEW_ARCHITECTURE:-true}
      - DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/mcp_db
      - EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-local}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-all-MiniLM-L6-v2}
      - EMBEDDING_DIMENSION=${EMBEDDING_DIMENSION:-1536}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    env_file:
      - .env  # Load additional variables from .env
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=mcp_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"

volumes:
  postgres_data:
```

---

## Troubleshooting Configuration Issues

### Issue: Configuration not loading

**Symptoms:** Default values used instead of .env values

**Solutions:**
```bash
# 1. Verify .env file location
ls -la .env  # Should be in project root

# 2. Check file format (no BOM, LF line endings)
file .env  # Should show: ASCII text

# 3. Verify no syntax errors
cat .env | grep -v '^#' | grep -v '^$'  # Show non-comment lines

# 4. Test loading
python -c "from app.infrastructure.config import get_settings; print(get_settings().model_dump())"
```

### Issue: Database connection fails

**Solutions:**
```bash
# 1. Test connection directly
psql "$DATABASE_URL"

# 2. Verify URL format
echo $DATABASE_URL
# Should be: postgresql+psycopg://...

# 3. Test from Python
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); conn = engine.connect(); print('Connected!')"
```

### Issue: OpenAI API key invalid

**Solutions:**
```bash
# 1. Verify key format
echo $OPENAI_API_KEY | grep -E '^sk-proj-'  # New format
echo $OPENAI_API_KEY | grep -E '^sk-'       # Old format

# 2. Test key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. Check quota
# Visit: https://platform.openai.com/account/usage
```

---

## Additional Resources

- **Example Configurations:** See `.env.example` in project root
- **Configuration Schema:** See `app/infrastructure/config.py`
- **Validation Script:** See `scripts/validate_config.py`
- **Documentation:** [Phase 3 Architecture](Phase3-Architecture.md)

---

**Document Status**: Complete  
**Last Updated**: November 7, 2025  
**Maintained By**: Product Owner Agent
