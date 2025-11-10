# MCP RAG Demo - Phase 4 Complete

A production-ready Model Context Protocol (MCP) backend service implementing hexagonal architecture with RAG (Retrieval-Augmented Generation) capabilities using LangChain for intelligent question answering.

## 🎉 Phase 4: LangChain RAG Integration - Complete

Phase 4 implements the RAG service with full LangChain integration, enabling AI-powered question answering over your conversational data.

### Key Features

- ✅ **Hexagonal Architecture** - Complete domain, application, and adapter layers
- ✅ **RAG Service** - Full LangChain integration for question answering
- ✅ **Multiple LLM Providers** - OpenAI, Anthropic, and local model support
- ✅ **Streaming Responses** - Real-time answer generation
- ✅ **Conversation Memory** - Multi-turn conversational context
- ✅ **Source Citations** - Answers include references to source material
- ✅ **Multiple Embedding Providers** - Local (sentence-transformers), OpenAI, FastEmbed, LangChain
- ✅ **Dependency Injection** - Fully configured DI container with automatic wiring
- ✅ **Repository Pattern** - Clean data access with transaction support
- ✅ **Configuration-Driven** - Runtime provider selection via environment variables
- ✅ **Response Caching** - In-memory caching with TTL for performance
- ✅ **Token Tracking** - Monitor LLM usage and costs
- ✅ **100% Test Coverage** - Comprehensive unit tests with mocked dependencies
- ✅ **Production Ready** - Comprehensive error handling, logging, and monitoring

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              PRESENTATION LAYER                          │
│         FastAPI REST API + MCP Server                    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│             APPLICATION LAYER                            │
│    Use Cases: Ingest, Search, RAG Service               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│               DOMAIN LAYER                               │
│    Entities, Value Objects, Port Interfaces              │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│           ADAPTER LAYER (Phase 3)                        │
│  • Repository Adapters (PostgreSQL + pgvector)           │
│  • Embedding Service Adapters (Local/OpenAI/FastEmbed)  │
│  • Dependency Injection Container                        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│            INFRASTRUCTURE                                │
│    PostgreSQL + pgvector, OpenAI API                     │
└─────────────────────────────────────────────────────────┘
```

## Core Features

- **FastAPI** REST API with automatic OpenAPI documentation
- **RAG Service** - LangChain-powered question answering with source citations
- **Multiple LLM Providers** - OpenAI GPT-3.5/4, Anthropic Claude, local models
- **Streaming Support** - Real-time answer generation for better UX
- **Conversation Memory** - Maintain context across multiple turns
- **PostgreSQL** with **pgvector** extension for vector similarity search
- **Multiple embedding providers** - Local, OpenAI, FastEmbed, LangChain
- **Hexagonal architecture** with clean separation of concerns
- **Dependency injection** for testability and flexibility
- **Docker** containerized deployment
- **MCP protocol** support for Claude Desktop integration
- **Response Caching** - Reduce API calls and improve performance
- **Token Tracking** - Monitor usage and costs
- Conversation chunking and embedding generation
- Comprehensive test suite (41+ unit tests)

## Dependencies & Prerequisites

### System Requirements

- **Python 3.11+** (recommended) or Python 3.10+
- **Docker & Docker Compose** (for PostgreSQL container)
- **OpenAI API key** (for embeddings generation)

### Required System Dependencies

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Install uv (fast Python package manager)
brew install uv

# Install Docker Desktop
brew install --cask docker
```

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Docker
sudo apt install docker.io docker-compose

# Add user to docker group
sudo usermod -a -G docker $USER
```

#### Windows
- Install Python 3.11 from [python.org](https://www.python.org/downloads/)
- Install uv from [astral.sh/uv](https://astral.sh/uv/) or via PowerShell: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)

### Python Dependencies

The project uses **uv** as the modern, fast Python package manager for dependency management and **psycopg 3** (not psycopg2) for PostgreSQL connectivity with Python 3.13 compatibility:

#### Dependency Management with uv
- `requirements.in`: Declares high-level dependencies
- `requirements.txt`: Generated by uv with pinned versions and transitive dependencies
- `uv.lock`: Lock file for deterministic builds (if present)

```bash
# Core dependencies (managed via requirements.in and compiled with uv)
fastapi==0.104.1          # Web framework
uvicorn==0.24.0           # ASGI server
sqlalchemy==2.0.23        # ORM
psycopg[binary]==3.1.20   # PostgreSQL adapter (Python 3.13 compatible)
pgvector==0.2.4           # Vector similarity search
pydantic==2.5.0           # Data validation
openai==1.3.7             # OpenAI API client
alembic==1.13.1           # Database migrations
```

#### Working with Dependencies
```bash
# Add a new dependency
echo "new-package" >> requirements.in
uv pip compile requirements.in -o requirements.txt

