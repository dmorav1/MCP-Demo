# Docker MCP Server - Setup Complete ✅

## Summary

You've successfully configured the MCP server to run in Docker containers and be accessible from Claude Desktop!

## What Was Done

### 1. Docker Infrastructure
- **PostgreSQL** with pgvector extension (port 5433)
- **FastAPI Backend** with REST API (port 8000)
- **MCP Server** using stdio transport for Claude Desktop communication

### 2. Updated Files
- `docker-compose.yml` - Added MCP server service with stdio transport
- `requirements.in` - Added `openai`, `httpx`, and `mcp` dependencies
- `requirements.txt` - Compiled with all dependencies
- `app/mcp_server.py` - Fixed for newer MCP library compatibility
- `app/crud.py` - Fixed vector search query with proper type casting
- `run_mcp_server_standalone.py` - Simplified for stdio transport
- `start-dev.sh` - Added `.env` loading with `set -a && source .env && set +a`

### 3. Created Files
- `claude_desktop_config.json` - Configuration for Claude Desktop
- `DOCKER_MCP_SETUP.md` - Comprehensive setup and troubleshooting guide
- `test-docker-mcp.sh` - Automated test script

## Current Status

### ✅ Working
- PostgreSQL database with pgvector
- FastAPI backend API (http://localhost:8000)
- Conversation ingestion via `/ingest` endpoint
- Vector similarity search via `/search` endpoint
- MCP server running with stdio transport
- Claude Desktop configuration file created

### Commands Summary

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f mcp-server
docker-compose logs -f mcp-backend

# Test the setup
./test-docker-mcp.sh

# Stop services
docker-compose down
```

## Using with Claude Desktop

### 1. Copy Configuration (Already Done)
The configuration file is already in place at:
`~/Library/Application Support/Claude/claude_desktop_config.json`

### 2. Restart Claude Desktop
Completely quit and reopen Claude Desktop (not just close the window)

### 3. Verify Connection
In Claude Desktop settings, you should see the "conversational-data" MCP server listed

### 4. Test Questions
Try asking Claude:
- "Search for conversations about docker"
- "What conversations do we have?"
- "Get conversation with ID 1"
- "Ingest a new test conversation"

## Architecture

```
┌──────────────────┐
│  Claude Desktop  │
└────────┬─────────┘
         │ stdio (docker exec)
         │
┌────────▼─────────────────────────────────────┐
│           Docker Environment                  │
│                                               │
│  ┌────────────┐      ┌──────────────┐       │
│  │ MCP Server │─────▶│  FastAPI     │       │
│  │  (stdio)   │ HTTP │  Backend     │       │
│  └────────────┘      └──────┬───────┘       │
│                              │               │
│                       ┌──────▼────────┐      │
│                       │  PostgreSQL   │      │
│                       │   pgvector    │      │
│                       └───────────────┘      │
└───────────────────────────────────────────────┘
```

## Key Technical Details

### Database Connection
- **URL**: `postgresql://mcp_user:mcp_password@postgres:5432/mcp_db`
- **Format**: Uses `postgresql+psycopg://` for psycopg 3 compatibility
- **Vector Dimension**: 1536 (384d local embeddings padded to 1536)

### Embedding Pipeline
- **Provider**: Local `sentence-transformers` (all-MiniLM-L6-v2)
- **Fallback**: OpenAI embeddings if configured
- **Dimension**: 384d → padded to 1536d to match DB schema

### MCP Server
- **Transport**: stdio (for local Claude Desktop communication)
- **Tools**: search, ingest, get_conversations, get_conversation, delete_conversation, health_check
- **Backend URL**: `http://mcp-backend:8000` (internal Docker network)

## Troubleshooting Quick Reference

### Services won't start
```bash
docker-compose down
docker-compose up -d --build
docker-compose logs
```

### Backend not responding
```bash
curl http://localhost:8000/health
docker-compose restart mcp-backend
docker-compose logs mcp-backend
```

### MCP server issues
```bash
docker-compose logs -f mcp-server
docker exec -it mcp-demo-mcp-server-1 python run_mcp_server_standalone.py
```

### Search errors
```bash
# Check if embeddings are being generated
docker-compose exec mcp-backend python -c "from app.services import EmbeddingService; import asyncio; print(asyncio.run(EmbeddingService().generate_embedding('test')))"

# Check database
docker-compose exec postgres psql -U mcp_user -d mcp_db -c "SELECT COUNT(*) FROM conversation_chunks WHERE embedding IS NOT NULL;"
```

## Next Steps

### 1. Add More Data
Use the Slack integration to ingest real conversations:
```bash
# Set in .env
ENABLE_SLACK_INGEST=true
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=your-channel

# Restart with Slack ingest
./start-dev.sh all
```

### 2. Customize Search
Modify `app/crud.py` to add:
- Date range filtering
- Author filtering  
- Conversation type filtering
- Custom ranking algorithms

### 3. Add MCP Tools
Extend `app/mcp_server.py` with new tools:
- Conversation analytics
- Sentiment analysis
- Summary generation
- Export functionality

### 4. Production Deployment
- Add proper health checks to docker-compose
- Set up SSL/TLS termination
- Configure backup strategies
- Implement monitoring and alerting
- Use secrets management for credentials

## Documentation

- **Full Setup Guide**: `DOCKER_MCP_SETUP.md`
- **Main README**: `README.md`
- **GitHub Copilot Guide**: `.github/copilot-instructions.md`
- **BMAP Context**: `.copilot/bmap-context.md`

## Support

If you encounter issues:
1. Check `DOCKER_MCP_SETUP.md` for detailed troubleshooting
2. Review logs: `docker-compose logs`
3. Run tests: `./test-docker-mcp.sh`
4. Check the GitHub repository issues

---

**Status**: 🟢 All systems operational
**Last Updated**: October 2, 2025
