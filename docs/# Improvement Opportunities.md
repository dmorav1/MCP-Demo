# Improvement Opportunities

## Critical Issues

### 1. Vector Dimension Waste

**Current State**: Local embeddings padded from 384d to 1536d
```python
# 75% of each vector is zeros
embedding = [0.1, 0.2, ..., 0.384] + [0, 0, ..., 0]  # 384 + 1152 zeros
```

**Impact**:
- Storage: 4× larger than necessary (1536 floats vs. 384)
- Memory: Wasted RAM during search operations
- Index size: IVFFlat index unnecessarily large

**Solutions**:

**Option A**: Dynamic schema (recommended)
```python
# Detect model dimension at initialization
if settings.embedding_provider == "local":
    dimension = 384
elif settings.embedding_provider == "openai":
    dimension = 1536

# Create table with variable dimension
CREATE TABLE chunks (
    embedding vector({dimension})
);
```

**Option B**: Separate tables
```sql
CREATE TABLE chunks_local (
    embedding vector(384)
);

CREATE TABLE chunks_openai (
    embedding vector(1536)
);
```

**Option C**: Keep current approach but document trade-off
- Simplicity vs. efficiency
- Easy provider switching
- Acceptable for <100K conversations

**Recommendation**: Implement Option A with Alembic migration

### 2. Missing Authentication

**Current State**: All API endpoints are open
```bash
# Anyone can:
curl http://your-server.com/conversations  # List all
curl -X DELETE http://your-server.com/conversations/1  # Delete any
curl http://your-server.com/search?q=secrets  # Search everything
```

**Risks**:
- Data exposure
- Unauthorized data manipulation
- Resource abuse (expensive embedding calls)
- No audit trail

**Solutions**:

**API Key Authentication** (simple):
```python
# app/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# app/main.py
@app.get("/search", dependencies=[Depends(verify_api_key)])
async def search_conversations(...):
    ...
```

**OAuth2/JWT** (production):
```python
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify JWT token
    # Check user permissions
    # Return user object
    pass

@app.get("/search")
async def search_conversations(
    ...,
    current_user: User = Depends(get_current_user)
):
    # Filter results by user permissions
    ...
```

**Slack Channel Permissions** (advanced):
```python
# Respect Slack channel membership
# Only show conversations from channels user has access to
async def filter_by_slack_permissions(
    results: List[SearchResult],
    user_slack_id: str
) -> List[SearchResult]:
    user_channels = await get_user_channels(user_slack_id)
    return [r for r in results if r.channel_id in user_channels]
```

### 3. No Rate Limiting

**Attack Scenario**:
```bash
# Expensive operations
for i in {1..1000}; do
    curl "http://api.com/search?q=test&top_k=100"  # 1000 embedding + search calls
done
```

**Solution**: Implement rate limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/search")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def search_conversations(...):
    ...
```

## Performance Optimizations

### 4. Search Deduplication in Application Layer

**Current Approach**: Fetch extra results, deduplicate in Python
```python
# Fetches 10 chunks, keeps 5 conversations
query.limit(top_k * 2)
# Then Python deduplication
for chunk, conversation, distance in rows:
    if conversation.id not in seen:
        ...
```

**Better Approach**: Use PostgreSQL `DISTINCT ON`
```python
query = select(
    ConversationChunk,
    Conversation,
    ConversationChunk.embedding.l2_distance(query_embedding).label("distance")
).join(Conversation).distinct(
    Conversation.id  # Only first (best) chunk per conversation
).order_by(
    // filepath: docs/04-improvement-opportunities.md
# Improvement Opportunities

## Critical Issues

### 1. Vector Dimension Waste

**Current State**: Local embeddings padded from 384d to 1536d
```python
# 75% of each vector is zeros
embedding = [0.1, 0.2, ..., 0.384] + [0, 0, ..., 0]  # 384 + 1152 zeros
```

**Impact**:
- Storage: 4× larger than necessary (1536 floats vs. 384)
- Memory: Wasted RAM during search operations
- Index size: IVFFlat index unnecessarily large

**Solutions**:

**Option A**: Dynamic schema (recommended)
```python
# Detect model dimension at initialization
if settings.embedding_provider == "local":
    dimension = 384
elif settings.embedding_provider == "openai":
    dimension = 1536

# Create table with variable dimension
CREATE TABLE chunks (
    embedding vector({dimension})
);
```

**Option B**: Separate tables
```sql
CREATE TABLE chunks_local (
    embedding vector(384)
);

CREATE TABLE chunks_openai (
    embedding vector(1536)
);
```

**Option C**: Keep current approach but document trade-off
- Simplicity vs. efficiency
- Easy provider switching
- Acceptable for <100K conversations

**Recommendation**: Implement Option A with Alembic migration

### 2. Missing Authentication

**Current State**: All API endpoints are open
```bash
# Anyone can:
curl http://your-server.com/conversations  # List all
curl -X DELETE http://your-server.com/conversations/1  # Delete any
curl http://your-server.com/search?q=secrets  # Search everything
```

**Risks**:
- Data exposure
- Unauthorized data manipulation
- Resource abuse (expensive embedding calls)
- No audit trail

**Solutions**:

**API Key Authentication** (simple):
```python
# app/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# app/main.py
@app.get("/search", dependencies=[Depends(verify_api_key)])
async def search_conversations(...):
    ...
```

**OAuth2/JWT** (production):
```python
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify JWT token
    # Check user permissions
    # Return user object
    pass

@app.get("/search")
async def search_conversations(
    ...,
    current_user: User = Depends(get_current_user)
):
    # Filter results by user permissions
    ...
```

**Slack Channel Permissions** (advanced):
```python
# Respect Slack channel membership
# Only show conversations from channels user has access to
async def filter_by_slack_permissions(
    results: List[SearchResult],
    user_slack_id: str
) -> List[SearchResult]:
    user_channels = await get_user_channels(user_slack_id)
    return [r for r in results if r.channel_id in user_channels]
```

### 3. No Rate Limiting

**Attack Scenario**:
```bash
# Expensive operations
for i in {1..1000}; do
    curl "http://api.com/search?q=test&top_k=100"  # 1000 embedding + search calls
done
```

**Solution**: Implement rate limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/search")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def search_conversations(...):
    ...
```

## Performance Optimizations

### 4. Search Deduplication in Application Layer

**Current Approach**: Fetch extra results, deduplicate in Python
```python
# Fetches 10 chunks, keeps 5 conversations
query.limit(top_k * 2)
# Then Python deduplication
for chunk, conversation, distance in rows:
    if conversation.id not in seen:
        ...
```

**Better Approach**: Use PostgreSQL `DISTINCT ON`
```python
query = select(
    ConversationChunk,
    Conversation,
    ConversationChunk.embedding.l2_distance(query_embedding).label("distance")
).join(Conversation).distinct(
    Conversation.id  # Only first (best) chunk per conversation
).order_by(
    