# Install/sync all dependencies
uv pip install -r requirements.txt

# Or use uv pip directly for quick installs
uv pip install package-name
```

### Database Requirements

- **PostgreSQL 12+** with **pgvector extension**
- The project uses Docker to provide this automatically

### Environment Setup

1. **OpenAI API Key**: Required for embeddings generation
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Generate an API key from the dashboard
   - Add to `.env` file as `OPENAI_API_KEY`

2. **Database Configuration**: 
   - Uses `postgresql+psycopg://` connection string format
   - Configured automatically via Docker Compose

### Quick Dependency Check

Before running `start-dev.sh`, verify you have:

```bash
# Check Python version (should be 3.10+)
python3 --version

# Check if uv is installed
uv --version

# Check if Docker is running
docker --version
docker-compose --version

# Check if OpenAI API key is set (after creating .env)
grep OPENAI_API_KEY .env
```

## Quick Start

### Using the Development Script (Recommended)

The easiest way to get started is using the provided `start-dev.sh` script:

```bash
# Navigate to the project directory
cd mcp-backend

# Make the script executable (if needed)
chmod +x start-dev.sh

# Run the development setup script
./start-dev.sh
```

**What the script does:**
1. Creates a Python 3.11 virtual environment (if not exists)
2. Activates the virtual environment
3. Installs all Python dependencies using uv from `requirements.txt`
4. Starts PostgreSQL container with Docker Compose
5. Waits for database to be ready
6. Starts the FastAPI development server

**Prerequisites for start-dev.sh:**
- Python 3.11+ installed on your system
- uv package manager installed
- Docker and Docker Compose running
- `.env` file with valid OpenAI API key

### Enabling OpenAI Chat (LLM Answers)

The chat gateway supports real LLM answers when an `OPENAI_API_KEY` is present. Without it you will see a clearly marked fallback answer like:

`(Fallback answer) LLM unavailable and no context found. Please configure OPENAI_API_KEY or ingest more data.`

To enable real answers:

```bash
export OPENAI_API_KEY=sk-your-key
# Optional: choose a model (defaults to gpt-4o-mini)
export CHAT_MODEL=gpt-4o-mini
docker compose up -d --build
```

Hot reload: If the backend is already running you can inject a key without rebuild:
```bash
docker compose exec mcp-backend bash -c 'export OPENAI_API_KEY=sk-your-key && curl -s http://localhost:8000/chat/health'
```
The gateway lazily initializes the OpenAI client, so subsequent `/chat/ask` calls use the LLM path automatically.

If the key is invalid or a provider error occurs, a fallback summary of top semantic matches is returned instead of a hard error.


## RAG Service Quick Start

The RAG (Retrieval-Augmented Generation) service provides intelligent question answering over your conversational data.

### Basic Usage

```python
from app.application.rag_service import RAGService
from app.infrastructure.config import get_rag_config
from app.infrastructure.container import container

# Initialize service
rag_service = RAGService(
    vector_search_repository=container.vector_search_repository(),
    embedding_service=container.embedding_service(),
    config=get_rag_config()
)

# Ask a question
result = await rag_service.ask("What is Python used for?")

print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Sources: {len(result['sources'])}")
```

### Configuration

Add to your `.env` file:

```bash
# RAG Configuration
RAG__PROVIDER=openai              # Options: openai, anthropic, local
RAG__MODEL=gpt-3.5-turbo
RAG__OPENAI_API_KEY=sk-your-key
RAG__TEMPERATURE=0.7
RAG__TOP_K=5                       # Number of context chunks
RAG__ENABLE_STREAMING=true
RAG__ENABLE_CACHE=true
RAG__ENABLE_CONVERSATION_MEMORY=true
```

### Features

- **Simple Q&A**: Ask questions and get answers with source citations
- **Conversational**: Multi-turn conversations with context memory
- **Streaming**: Real-time answer generation
- **Multiple Providers**: Switch between OpenAI, Anthropic, or local models
- **Caching**: Automatic response caching for performance
- **Token Tracking**: Monitor API usage and costs

