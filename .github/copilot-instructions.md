# MCP Demo Project Guide

## Business Context (BMAP Method)

**Purpose**: Enable AI agents to access and search conversational data from Slack channels through the Model Context Protocol (MCP), providing context-aware responses based on historical conversations.

**Business Value**: Transform scattered Slack conversations into searchable knowledge base for AI-augmented customer support, documentation, and decision-making.

## Architecture Overview

This is a **Model Context Protocol (MCP) server** that ingests Slack conversations, chunks and embeds them into PostgreSQL with pgvector, and serves semantic search via both REST API and MCP protocol.

### Core Components
- **FastAPI REST API** (`app/main.py`) - Primary service layer with CRUD operations
- **MCP Server** (`app/mcp_server.py`) - Standalone MCP protocol wrapper around FastAPI
- **Dual Embedding Support** (`app/services.py`) - Local `sentence-transformers` (384d→1536d padded) OR OpenAI embeddings
- **PostgreSQL + pgvector** - Vector similarity search with IVFFlat indexing
- **Slack Integration** (`app/slack/`) - Socket mode message ingestion

### Data Flow
1. Slack messages → `/ingest` endpoint → ConversationProcessor chunks by speaker/size
2. EmbeddingService generates vectors (local model padded to 1536d to match DB schema)
3. PostgreSQL stores conversations + chunks with `vector(1536)` embeddings
4. `/search` endpoint uses pgvector `<->` operator for L2 similarity
5. MCP server proxies FastAPI endpoints for AI agent consumption

## GitHub Copilot Integration

### Current AI-Friendly Features
- **Comprehensive type hints**: All functions use proper Python typing for better Copilot suggestions
- **Consistent patterns**: CRUD operations, dependency injection, async/await patterns
- **Clear naming conventions**: `ConversationCRUD`, `EmbeddingService`, `ConversationProcessor`
- **Structured schemas**: Pydantic models provide clear data contracts

### Copilot Chat Commands
```bash
# Ask Copilot about the codebase
@workspace How do I add a new search filter to the /search endpoint?
@workspace What's the difference between local and OpenAI embeddings?
@workspace Show me how to add a new MCP tool for conversation analytics
```

### AI-Assisted Development Patterns
- Use `# TODO:` comments for Copilot to suggest implementations
- Leverage docstring templates for consistent API documentation
- Follow the established async/await patterns for new endpoints

## Development Patterns

### Database & Embeddings
- **Critical**: Use `postgresql+psycopg://` URLs (not `postgresql://`) for psycopg 3 compatibility
- **Vector dimensions**: DB schema is fixed at `vector(1536)`. Local model outputs 384d but service pads to 1536
- **Search queries**: Use `<->` L2 distance operator with `vector_l2_ops` index
- **Session management**: Uses `expire_on_commit=False` and `selectinload()` for eager chunk loading

### Service Architecture 
- **Dependency injection**: All services instantiated with `get_db()` session dependency
- **CRUD pattern**: `ConversationCRUD(db)` encapsulates all database operations
- **Async embedding**: `EmbeddingService` handles both local and OpenAI providers asynchronously
- **Error handling**: Comprehensive logging with emoji prefixes (`🔍`, `✅`, `❌`) for easy scanning

### Configuration Management
```python
# app/config.py - Uses pydantic-settings with .env file
embedding_provider: "local" | "openai"  # defaults to local
embedding_dimension: 1536  # must match DB schema
database_url: postgresql+psycopg://...  # psycopg 3 format required
```

## Essential Commands

### Development Startup
```bash
./start-dev.sh          # Complete setup: venv, postgres, FastAPI, Slack ingest
./start-dev.sh setup    # Only venv + database
./start-dev.sh inspect  # Launch MCP Inspector for debugging
```

### Testing & Health Checks
```bash
# API health
curl http://localhost:8000/health

# Test ingestion
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"scenario_title":"test","messages":[{"content":"hello","author_name":"user"}]}'

# Vector search
curl "http://localhost:8000/search?q=hello&top_k=3"
```

### Database Management
```bash
# Direct postgres access
docker-compose exec postgres psql -U mcp_user -d mcp_db

# Check vector index
\d+ conversation_chunks  # Shows ivfflat index on embedding column
```

## Critical Implementation Details

### Embedding Pipeline
- **Local model**: `all-MiniLM-L6-v2` produces 384d vectors automatically padded to 1536d
- **Chunking strategy**: Split by speaker change OR 1000 char limit, preserving conversation flow
- **Search ranking**: Lower L2 distance = higher relevance (inverse of similarity score)

### Slack Integration
- **Socket Mode**: No webhooks required, uses `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN`
- **State management**: `.slack_ingest_state.json` tracks last processed message timestamp
- **Batch processing**: Configurable via `SLACK_BATCH_SIZE` and `SLACK_MIN_MESSAGES`

### MCP Protocol Layer
- **Proxy pattern**: MCP server makes HTTP calls to FastAPI backend (`FASTAPI_BASE_URL`)
- **Tool definitions**: Search, ingest, CRUD operations exposed as MCP tools
- **Error propagation**: HTTP errors converted to MCP exceptions with context

### Database Schema Considerations
- **CASCADE deletes**: Conversation deletion removes all associated chunks
- **Unique constraints**: `(conversation_id, order_index)` prevents duplicate chunks
- **Index tuning**: IVFFlat with `lists=100` - tune based on data volume

## Common Pitfalls

- **psycopg2 import errors**: Ensure `DATABASE_URL` uses `postgresql+psycopg://` format
- **Empty chunks in responses**: Use `selectinload(Conversation.chunks)` for eager loading
- **Vector dimension mismatch**: DB expects 1536d; local embeddings are padded automatically
- **NumPy version conflicts**: Pin `numpy>=1.26,<2.0` for sentence-transformers compatibility
- **Logging setup**: Every module must call `logger = get_logger(__name__)` before use