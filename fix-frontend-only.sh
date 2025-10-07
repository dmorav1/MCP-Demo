#!/bin/bash
# filepath: fix-frontend-only.sh

set -e

echo "🔧 Fixing Frontend (ajv compatibility issue)"
echo "============================================="
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

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    DC="docker compose"
fi

# Step 1: Stop and remove frontend container
log_info "Stopping frontend container..."
$DC stop frontend 2>/dev/null || true
$DC rm -f frontend 2>/dev/null || true
log_success "Frontend container removed"
echo ""

# Step 2: Remove package-lock.json to force clean install
log_info "Removing package-lock.json for clean dependency resolution..."
rm -f frontend/package-lock.json
log_success "Lock file removed"
echo ""

# Step 3: Update package.json with fixed versions
log_info "Updating package.json with pinned ajv versions..."
cat > frontend/package.json << 'EOF'
{
  "name": "mcp-chat-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@testing-library/jest-dom": "5.17.0",
    "@testing-library/react": "13.4.0",
    "@testing-library/user-event": "13.5.0",
    "@types/jest": "27.5.2",
    "@types/node": "16.18.0",
    "@types/react": "18.2.0",
    "@types/react-dom": "18.2.0",
    "ajv": "6.12.6",
    "ajv-keywords": "3.5.2",
    "axios": "1.6.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "react-scripts": "5.0.1",
    "typescript": "4.9.5",
    "web-vitals": "2.1.4"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": ["react-app"]
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version"]
  },
  "resolutions": {
    "ajv": "6.12.6",
    "ajv-keywords": "3.5.2"
  }
}
EOF
log_success "package.json updated"
echo ""

# Step 4: Update Dockerfile
log_info "Updating Dockerfile with multi-stage build..."
cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine as builder

WORKDIR /app

RUN apk add --no-cache python3 make g++ git

COPY package*.json ./

RUN rm -f package-lock.json

RUN npm cache clean --force && \
    npm install --legacy-peer-deps \
                --no-package-lock \
                --loglevel verbose \
                ajv@6.12.6 \
                ajv-keywords@3.5.2 && \
    npm install --legacy-peer-deps \
                --loglevel verbose

RUN node -e "console.log('ajv version:', require('ajv/package.json').version)" && \
    node -e "console.log('ajv-keywords version:', require('ajv-keywords/package.json').version)"

COPY . .

FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache curl

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/src ./src
COPY --from=builder /app/tsconfig.json ./tsconfig.json

ENV SKIP_PREFLIGHT_CHECK=true
ENV NODE_OPTIONS="--max_old_space_size=4096"
ENV TSC_COMPILE_ON_ERROR=true
ENV DISABLE_ESLINT_PLUGIN=true

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
  CMD curl -f http://localhost:3000 || exit 1

CMD ["sh", "-c", "npm start || (echo 'Startup failed, checking logs...' && cat /root/.npm/_logs/*.log 2>/dev/null && exit 1)"]
EOF
log_success "Dockerfile updated"
echo ""

# Step 5: Rebuild frontend image (no cache)
log_info "Rebuilding frontend image (this may take 3-5 minutes)..."
if ! $DC build --no-cache frontend 2>&1 | tee frontend-build.log; then
    log_error "Frontend build failed"
    echo ""
    log_info "Last 30 lines of build log:"
    tail -30 frontend-build.log
    exit 1
fi
log_success "Frontend image rebuilt"
echo ""

# Step 6: Start frontend
log_info "Starting frontend container..."
$DC up -d frontend
log_success "Frontend container started"
echo ""

# Step 7: Monitor startup
log_info "Monitoring frontend startup (max 120 seconds)..."
echo "   Logs will appear below (Ctrl+C to stop monitoring, container continues running)"
echo ""

TIMEOUT=120
START_TIME=$(date +%s)

# Follow logs in background
$DC logs -f frontend &
LOGS_PID=$!

# Check health in foreground
while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED -gt $TIMEOUT ]; then
        kill $LOGS_PID 2>/dev/null || true
        echo ""
        log_error "Frontend failed to start within ${TIMEOUT} seconds"
        echo ""
        log_info "Checking container status..."
        $DC ps frontend
        echo ""
        log_info "Last 50 lines of logs:"
        $DC logs --tail=50 frontend
        exit 1
    fi
    
    # Check if healthy
    if curl -sf http://localhost:3001 >/dev/null 2>&1; then
        kill $LOGS_PID 2>/dev/null || true
        echo ""
        log_success "Frontend is ready! (started in ${ELAPSED}s)"
        break
    fi
    
    # Check if container crashed
    if ! docker ps | grep -q mcp-frontend; then
        kill $LOGS_PID 2>/dev/null || true
        echo ""
        log_error "Frontend container crashed"
        echo ""
        log_info "Container logs:"
        $DC logs --tail=100 frontend
        exit 1
    fi
    
    sleep 2
done

echo ""
log_success "Frontend fix complete!"
echo ""
echo "📍 Access Points:"
echo "   🌐 Chat Interface:  http://localhost:3001"
echo "   🔧 Backend API:     http://localhost:8000"
echo ""
echo "📋 Quick Commands:"
echo "   View logs:    $DC logs -f frontend"
echo "   Restart:      $DC restart frontend"
echo "   Stop:         $DC stop frontend"
echo ""