### Example: Conversational Q&A

```python
# Start a conversation
conversation_id = "user-session-123"

# Ask follow-up questions with context
result1 = await rag_service.ask_with_context(
    query="What is Python?",
    conversation_id=conversation_id
)

result2 = await rag_service.ask_with_context(
    query="Who created it?",  # Context is maintained
    conversation_id=conversation_id
)
```

### Documentation

- **[Complete Usage Guide](docs/RAG_SERVICE_USAGE.md)** - Comprehensive documentation
- **[Configuration Reference](docs/Configuration-Guide.md)** - All configuration options
- **[Architecture](docs/Phase3-Architecture.md)** - System design details

### Testing

Run the comprehensive test suite:

```bash
# Run RAG service unit tests (41 tests)
pytest tests/test_rag_service.py -v

# Run all tests
pytest tests/ -v
```

All tests use mocked LLM responses to avoid API calls.


### Manual Setup

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (for embeddings)

### Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   cd mcp-backend
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. The API will be available at `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

## API Endpoints

### POST /ingest
Ingest a new conversation into the database.

**Request Body:**
```json
{
  "scenario_title": "Customer Support Chat",
  "original_title": "Help with Product Issue",
  "url": "https://example.com/chat/123",
  "messages": [
    {
      "author_name": "Customer",
      "author_type": "human",
      "content": "I'm having trouble with my product...",
      "timestamp": "2023-01-01T12:00:00Z"
    },
    {
      "author_name": "Support Agent",
      "author_type": "human",
      "content": "I'd be happy to help you with that...",
      "timestamp": "2023-01-01T12:01:00Z"
    }
  ]
}
```

**Response:** `201 Created` with conversation details

### GET /search
Search for relevant conversations using semantic similarity.

**Parameters:**
- `q` (required): Search query string
- `top_k` (optional, default=5): Number of results to return (1-50)

**Example:**
```bash
curl "http://localhost:8000/search?q=product%20issue&top_k=10"
```

### GET /conversations
List all conversations with pagination.

**Parameters:**
- `skip` (optional, default=0): Number of conversations to skip
- `limit` (optional, default=100): Maximum conversations to return (1-1000)

### GET /conversations/{id}
Get a specific conversation by ID.

### DELETE /conversations/{id}
Delete a conversation and all its chunks.

## Development

### Local Development Setup

1. Install Python dependencies using uv:
   ```bash
   # Install using uv (recommended)
   uv pip install -r requirements.txt
   
   # Or traditional pip if uv is not available
   pip install -r requirements.txt
   ```

2. Set up PostgreSQL with pgvector:
   ```bash
   # Using Docker for PostgreSQL
   docker run --name postgres-pgvector \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=mcp_db \
     -p 5432:5432 \
     -d pgvector/pgvector:pg15
   ```

3. Run database migrations:
   ```bash
   # Execute the init-db.sql script
   psql -h localhost -U postgres -d mcp_db -f init-db.sql
   ```

4. Start the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Running Tests

```bash
# Install test dependencies using uv (recommended)
uv pip install pytest pytest-asyncio httpx

# Or using traditional pip
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### Database Schema

#### conversations table
- `id`: Primary key
- `scenario_title`: Optional scenario title
- `original_title`: Optional original title
- `url`: Optional URL reference
- `created_at`: Timestamp of creation

#### conversation_chunks table
- `id`: Primary key
- `conversation_id`: Foreign key to conversations
- `order_index`: Order of chunk in conversation
- `chunk_text`: Text content of the chunk
- `embedding`: Vector embedding (1536 dimensions)
- `author_name`: Name of message author
- `author_type`: Type of author (human/ai)
- `timestamp`: Timestamp of the message

## Configuration

Environment variables (set in `.env` file):

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for embeddings
- `EMBEDDING_MODEL`: OpenAI embedding model (default: text-embedding-ada-002)
- `EMBEDDING_DIMENSION`: Embedding vector dimension (default: 1536)

## Production Deployment

1. Update the `.env` file with production values
2. Configure CORS origins in `app/main.py`
3. Set up proper SSL/TLS termination
4. Configure database backups
5. Monitor API usage and rate limits

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │────│   FastAPI API   │────│   PostgreSQL    │
│                 │    │                 │    │   + pgvector    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                │
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │   (Embeddings)  │
                       └─────────────────┘
```

 ```plantuml
