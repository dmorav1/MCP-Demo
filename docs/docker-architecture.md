# Docker Architecture Deep Dive

This document explains the Docker architecture decisions and patterns used in the MCP service implementation.

## Architecture Overview

The MCP service uses a **multi-service, single-image** architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Architecture                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Base Image Layer                         ││
│  │  python:3.11-slim + system packages + Python dependencies  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                    │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               Application Layer                             ││
│  │  • FastAPI Application (app/)                               ││
│  │  • MCP Server (run_mcp_server_standalone.py)               ││
│  │  • Docker Entrypoint (docker-entrypoint.sh)                ││
│  └─────────────────────────────────────────────────────────────┘│
│                                    │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                Runtime Modes                                ││
│  │  ┌─────────────────┐    ┌─────────────────────────────────┐ ││
│  │  │  FastAPI Mode   │    │         MCP Mode                │ ││
│  │  │  Port: 8000     │    │  Transport: stdio               │ ││
│  │  │  HTTP API       │    │  JSON-RPC Protocol              │ ││
│  │  └─────────────────┘    └─────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Patterns

### 1. Single Image, Multiple Modes

**Pattern:** One Docker image that can run in different modes based on runtime arguments.

**Implementation:**
```dockerfile
# Single image definition
FROM python:3.11-slim
# ... install dependencies ...
COPY app/ ./app/
COPY run_mcp_server_standalone.py .
COPY docker-entrypoint.sh .

# Flexible entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["fastapi"]  # Default mode
```

**Usage:**
```bash
# FastAPI mode (default)
docker run mcp-demo-mcp-backend:latest

# MCP mode
docker run mcp-demo-mcp-backend:latest mcp
```

**Benefits:**
- **Single Image**: Only one image to build and maintain
- **Consistency**: Same dependencies and base for both modes
- **Simplicity**: No need for separate images

**Trade-offs:**
- **Image Size**: Slightly larger as it includes both applications
- **Complexity**: Entrypoint script adds a layer of indirection

### 2. Entrypoint Script Pattern

**Pattern:** Use a shell script as entrypoint to handle different runtime modes.

**Implementation:**
```bash
#!/bin/bash
MODE=${1:-fastapi}

case "$MODE" in
    "fastapi")
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000
        ;;
    "mcp")
        export FASTAPI_BASE_URL=${FASTAPI_BASE_URL:-http://host.docker.internal:8000}
        exec python run_mcp_server_standalone.py
        ;;
    *)
        echo "❌ Unknown mode: $MODE"
        exit 1
        ;;
esac
```

**Why `exec`:**
- **Signal Forwarding**: Proper signal handling for graceful shutdowns
- **PID 1**: The actual application becomes PID 1, not the shell script
- **Resource Management**: No extra shell process consuming resources

**Environment Defaults:**
- **FASTAPI_BASE_URL**: Sensible default for container networking
- **Flexibility**: Can be overridden at runtime

### 3. Health Check Strategy

**Pattern:** Container-level health checks for service readiness.

**Implementation:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**Docker Compose Integration:**
```yaml
services:
  mcp-backend:
    # ...
    depends_on:
      postgres:
        condition: service_healthy

  mcp-server:
    # ...
    depends_on:
      mcp-backend:
        condition: service_healthy
```

**Benefits:**
- **Orchestration**: Services wait for dependencies to be ready
- **Reliability**: Failed health checks trigger container restarts
- **Monitoring**: External systems can monitor service health

### 4. Service Profile Pattern

**Pattern:** Optional services using Docker Compose profiles.

**Implementation:**
```yaml
services:
  # Always runs
  postgres:
    # ...
  
  mcp-backend:
    # ...

  # Only runs when profile is specified
  mcp-server:
    # ...
    profiles:
      - mcp
```

**Usage:**
```bash
# Start core services only
docker-compose up -d

# Start with MCP server
docker-compose --profile mcp up -d
```

**Benefits:**
- **Flexibility**: Different deployment scenarios
- **Resource Management**: Don't run unnecessary services
- **Development**: Different setups for different needs

## Container Networking

### Internal Service Communication

```yaml
# docker-compose.yml
services:
  mcp-backend:
    ports:
      - "8000:8000"  # Exposed to host
    
  mcp-server:
    environment:
      FASTAPI_BASE_URL: http://mcp-backend:8000  # Internal DNS
```

**Key Points:**
- **Internal DNS**: Services can reach each other by service name
- **No Port Exposure**: MCP server doesn't expose ports (stdio only)
- **Network Isolation**: Internal communication is isolated

