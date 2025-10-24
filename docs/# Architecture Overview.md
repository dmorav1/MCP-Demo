# Architecture Overview

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         External Systems                         │
├─────────────────────────────────────────────────────────────────┤
│  Slack API          OpenAI API (optional)      MCP Clients      │
└──────┬────────────────────┬────────────────────────┬────────────┘
       │                    │                        │
       │                    │                        │
┌──────▼────────────────────▼────────────────────────▼────────────┐
│                        Application Layer                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ Slack Socket    │    │   FastAPI REST   │                   │
│  │ Mode Listener   │───▶│   API Server     │◀────┐             │
│  └─────────────────┘    └──────────────────┘     │             │
│          │                       │                │             │
│          │              ┌────────▼────────┐       │             │
│          │              │  MCP Protocol   │       │             │
│          │              │  Server Wrapper │       │             │
│          │              └─────────────────┘       │             │
│          │                                        │             │
│          └────────────────┬───────────────────────┘             │
│                           │                                     │
│                  ┌────────▼─────────┐                          │
│                  │  Service Layer   │                          │
│                  ├──────────────────┤                          │
│                  │ • EmbeddingService (Local/OpenAI)          │
│                  │ • ConversationProcessor (Chunking)         │
│                  │ • ConversationCRUD (DB Operations)         │
│                  └────────┬─────────┘                          │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                  ┌─────────▼──────────┐
                  │  Data Layer        │
                  ├────────────────────┤
                  │  PostgreSQL 16     │
                  │  + pgvector 0.5.1  │
                  │                    │
                  │  Tables:           │
                  │  • conversations   │
                  │  • chunks          │
                  │                    │
                  │  Indexes:          │
                  │  • IVFFlat (L2)    │
                  └────────────────────┘