@startuml
!theme vibrant

title Technical Problem Resolution Flow

skinparam sequence {
    ArrowColor #555
    ActorBorderColor #555
    LifeLineBorderColor #777
    ParticipantBorderColor #555
    ParticipantBackgroundColor #f8f8f8
    DatabaseBorderColor #555
    DatabaseBackgroundColor #f8f8f8
    ActorBackgroundColor #f8f8f8
}

actor "Client MCP + LLM" as Client
participant "Claude Desktop" as ClaudeDesktop
participant "Conversations (Backend)" as ConversationsBackend
participant "MCP (Backend)" as MCPBackend
database "Database" as DB
participant "Generic Backend" as GenericBackend

group Non-Deterministic Flow
    Client -> ClaudeDoctor: Reports "Blank text problem"
    activate ClaudeDoctor #1b20acff
    note right of ClaudeDoctor
        If there's a problem, I'll see
        if I have a response I can use.
        ---
        Tool RTA:
    end note

    ClaudeDesktop -> ConversationsBackend: Search Conversations History
    activate ConversationsBackend #a1d57eff
    ConversationsBackend --> ClaudeDoctor: Survey Query
    deactivate ConversationsBackend

    ClaudeDesktop -> ConversationsBackend: Send Query
    activate ConversationsBackend #a1d57eff
    ConversationsBackend --> ClaudeDoctor: Query Response
    deactivate ConversationsBackend

    ClaudeDesktop -> ConversationsBackend: Get Conversation ID
    activate ConversationsBackend #a1d57eff
    ConversationsBackend --> ClaudeDoctor: conversation_id
    deactivate ConversationsBackend

    note left of Client
        The problem could be...
    end note
    deactivate ClaudeDesktop
end

group Deterministic Flow
    note over MCPBackend #F9E79F
        Execute conversations
        of past technical problems
    end note

    MCPBackend -> DB: Consult conversations
    activate DB #85C1E9
    DB --> MCPBackend: Return conversations
    deactivate DB

    MCPBackend -> GenericBackend: Process data (cv,s,a,t)
    activate GenericBackend #F5B7B1
    note right of GenericBackend
        Search command in this vector:
        v,s,a,t,j...?
    end note
    GenericBackend --> MCPBackend: Prompt Response
    deactivate GenericBackend
end

@enduml

```


## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Troubleshooting

### Common Issues

#### psycopg2 / psycopg Compatibility Error

If you encounter errors like `ModuleNotFoundError: No module named 'psycopg2'`, this is a common issue with newer Python versions (3.13+):

**Problem:** The project uses psycopg 3 but SQLAlchemy is trying to use the old psycopg2 driver.

**Solution:** Ensure your database URL uses the correct format:
```bash
# Correct format for psycopg 3
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/database

# Incorrect format (will try to use psycopg2)
DATABASE_URL=postgresql://user:password@localhost:5432/database
```

**Why this happens:** 
- psycopg2-binary doesn't support Python 3.13+
- We use psycopg 3 (the modern PostgreSQL adapter) instead
- SQLAlchemy needs the `+psycopg` dialect specification to use the correct driver

#### Virtual Environment Python Version

The `start-dev.sh` script creates a virtual environment with Python 3.11 by default. If you need a different version:

```bash
# Edit start-dev.sh and change this line:
python3.11 -m venv venv

