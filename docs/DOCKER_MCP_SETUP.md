# MCP Docker Setup Guide

## Overview

This guide explains how to run the MCP server in Docker and configure Claude Desktop to connect to it.

## Quick Start

### 1. Start All Services

```bash
# Start all Docker services
docker-compose up -d

# Or using the standalone docker-compose command
/usr/local/bin/docker-compose up -d

# Check status
docker-compose ps
```

### 2. Verify Services Are Running

```bash
# Check PostgreSQL
curl http://localhost:8000/health

# View MCP server logs
docker-compose logs -f mcp-server

# Check all services
docker-compose ps
```

Expected output:
- **postgres**: `Up (healthy)`
- **mcp-backend**: `Up` (port 8000)
- **mcp-server**: `Up`

### 3. Configure Claude Desktop

#### macOS/Linux

1. Copy the configuration file:
```bash
# macOS
mkdir -p ~/Library/Application\ Support/Claude
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
mkdir -p ~/.config/Claude
cp claude_desktop_config.json ~/.config/Claude/claude_desktop_config.json
```

2. Restart Claude Desktop completely (Quit and reopen)

3. Verify the connection in Claude Desktop's settings

#### Windows

```powershell
# Create directory if it doesn't exist
New-Item -Path "$env:APPDATA\Claude" -ItemType Directory -Force

# Copy configuration
Copy-Item claude_desktop_config.json "$env:APPDATA\Claude\claude_desktop_config.json"
```

Then restart Claude Desktop.

## Testing the Setup

### Test Ingestion

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_title": "Docker Test",
    "original_title": "Testing MCP Docker Setup",
    "url": "http://example.com/test",
    "messages": [
      {
        "author_name": "User",
        "author_type": "human",
        "content": "Hello from Docker!",
        "timestamp": "2025-01-15T10:00:00Z"
      },
      {
        "author_name": "Assistant",
        "author_type": "ai",
        "content": "Hello! How can I help you today?",
        "timestamp": "2025-01-15T10:00:05Z"
      }
    ]
  }'
```

### Test Search

```bash
curl "http://localhost:8000/search?q=hello&top_k=3" | python3 -m json.tool
```

### Test from Claude Desktop

Once configured, you can ask Claude:
- "Search for conversations about hello"
- "What conversations do we have in the database?"
- "Get conversation with ID 1"

## Architecture

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │ stdio
         ├─────────────────────┐
         │                     │
    ┌────▼──────────┐    ┌────▼─────────┐
    │  MCP Server   │───▶│  FastAPI     │
    │   (Docker)    │    │   Backend    │
    └───────────────┘    └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │  PostgreSQL  │
                         │  + pgvector  │
                         └──────────────┘
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs for all services
docker-compose logs

# Check specific service
docker-compose logs mcp-backend
docker-compose logs mcp-server
docker-compose logs postgres

# Restart specific service
docker-compose restart mcp-server
```

### Backend Connection Issues

```bash
# Verify backend is accessible
curl http://localhost:8000/health

# Check if database is accessible from backend
docker-compose exec mcp-backend env | grep DATABASE_URL
```

### MCP Server Not Connecting from Claude

1. Verify the Docker container is running:
```bash
docker ps | grep mcp-server
```

2. Check MCP server logs:
```bash
docker-compose logs -f mcp-server
```

3. Verify Claude Desktop config path:
```bash
# macOS
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
ls -la ~/.config/Claude/claude_desktop_config.json

# Windows
dir $env:APPDATA\Claude\claude_desktop_config.json
```

4. Ensure Claude Desktop is completely restarted (quit and reopen, not just close window)

### Database Issues

```bash
# Connect to database directly
docker-compose exec postgres psql -U mcp_user -d mcp_db

# Check tables
\dt

# Check conversation chunks
SELECT COUNT(*) FROM conversation_chunks;

# Check vector index
\d+ conversation_chunks
```

### Permission Issues

```bash
# If you get "permission denied" errors
sudo chown -R $USER:$USER .

# For Docker socket issues
sudo chmod 666 /var/run/docker.sock
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Stop specific service
docker-compose stop mcp-server
```

## Rebuilding After Code Changes

```bash
# Rebuild and restart all services
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build mcp-server
```

## Environment Variables

The following environment variables can be set in `.env`:

```bash
# Database
DATABASE_URL=postgresql://mcp_user:mcp_password@postgres:5432/mcp_db

# Embeddings
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536
EMBEDDING_PROVIDER=local  # or 'openai'

# Logging
LOG_LEVEL=WARN  # or INFO, DEBUG

# Slack (optional)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
SLACK_CHANNEL=your-channel
```

## Performance Tips

1. **Database Connection Pooling**: The backend uses SQLAlchemy with connection pooling
2. **Vector Index**: IVFFlat index is created automatically for fast similarity search
3. **Embedding Cache**: Local embeddings are cached by the sentence-transformers library
4. **Docker Resources**: Allocate sufficient memory to Docker (4GB+ recommended)

## Security Notes

- The MCP server uses stdio transport, which is secure for local communication
- Never expose port 5432 (PostgreSQL) publicly
- Keep your OpenAI API key secure in the `.env` file
- Use proper authentication for production deployments

## Next Steps

1. **Add More Data**: Ingest conversations from Slack using the Slack integration
2. **Customize Search**: Modify search parameters in `app/crud.py`
3. **Add Tools**: Extend MCP server with new tools in `app/mcp_server.py`
4. **Monitor**: Set up logging and monitoring for production use
