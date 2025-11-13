#!/bin/bash
# smoke-tests.sh - Quick validation of deployed application

set -e

API_URL="${1:-http://localhost:8000}"
FAILED=0

echo "Running smoke tests against: $API_URL"
echo "========================================="

# Test 1: Health check
echo -n "✓ Testing health endpoint... "
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
if [ "$HEALTH" = "200" ]; then
    echo "PASS"
else
    echo "FAIL (HTTP $HEALTH)"
    FAILED=$((FAILED + 1))
fi

# Test 2: Ready check
echo -n "✓ Testing readiness endpoint... "
READY=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/ready")
if [ "$READY" = "200" ]; then
    echo "PASS"
else
    echo "FAIL (HTTP $READY)"
    FAILED=$((FAILED + 1))
fi

# Test 3: Search endpoint
echo -n "✓ Testing search endpoint... "
SEARCH=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}')
if [ "$SEARCH" = "200" ]; then
    echo "PASS"
else
    echo "FAIL (HTTP $SEARCH)"
    FAILED=$((FAILED + 1))
fi

# Test 4: Conversations list
echo -n "✓ Testing conversations list... "
CONVS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/conversations")
if [ "$CONVS" = "200" ]; then
    echo "PASS"
else
    echo "FAIL (HTTP $CONVS)"
    FAILED=$((FAILED + 1))
fi

echo "========================================="
if [ $FAILED -eq 0 ]; then
    echo "✅ All smoke tests passed!"
    exit 0
else
    echo "❌ $FAILED test(s) failed"
    exit 1
fi
