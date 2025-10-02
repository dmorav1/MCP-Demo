# Testing Guide: Docker MCP Implementation

This guide shows you how to test the Docker MCP implementation step by step.

## Prerequisites

1. **Docker and Docker Compose installed**
2. **Services are up and running**

## Step 1: Clean Up and Rebuild

First, let's ensure we have the latest image with all our changes:

```bash
# Stop any running containers
docker-compose down

# Remove any cached images
docker rmi mcp-demo-mcp-backend:latest

# Rebuild with no cache to ensure all changes are included
docker-compose build --no-cache

# Start the services
docker-compose up -d postgres mcp-backend
```

## Step 2: Test the FastAPI Backend

### 2.1 Health Check
```bash
# Wait for services to start (about 10 seconds)
sleep 10

# Test the health endpoint
curl http://localhost:8000/health
```

**Expected output:**
```json
{"status":"healthy","service":"mcp-backend"}
```

### 2.2 API Documentation
```bash
# Open API docs in browser
open http://localhost:8000/docs

# Or test with curl
curl http://localhost:8000/docs
```

### 2.3 Test Basic API Endpoints
```bash
# Test conversations endpoint
curl "http://localhost:8000/conversations?limit=5"

# Test search endpoint (should work even with empty database)
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

## Step 3: Test MCP Server in Docker

### 3.1 Test MCP Server Startup
```bash
# Test that MCP server can start without errors
docker run --rm -i \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo-mcp-backend:latest mcp
```

**Expected:** The server should start without errors and wait for input.

### 3.2 Test MCP Protocol Communication

Open a new terminal and test JSON-RPC communication:

```bash
# Test tools listing
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | \
docker run --rm -i \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo-mcp-backend:latest mcp
```

**Expected output:** A JSON response listing available tools.

### 3.3 Test MCP Health Check Tool
```bash
# Test health check tool
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "health_check", "arguments": {}}}' | \
docker run --rm -i \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo-mcp-backend:latest mcp
```

**Expected:** A response showing the FastAPI backend health status.

## Step 4: Test with Sample Data

### 4.1 Ingest Test Conversation
```bash
# Add sample conversation via API
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Conversation",
    "content": "This is a test conversation about Docker and MCP implementation. It includes topics like containerization, MCP protocol, and service orchestration.",
    "scenario_title": "Docker Testing",
    "url": "https://example.com/test"
  }'
```

### 4.2 Test Search via MCP
```bash
# Search via MCP server
echo '{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search_conversations", "arguments": {"query": "Docker", "top_k": 3}}}' | \
docker run --rm -i \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo-mcp-backend:latest mcp
```

### 4.3 Get Conversations via MCP
```bash
# Get conversations via MCP
echo '{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_conversations", "arguments": {"limit": 5, "offset": 0}}}' | \
docker run --rm -i \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo-mcp-backend:latest mcp
```

## Step 5: Test Claude Desktop Integration

### 5.1 Create Claude Desktop Configuration

1. **Find your Claude Desktop config file:**
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add the MCP server configuration:**
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
        "mcp-demo-mcp-backend:latest", "mcp"
      ]
    }
  }
}
```

### 5.2 Test in Claude Desktop

1. **Restart Claude Desktop** after adding the configuration
2. **Start a new conversation** in Claude Desktop
3. **Try MCP commands:**
   - "Can you search for conversations about Docker?"
   - "Can you list the available conversations?"
   - "Can you check the health of the backend service?"

## Step 6: Troubleshooting Tests

### 6.1 Check Container Logs
```bash
# Check FastAPI backend logs
docker-compose logs mcp-backend

# Check PostgreSQL logs
docker-compose logs postgres
```

### 6.2 Debug Container Issues
```bash
# Enter the container for debugging
docker run --rm -it --entrypoint bash mcp-demo-mcp-backend:latest

# Test Python imports inside container
docker run --rm --entrypoint python mcp-demo-mcp-backend:latest -c "import mcp; print('MCP imported successfully')"

# Test database connection
docker run --rm -it \
  -e DATABASE_URL="postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db" \
  --entrypoint python \
  mcp-demo-mcp-backend:latest -c "
import os
from sqlalchemy import create_engine, text
url = os.environ['DATABASE_URL']
engine = create_engine(url)
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection successful')
"
```

### 6.3 Test Different Docker Modes
```bash
# Test FastAPI mode explicitly
docker run --rm -p 8001:8000 mcp-demo-mcp-backend:latest fastapi

# Test in another terminal
curl http://localhost:8001/health

# Test MCP mode
docker run --rm -i mcp-demo-mcp-backend:latest mcp
```

## Expected Results Summary

### ✅ **Successful FastAPI Backend:**
- Health endpoint returns `{"status":"healthy","service":"mcp-backend"}`
- API docs accessible at `http://localhost:8000/docs`
- Can ingest and search conversations

### ✅ **Successful MCP Server:**
- Starts without import errors
- Responds to `tools/list` with available tools
- Can execute tools and return responses
- Works with Claude Desktop integration

### ✅ **Full Integration:**
- Sample data can be ingested via API
- Same data can be searched via MCP
- Claude Desktop can interact with the service
- All components communicate correctly

## Common Issues and Solutions

### Issue: "ModuleNotFoundError: No module named 'mcp'"
**Solution:** Rebuild the Docker image without cache:
```bash
docker-compose build --no-cache
```

### Issue: "Cannot connect to database"
**Solution:** Check that PostgreSQL is running and healthy:
```bash
docker-compose ps
docker-compose logs postgres
```

### Issue: "Connection refused to FastAPI"
**Solution:** Ensure FastAPI backend is running and healthy:
```bash
curl http://localhost:8000/health
docker-compose logs mcp-backend
```

### Issue: Claude Desktop doesn't see the MCP server
**Solution:** 
1. Check the config file path is correct
2. Restart Claude Desktop after config changes
3. Ensure Docker services are running

## Performance Testing

### Test with Larger Dataset
```bash
# Ingest multiple conversations
for i in {1..10}; do
  curl -X POST "http://localhost:8000/ingest" \
    -H "Content-Type: application/json" \
    -d "{
      \"title\": \"Conversation $i\",
      \"content\": \"This is test conversation number $i about various topics including Docker, MCP, and system integration.\",
      \"scenario_title\": \"Test Scenario $i\"
    }"
done

# Test search performance
time curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "Docker MCP integration", "top_k": 5}'
```

This comprehensive testing guide ensures your Docker MCP implementation is working correctly at every level!