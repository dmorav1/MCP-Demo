# TECHNICAL_CONTEXT

## 1. High-Level Application Purpose
This application ingests real Slack conversation history, transforms it into a structured and vector-searchable knowledge base, and exposes it through:
- A FastAPI REST API for ingestion, querying, and CRUD operations over conversations.
- An MCP (Model Context Protocol) server that allows AI agents/tools to request contextual conversation data.
- A React-based frontend (chat/search UI) that enables users to search historical context and interact with the knowledge base.
It solves the problem of fragmented conversational knowledge by turning Slack threads into semantically searchable context that can power AI-assisted customer support, troubleshooting, and internal knowledge retrieval.

## 2. Technology Stack
- Programming Languages:
  - Python 3.11 (backend, MCP server)
  - TypeScript / JavaScript (frontend)
- Backend Framework:
  - FastAPI (REST API + dependency injection)
- MCP Layer:
  - Custom server wrapping FastAPI endpoints (app/mcp_server.py)
- Data & Storage:
  - PostgreSQL with pgvector extension (vector similarity search)
- Vector & Embeddings:
  - Local: sentence-transformers (all-MiniLM-L6-v2 → 384d padded to 1536d)
  - Remote (optional): OpenAI embeddings (1536d)
- Key Python Libraries:
  - sqlalchemy (ORM), psycopg (psycopg3 driver)
  - pgvector (SQLAlchemy integration)
  - pydantic / pydantic-settings
  - uvicorn
  - httpx / requests
  - slack_sdk (Slack ingestion)
- Frontend:
  - React 18 + react-scripts
  - Axios (API calls)
- Containerization & Orchestration:
  - Docker, docker-compose
- Other:
  - Logging: structured, emoji-tagged
  - Environment management: .env + pydantic settings

## 3. Service Breakdown & Responsibilities
### frontend-service (React)
- Provides user-facing chat/search UI.
- Calls backend REST endpoints: /search, /ingest, /conversations, /chat (if enabled).
- Runs dev server on port 3000 (mapped to 3001 externally).
- Not responsible for embedding or persistence logic.

### backend-service (FastAPI)
- Core API surface: ingestion (/ingest), search (/search), conversation CRUD (/conversations...), health (/health).
- Manages embedding pipeline via EmbeddingService.
- Owns ConversationCRUD logic (app/crud.py).
- Handles Slack ingestion transformation via ConversationProcessor.
- Exposes vector search with pgvector operators.
- Provides MCP compatibility layer base URL for the MCP server.

### mcp-server (Model Context Protocol layer)
- Wraps/bridges FastAPI endpoints into MCP tools (search, ingest, list, fetch, etc.).
- Allows AI agents to query conversation context programmatically.
- Lives in app/mcp_server.py (can be run standalone or integrated).
- Makes internal HTTP calls to FASTAPI_BASE_URL to stay decoupled.

### db-service (PostgreSQL + pgvector)
- Stores:
  - conversations (metadata)
  - conversation_chunks (content + vector embedding column vector(1536))
- Provides vector index (IVFFlat with L2 distance) for semantic search.
- Enforces relational integrity and cascading deletes.
- Requires correct database URL format: postgresql+psycopg://...

## 4. Core Data Flow
1. Slack messages are collected (batch or streaming) via Slack integration logic (socket mode; tokens from env).
2. Ingestion:
   - Client (Slack processor or manual POST) calls POST /ingest with scenario_title + messages.
   - ConversationProcessor chunks messages by speaker change or size threshold (≈1000 chars).
3. Embedding:
   - EmbeddingService selects provider:
     - Local: sentence-transformers model → 384d → zero-padded to 1536d.
     - OpenAI: direct 1536d vector.
   - Each chunk gets an embedding stored in conversation_chunks.embedding.
4. Persistence:
   - SQLAlchemy ORM writes Conversation + associated Chunks in a transaction.
5. Search:
   - User or agent calls GET /search?q=...&top_k=K.
   - Query text → embedding → pgvector similarity (L2 distance operator <->).
   - Results ranked (lower distance → higher relevance) and returned as structured payload.
6. MCP Access:
   - MCP server exposes similar functionality to external AI tooling, proxying the REST layer.
7. Frontend:
   - React UI calls backend endpoints to display conversation lists, perform semantic search, and (optionally) chat.

## 5. Local Setup and Execution
### Prerequisites
- Docker & docker-compose
- (Optional) OpenAI API Key for remote embeddings
- (Optional) Slack tokens (SLACK_BOT_TOKEN, SLACK_APP_TOKEN) for live ingestion

### Environment Variables (.env)
Minimum:
```
DATABASE_URL=postgresql+psycopg://mcp_user:mcp_password@postgres:5432/mcp_db
EMBEDDING_PROVIDER=local
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-...  (optional)
SLACK_BOT_TOKEN=xoxb-... (optional)
SLACK_APP_TOKEN=xapp-... (optional)
```

### Startup (Containers)
```
docker-compose build
docker-compose up -d
curl http://localhost:8000/health
```

### Verify
- Backend API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Frontend UI (if enabled): http://localhost:3001
- Database shell:
  ```
  docker-compose exec postgres psql -U mcp_user -d mcp_db
  ```

### Ingest Test
```
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"scenario_title":"demo","messages":[{"content":"Hello world","author_name":"user"}]}'
```

### Search Test
```
curl "http://localhost:8000/search?q=hello&top_k=3"
```

### Running MCP Server (Standalone Example)
```
python run_mcp_server_standalone.py
# or
python -m app.mcp_server
```

## 6. Key Files and Entrypoints
### Backend (app/)
- main.py: FastAPI app creation, router inclusion, health/search/conversation endpoints.
- crud.py: ConversationCRUD class and legacy wrapper functions.
- models.py: SQLAlchemy ORM models (Conversation, ConversationChunk) with vector field.
- schemas.py: Pydantic models for request/response contracts.
- services.py: EmbeddingService (local/OpenAI), ConversationProcessor, ContextFormatter.
- database.py: Engine creation, session management, test_connection logic.
- mcp_server.py: MCP protocol server bridging FastAPI endpoints.
- routers/ingest.py: Dedicated ingestion endpoint logic.
- logging_config.py: Centralized logging with emoji-format patterns.
- config.py: Settings management via pydantic-settings.
- run_mcp_server_standalone.py: Convenience bootstrap for MCP mode.

### Frontend (frontend/)
- Dockerfile: Builds React development environment.
- package.json: Dependency manifest (React, axios, etc.).
- src/index.tsx: React root entrypoint.
- src/App.* (if present): Main UI component (chat / search interface).
- .env (frontend-specific runtime overrides).

### Database / Infra
- docker-compose.yml: Defines postgres, backend, and frontend services (networks, healthchecks).
- init-db.sql (if present): Initializes extensions (e.g., CREATE EXTENSION IF NOT EXISTS vector).
- start-all.sh / start-all-fixed.sh: Orchestrated startup scripts (validation + dependency setup).

### Slack Integration (app/slack/)
- Modules for Slack socket ingestion, batching, and state persistence (.slack_ingest_state.json).

### MCP / Agent Integration
- app/mcp_server.py: Tool definitions + HTTP bridging.
- FASTAPI_BASE_URL environment variable: MCP server uses this to call REST API.

### Other
- requirements.txt: Python dependency pinning (fastapi, psycopg, pgvector, sentence-transformers, etc.).
- .env.example (if present): Template for environment variables.
- .github/copilot-instructions.md: AI-oriented architectural guidance.

---
All required sections have been provided. This document reflects the current architecture and operational model of the project.