# MCP Demo: Dockerized Conversation Intelligence Platform

A complete **Model Context Protocol (MCP)** implementation that ingests conversations, generates semantic embeddings, and provides intelligent search capabilities via both REST API and MCP tools. Now fully containerized with **Docker** and ready for **Claude Desktop** integration.

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** installed
- **OpenAI API Key** (for embeddings)
- **Claude Desktop** (for MCP integration)

### 1. Environment Setup
```bash
# Clone and navigate to project
git clone <repository-url>
cd MCP-Demo

# Copy and configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 2. Build and Start Services
```bash
# Build the Docker image
docker-compose build

# Start database and FastAPI backend
docker-compose up -d postgres mcp-backend

# Verify services are running
docker ps
```

### 3. Test the API
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Quick test ingestion
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_title": "Test Conversation",
    "original_title": "Demo",
    "url": "test",
    "messages": [
      {
        "author_name": "user",
        "author_type": "human",
        "content": "Hello, I need help with my account",
        "timestamp": "2023-12-01T10:00:00Z"
      }
    ]
  }'

# Search test
curl "http://localhost:8000/search?q=account%20help&top_k=5"
```

## 📋 MCP Integration with Claude Desktop

### Option 1: Persistent Service (Recommended)

**Step 1: Start MCP Server as Service**
```bash
# Start all services including MCP server
docker-compose --profile mcp up -d

# Verify mcp-server is running
docker ps | grep mcp-server
```

**Step 2: Configure Claude Desktop**

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

**Step 3: Restart Claude Desktop**

✅ **Advantages:**
- Persistent container reduces startup time
- Better resource management
- Consistent container state
- Easy debugging with `docker logs mcp-demo-mcp-server-1`

### Option 2: On-Demand Container

Alternative Claude Desktop configuration that starts container on each connection:
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

## 🔧 Available MCP Tools

Once configured, Claude Desktop will have access to these tools:

- **`search_conversations`** - Semantic search through conversation history
- **`ingest_conversation`** - Add new conversations to the database
- **`get_conversations`** - List all conversations with pagination
- **`get_conversation`** - Get specific conversation details
- **`delete_conversation`** - Remove conversations from database

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Claude Desktop │────│   MCP Server    │────│   FastAPI API   │
│  (MCP Client)   │    │  (Docker Exec)  │    │   (Backend)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   OpenAI API    │────│   PostgreSQL    │
                       │  (Embeddings)   │    │   + pgvector    │
                       └─────────────────┘    └─────────────────┘
```

### Core Components

**1. FastAPI Backend** (`app/main.py`)
- REST API with OpenAPI documentation
- Conversation ingestion and management
- Semantic search with OpenAI embeddings
- Runs in Docker container on port 8000

**2. MCP Server** (`app/mcp_server.py`)
- Standard MCP server implementation
- Proxies requests to FastAPI endpoints
- JSON-RPC over stdio transport
- Runs in separate Docker container

**3. Database Layer**
- PostgreSQL 15 with pgvector extension
- Vector similarity search (1536 dimensions)
- Automatic schema creation and indexing
- Runs in Docker container on port 5433

**4. Embedding Service**
- OpenAI `text-embedding-ada-002` model
- 1536-dimensional vectors
- Configurable embedding providers

## 📊 Data Flow

1. **Ingestion**: Messages → FastAPI `/ingest` → Conversation processing → Embeddings → PostgreSQL
2. **Retrieval**: Query → Embedding → pgvector similarity search → Top-k chunks
3. **MCP Integration**: MCP tools → FastAPI endpoints → Database → Formatted responses

## ⚙️ Configuration

### Environment Variables (`.env`)
```bash
# Database
DATABASE_URL=postgresql+psycopg://mcp_user:mcp_password@localhost:5432/mcp_db

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536