```

## Core Components

### 1. FastAPI REST API (`app/main.py`)
- **Purpose**: Primary HTTP interface for conversation management
- **Endpoints**: `/ingest`, `/search`, `/conversations/*`, `/health`
- **Responsibilities**:
  - Receive conversation data from Slack or manual ingestion
  - Coordinate chunking, embedding, and storage
  - Serve semantic search queries
  - Provide CRUD operations for conversations

### 2. MCP Server (`app/mcp_server.py`)
- **Purpose**: Expose FastAPI functionality via Model Context Protocol
- **Architecture**: Standalone server that proxies to FastAPI backend
- **Tools**: Search, ingest, get_conversation, list_conversations, delete_conversation
- **Communication**: HTTP requests to `FASTAPI_BASE_URL` (configurable)

### 3. Slack Integration (`app/slack/`)
- **Socket Mode Listener** (`app/slack/bot.py`): Real-time event processing
- **Ingest Processor** (`app/slack/tools/slack_ingest_processor.py`): Polling-based message fetching
- **State Management**: `.slack_ingest_state.json` tracks last processed timestamp
- **Flow**: Slack → Processor → `/ingest` endpoint → Database

### 4. Embedding Service (`app/services.py`)
- **Dual Provider Support**:
  - **Local**: `sentence-transformers/all-MiniLM-L6-v2` (384d → padded to 1536d)
  - **OpenAI**: `text-embedding-3-small` (native 1536d)
- **Padding Strategy**: Zero-pad local embeddings to match DB schema
- **Async Processing**: Batch embedding generation with asyncio

### 5. Conversation Processor (`app/services.py`)
- **Chunking Algorithm**:
  - Split on speaker changes
  - Maximum chunk size: 1000 characters
  - Preserve conversation flow and context
- **Output**: List of chunks with author metadata and order preservation

### 6. Data Layer (`app/models.py`)
- **Conversations Table**: Metadata, title, URL, timestamps
- **Chunks Table**: Content, embeddings (vector[1536]), order, foreign key to conversation
- **Indexes**: IVFFlat index on embeddings with `lists=100` parameter
- **Relationships**: One-to-many with CASCADE delete

## Data Flow

### Ingestion Pipeline

```
1. Slack Message Received
   ↓
2. slack_ingest_processor.py polls conversations_history
   ↓
3. Build ingest payload (JSON with messages array)
   ↓
4. POST /ingest endpoint
   ↓
5. ConversationProcessor.chunk_messages()
   │  • Split by speaker change
   │  • Limit chunk size to 1000 chars
   │  • Maintain conversation order
   ↓
6. EmbeddingService.embed_texts()
   │  • Local: sentence-transformers (384d)
   │  • Pad vectors: [384d] → [384d + 1152 zeros] = 1536d
   │  • OR OpenAI: direct 1536d vectors
   ↓
7. ConversationCRUD.create_conversation()
   │  • Insert into conversations table
   │  • Bulk insert chunks with embeddings
   │  • Commit transaction
   ↓
8. Return conversation_id and chunk count
```

### Search Pipeline

```
1. User Query "How to fix database errors?"
   ↓
2. GET /search?q=...&top_k=5
   ↓
3. EmbeddingService.embed_text(query)
   │  • Generate query vector (1536d)
   ↓
4. PostgreSQL vector similarity search
   │  • SELECT * FROM chunks
   │  • ORDER BY embedding <-> query_vector
   │  • LIMIT top_k
   │  • Uses IVFFlat index for performance
   ↓
5. ConversationCRUD.search_conversations()
   │  • Load associated conversation metadata
   │  • Calculate relevance scores
   │  • Deduplicate by conversation_id
   ↓
6. Return SearchResult[]
   │  • conversation_id, title, URL
   │  • matching chunk content
   │  • similarity score (0-1)
```

## Key Design Decisions

### 1. Vector Dimension Padding
**Problem**: Local model produces 384d vectors, but DB schema is fixed at 1536d (OpenAI standard)

**Solution**: Zero-pad local embeddings to 1536d in `EmbeddingService`

**Trade-off**: Wastes storage space (1152 zeros per vector) but maintains schema flexibility

### 2. Dual Embedding Providers
**Rationale**: 
- Local models = no API costs, faster for development
- OpenAI = higher quality embeddings for production

**Implementation**: Factory pattern with config-driven provider selection

### 3. MCP Server as Proxy
**Approach**: MCP server doesn't duplicate logic, it makes HTTP calls to FastAPI

**Benefits**:
- Single source of truth for business logic
- FastAPI can be used independently
- Easier testing and debugging

**Trade-off**: Extra network hop, requires both servers running

### 4. Polling vs. Socket Mode for Slack
**Current State**: Both implementations exist
- `slack_ingest_processor.py`: Polling-based (production)
- `bot.py` + `socket_reader.py`: Real-time Socket Mode (alternative)

**Recommendation**: See improvement opportunities doc

### 5. IVFFlat Index Strategy
**Configuration**: `lists=100` (hardcoded in migrations)

**Suitable for**: ~10K-100K vectors

**Not optimized for**: <10K vectors (exact search faster) or >1M vectors (need more lists)

## Technology Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI 0.115.6
- **Database**: PostgreSQL 16 with pgvector 0.5.1
- **ORM**: SQLAlchemy 2.0.36 with psycopg 3
- **Embeddings**: sentence-transformers 3.3.1 OR OpenAI API
- **Slack SDK**: slack-sdk 3.27.1
- **MCP Protocol**: mcp 1.1.2
- **Containerization**: Docker + Docker Compose

## Configuration Management

### Environment Variables (`.env`)
```bash
# Database
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db

# Embeddings
EMBEDDING_PROVIDER=local  # or "openai"
OPENAI_API_KEY=sk-...     # if provider=openai

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHANNEL=warchan-ai
SLACK_POLL_INTERVAL=120   # seconds

# MCP
FASTAPI_BASE_URL=http://localhost:8000
```

### Configuration Loading (`app/config.py`)
- Uses `pydantic-settings` for type-safe config
- Supports `.env` file and environment variables
- Validates required fields at startup
- Provides sensible defaults

## Deployment Architecture

### Development (`./start-dev.sh all`)
```
┌─────────────────────────────────────────┐
│  Host Machine (macOS/Linux)             │
├─────────────────────────────────────────┤
│                                         │
│  Docker Container: PostgreSQL (5432)    │
│                                         │
│  Python Process: FastAPI (8000)         │
│                                         │
│  Python Process: Slack Ingest (bg)      │
│                                         │
│  Python Process: MCP Server (optional)  │
│                                         │
└─────────────────────────────────────────┘
```

### Docker Compose (`docker-compose up`)
```
┌─────────────────────────────────────────┐
│  Docker Network: mcp-network            │
├─────────────────────────────────────────┤
│                                         │
│  Container: postgres (5432)             │
│  Container: mcp-backend (8000)          │
│  Container: frontend (3000)             │
│  Container: mcp-server (optional)       │
│                                         │
└─────────────────────────────────────────┘
```

## Security Considerations

### Current State
- ❌ No authentication on API endpoints
- ❌ No rate limiting
- ❌ Slack tokens stored in plaintext `.env`
- ❌ No HTTPS enforcement
- ❌ No input sanitization beyond Pydantic validation
- ✅ SQL injection protected by SQLAlchemy ORM
- ✅ Database credentials in environment variables

### Recommended for Production
See [Improvement Opportunities](04-improvement-opportunities.md#security-enhancements)