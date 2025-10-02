# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Quick Start

#### Local Development
```bash
# Complete setup (database + API + optional Slack ingest)
./start-dev.sh all

# Setup only (database + dependencies)
./start-dev.sh setup

# Run servers only (assumes setup already done)
./start-dev.sh run

# Run MCP Inspector for testing MCP tools
./start-dev.sh inspect
```

#### Docker Deployment
```bash
# Build the Docker image
docker-compose build

# Start database and FastAPI backend
docker-compose up -d postgres mcp-backend

# For MCP server integration (optional)
docker-compose --profile mcp up -d

# Or run MCP server standalone for Claude Desktop integration
docker run --rm -it \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo_mcp-backend:latest mcp
```

### Running Tests
```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Install test dependencies
uv pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v tests/
```

### Quick API Testing
```bash
# Test main endpoints
./test-curl.sh

# Manual health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

### Dependency Management
```bash
# Add new dependency
echo "new-package" >> requirements.in
uv pip compile requirements.in -o requirements.txt
uv pip install -r requirements.txt

# Sync dependencies
uv pip install -r requirements.txt
```

## Architecture Overview

This is an **MCP (Model Context Protocol) backend** that ingests conversations from Slack, embeds them using local models, stores them in PostgreSQL with pgvector, and provides semantic search via both REST API and MCP tools.

### Core Components

**FastAPI Application** (`app/main.py`)
- REST API with endpoints for ingestion, search, and conversation management
- Handles CORS, dependency injection, and error handling
- Runs on port 8000 by default

**MCP Server** (`app/mcp_server.py`)
- Standalone MCP server that proxies requests to FastAPI endpoints
- Implements MCP tools: `search_conversations`, `ingest_conversation`, `get_conversations`, etc.
- Communicates with FastAPI via HTTP client

**Database Layer**
- PostgreSQL with pgvector extension for vector similarity search
- SQLAlchemy ORM models in `app/models.py`
- CRUD operations in `app/crud.py`
- Database runs in Docker container on port 5433

**Embedding Service** (`app/services.py`)
- Uses local `all-MiniLM-L6-v2` model (384 dimensions)
- Automatically pads embeddings to 1536 dimensions to match database schema
- Can be configured to use OpenAI embeddings alternatively

**Slack Integration** (`app/slack/`)
- Optional background worker that polls Slack channels
- Processes messages and posts to `/ingest` endpoint
- Configurable via environment variables

### Data Flow

1. **Ingestion**: Slack messages → API `/ingest` → ConversationProcessor → Chunks with embeddings → PostgreSQL
2. **Retrieval**: Query → Embedding → pgvector similarity search → Top-k chunks
3. **MCP Integration**: MCP tools → FastAPI endpoints → Database → Formatted responses

### Key Configuration

**Environment Variables** (`.env`)
```bash
DATABASE_URL=postgresql+psycopg://mcp_user:mcp_password@127.0.0.1:5433/mcp_db
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536
SLACK_BOT_TOKEN=...  # Optional for Slack integration
SLACK_CHANNEL=...    # Optional for Slack integration
ENABLE_SLACK_INGEST=true  # Optional
```

**Database Schema**
- `conversations` table: metadata (id, scenario_title, original_title, url, created_at)
- `conversation_chunks` table: chunked content with vector embeddings (1536-dimensional)
- IVFFlat index on embedding column for fast similarity search

## Common Development Tasks

### Adding New API Endpoints
1. Add route function to appropriate router in `app/routers/`
2. Define request/response schemas in `app/schemas.py`
3. Add CRUD operations in `app/crud.py` if needed
4. Include router in `app/main.py`

### Adding New MCP Tools
1. Add tool function with `@mcp_app.tool()` decorator in `app/mcp_server.py`
2. Use `httpx.AsyncClient` to call FastAPI endpoints
3. Handle errors and provide context logging
4. Update tool documentation with proper type hints

### Database Migrations
- The application uses SQLAlchemy metadata to create tables automatically
- For schema changes, modify models in `app/models.py`
- Consider data migration scripts for production deployments

### Testing Strategy
- Unit tests use mocked dependencies (embedding service, conversation processor)
- Integration tests can use the test database
- Mock services are configured in `tests/conftest.py`
- API tests use `httpx.AsyncClient` for async testing

## Important Notes

### Embedding Dimensions
- Local model outputs 384 dimensions but database expects 1536
- Service automatically pads embeddings unless `EMBEDDING_DIMENSION=384` is set
- To use native 384-dimensional embeddings, migrate database column to `vector(384)`

### Database Connection
- Uses `postgresql+psycopg` (not `postgresql`) for psycopg v3 compatibility
- Database runs on port 5433 (not 5432) to avoid conflicts
- Connection string must include `+psycopg` for proper driver selection

### Slack Integration
- Completely optional - API works independently
- Requires `SLACK_BOT_TOKEN` and `ENABLE_SLACK_INGEST=true`
- Background worker spawned by `start-dev.sh` if configured

### MCP Inspector Usage
- Use `./start-dev.sh inspect` to test MCP tools interactively
- Requires both database and FastAPI server to be running
- Opens browser interface for tool testing and debugging

### Docker Deployment
- **FastAPI + Database**: Use `docker-compose up -d postgres mcp-backend` for API-only deployment
- **MCP Server**: For Claude Desktop integration, run the MCP container separately with stdio transport
- **Networking**: Use `host.docker.internal` to connect between containers and host services
- **Environment**: Configure database connection and FastAPI URL via environment variables

### Claude Desktop Integration

#### Option 1: Persistent Service (Recommended)
Run MCP server as a persistent service and connect via docker exec:

```bash
# 1. Start the services
docker-compose --profile mcp up -d

# 2. Verify mcp-server is running
docker ps | grep mcp-server

# 3. Configure Claude Desktop
```

Create/edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mcp-demo": {
      "command": "docker",
      "args": [
        "exec", "-i", 
        "mcp-demo-mcp-server-1", 
        "python", "run_mcp_server_standalone.py"
      ]
    }
  }
}
```

**Advantages:**
- Persistent container reduces startup time
- Better resource management
- Consistent container state
- Easy debugging with `docker logs`

#### Option 2: On-Demand Container
Alternative configuration that starts container on each Claude Desktop connection:
```json
{
  "mcpServers": {
    "mcp-demo": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "DATABASE_URL=postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db",
        "-e", "FASTAPI_BASE_URL=http://host.docker.internal:8000",
        "--network", "host",
        "mcp-demo_mcp-backend:latest", "mcp"
      ]
    }
  }
}
```

**Note:** Option 1 is recommended for better performance and reliability.