#!/bin/bash
// filepath: diagnose-backend.sh

set -e

echo "🔍 Diagnosing Backend API Issues"
echo "=================================="
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

log_info "Checking backend container status..."
if ! $DC ps | grep -q mcp-backend; then
    log_error "Backend container not found"
    echo ""
    log_info "Attempting to start backend..."
    $DC up -d mcp-backend
    sleep 5
fi

log_info "Backend container status:"
$DC ps mcp-backend
echo ""

log_info "Checking backend logs for errors..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$DC logs --tail=100 mcp-backend
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

log_info "Checking database connectivity..."
if $DC exec -T postgres pg_isready -U mcp_user -d mcp_db >/dev/null 2>&1; then
    log_success "PostgreSQL is ready"
else
    log_error "PostgreSQL is not responding"
    log_info "PostgreSQL logs:"
    $DC logs --tail=50 postgres
    exit 1
fi

log_info "Testing database connection from backend..."
$DC exec -T mcp-backend python3 -c "
import sys
sys.path.insert(0, '/app')
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version();'))
        print('✅ Database connection successful')
        print('PostgreSQL version:', result.fetchone()[0])
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
" 2>&1

log_info "Checking backend health endpoint..."
if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    log_success "Backend is responding"
    curl http://localhost:8000/health | python3 -m json.tool
else
    log_error "Backend health check failed"
    log_info "Attempting to restart backend..."
    $DC restart mcp-backend
    sleep 10
    
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        log_success "Backend recovered after restart"
    else
        log_error "Backend still not responding"
        log_info "Full backend logs:"
        $DC logs mcp-backend
        exit 1
    fi
fi

echo ""
log_success "Diagnostics complete!"