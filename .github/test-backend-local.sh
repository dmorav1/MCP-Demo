#!/bin/bash
# Local Backend Test Runner
# Mimics the CI environment setup for debugging

set -e

echo "🧪 Backend Test Runner (matches CI environment)"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo "📍 Python version: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" != "3.11" ]]; then
    echo -e "${YELLOW}⚠️  Warning: CI uses Python 3.11, you have $PYTHON_VERSION${NC}"
    echo "   This may cause dependency issues"
    echo ""
fi

# Check if PostgreSQL is running
echo "🔍 Checking for PostgreSQL..."
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is running${NC}"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL not running on localhost:5432${NC}"
        echo "   Tests may fail or skip database tests"
    fi
else
    echo -e "${YELLOW}⚠️  pg_isready not found${NC}"
fi
echo ""

# Setup environment
echo "🔧 Setting up environment..."
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-key}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-key}"
echo "   DATABASE_URL: $DATABASE_URL"
echo "   OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo "   ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:10}..."
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
python3 -m pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q 2>&1 | grep -v "Requirement already satisfied" || true
pip install pytest pytest-cov pytest-asyncio pytest-timeout -q

# Check for common missing dependencies
echo ""
echo "🔍 Checking critical dependencies..."
python3 -c "
import sys
missing = []
try:
    import pytest
    print('✅ pytest')
except ImportError:
    missing.append('pytest')
    print('❌ pytest')

try:
    import sqlalchemy
    print('✅ sqlalchemy')
except ImportError:
    missing.append('sqlalchemy')
    print('❌ sqlalchemy')

try:
    import fastapi
    print('✅ fastapi')
except ImportError:
    missing.append('fastapi')
    print('❌ fastapi')

try:
    import pgvector
    print('✅ pgvector')
except ImportError as e:
    print('⚠️  pgvector (optional for some tests)')

if missing:
    print(f'\\n❌ Missing dependencies: {missing}')
    sys.exit(1)
"

# Run tests
echo ""
echo "🧪 Running tests..."
echo "================================================"
echo ""

pytest tests/ \
    -v \
    --tb=short \
    -m "not slow" \
    --cov=app \
    --cov-report=xml \
    --cov-report=term-missing \
    --cov-report=html \
    "$@"

EXIT_CODE=$?

echo ""
echo "================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Tests passed!${NC}"
else
    echo -e "${RED}❌ Tests failed with exit code: $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