# To your preferred version, e.g.:
python3.10 -m venv venv
```

#### uv Installation Issues

If you encounter issues with uv:

```bash
# Install uv via curl (Unix/Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install uv via PowerShell (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip as fallback
pip install uv
```

#### Docker Permission Issues (Linux)

If you get permission errors with Docker:
```bash
sudo usermod -a -G docker $USER
# Then log out and log back in
```

#### OpenAI API Key Issues

Make sure your `.env` file has a valid OpenAI API key:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

# MCP Demo: Slack → Vector DB → Context-Augmented Answers

This project ingests messages from a Slack channel, chunks and embeds them, stores them in Postgres with pgvector, and retrieves the most relevant chunks to augment answers served via an MCP server.

## Architecture

- Slack Ingest Worker (spawned by `start-dev.sh`) reads channel messages via Slack SDK and posts them to the API `/ingest`.
- FastAPI service validates and processes the conversation:
  - ConversationProcessor chunks messages by speaker/size.
  - EmbeddingService generates embeddings:
    - Local model: `all-MiniLM-L6-v2` (384-d), padded to 1536 to match DB column `vector(1536)`.
    - OpenAI can be used alternatively if configured.
- Postgres + pgvector stores:
  - `conversations`
  - `conversation_chunks(embedding vector(1536))` with IVFFlat index.
- Retrieval:
  - `/search` embeds the query, pads to 1536, and uses pgvector similarity (`<=>`) to return top-k chunks.
  - MCP server uses those chunks to augment the prompt and answer user questions grounded in Slack conversations.

Diagram: see `docs/diagrams/ingest_and_retrieval.puml`.

## Data Model

- conversations
  - id, scenario_title, original_title, url, created_at
- conversation_chunks
  - id, conversation_id (FK), order_index, chunk_text, author_name, author_type, timestamp
  - embedding vector(1536), IVFFlat index (`vector_l2_ops`)

## Configuration (.env)

```
DATABASE_URL=postgresql+psycopg://<user>:<password>@127.0.0.1:5433/<db>
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536
SLACK_BOT_TOKEN=...
SLACK_CHANNEL=...
ENABLE_SLACK_INGEST=true
```

Notes:
- 127.0.0.1 (not 0.0.0.0) for local Docker access.
- Local model outputs 384 dims; service pads to 1536 to match DB. If you switch DB to `vector(384)`, remove padding by setting `EMBEDDING_DIMENSION=384` and migrating the column.

## Running Locally (macOS)

1) Install dependencies into the venv (NumPy pinned for Py3.11/macOS).
```
source .venv/bin/activate || python3 -m venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

2) Start Postgres and the API.
```
./start-dev.sh all
```

3) Verify health.
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

4) Ingest test data.
```
curl -s -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"scenario_title":"demo","original_title":"demo","url":"u","messages":[{"author_name":"user","author_type":"human","content":"hello world"}]}'
```

5) Retrieve conversations and chunks.
```
curl -s "http://localhost:8000/conversations?skip=0&limit=10" | jq .
```

6) Search (retrieval).
```
curl -s "http://localhost:8000/search?q=hello&top_k=3" | jq .
```

## MCP Integration

- The MCP server calls the `/search` endpoint with the user’s query.
- The API returns top-k chunks (id, text, author, timestamp, scores).
- MCP constructs an augmented prompt (question + retrieved chunks) and produces grounded answers.

## Troubleshooting

- Duplicate route warnings: ensure only one `/ingest` and one `/conversations` route is active.
- NameError logger/settings: every module that calls `logger.` must define `logger = get_logger(__name__)`; import `settings` where used.
- Embedding dimension mismatch:
  - Keep DB at 1536 and pad local vectors to 1536 (default here).
  - Or migrate DB to `vector(384)` if you want native 384-d local embeddings.
- NumPy errors with sentence-transformers:
  - Ensure `numpy>=1.26,<2.0` is installed in the venv used by `start-dev.sh`.

## Performance Notes

- IVFFlat index speeds similarity queries; tune `lists` per data volume.
- Use `selectinload` to eager-load chunks in list endpoints.
- Session factory sets `expire_on_commit=False` to avoid stale attribute issues during response building.

## MCP Server Docker Deployment

### Running the MCP Server in Docker

1. **Start all services including MCP server:**
   ```bash
   docker-compose up -d
   ```

2. **Verify MCP server is running:**
   ```bash
   curl http://localhost:3000/health
   ```

3. **Configure Claude Desktop:**
   
   **macOS/Linux:**
   Copy the configuration to Claude Desktop config directory:
   ```bash
   mkdir -p ~/.config/Claude
   cp claude_desktop_config.json ~/.config/Claude/config.json
   ```

   **Windows:**
   Copy to `%APPDATA%\Claude\config.json`:
   ```powershell
   New-Item -Path "$env:APPDATA\Claude" -ItemType Directory -Force
   Copy-Item claude_desktop_config_windows.json "$env:APPDATA\Claude\config.json"
   ```

4. **Restart Claude Desktop** to load the new configuration.

5. **Test the connection:**
   Open Claude Desktop and try asking: "Search for conversations about hello"

### Troubleshooting Docker MCP Server

**Connection refused:**
- Ensure all containers are running: `docker-compose ps`
- Check MCP server logs: `docker-compose logs mcp-server`
- Verify port 3000 is not in use: `netstat -an | grep 3000`

