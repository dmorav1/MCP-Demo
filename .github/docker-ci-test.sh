#!/bin/bash
# Docker-based CI Test Runner
# Runs tests in a container identical to GitHub Actions environment
# This ensures tests behave the same locally as in CI

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Docker-based CI Test Runner                          ║${NC}"
echo -e "${BLUE}║   Exactly mirrors GitHub Actions environment           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Create network if not exists
docker network create ci-test-network 2>/dev/null || true

# Start PostgreSQL with pgvector (same as CI)
echo -e "${YELLOW}▶ Starting PostgreSQL with pgvector...${NC}"
docker rm -f ci-test-postgres 2>/dev/null || true
docker run -d \
    --name ci-test-postgres \
    --network ci-test-network \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=test_db \
    -p 5433:5432 \
    --health-cmd="pg_isready" \
    --health-interval=10s \
    --health-timeout=5s \
    --health-retries=5 \
    pgvector/pgvector:pg16

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}▶ Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker exec ci-test-postgres pg_isready -U postgres &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ PostgreSQL failed to start${NC}"
        docker logs ci-test-postgres
        exit 1
    fi
done

# Enable pgvector extension
docker exec ci-test-postgres psql -U postgres -d test_db -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

# Build test container
echo -e "${YELLOW}▶ Building test container (Python 3.11, same as CI)...${NC}"

cat > /tmp/Dockerfile.ci-test << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir sqlalchemy psycopg2-binary fastapi httpx pytest pytest-cov pytest-asyncio pytest-timeout pydantic pydantic-settings pgvector openai anthropic

# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio pytest-timeout

# Copy application code
COPY . .

# Set environment variables
ENV DATABASE_URL=postgresql://postgres:postgres@ci-test-postgres:5432/test_db
ENV OPENAI_API_KEY=sk-test-key
ENV ANTHROPIC_API_KEY=test-key
ENV PYTHONPATH=/app

CMD ["pytest", "tests/", "-v", "--tb=short", "-m", "not slow and not integration", "--timeout=30", "-x"]
EOF

docker build -t ci-test-runner -f /tmp/Dockerfile.ci-test .

# Run tests with 15-minute timeout
echo -e "${YELLOW}▶ Running tests (15-minute timeout, same as CI)...${NC}"
echo ""

START_TIME=$(date +%s)

# Run with timeout
if timeout 900 docker run --rm \
    --network ci-test-network \
    -e DATABASE_URL=postgresql://postgres:postgres@ci-test-postgres:5432/test_db \
    -e OPENAI_API_KEY=sk-test-key \
    -e ANTHROPIC_API_KEY=test-key \
    ci-test-runner; then
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ TESTS PASSED in ${ELAPSED}s                              ║${NC}"
    echo -e "${GREEN}║   CI should pass with these tests                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    EXIT_CODE=0
else
    EXIT_CODE=$?
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    echo ""
    if [ $EXIT_CODE -eq 124 ]; then
        echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║   ⏱️  TIMEOUT after ${ELAPSED}s                             ║${NC}"
        echo -e "${RED}║   A test is hanging - this is the CI issue!           ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║   ❌ TESTS FAILED (exit code: $EXIT_CODE)                   ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    fi
fi

# Cleanup
echo ""
echo -e "${YELLOW}▶ Cleaning up...${NC}"
docker rm -f ci-test-postgres 2>/dev/null || true
docker network rm ci-test-network 2>/dev/null || true

exit $EXIT_CODE