# MCP
MCP_TRANSPORT=stdio
FASTAPI_BASE_URL=http://mcp-backend:8000
```

### Docker Services

**postgres** - PostgreSQL with pgvector
- Image: `pgvector/pgvector:pg15`
- Port: `5433:5432`
- Data persistence via Docker volume

**mcp-backend** - FastAPI application
- Build: Dockerfile in project root
- Port: `8000:8000`
- Mode: `fastapi` (default)

**mcp-server** - MCP server (optional)
- Same image as mcp-backend
- Mode: `mcp`
- Profile: `mcp` (start with `--profile mcp`)

## 🛠️ Development

### Local Development with Docker
```bash
# Start development environment
docker-compose up -d postgres mcp-backend

# View logs
docker-compose logs -f mcp-backend

# Execute commands in running container
docker exec -it mcp-demo-mcp-backend-1 bash

# Run tests in container
docker exec mcp-demo-mcp-backend-1 pytest tests/
```

### Traditional Development (without Docker)
```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start services
./start-dev.sh all
```

### Adding Dependencies
```bash
# Add to requirements.in
echo "new-package==1.0.0" >> requirements.in

# Regenerate requirements.txt
uv pip compile requirements.in -o requirements.txt

# Rebuild Docker image
docker-compose build
```

## 🧪 Testing

### API Testing
```bash
# Run comprehensive test suite
./test-curl.sh

# Individual endpoint tests
curl http://localhost:8000/health
curl http://localhost:8000/conversations
curl "http://localhost:8000/search?q=test&top_k=5"
```

### MCP Testing
```bash
# Test MCP server directly
docker exec -i mcp-demo-mcp-server-1 python run_mcp_server_standalone.py

# Test with MCP Inspector
./start-dev.sh inspect
```

## 📁 Database Schema

### `conversations` table
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    scenario_title VARCHAR,
    original_title VARCHAR,
    url VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `conversation_chunks` table
```sql
CREATE TABLE conversation_chunks (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    order_index INTEGER,
    chunk_text TEXT,
    embedding vector(1536),
    author_name VARCHAR,
    author_type VARCHAR,
    timestamp TIMESTAMP
);

-- Vector similarity index
CREATE INDEX conversation_chunks_embedding_idx 
ON conversation_chunks USING ivfflat (embedding vector_l2_ops);
```

## 🚨 Troubleshooting

### Common Issues

**MCP Server Not Connecting**
```bash
# Check if container is running
docker ps | grep mcp-server

# Check container logs
docker logs mcp-demo-mcp-server-1

# Restart MCP service
docker-compose --profile mcp restart mcp-server
```

**Database Connection Issues**
```bash
# Check database is ready
docker exec mcp-demo-postgres-1 pg_isready -U mcp_user -d mcp_db

# Check network connectivity
docker exec mcp-demo-mcp-backend-1 curl -I http://postgres:5432
```

**Claude Desktop Configuration**
```bash
# Verify config file location (macOS)
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Check JSON syntax
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .
```

**OpenAI API Issues**
```bash
# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### Performance Optimization

**Database Tuning**
```sql
-- Adjust IVFFlat index for your data size
DROP INDEX conversation_chunks_embedding_idx;
CREATE INDEX conversation_chunks_embedding_idx 
ON conversation_chunks USING ivfflat (embedding vector_l2_ops) 
WITH (lists = 100);  -- Adjust lists based on data volume
```

**Container Resources**
```yaml
# Add to docker-compose.yml services
mcp-backend:
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '0.5'
```

## 🔄 Migration from Local Setup

If migrating from a local development setup:

1. **Export existing data** (if needed)
2. **Update environment variables** for Docker networking
3. **Rebuild containers** with new configuration
4. **Update Claude Desktop config** to use Docker commands
5. **Test MCP integration** thoroughly

## 📝 License

[Add your license information here]

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: See `CLAUDE.md` for detailed technical documentation
- **Examples**: Check `test-curl.sh` for API usage examples