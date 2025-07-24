# MCP Backend

A Model Context Protocol (MCP) backend service for storing and retrieving conversational data using PostgreSQL with pgvector for semantic search.

## Features

- **FastAPI** REST API with automatic OpenAPI documentation
- **PostgreSQL** with **pgvector** extension for vector similarity search
- **OpenAI embeddings** for semantic search capabilities
- **Docker** containerized deployment
- Conversation chunking and embedding generation
- Comprehensive test suite

## Quick Start

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

1. Install Python dependencies:
   ```bash
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
# Install test dependencies
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License
