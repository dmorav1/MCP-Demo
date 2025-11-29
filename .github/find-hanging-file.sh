#!/bin/bash
# Quick Hanging Test Finder
# Runs each test file individually with a short timeout to find the culprit

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Quick Hanging Test Finder                            ║${NC}"
echo -e "${BLUE}║   Tests each file with 60-second timeout               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Setup
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/test_db}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-key}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-key}"

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Get list of test files (excluding integration/evaluation)
TEST_FILES=$(find tests -name "test_*.py" -not -path "*/integration/*" -not -path "*/evaluation/*" | sort)

echo "Found $(echo "$TEST_FILES" | wc -l | tr -d ' ') test files to check"
echo ""

HANGING_FILES=()
FAILED_FILES=()
PASSED_FILES=()

for test_file in $TEST_FILES; do
    echo -n "Testing $test_file ... "
    
    # Run with 60-second timeout
    if timeout 60 pytest "$test_file" -x --timeout=30 -m "not slow and not integration" -q 2>&1 > /tmp/test_output.log; then
        echo -e "${GREEN}✅ PASSED${NC}"
        PASSED_FILES+=("$test_file")
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            echo -e "${RED}⏱️  TIMEOUT - HANGING!${NC}"
            HANGING_FILES+=("$test_file")
            echo "  Last output:"
            tail -5 /tmp/test_output.log | sed 's/^/    /'
        else
            echo -e "${YELLOW}❌ FAILED (code: $EXIT_CODE)${NC}"
            FAILED_FILES+=("$test_file")
            # Show error
            grep -E "FAILED|ERROR|Error" /tmp/test_output.log | head -3 | sed 's/^/    /' || true
        fi
    fi
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${GREEN}Passed: ${#PASSED_FILES[@]}${NC}"
echo -e "${YELLOW}Failed: ${#FAILED_FILES[@]}${NC}"
echo -e "${RED}Hanging: ${#HANGING_FILES[@]}${NC}"

if [ ${#HANGING_FILES[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}⚠️  HANGING TEST FILES (causing CI timeout):${NC}"
    for f in "${HANGING_FILES[@]}"; do
        echo "  - $f"
    done
    echo ""
    echo "To debug a hanging file:"
    echo "  pytest <file> -v --timeout=10 -x"
fi

if [ ${#FAILED_FILES[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Failed test files:${NC}"
    for f in "${FAILED_FILES[@]}"; do
        echo "  - $f"
    done
fi
