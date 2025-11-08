# Phase 3 Migration Guide - Outbound Adapters

**Version:** 1.0  
**Date:** November 7, 2025  
**Status:** Complete  
**Related Documents:**
- [Phase 3 Architecture](Phase3-Architecture.md)
- [Configuration Guide](Configuration-Guide.md)
- [General Migration Guide](MIGRATION_GUIDE.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Migration Strategy](#migration-strategy)
3. [Pre-Migration Checklist](#pre-migration-checklist)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [Feature Flag Usage](#feature-flag-usage)
6. [Breaking Changes](#breaking-changes)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)
9. [Validation and Testing](#validation-and-testing)

---

## Overview

Phase 3 completes the hexagonal architecture migration by implementing the outbound adapter layer. This migration introduces:

- **Repository Adapters**: SQLAlchemy implementations for data persistence
- **Embedding Service Adapters**: Multiple provider support (Local, OpenAI, FastEmbed, LangChain)
- **Dependency Injection**: Fully configured DI container
- **Configuration-Driven Behavior**: Runtime provider selection via environment variables

### Migration Type: **Non-Breaking, Feature-Flagged**

✅ **Safe Migration**: Both old and new implementations coexist  
✅ **Gradual Rollout**: Feature flag controls which implementation is used  
✅ **Zero Downtime**: No service interruption required  
✅ **Rollback Ready**: Can revert instantly via feature flag  

---

## Migration Strategy

### Coexistence Architecture

The system supports both legacy and new architecture simultaneously:

```
┌─────────────────────────────────────────────────┐
│           FastAPI Application                    │
│                                                  │
│  ┌────────────────┐    ┌──────────────────┐    │
│  │  Legacy Routes │    │  New Routes      │    │
│  │  (crud.py)     │    │  (Use Cases +    │    │
│  │                │    │   DI Container)  │    │
│  └────────────────┘    └──────────────────┘    │
│         │                       │               │
│         │                       │               │
│    [Feature Flag: USE_NEW_ARCHITECTURE]        │
│         │                       │               │
│         ▼                       ▼               │
│  ┌────────────────┐    ┌──────────────────┐    │
│  │  Legacy Code   │    │  Adapters Layer  │    │
│  │  (services.py) │    │  (Repositories)  │    │
│  └────────────────┘    └──────────────────┘    │
│         │                       │               │
│         └───────────┬───────────┘               │
│                     ▼                           │
│            PostgreSQL + pgvector                │
└─────────────────────────────────────────────────┘
```

### Migration Phases

**Phase 3.1: Adapter Implementation** ✅ COMPLETE
- Repository adapters implemented
- Embedding service adapters implemented
- DI container configured
- Feature flag system in place

**Phase 3.2: Gradual Enablement** ← YOU ARE HERE
- Enable new architecture in development
- Validate functionality parity
- Monitor performance metrics
- Gather feedback

**Phase 3.3: Production Rollout**
- Enable for subset of users (canary deployment)
- Monitor error rates and performance
- Gradual rollout to all users
- Keep feature flag for emergency rollback

**Phase 3.4: Legacy Cleanup** (Future)
- Remove feature flag after stability proven
- Delete legacy code (crud.py, services.py)
- Update documentation
- Remove unused dependencies

---

## Pre-Migration Checklist

Before enabling the new architecture, verify:

### Environment Configuration

- [ ] `DATABASE_URL` is set correctly
- [ ] `EMBEDDING_PROVIDER` is configured (local/openai/fastembed)
- [ ] `EMBEDDING_MODEL` is appropriate for chosen provider
- [ ] `EMBEDDING_DIMENSION` matches database schema (1536)
- [ ] `OPENAI_API_KEY` is set (if using OpenAI provider)
- [ ] `USE_NEW_ARCHITECTURE` environment variable exists

### Database Schema

- [ ] PostgreSQL with pgvector extension installed
- [ ] Tables exist: `conversations`, `conversation_chunks`
- [ ] Vector column is `vector(1536)` dimension
- [ ] IVFFlat index created on embedding column
- [ ] Foreign key constraints in place

### Dependencies

- [ ] All Python dependencies installed (`pip install -r requirements.txt`)
- [ ] sentence-transformers installed (if using local provider)
- [ ] OpenAI SDK installed (if using OpenAI provider)
- [ ] FastEmbed installed (if using fastembed provider)

### Testing

- [ ] Unit tests pass: `pytest tests/unit/`
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] Existing data is accessible via new adapters
- [ ] Performance benchmarks meet requirements

### Backup

- [ ] Database backup created
- [ ] Configuration files backed up
- [ ] Rollback plan documented and tested

---

## Step-by-Step Migration

### Step 1: Update Environment Configuration

**File:** `.env`

```bash
# Add or update these variables
USE_NEW_ARCHITECTURE=true

# Ensure embedding configuration is set
EMBEDDING_PROVIDER=local  # or openai, fastembed
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536

# Database (verify existing setting)
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/mcp_db

# OpenAI (if using OpenAI provider)
# OPENAI_API_KEY=sk-...
```

**Validation:**
```bash
# Verify environment variables are loaded
python -c "from app.infrastructure.config import get_settings; s = get_settings(); print(f'USE_NEW_ARCHITECTURE={s.use_new_architecture}')"
```

### Step 2: Verify Database Schema

Check that your database schema is compatible:

```sql
-- Connect to database
psql -U user -d mcp_db

-- Verify tables exist
\dt

-- Check vector column dimension
SELECT 
    column_name, 
    udt_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'conversation_chunks' 
  AND column_name = 'embedding';

-- Verify index exists
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'conversation_chunks';
```

**Expected Results:**
- `conversations` table exists
- `conversation_chunks` table exists
- `embedding` column is `vector(1536)`
- IVFFlat index exists on `embedding` column

### Step 3: Test Adapter Functionality

Run integration tests to verify adapters work correctly:

```bash
# Run adapter-specific tests
pytest tests/integration/database/ -v

# Run embedding service tests
pytest tests/integration/embedding/ -v

# Run end-to-end workflow tests
pytest tests/integration/e2e/ -v
```

**All tests should pass before proceeding.**

### Step 4: Enable New Architecture (Development)

Start with development environment only:

```bash
# Update .env
USE_NEW_ARCHITECTURE=true

# Restart application
./start-dev.sh

# Or with Docker
docker-compose down
docker-compose up -d
```

**Verify startup:**
```bash
# Check logs for DI container initialization
docker-compose logs -f mcp-backend | grep "DI container"

# Expected output:
# 🔌 Initializing dependency injection container...
# ✅ DI container initialized with all adapters
```

### Step 5: Validate Functionality

Test critical workflows:

**Test 1: Ingest Conversation**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_title": "Migration Test",
    "original_title": "Test Conversation",
    "url": "http://example.com",
    "messages": [
      {
        "author_name": "Alice",
        "author_type": "human",
        "content": "Hello, this is a test message."
      },
      {
        "author_name": "Bob",
        "author_type": "human",
        "content": "Hi Alice, testing the new architecture!"
      }
    ]
  }'
```

**Expected:** HTTP 200, conversation ID returned

**Test 2: Search Conversations**
```bash
curl -X GET "http://localhost:8000/search?q=test+message&top_k=5"
```

**Expected:** HTTP 200, relevant results returned

**Test 3: List Conversations**
```bash
curl -X GET "http://localhost:8000/conversations?skip=0&limit=10"
```

**Expected:** HTTP 200, conversations with chunks

**Test 4: Health Check**
```bash
curl -X GET http://localhost:8000/health
```

**Expected:** HTTP 200, all components healthy

### Step 6: Monitor Performance

Compare performance between old and new architecture:

```bash
# Run performance benchmarks
python scripts/benchmark_ingest.py --architecture=new
python scripts/benchmark_search.py --architecture=new

# Compare with legacy
python scripts/benchmark_ingest.py --architecture=legacy
python scripts/benchmark_search.py --architecture=legacy
```

**Performance Targets:**
- Ingestion: ≤ 3 seconds per conversation (10 messages)
- Search: ≤ 200ms (p95) for top-10 results
- No performance regression > 10%

### Step 7: Gradual Rollout (Production)

For production deployment:

**Option A: Canary Deployment**
```bash
# Deploy to subset of servers with new architecture enabled
# Route 10% of traffic to canary servers
USE_NEW_ARCHITECTURE=true  # Canary servers
USE_NEW_ARCHITECTURE=false # Main servers (90%)

# Monitor for 24-48 hours
# Gradually increase canary percentage: 10% → 25% → 50% → 100%
```

**Option B: Feature Flag Service**
```python
# Use feature flag service (e.g., LaunchDarkly)
from feature_flags import get_flag

USE_NEW_ARCHITECTURE = get_flag("use_new_architecture", default=False)
```

### Step 8: Validation in Production

Monitor these metrics after enabling:

**Error Rates**
- HTTP 5xx errors
- Database connection errors
- Embedding generation failures

**Performance Metrics**
- API response times (p50, p95, p99)
- Database query latency
- Embedding generation time

**Business Metrics**
- Successful ingestions per hour
- Search queries per hour
- User-facing error rate

**Alerting Thresholds:**
- Error rate increase > 5% → Investigate
- Error rate increase > 10% → Consider rollback
- Latency increase > 20% → Investigate
- Latency increase > 50% → Consider rollback

---

## Feature Flag Usage

### Environment Variable

The `USE_NEW_ARCHITECTURE` environment variable controls which implementation is used:

```bash
# Enable new architecture (default for new deployments)
USE_NEW_ARCHITECTURE=true

# Use legacy implementation (fallback)
USE_NEW_ARCHITECTURE=false

# Not set - defaults to true
# USE_NEW_ARCHITECTURE=
```

### Application Startup

The feature flag is checked during application startup:

```python
# app/main.py
from app.infrastructure.config import get_settings

settings = get_settings()
USE_NEW_ARCHITECTURE = settings.use_new_architecture

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("🔧 Application startup...")
    
    if USE_NEW_ARCHITECTURE:
        logger.info("🔌 Initializing dependency injection container...")
        initialize_container(include_adapters=True)
        logger.info("✅ DI container initialized with all adapters")
    else:
        logger.info("⚠️  Using legacy architecture (USE_NEW_ARCHITECTURE=false)")
    
    yield
```

### Route Handling

Routes can conditionally use new or legacy implementation:

```python
@router.post("/ingest")
async def ingest_conversation(request: IngestRequest):
    if USE_NEW_ARCHITECTURE:
        # Use new architecture with DI
        use_case = resolve_service(IngestConversationUseCase)
        return await use_case.execute(request)
    else:
        # Use legacy implementation
        return await legacy_ingest(request)
```

### Runtime Toggle (Advanced)

For advanced scenarios, support runtime toggling:

```python
# Feature flag service integration
class FeatureFlagService:
    def is_enabled(self, flag_name: str, user_id: str = None) -> bool:
        """Check if feature is enabled for user."""
        # Check external feature flag service
        return feature_service.check(flag_name, user_id)

# Use in routes
@router.post("/ingest")
async def ingest_conversation(request: IngestRequest, user_id: str = None):
    use_new = feature_flags.is_enabled("use_new_architecture", user_id)
    
    if use_new:
        # New architecture
        ...
    else:
        # Legacy
        ...
```

---

## Breaking Changes

### ✅ No Breaking Changes in Phase 3

Phase 3 is designed to be **100% backward compatible**:

- ✅ **API Contracts Unchanged**: All endpoints maintain same request/response format
- ✅ **Data Model Unchanged**: Database schema remains identical
- ✅ **Configuration Compatible**: Existing environment variables still work
- ✅ **Client Compatibility**: No client-side changes required

### Non-Breaking Changes

These changes are internal and don't affect external consumers:

**1. Internal Architecture**
- Added adapter layer
- Added DI container
- Refactored domain and application layers
- **Impact:** None to external clients

**2. New Configuration Options**
- `USE_NEW_ARCHITECTURE` (defaults to true)
- **Impact:** Optional, backward compatible

**3. New Dependencies**
- No new external service dependencies
- Additional Python packages (already in requirements.txt)
- **Impact:** None if using existing requirements.txt

**4. Logging Format**
- Enhanced structured logging with more context
- **Impact:** Log parsing tools may need updates (optional)

### Future Breaking Changes (Phase 4+)

These are planned for future phases and NOT in Phase 3:

- ⚠️ **API Versioning**: New v2 endpoints with improved schemas
- ⚠️ **Authentication**: Required authentication on all endpoints
- ⚠️ **Rate Limiting**: Request rate limits enforced
- ⚠️ **Webhook Changes**: Modified webhook payload format

---

## Rollback Procedures

### Immediate Rollback (Feature Flag)

**Fastest rollback method - use in emergencies:**

```bash
# 1. Set feature flag to false
export USE_NEW_ARCHITECTURE=false

# 2. Restart application
./start-dev.sh

# Or with Docker
docker-compose restart mcp-backend

# 3. Verify rollback
curl http://localhost:8000/health
# Check logs for: "Using legacy architecture"
```

**Downtime:** ~10-30 seconds (application restart)

### Rollback via Configuration Update

**For containerized deployments:**

```bash
# 1. Update docker-compose.yml
services:
  mcp-backend:
    environment:
      - USE_NEW_ARCHITECTURE=false

# 2. Restart service
docker-compose up -d mcp-backend

# 3. Verify
docker-compose logs mcp-backend | grep "architecture"
```

**Downtime:** ~10-30 seconds (container restart)

### Rollback via Deployment

**For Kubernetes/cloud deployments:**

```bash
# 1. Update deployment config
kubectl set env deployment/mcp-backend USE_NEW_ARCHITECTURE=false

# 2. Rollout
kubectl rollout restart deployment/mcp-backend

# 3. Monitor rollout
kubectl rollout status deployment/mcp-backend

# 4. Verify
kubectl logs -l app=mcp-backend | grep "architecture"
```

**Downtime:** Zero (rolling restart)

### Rollback via Git

**If feature flag method doesn't work:**

```bash
# 1. Revert to commit before Phase 3
git revert <phase3-commit-hash>

# 2. Rebuild and deploy
docker-compose build
docker-compose up -d

# 3. Verify
curl http://localhost:8000/health
```

**Downtime:** ~2-5 minutes (rebuild + restart)

### Data Rollback

**Phase 3 does NOT require data migration**, so no data rollback needed.

If you need to rollback database changes from testing:

```bash
# Restore from backup
pg_restore -U user -d mcp_db /path/to/backup.sql

# Or use PITR (Point-in-Time Recovery)
# Follow your PostgreSQL backup/restore procedures
```

### Post-Rollback Checklist

After rollback, verify:

- [ ] Application starts successfully
- [ ] Health check endpoint returns 200
- [ ] Ingestion endpoint works
- [ ] Search endpoint works
- [ ] No error spikes in logs
- [ ] Database connections are healthy
- [ ] Embedding generation works

---

## Troubleshooting

### Issue 1: DI Container Initialization Fails

**Symptoms:**
```
ERROR: Failed to initialize DI container
KeyError: <class 'IEmbeddingService'>
```

**Cause:** Embedding service not registered properly

**Solution:**
```bash
# 1. Check embedding provider configuration
echo $EMBEDDING_PROVIDER

# 2. Verify OPENAI_API_KEY if using OpenAI
echo $OPENAI_API_KEY

# 3. Check logs for specific error
docker-compose logs mcp-backend | grep -A 10 "Failed to initialize"

# 4. Try with local provider
export EMBEDDING_PROVIDER=local
export EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Issue 2: Database Connection Errors

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Cause:** Database not accessible or configuration incorrect

**Solution:**
```bash
# 1. Verify database is running
docker-compose ps postgres

# 2. Test connection
psql -h localhost -p 5432 -U user -d mcp_db

# 3. Check DATABASE_URL format
# Correct: postgresql+psycopg://user:pass@host:port/db
# NOT: postgresql://... (old psycopg2 format)

# 4. Verify connection pooling settings
# Check app/database.py for pool_size, max_overflow
```

### Issue 3: Embedding Generation Fails

**Symptoms:**
```
EmbeddingError: Failed to generate embedding
```

**Cause:** Model not found or API key invalid

**Solution:**

**For Local Provider:**
```bash
# 1. Verify sentence-transformers is installed
pip show sentence-transformers

# 2. Test model download
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('all-MiniLM-L6-v2'); print('OK')"

# 3. Check disk space (models ~100MB)
df -h
```

**For OpenAI Provider:**
```bash
# 1. Verify API key is set
echo $OPENAI_API_KEY

# 2. Test API key
curl https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-ada-002","input":"test"}'

# 3. Check rate limits
# OpenAI returns 429 if rate limited
```

### Issue 4: Vector Search Returns No Results

**Symptoms:**
- Search endpoint returns empty results
- Previously ingested data not found

**Cause:** Embedding dimension mismatch or missing index

**Solution:**
```sql
-- 1. Check embedding column dimension
SELECT 
    chunk_text, 
    array_length(embedding, 1) as dim
FROM conversation_chunks 
LIMIT 5;

-- 2. Verify all embeddings are 1536-d
SELECT COUNT(*), array_length(embedding, 1) as dim
FROM conversation_chunks
GROUP BY dim;

-- 3. Check index exists
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'conversation_chunks';

-- 4. Rebuild index if needed
DROP INDEX IF EXISTS idx_chunk_embedding;
CREATE INDEX idx_chunk_embedding 
ON conversation_chunks 
USING ivfflat (embedding vector_l2_ops) 
WITH (lists = 100);
```

### Issue 5: Performance Degradation

**Symptoms:**
- Requests taking longer than expected
- Database connection pool exhausted

**Solution:**
```bash
# 1. Check database connection pool
# In app/database.py, verify settings:
# pool_size=5, max_overflow=10

# 2. Monitor active connections
psql -d mcp_db -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname='mcp_db';"

# 3. Check for slow queries
psql -d mcp_db -c "SELECT query, query_start, state FROM pg_stat_activity WHERE state = 'active';"

# 4. Verify embedding service is cached (singleton)
# Check logs for: "Loading embedding model" (should appear once)

# 5. Use batch operations
# Ensure using generate_embeddings_batch() for multiple texts
```

### Issue 6: Feature Flag Not Working

**Symptoms:**
- Setting `USE_NEW_ARCHITECTURE=false` but new architecture still used
- Or vice versa

**Solution:**
```bash
# 1. Verify environment variable is loaded
python -c "from app.infrastructure.config import get_settings; print(get_settings().use_new_architecture)"

# 2. Check .env file location
ls -la .env
# Should be in project root directory

# 3. Verify no shell export overrides
env | grep USE_NEW_ARCHITECTURE

# 4. Restart application after changing
docker-compose restart mcp-backend

# 5. Check application logs
docker-compose logs mcp-backend | grep "architecture"
```

### Issue 7: Import Errors

**Symptoms:**
```
ImportError: cannot import name 'IConversationRepository'
ModuleNotFoundError: No module named 'app.adapters'
```

**Cause:** Python path issues or missing __init__.py files

**Solution:**
```bash
# 1. Verify __init__.py files exist
find app -name __init__.py

# 2. Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# 3. Install in development mode
pip install -e .

# 4. Verify imports work
python -c "from app.domain.repositories import IConversationRepository; print('OK')"
```

### Getting Help

If issues persist:

1. **Check Logs:**
   ```bash
   docker-compose logs -f mcp-backend
   # Look for ERROR or WARNING messages
   ```

2. **Enable Debug Logging:**
   ```bash
   export LOG_LEVEL=DEBUG
   docker-compose restart mcp-backend
   ```

3. **Run Diagnostics:**
   ```bash
   python scripts/diagnose_system.py
   # Checks database, models, configuration
   ```

4. **Consult Documentation:**
   - [Configuration Guide](Configuration-Guide.md)
   - [Operations Guide](Operations-Guide.md)
   - [Architecture Documentation](Phase3-Architecture.md)

---

## Validation and Testing

### Pre-Migration Testing

Run these tests BEFORE enabling new architecture:

```bash
# 1. Unit tests
pytest tests/unit/ -v

# 2. Adapter tests
pytest tests/integration/database/ -v
pytest tests/integration/embedding/ -v

# 3. Use case tests
pytest tests/integration/usecases/ -v

# 4. End-to-end tests
pytest tests/integration/e2e/ -v
```

**All tests must pass before migration.**

### Post-Migration Testing

Run these tests AFTER enabling new architecture:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. API functionality tests
pytest tests/test_api.py -v

# 3. Ingestion workflow
pytest tests/integration/e2e/test_ingestion_workflow.py -v

# 4. Search workflow
pytest tests/integration/e2e/test_search_workflow.py -v

# 5. Performance benchmarks
python scripts/benchmark_all.py --output=results.json
```

### Regression Testing

Verify backward compatibility:

**Test 1: Existing Data Accessible**
```bash
# Query for conversations created before migration
curl "http://localhost:8000/conversations?skip=0&limit=10"

# Verify chunks are loaded correctly
# Verify embeddings are present
```

**Test 2: Search Functionality Unchanged**
```bash
# Search for content ingested before migration
curl "http://localhost:8000/search?q=<previous-query>&top_k=10"

# Compare results with expected results
```

**Test 3: API Contract Compatibility**
```bash
# Run API contract tests
pytest tests/contract/ -v

# Verify request/response schemas match
```

### Performance Testing

Compare performance metrics:

```bash
# Baseline (legacy architecture)
USE_NEW_ARCHITECTURE=false pytest tests/performance/ -v --benchmark-only

# New architecture
USE_NEW_ARCHITECTURE=true pytest tests/performance/ -v --benchmark-only

# Compare results
python scripts/compare_benchmarks.py
```

**Acceptance Criteria:**
- No performance regression > 10%
- All functionality tests pass
- No increase in error rates
- Search results quality maintained

---

## Success Criteria

Migration is considered successful when:

- [x] All adapters implemented and tested
- [ ] Feature flag toggles between architectures successfully
- [ ] All integration tests pass with new architecture
- [ ] No breaking changes to external APIs
- [ ] Performance metrics meet or exceed targets
- [ ] Error rates remain stable or improve
- [ ] Documentation is complete and accurate
- [ ] Team is trained on new architecture
- [ ] Rollback procedure is tested and documented
- [ ] Production deployment completed without issues

---

## Next Steps

After successful Phase 3 migration:

1. **Monitor Production** - Track metrics for 2-4 weeks
2. **Gather Feedback** - Collect team and user feedback
3. **Optimize Performance** - Fine-tune based on production data
4. **Phase 4 Planning** - Begin inbound adapters implementation
5. **Legacy Cleanup** - Remove feature flag and legacy code (after stability proven)

---

## Support and Resources

- **Architecture Documentation**: [Phase3-Architecture.md](Phase3-Architecture.md)
- **Configuration Guide**: [Configuration-Guide.md](Configuration-Guide.md)
- **Operations Guide**: [Operations-Guide.md](Operations-Guide.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/dmorav1/MCP-Demo/issues)
- **Team Contacts**: See project README for team member contacts

---

**Document Status**: Complete  
**Last Updated**: November 7, 2025  
**Maintained By**: Product Owner Agent
