#!/bin/bash
// filepath: fix-backend-and-restart.sh

set -e

echo "🔧 Fixing Backend and Restarting All Services"
echo "=============================================="
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

# Step 1: Verify crud.py has all functions
log_info "Verifying app/crud.py has all required functions..."
if ! grep -q "def get_conversations" app/crud.py; then
    log_error "app/crud.py is missing get_conversations function"
    log_info "Please update app/crud.py with the complete implementation"
    exit 1
fi
log_success "crud.py verified"
echo ""

# Step 2: Stop backend
log_info "Stopping backend container..."
$DC stop mcp-backend
$DC rm -f mcp-backend
log_success "Backend stopped"
echo ""

# Step 3: Rebuild backend
log_info "Rebuilding backend (no cache)..."
if ! $DC build --no-cache mcp-backend 2>&1 | tee backend-build.log; then
    log_error "Backend build failed"
    tail -30 backend-build.log
    exit 1
fi
log_success "Backend rebuilt"
echo ""

# Step 4: Start backend
log_info "Starting backend..."
$DC up -d mcp-backend
log_success "Backend started"
echo ""

# Step 5: Wait for backend health
log_info "Waiting for backend to be healthy..."
for i in {1..60}; do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo ""
        log_success "Backend is healthy"
        break
    fi
    
    if ! docker ps | grep -q mcp-backend; then
        echo ""
        log_error "Backend container crashed"
        echo ""
        $DC logs mcp-backend
        exit 1
    fi
    
    sleep 1
    echo -n "."
    
    if [ $i -eq 60 ]; then
        echo ""
        log_error "Backend failed to start"
        echo ""
        $DC logs --tail=50 mcp-backend
        exit 1
    fi
done
echo ""

# Step 6: Test endpoints
log_info "Testing API endpoints..."

echo "  Health check:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

echo "  Conversations list:"
curl -s http://localhost:8000/conversations | python3 -m json.tool | head -20
echo ""

echo "  Root endpoint:"
curl -s http://localhost:8000/ | python3 -m json.tool
echo ""

# Step 7: Start frontend if not running
if ! docker ps | grep -q mcp-frontend; then
    log_info "Starting frontend..."
    $DC up -d frontend
    
    log_info "Waiting for frontend..."
    for i in {1..60}; do
        if curl -sf http://localhost:3001 >/dev/null 2>&1; then
            echo ""
            log_success "Frontend is ready"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
fi

# Step 8: Show final status
log_info "Final service status:"
$DC ps
echo ""

log_success "All services are running!"
echo ""
echo "📍 Access Points:"
echo "   🌐 Chat Interface:  http://localhost:3001"
echo "   🔧 Backend API:     http://localhost:8000"
echo "   📚 API Docs:        http://localhost:8000/docs"
echo "   🏥 Health Check:    http://localhost:8000/health"
echo ""
echo "📋 Test Commands:"
echo "   List conversations: curl http://localhost:8000/conversations"
echo "   Search:             curl 'http://localhost:8000/search?q=test&top_k=5'"
echo "   Health:             curl http://localhost:8000/health"
echo ""
echo "📊 View Logs:"
echo "   Backend:   $DC logs -f mcp-backend"
echo "   Frontend:  $DC logs -f frontend"
echo "   All:       $DC logs -f"
echo ""