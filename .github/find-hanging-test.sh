#!/bin/bash
# Quick Diagnostic: Find Which Test is Hanging
# Runs tests with verbose output and short timeout to identify problematic tests

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔍 Finding Hanging Tests${NC}"
echo "Running with 30-second timeout per test to quickly identify issues..."
echo ""

# Setup environment
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-key}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-key}"

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run with short timeout and stop at first failure
echo -e "${YELLOW}Command: pytest -x --timeout=30 -v -m 'not slow and not integration'${NC}"
echo ""

pytest -x \
    --timeout=30 \
    -v \
    -m "not slow and not integration" \
    --tb=short \
    tests/ 2>&1 | tee test_output.log

EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed with 30s timeout${NC}"
    echo "The issue might be specific to the 5-minute timeout or CI environment"
else
    echo -e "${RED}❌ Test failed or timed out${NC}"
    echo ""
    echo "Check the last test in the output above ^^"
    echo ""
    echo "Common issues:"
    echo "  - Test making real API calls (should be mocked)"
    echo "  - Test downloading models (should be skipped)"
    echo "  - Infinite loop in test logic"
    echo "  - Waiting for external resource"
fi

# Save for analysis
echo ""
echo "Full output saved to: test_output.log"