### Host Integration

For Claude Desktop integration, the MCP server needs to connect to the host-running FastAPI service:

```bash
docker run --rm -i \
  -e FASTAPI_BASE_URL="http://host.docker.internal:8000" \
  --network host \
  mcp-demo-mcp-backend:latest mcp
```

**Explanation:**
- **host.docker.internal**: Docker's way to reach the host machine
- **--network host**: Use host networking for stdio transport
- **Port 8000**: Connect to the FastAPI service on the host

## Environment Configuration

### Layered Configuration

1. **Dockerfile Defaults**: Sensible defaults built into the image
2. **Compose Defaults**: Service-specific defaults in docker-compose.yml
3. **Environment Override**: Runtime environment variables
4. **Command Override**: Runtime command arguments

**Example Flow:**
```bash
# 1. Dockerfile default
ENV FASTAPI_BASE_URL=http://localhost:8000

# 2. Compose override
environment:
  FASTAPI_BASE_URL: http://mcp-backend:8000

# 3. Runtime override
docker run -e FASTAPI_BASE_URL=http://host.docker.internal:8000 ...
```

### Environment Variable Patterns

**Database Configuration:**
```bash
# Internal (compose)
DATABASE_URL=postgresql+psycopg://mcp_user:mcp_password@postgres:5432/mcp_db

# External (standalone)
DATABASE_URL=postgresql+psycopg://mcp_user:mcp_password@host.docker.internal:5433/mcp_db
```

**Connection String Format:**
- **postgresql+psycopg**: Specifies psycopg v3 driver
- **Service Names**: For internal compose networking
- **host.docker.internal**: For host machine access

## Volume and Data Management

### Database Persistence

```yaml
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persistent data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql  # Init script

volumes:
  postgres_data:  # Named volume for persistence
```

**Benefits:**
- **Data Persistence**: Database survives container restarts
- **Initialization**: Automatic database setup
- **Backup**: Easy volume backup and restore

### Application Code

```yaml
services:
  mcp-backend:
    volumes:
      - ./app:/app/app  # Development override
```

**Development Pattern:**
- **Live Reload**: Changes reflected immediately
- **Debugging**: Easy access to modify code
- **Production**: Remove volume mounts for immutable containers

## Security Considerations

### Non-Root User (Future Enhancement)

```dockerfile
# Future improvement
RUN adduser --disabled-password --gecos '' appuser
USER appuser
```

### Secret Management

```yaml
# Current: Environment variables (development)
environment:
  DATABASE_URL: postgresql+psycopg://mcp_user:mcp_password@postgres:5432/mcp_db

# Future: Docker secrets (production)
secrets:
  - database_password
```

### Network Security

```yaml
# Internal network isolation
networks:
  default:
    driver: bridge
    internal: true  # No internet access
  
  external:
    driver: bridge  # Internet access for specific services
```

## Monitoring and Observability

### Logging Strategy

```bash
# Structured logging in applications
docker-compose logs mcp-backend

# Centralized logging (future)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Metrics Collection

```dockerfile
# Health check endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**Future Enhancements:**
- Prometheus metrics endpoints
- Application performance monitoring
- Resource usage tracking

## Build Optimization

### Current Build Strategy

```dockerfile
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last
COPY app/ ./app/
```

**Layer Caching:**
- **Dependencies**: Cached until requirements.txt changes
- **Application**: Only rebuilt when code changes
- **Base Image**: Shared across multiple builds

### Future Optimizations

**Multi-stage builds:**
```dockerfile
# Build stage
FROM python:3.11-slim as builder
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
```

**Benefits:**
- **Smaller Images**: Remove build dependencies
- **Security**: Fewer attack vectors
- **Performance**: Faster deployment

## Deployment Patterns

### Local Development
```bash
docker-compose up -d  # Full stack
```

### Production Deployment
```bash
# Separate database
docker run -d postgres:15

# Application only
docker run -d -e DATABASE_URL=... mcp-demo-mcp-backend:latest
```

### Cloud Deployment
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: mcp-backend
        image: mcp-demo-mcp-backend:latest
        args: ["fastapi"]
```

## Conclusion

This Docker architecture provides:

1. **Flexibility**: Single image, multiple deployment modes
2. **Maintainability**: Clear separation of concerns
3. **Scalability**: Easy to scale individual components
4. **Development Experience**: Simple local setup
5. **Production Ready**: Health checks, proper networking, persistence

The architecture balances simplicity for development with the flexibility needed for various deployment scenarios.