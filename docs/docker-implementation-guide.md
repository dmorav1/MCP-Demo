# Docker Implementation Guide

This document explains the step-by-step process of converting the MCP service from developer mode to a production-ready Docker deployment.

## Table of Contents
1. [Overview](#overview)
2. [Before vs After](#before-vs-after)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Key Files Modified](#key-files-modified)
5. [Docker Architecture](#docker-architecture)
6. [Testing the Implementation](#testing-the-implementation)
7. [Troubleshooting](#troubleshooting)

## Overview

The original MCP service required users to:
- Install Python and dependencies locally
- Run multiple processes manually
- Configure complex Claude Desktop settings with local paths

After Dockerization, users can:
- Run everything with simple Docker commands
- Use pre-built images without local setup
- Configure Claude Desktop with a single Docker command

## Before vs After

### Before (Developer Mode)
```bash
# User had to do this:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./start-dev.sh all

# Claude Desktop config:
{
  "mcpServers": {
    "mcp-demo": {
      "command": "python",
      "args": ["/full/path/to/run_mcp_server_standalone.py"],
      "cwd": "/full/path/to/project"
    }
  }
}
```

### After (Docker Mode)
```bash
# User now does this:
docker-compose up -d

# Claude Desktop config:
{
  "mcpServers": {
    "mcp-demo": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-e", "DATABASE_URL=...", "mcp-demo_mcp-backend:latest", "mcp"]
    }
  }
}
```

## Step-by-Step Implementation

### Step 1: Enhanced Dockerfile

**File:** `Dockerfile`

**What was added:**
```dockerfile
# NEW: Added curl for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \  # <-- ADDED THIS
    && rm -rf /var/lib/apt/lists/*

# NEW: Copy MCP server files
COPY run_mcp_server_standalone.py .  # <-- ADDED THIS
COPY docker-entrypoint.sh .          # <-- ADDED THIS

# NEW: Make entrypoint executable
RUN chmod +x docker-entrypoint.sh    # <-- ADDED THIS

# NEW: Flexible entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"] # <-- CHANGED FROM CMD
CMD ["fastapi"]                       # <-- DEFAULT MODE
```

**Why these changes:**
- **curl**: Required for Docker health checks
- **MCP files**: Need the standalone MCP server in the container
- **Entrypoint script**: Allows switching between FastAPI and MCP modes
- **Default to FastAPI**: Most common use case is the API server

### Step 2: Docker Entrypoint Script

**File:** `docker-entrypoint.sh` (NEW)

```bash
#!/bin/bash
MODE=${1:-fastapi}  # Get mode from command line, default to fastapi

case "$MODE" in
    "fastapi")
        echo "🚀 Starting FastAPI server..."
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000
        ;;
    "mcp")
        echo "🔧 Starting MCP server..."
        export FASTAPI_BASE_URL=${FASTAPI_BASE_URL:-http://host.docker.internal:8000}
        exec python run_mcp_server_standalone.py
        ;;
    *)
        echo "❌ Unknown mode: $MODE"
        exit 1
        ;;
esac
```

**Why this approach:**
- **Single Image**: One Docker image serves both purposes
- **Mode Selection**: Command-line argument determines behavior
- **Environment Defaults**: Sensible defaults for container networking
- **exec**: Proper signal handling for container shutdown

### Step 3: Updated Docker Compose

**File:** `docker-compose.yml`

**Key changes:**

```yaml
# ENHANCED: Backend service
mcp-backend:
  build: .
  ports:
    - "8000:8000"
  environment:
    # FIXED: Use proper psycopg connection string
    DATABASE_URL: postgresql+psycopg://mcp_user:mcp_password@postgres:5432/mcp_db
    # NEW: Environment-based configuration
    EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-local}
    EMBEDDING_MODEL: ${EMBEDDING_MODEL:-all-MiniLM-L6-v2}
    EMBEDDING_DIMENSION: ${EMBEDDING_DIMENSION:-1536}
  depends_on:
    postgres:
      condition: service_healthy  # Wait for DB to be ready
  command: ["fastapi"]  # Explicit mode selection

# NEW: Optional MCP server service
mcp-server:
  build: .
  environment:
    DATABASE_URL: postgresql+psycopg://mcp_user:mcp_password@postgres:5432/mcp_db
    FASTAPI_BASE_URL: http://mcp-backend:8000  # Internal networking
  depends_on:
    mcp-backend:
      condition: service_healthy
  command: ["mcp"]  # MCP mode
  profiles:
    - mcp  # Only start when explicitly requested
```

**Why these changes:**
- **Health Checks**: Ensure dependencies are ready
- **Environment Variables**: Flexible configuration
- **Service Dependencies**: Proper startup order
- **Profiles**: Optional services for different use cases

### Step 4: MCP Server Rewrite

**File:** `app/mcp_server.py`

**Major changes:**

```python
# OLD (fastmcp - didn't exist in installed MCP package):
from mcp.server.fastmcp import FastMCP, Context
mcp_app = FastMCP(name="mcp-demo")

@mcp_app.tool()
async def search_conversations(query: str) -> dict:
    # ...

# NEW (standard MCP server):
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("mcp-demo")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [Tool(name="search_conversations", ...)]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    # Route to appropriate function
```

**Why this rewrite was necessary:**
- **Package Compatibility**: The installed MCP package didn't have `fastmcp`
- **Standard API**: Using the official MCP server interface
- **Tool Registration**: Explicit tool definition and routing
- **Response Format**: TextContent for consistent output

### Step 5: Dependency Management

**Files:** `requirements.in` and `requirements.txt`

**Added dependencies:**
```text
openai>=1.0.0  # For OpenAI API integration
mcp>=1.0.0     # For MCP server functionality
```

**Why these were needed:**
- **OpenAI**: The service imports OpenAI even when using local embeddings
- **MCP**: Core package for MCP server functionality

### Step 6: Updated Documentation

**File:** `CLAUDE.md`

**Added sections:**
- Docker deployment instructions
- Claude Desktop configuration for Docker
- Environment variable explanations
- Networking considerations

## Docker Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                   │
│                                                             │
│  ┌─────────────────┐    ┌──────────────────────────────────┐ │
│  │   PostgreSQL    │    │         MCP Backend              │ │
│  │   (port 5432)   │◄───┤  Mode: fastapi (default)        │ │
│  │   Health: ✓     │    │  Port: 8000                      │ │
│  └─────────────────┘    │  Health: ✓                       │ │
│                         └──────────────────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              MCP Server (Optional)                      │ │
│  │  Mode: mcp                                              │ │
│  │  Transport: stdio                                       │ │
│  │  Profile: mcp                                           │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                Claude Desktop Integration                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  docker run --rm -i \                                  │ │
│  │    -e DATABASE_URL="..." \                             │ │
│  │    -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \ │
│  │    --network host \                                     │ │
│  │    mcp-demo_mcp-backend:latest mcp                      │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Testing the Implementation

### 1. Build and Start Services
```bash
docker-compose build
docker-compose up -d postgres mcp-backend
```

### 2. Verify FastAPI Backend
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","service":"mcp-backend"}
```

### 3. Test MCP Server
```bash
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | \
docker run --rm -i \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo-mcp-backend:latest mcp
```

### 4. Claude Desktop Integration
Add to `claude_desktop_config.json`:
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

## Troubleshooting

### Common Issues and Solutions

#### 1. "Module not found: mcp"
**Problem:** MCP package not installed in Docker image
**Solution:** Added `mcp>=1.0.0` to requirements.txt

#### 2. "Module not found: openai"
**Problem:** OpenAI package missing even when using local embeddings
**Solution:** Added `openai>=1.0.0` to requirements.txt

#### 3. "Cannot connect to database"
**Problem:** Wrong database URL format or container networking
**Solution:** Use `postgresql+psycopg://` and `host.docker.internal` for host networking

#### 4. "Health check failed"
**Problem:** FastAPI server not ready when MCP server starts
**Solution:** Added health checks and service dependencies

#### 5. "MCP server startup errors"
**Problem:** fastmcp module doesn't exist in installed MCP package
**Solution:** Rewrote to use standard MCP server interface

### Debugging Commands

```bash
# Check container logs
docker-compose logs mcp-backend

# Enter container for debugging
docker run --rm -it --entrypoint bash mcp-demo-mcp-backend:latest

# Test MCP server directly
docker run --rm -it mcp-demo-mcp-backend:latest mcp

# Check MCP package contents
docker run --rm --entrypoint python mcp-demo-mcp-backend:latest -c "import mcp; print(dir(mcp))"
```

## Benefits of This Implementation

1. **User Experience**: No Python setup required
2. **Consistency**: Same environment everywhere
3. **Distribution**: Easy to share and deploy
4. **Isolation**: Dependencies contained
5. **Scalability**: Can easily deploy to cloud platforms
6. **Maintenance**: Single Docker image to update

## Next Steps

To further improve this implementation:

1. **Multi-stage builds**: Reduce image size
2. **Security scanning**: Add vulnerability checks
3. **Helm charts**: Kubernetes deployment
4. **Docker Hub**: Publish official images
5. **CI/CD**: Automated building and testing