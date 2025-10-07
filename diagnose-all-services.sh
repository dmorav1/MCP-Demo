#!/bin/bash
// filepath: diagnose-all-services.sh

set -e

echo "🔍 Complete Service Diagnostics"
echo "================================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    DC="docker compose"
fi

# Check backend logs
log_info "Backend container logs (last 50 lines):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$DC logs --tail=50 mcp-backend
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python module structure
log_info "Checking app module structure in container:"
$DC exec mcp-backend find /app/app -name "*.py" | sort
echo ""

# Check if crud.py has get_conversations
log_info "Checking crud.py functions:"
$DC exec mcp-backend python3 -c "
import sys
sys.path.insert(0, '/app')
try:
    import app.crud as crud
    print('Available functions in crud module:')
    for name in dir(crud):
        if not name.startswith('_'):
            print(f'  - {name}')
except Exception as e:
    print(f'Error: {e}')
"
echo ""

# Test API endpoint
log_info "Testing /conversations endpoint:"
curl -s http://localhost:8000/conversations || echo "Failed to connect"
echo ""
echo ""

# Test health endpoint
log_info "Testing /health endpoint:"
curl -s http://localhost:8000/health | python3 -m json.tool || echo "Failed to connect"
echo ""