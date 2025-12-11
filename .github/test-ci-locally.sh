#!/bin/bash
# Local CI Pipeline Simulator
# Mimics GitHub Actions CI workflow to test locally before pushing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Local CI Pipeline Simulator                         ║${NC}"
echo -e "${BLUE}║   Mimics GitHub Actions CI workflow                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
export PYTHON_VERSION="3.11"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-key}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-key}"

# Track timing
START_TIME=$(date +%s)

# Function to print section header
section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check elapsed time
check_time() {
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    MINUTES=$((ELAPSED / 60))
    SECONDS=$((ELAPSED % 60))

    echo -e "${YELLOW}⏱️  Elapsed time: ${MINUTES}m ${SECONDS}s${NC}"

    # Warn if approaching timeout
    if [ $MINUTES -ge 12 ]; then
        echo -e "${RED}⚠️  WARNING: Approaching 15-minute timeout!${NC}"
    fi
}

# Function to run with timeout
run_with_timeout() {
    local timeout_minutes=$1
    shift
    local cmd="$@"

    echo -e "${YELLOW}⏱️  Timeout: ${timeout_minutes} minutes${NC}"

    if command -v timeout &> /dev/null; then
        timeout ${timeout_minutes}m bash -c "$cmd"
    elif command -v gtimeout &> /dev/null; then
        gtimeout ${timeout_minutes}m bash -c "$cmd"
    else
        echo -e "${YELLOW}⚠️  'timeout' command not available, running without timeout${NC}"
        bash -c "$cmd"
    fi
}

# Check Python version
section "1. Checking Python Version"
CURRENT_PYTHON=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo "Required: Python ${PYTHON_VERSION}"
echo "Current:  Python ${CURRENT_PYTHON}"

if [ "$CURRENT_PYTHON" != "$PYTHON_VERSION" ]; then
    echo -e "${YELLOW}⚠️  Warning: Python version mismatch (CI uses ${PYTHON_VERSION})${NC}"
    echo "This may cause different test results than CI"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check PostgreSQL
section "2. Checking PostgreSQL"
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is running on port 5432${NC}"
    else
        echo -e "${RED}❌ PostgreSQL not running on port 5432${NC}"
        echo "CI requires PostgreSQL with pgvector extension"
        echo ""
        echo "Quick setup with Docker:"
        echo "  docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16"
        echo ""
        read -p "Continue without PostgreSQL? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}⚠️  pg_isready not found, skipping PostgreSQL check${NC}"
fi

# Install dependencies
section "3. Installing Dependencies"
echo "Installing Python packages..."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel -q

echo "Installing requirements..."
pip install -r requirements.txt -q 2>&1 | grep -v "Requirement already satisfied" || true

echo "Installing test dependencies..."
pip install pytest pytest-cov pytest-asyncio>=0.21.0 pytest-timeout -q

echo -e "${GREEN}✅ Dependencies installed${NC}"
check_time

# Run the actual tests (mimics CI command exactly)
section "4. Running Tests (EXACTLY as CI does)"
echo "Command: pytest tests/ -v --tb=short -m \"not slow and not integration\" --timeout=300 --cov=app --cov-report=xml --cov-report=term-missing --cov-report=html"
echo ""

# Run with 15-minute timeout (same as CI)
run_with_timeout 15 "pytest tests/ -v --tb=short -m 'not slow and not integration' --timeout=300 --cov=app --cov-report=xml --cov-report=term-missing --cov-report=html"

TEST_EXIT_CODE=$?

check_time

# Analyze results
section "5. Test Results"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
elif [ $TEST_EXIT_CODE -eq 124 ]; then
    echo -e "${RED}❌ Tests TIMED OUT after 15 minutes${NC}"
    echo "This is exactly what's happening in CI!"
    echo ""
    echo "Likely causes:"
    echo "  - A test is hanging (not respecting --timeout=300)"
    echo "  - Infinite loop in test code"
    echo "  - Waiting for external resource"
    echo ""
    echo "Check the last test that was running above ^^"
else
    echo -e "${RED}❌ Tests failed with exit code: $TEST_EXIT_CODE${NC}"
    echo "Review the output above for details"
fi

# Coverage analysis
if [ -f "coverage.xml" ]; then
    section "6. Coverage Analysis"

    coverage_percent=$(python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    print(root.attrib.get('line-rate', '0'))
except Exception as e:
    print('0')
")
    coverage_int=$(python3 -c "print(int(float($coverage_percent) * 100))")

    echo "Coverage: ${coverage_int}%"

    if [ $coverage_int -lt 80 ]; then
        echo -e "${YELLOW}⚠️  Coverage is below 80% threshold (advisory)${NC}"
    else
        echo -e "${GREEN}✅ Coverage meets 80% threshold${NC}"
    fi
fi

# Summary
section "7. Summary"

TOTAL_TIME=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_TIME - START_TIME))
TOTAL_MINUTES=$((TOTAL_ELAPSED / 60))
TOTAL_SECONDS=$((TOTAL_ELAPSED % 60))

echo "Total execution time: ${TOTAL_MINUTES}m ${TOTAL_SECONDS}s"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ LOCAL CI SIMULATION PASSED                        ║${NC}"
    echo -e "${GREEN}║   Tests should pass in GitHub Actions CI               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    exit 0
elif [ $TEST_EXIT_CODE -eq 124 ]; then
    echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ⏱️  TIMEOUT - THIS IS THE CI ISSUE                   ║${NC}"
    echo -e "${RED}║   A test is hanging for more than 15 minutes           ║${NC}"
    echo -e "${RED}║   Fix the hanging test before pushing                  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    exit 1
else
    echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ❌ TESTS FAILED                                      ║${NC}"
    echo -e "${RED}║   Review errors above and fix before pushing           ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
