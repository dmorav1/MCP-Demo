# MCP Backend

A Model Context Protocol (MCP) backend service for storing and retrieving conversational data using PostgreSQL with pgvector for semantic search.

## Features

- **FastAPI** REST API with automatic OpenAPI documentation
- **PostgreSQL** with **pgvector** extension for vector similarity search
- **OpenAI embeddings** for semantic search capabilities
- **Docker** containerized deployment
- Conversation chunking and embedding generation
- Comprehensive test suite

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

# Install Docker Desktop
brew install --cask docker
```

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install Docker
sudo apt install docker.io docker-compose

# Add user to docker group
sudo usermod -a -G docker $USER
```

#### Windows
- Install Python 3.11 from [python.org](https://www.python.org/downloads/)
- Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)

### Python Dependencies

The project uses **psycopg 3** (not psycopg2) for PostgreSQL connectivity with Python 3.13 compatibility:

```bash
# Core dependencies (automatically installed via requirements.txt)
fastapi==0.104.1          # Web framework
uvicorn==0.24.0           # ASGI server
sqlalchemy==2.0.23        # ORM
psycopg[binary]==3.1.20   # PostgreSQL adapter (Python 3.13 compatible)
pgvector==0.2.4           # Vector similarity search
pydantic==2.5.0           # Data validation
openai==1.3.7             # OpenAI API client
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
3. Installs all Python dependencies from `requirements.txt`
4. Starts PostgreSQL container with Docker Compose
5. Waits for database to be ready
6. Starts the FastAPI development server

**Prerequisites for start-dev.sh:**
- Python 3.11+ installed on your system
- Docker and Docker Compose running
- `.env` file with valid OpenAI API key

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

## License

MIT License