**SSE stream errors:**
- Check network connectivity between containers
- Verify FASTAPI_BASE_URL points to mcp-backend service
- Review logs: `docker-compose logs -f mcp-server`

**Claude Desktop not connecting:**
- Verify config.json is in the correct location
- Check that localhost:3000 is accessible from your machine
- Restart Claude Desktop completely (quit and reopen)

---

## 📚 Documentation

### Phase 3 Documentation (NEW)

Comprehensive documentation for the Phase 3 hexagonal architecture implementation:

- **[Phase 3 Architecture](docs/Phase3-Architecture.md)** - Complete architecture documentation with diagrams, design patterns, and implementation details
- **[Phase 3 Migration Guide](docs/Phase3-Migration-Guide.md)** - Step-by-step migration from legacy to new architecture with rollback procedures
- **[Configuration Guide](docs/Configuration-Guide.md)** - Complete reference for all environment variables and configuration options
- **[Operations Guide](docs/Operations-Guide.md)** - Deployment procedures, monitoring, incident response, and backup/recovery
- **[Phase 3 Release Notes](docs/Phase3-Release-Notes.md)** - What's new, improvements, known limitations, and upgrade instructions

### Additional Documentation

- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - General migration guide for hexagonal architecture
- **[DI Container Implementation](docs/DI_CONTAINER_IMPLEMENTATION.md)** - Dependency injection container implementation details
- **[DI Usage Examples](docs/DI_USAGE_EXAMPLES.md)** - Code examples for using the DI container
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Deployment instructions for various platforms
- **[Docker Setup](docs/DOCKER_SETUP_COMPLETE.md)** - Complete Docker setup guide
- **[Logging Guide](docs/LOGGING.md)** - Logging configuration and best practices
- **[Embedding Services](docs/embedding-services.md)** - Embedding provider comparison and configuration

### Architecture Documentation

- **[Phase 3 Outbound Adapters Design](docs/architecture/Phase3-Outbound-Adapters-Design.md)** - Detailed adapter layer design
- **[Phase 3 C4 Diagrams](docs/architecture/Phase3-C4-Diagrams.md)** - C4 architecture diagrams

### Product Documentation

- **[Phase 3 Product Requirements](docs/product/Phase3-Product-Requirements.md)** - Product requirements for Phase 3
- **[Phase 3 Acceptance Criteria](docs/product/Phase3-Acceptance-Criteria.md)** - Validation checklist
- **[Phase 3 Completion Summary](docs/product/PHASE3_COMPLETION_SUMMARY.md)** - Phase 3 completion report

### API Documentation

- **OpenAPI/Swagger:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

---

## 🚀 Quick Start

### Option 1: Using New Architecture (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/dmorav1/MCP-Demo.git
cd MCP-Demo

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings (default uses local embeddings)

# 3. Start services
./start-dev.sh all

# 4. Verify health
curl http://localhost:8000/health
# Should show: "architecture": "new"

# 5. Test ingestion
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d @sample-data.json

# 6. Test search
curl "http://localhost:8000/search?q=hello&top_k=5"
```

### Option 2: Using Legacy Architecture

```bash
# Set feature flag to false
echo "USE_NEW_ARCHITECTURE=false" >> .env

# Start services
./start-dev.sh all
```

---

## ⚙️ Configuration

### Embedding Providers

The system supports multiple embedding providers:

| Provider | Cost | Speed | Quality | Use Case |
|----------|------|-------|---------|----------|
| **local** (sentence-transformers) | $0 | 50ms | Good | Development, cost-sensitive |
| **openai** (text-embedding-ada-002) | $0.10/1M tokens | 100ms | Excellent | Production, best quality |
| **fastembed** (FastEmbed library) | $0 | 40ms | Good | Fast inference, lightweight |
| **langchain** (LangChain wrapper) | Varies | Varies | Varies | Future extensibility |

**Configuration:**

```bash
# Local provider (default, free)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536

# OpenAI provider (paid, best quality)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-your-key-here
```

See [Configuration Guide](docs/Configuration-Guide.md) for complete reference.

---

## 🧪 Testing

### Run All Tests

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html
```

### Run Specific Test Suites

```bash
# Repository adapter tests
pytest tests/integration/database/ -v

# Embedding service tests
pytest tests/integration/embedding/ -v

# End-to-end workflow tests
pytest tests/integration/e2e/ -v

# Performance benchmarks
pytest tests/performance/ -v --benchmark-only
```

