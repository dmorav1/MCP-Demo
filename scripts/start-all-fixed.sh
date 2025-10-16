#!/bin/bash
// filepath: start-all-fixed.sh

set -e

echo "🚀 Starting MCP Chat Application (with Backend Fixes)"
echo "======================================================"
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

log_success "Using: $DC"
echo ""

# 1. Check Docker daemon
log_info "Checking Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running"
    exit 1
fi
log_success "Docker daemon is running"
echo ""

# 2. Setup .env
log_info "Checking .env file..."
if [ ! -f .env ]; then
    log_warning "Creating .env from .env.example"
    cp .env.example .env
fi
log_success ".env file ready"
echo ""

# 3. Verify DATABASE_URL format
log_info "Verifying DATABASE_URL format..."
if grep -q "DATABASE_URL=postgresql://" .env 2>/dev/null; then
    log_warning "Converting DATABASE_URL to psycopg3 format"
    sed -i.bak 's|postgresql://|postgresql+psycopg://|g' .env
    log_success "DATABASE_URL updated to postgresql+psycopg://"
fi
echo ""

# 4. Setup frontend (all previous code)
log_info "Setting up frontend structure..."
mkdir -p frontend/src frontend/public

if [ ! -f frontend/package.json ]; then
    log_warning "Creating frontend/package.json"
    cat > frontend/package.json << 'EOF'
{
  "name": "mcp-chat-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@testing-library/jest-dom": "^5.17.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^13.5.0",
    "@types/jest": "^27.5.2",
    "@types/node": "^16.18.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.5",
    "web-vitals": "^2.1.4",
    "ajv": "6.12.6",
    "ajv-keywords": "3.5.2"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "eslintConfig": {
    "extends": ["react-app", "react-app/jest"]
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version"]
  },
  "overrides": {
    "ajv": "6.12.6",
    "ajv-keywords": "3.5.2",
    "schema-utils": {
      "ajv": "6.12.6",
      "ajv-keywords": "3.5.2"
    },
    "webpack-dev-server": {
      "ajv": "6.12.6",
      "ajv-keywords": "3.5.2"
    }
  }
}
EOF
fi

# Create all frontend files (previous code...)
[ ! -f frontend/.env ] && cat > frontend/.env << 'EOF'
SKIP_PREFLIGHT_CHECK=true
GENERATE_SOURCEMAP=false
REACT_APP_API_URL=http://localhost:8000
PORT=3000
EOF

[ ! -f frontend/.dockerignore ] && cat > frontend/.dockerignore << 'EOF'
node_modules
npm-debug.log
build
.git
.DS_Store
coverage
EOF

[ ! -f frontend/Dockerfile ] && cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
RUN apk add --no-cache python3 make g++
COPY package*.json ./
RUN npm cache clean --force && npm install --legacy-peer-deps --loglevel info
COPY . .
ENV SKIP_PREFLIGHT_CHECK=true
ENV NODE_OPTIONS=--max_old_space_size=4096
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"
CMD ["npm", "start"]
EOF

[ ! -f frontend/tsconfig.json ] && cat > frontend/tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
EOF

[ ! -f frontend/public/index.html ] && cat > frontend/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#667eea" />
    <title>Technical Support Assistant</title>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
EOF

[ ! -f frontend/src/index.tsx ] && cat > frontend/src/index.tsx << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css';
import App from './App';
const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(<React.StrictMode><App /></React.StrictMode>);
EOF

log_success "Frontend structure ready"
echo ""

# 5. Clean and rebuild
log_info "Cleaning up existing containers..."
$DC down -v 2>/dev/null || true
log_success "Cleanup complete"
echo ""

log_info "Building Docker images..."
if ! $DC build --no-cache 2>&1 | tee build.log; then
    log_error "Build failed"
    tail -50 build.log
    exit 1
fi
log_success "Images built"
echo ""

# 6. Start services
log_info "Starting services..."
$DC up -d

# 7. Wait for PostgreSQL
echo -n "   PostgreSQL: "
for i in {1..30}; do
    if $DC exec -T postgres pg_isready -U mcp_user -d mcp_db >/dev/null 2>&1; then
        log_success "Ready"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# 8. Wait for Backend with detailed logging
echo -n "   Backend API: "
BACKEND_READY=false
for i in {1..60}; do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        log_success "Ready"
        BACKEND_READY=true
        break
    fi
    
    # Check if container crashed
    if ! docker ps | grep -q mcp-backend; then
        echo ""
        log_error "Backend container crashed"
        echo ""
        log_info "Backend logs:"
        $DC logs --tail=100 mcp-backend
        exit 1
    fi
    
    sleep 1
    echo -n "."
    
    # Show logs every 15 seconds
    if [ $((i % 15)) -eq 0 ]; then
        echo ""
        log_info "Backend still starting (${i}s)..."
        $DC logs --tail=20 mcp-backend | grep -E "(ERROR|❌|✅|🚀)" || true
        echo -n "   Waiting: "
    fi
done

if [ "$BACKEND_READY" = false ]; then
    echo ""
    log_error "Backend failed to start within 60 seconds"
    echo ""
    log_info "Full backend logs:"
    $DC logs mcp-backend
    exit 1
fi
echo ""

# 9. Wait for Frontend
echo -n "   Frontend: "
for i in {1..120}; do
    if curl -sf http://localhost:3001 >/dev/null 2>&1; then
        log_success "Ready"
        break
    fi
    
    if ! docker ps | grep -q mcp-frontend; then
        echo ""
        log_error "Frontend container crashed"
        $DC logs frontend
        exit 1
    fi
    
    sleep 1
    echo -n "."
    
    if [ $((i % 20)) -eq 0 ]; then
        echo ""
        echo -n "   Still starting (${i}s)... "
    fi
done
echo ""

# 10. Show status
$DC ps
echo ""

log_success "Application is ready!"
echo ""
echo "📍 Access Points:"
echo "   🌐 Chat Interface:  http://localhost:3001"
echo "   🔧 Backend API:     http://localhost:8000"
echo "   📚 API Docs:        http://localhost:8000/docs"
echo ""
echo "📋 Quick Commands:"
echo "   View backend logs:  $DC logs -f mcp-backend"
echo "   View frontend logs: $DC logs -f frontend"
echo "   Stop services:      $DC down"
echo ""