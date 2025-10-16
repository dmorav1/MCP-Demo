# MCP Backend Deployment Guide

## Quick Start (Development)

1. **Setup the environment:**
   ```bash
   cd mcp-backend
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Run the development startup script:**
   ```bash
   ./start-dev.sh
   ```

3. **Test the API:**
   ```bash
   python test-api.py
   ```

## Manual Development Setup

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- OpenAI API key

### Step-by-step Setup

1. **Install Python dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL with pgvector:**
   ```bash
   docker-compose up -d postgres
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Update .env with your settings
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Production Deployment

### Using Docker Compose (Recommended)

1. **Prepare production environment:**
   ```bash
   cp .env.example .env
   # Update .env with production values
   ```

2. **Update docker-compose.yml for production:**
   - Remove volume mount for app code
   - Configure proper secrets management
   - Set up proper logging
   - Configure health checks

3. **Deploy:**
   ```bash
   docker-compose up -d
   ```

### Manual Production Deployment

1. **Set up PostgreSQL with pgvector:**
   ```sql
   CREATE DATABASE mcp_db;
   CREATE USER mcp_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE mcp_db TO mcp_user;
   \c mcp_db
   CREATE EXTENSION vector;
   ```

2. **Run database initialization:**
   ```bash
   psql -h your-postgres-host -U mcp_user -d mcp_db -f init-db.sql
   ```

3. **Configure production settings:**
   ```bash
   export DATABASE_URL="postgresql://mcp_user:password@postgres-host:5432/mcp_db"
   export OPENAI_API_KEY="your-production-api-key"
   ```

4. **Run with a production server:**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://username:password@localhost:5432/mcp_db` |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | Required |
| `EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-ada-002` |
| `EMBEDDING_DIMENSION` | Embedding vector dimension | `1536` |

## Production Considerations

### Security
- Use proper secrets management (e.g., HashiCorp Vault, AWS Secrets Manager)
- Configure CORS origins appropriately
- Set up SSL/TLS termination
- Implement rate limiting
- Enable API authentication if needed

### Performance
- Configure connection pooling for PostgreSQL
- Set up read replicas for search queries
- Implement caching for frequently accessed data
- Monitor API response times

### Monitoring
- Set up logging aggregation
- Configure health check endpoints
- Monitor database performance
- Track OpenAI API usage and costs

### Backup
- Set up automated database backups
- Test backup restoration procedures
- Consider point-in-time recovery

## Troubleshooting

### Common Issues

1. **Database connection errors:**
   - Check PostgreSQL is running
   - Verify DATABASE_URL is correct
   - Ensure pgvector extension is installed

2. **OpenAI API errors:**
   - Verify OPENAI_API_KEY is set correctly
   - Check API rate limits
   - Ensure sufficient credits

3. **Embedding generation failures:**
   - Check OpenAI API status
   - Verify network connectivity
   - Review rate limiting settings

4. **Search returning no results:**
   - Ensure conversations have been ingested
   - Check that embeddings were generated successfully
   - Verify pgvector index is created

### Logs
Check application logs for detailed error information:
```bash
docker-compose logs mcp-backend
```

### Database Health
Check database connectivity and extensions:
```sql
SELECT version();
SELECT * FROM pg_extension WHERE extname = 'vector';
```