See [Testing Documentation](docs/Phase3-Migration-Guide.md#validation-and-testing) for more details.

---

## 🏗️ Project Structure

```
MCP-Demo/
├── app/
│   ├── domain/              # Phase 1: Domain layer
│   │   ├── entities.py      # Core business entities
│   │   ├── value_objects.py # Immutable value objects
│   │   ├── repositories.py  # Port interfaces
│   │   └── services.py      # Domain services
│   │
│   ├── application/         # Phase 2: Application layer
│   │   ├── ingest_conversation.py    # Ingestion use case
│   │   ├── search_conversations.py   # Search use case
│   │   ├── rag_service.py            # RAG use case
│   │   └── dto.py                    # Data transfer objects
│   │
│   ├── adapters/            # Phase 3: Adapter layer (NEW)
│   │   └── outbound/
│   │       ├── persistence/          # Database adapters
│   │       │   ├── sqlalchemy_conversation_repository.py
│   │       │   ├── sqlalchemy_chunk_repository.py
│   │       │   ├── sqlalchemy_vector_search_repository.py
│   │       │   └── sqlalchemy_embedding_repository.py
│   │       │
│   │       └── embeddings/           # Embedding service adapters
│   │           ├── local_embedding_service.py
│   │           ├── openai_embedding_service.py
│   │           ├── fastembed_embedding_service.py
│   │           ├── langchain_embedding_adapter.py
│   │           └── factory.py
│   │
│   ├── infrastructure/      # Infrastructure layer
│   │   ├── config.py        # Configuration management
│   │   └── container.py     # DI container
│   │
│   ├── routers/             # API routes
│   ├── main.py              # FastAPI application
│   ├── mcp_server.py        # MCP protocol server
│   └── models.py            # SQLAlchemy models (legacy)
│
├── docs/                    # Documentation
│   ├── Phase3-Architecture.md
│   ├── Phase3-Migration-Guide.md
│   ├── Configuration-Guide.md
│   ├── Operations-Guide.md
│   ├── Phase3-Release-Notes.md
│   └── architecture/        # Architecture diagrams
│
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   │   ├── database/        # Repository tests
│   │   ├── embedding/       # Embedding service tests
│   │   └── e2e/             # End-to-end tests
│   └── performance/         # Performance benchmarks
│
├── scripts/                 # Utility scripts
├── .env.example             # Configuration template
├── docker-compose.yml       # Docker services
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes following the hexagonal architecture patterns
4. Add tests for new functionality
5. Run tests: `pytest tests/ -v`
6. Commit changes: `git commit -m "Add feature"`
7. Push to fork: `git push origin feature/my-feature`
8. Open a pull request

### Code Standards

- Follow hexagonal architecture principles
- Use dependency injection for new components
- Add type hints to all functions
- Write tests for all new code
- Update documentation as needed
- Follow existing code style

---

## 📋 Roadmap

### ✅ Phase 1: Domain Layer (Complete)
- Core business entities and value objects
- Port interfaces for repositories and services
- Domain services for business logic

### ✅ Phase 2: Application Layer (Complete)
- Use cases for ingestion, search, and RAG
- Application-level orchestration
- DTOs for request/response handling

### ✅ Phase 3: Outbound Adapters (Complete)
- Repository adapters for PostgreSQL + pgvector
- Embedding service adapters (Local, OpenAI, FastEmbed, LangChain)
- Dependency injection container
- Configuration management

### 🚧 Phase 4: Inbound Adapters (Planned)
- API request/response adapters
- Input validation adapters
- Authentication adapters
- Rate limiting

### 📅 Phase 5: Advanced Features (Planned)
- Redis caching layer
- Circuit breaker pattern
- Async embedding generation
- Multi-database support

### 📅 Phase 6: Production Hardening (Planned)
- Distributed tracing (OpenTelemetry)
- Enhanced monitoring and alerting
- Performance optimizations
- Security enhancements

---

## 📄 License

This project is part of the MCP Demo repository. See the repository for license information.

---

## 🙋 Support

- **Documentation:** See [docs/](docs/) directory
- **Issues:** [GitHub Issues](https://github.com/dmorav1/MCP-Demo/issues)
- **Discussions:** [GitHub Discussions](https://github.com/dmorav1/MCP-Demo/discussions)

---

**Status:** Phase 3 Complete ✅  
**Last Updated:** November 7, 2025  
**Maintained By:** Product Owner Agent
