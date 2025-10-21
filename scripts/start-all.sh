#!/bin/bash
// filepath: start-all.sh

set -euo pipefail

echo "🚀 Starting MCP Chat Application"
echo "================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    log_error "Docker Compose not found"
    exit 1
fi

log_success "Using: $DOCKER_COMPOSE"
echo ""

log_info "Checking Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi
log_success "Docker daemon is running"
echo ""

log_info "Checking .env file..."
if [ ! -f .env ]; then
    log_warning "Creating .env from .env.example"
    cp .env.example .env
fi

set -a
source .env
set +a

if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    log_warning "OPENAI_API_KEY not configured in .env"
    echo "   Please add your OpenAI API key to .env file"
    echo "   You can continue without it, but LLM features won't work"
fi
log_success ".env file ready"
echo ""

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
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": ["react-app", "react-app/jest"]
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
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

if [ ! -f frontend/.env ]; then
    log_warning "Creating frontend/.env"
    cat > frontend/.env << 'EOF'
SKIP_PREFLIGHT_CHECK=true
GENERATE_SOURCEMAP=false
REACT_APP_API_URL=http://localhost:8000
PORT=3000
EOF
fi

if [ ! -f frontend/.dockerignore ]; then
    log_warning "Creating frontend/.dockerignore"
    cat > frontend/.dockerignore << 'EOF'
node_modules
npm-debug.log
build
.git
.DS_Store
coverage
EOF
fi

if [ ! -f frontend/Dockerfile ]; then
    log_warning "Creating frontend/Dockerfile"
    cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache python3 make g++

COPY package*.json ./

RUN npm cache clean --force && \
    npm install --legacy-peer-deps --loglevel info

COPY . .

ENV SKIP_PREFLIGHT_CHECK=true
ENV NODE_OPTIONS=--max_old_space_size=4096

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

CMD ["npm", "start"]
EOF
fi

if [ ! -f frontend/tsconfig.json ]; then
    log_warning "Creating frontend/tsconfig.json"
    cat > frontend/tsconfig.json << 'EOF'
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
fi

if [ ! -f frontend/public/index.html ]; then
    log_warning "Creating frontend/public/index.html"
    cat > frontend/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#667eea" />
    <meta name="description" content="Technical Support Assistant powered by MCP" />
    <title>Technical Support Assistant</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
EOF
fi

if [ ! -f frontend/src/index.tsx ]; then
    log_warning "Creating frontend/src/index.tsx"
    cat > frontend/src/index.tsx << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css';
import App from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(<React.StrictMode><App /></React.StrictMode>);
EOF
fi

log_success "Frontend structure ready"
echo ""

log_info "Cleaning up existing containers..."
$DOCKER_COMPOSE down -v 2>/dev/null || true
log_success "Cleanup complete"
echo ""

log_info "Building Docker images..."
echo "   This may take several minutes on first run..."
echo ""

if ! $DOCKER_COMPOSE build --no-cache 2>&1 | tee build.log; then
  log_error "Failed to build images"
  echo ""
  echo "📋 Checking build.log for errors..."
  tail -50 build.log
  exit 1
fi

log_success "Images built successfully"
echo ""

log_info "Starting services..."
if ! $DOCKER_COMPOSE up -d; then
    log_error "Failed to start services"
    echo ""
    echo "📋 Checking logs..."
    $DOCKER_COMPOSE logs --tail=50
    exit 1
fi

log_success "Services started"
echo ""

log_info "Waiting for services to be ready..."

echo -n "   PostgreSQL: "
for i in {1..30}; do
    if $DOCKER_COMPOSE exec -T postgres pg_isready -U mcp_user -d mcp_db >/dev/null 2>&1; then
        log_success "Ready"
        break
    fi
    sleep 1
    echo -n "."
    if [ $i -eq 30 ]; then
        log_error "PostgreSQL failed to start"
        $DOCKER_COMPOSE logs postgres
        exit 1
    fi
done

echo -n "   Backend API: "
for i in {1..30}; do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        log_success "Ready"
        break
    fi
    sleep 1
    echo -n "."
    if [ $i -eq 30 ]; then
        log_error "Backend API failed to start"
        $DOCKER_COMPOSE logs mcp-backend
        exit 1
    fi
done

echo -n "   Frontend: "
# Give the frontend a short grace period before declaring a crash to avoid false alarms
FRONTEND_GRACE_SECS=10
for i in {1..120}; do
  if curl -sf http://localhost:3001 >/dev/null 2>&1; then
    log_success "Ready"
    break
  fi

  # Only consider it a crash if the container exists and has exited
  if [ "$i" -gt "$FRONTEND_GRACE_SECS" ]; then
    if docker ps -a --filter "name=mcp-frontend" --filter "status=exited" --format '{{.Names}}' | grep -q "mcp-frontend"; then
      echo ""
      log_error "Frontend container exited during startup"
      echo ""
      echo "📋 Frontend logs:"
      $DOCKER_COMPOSE logs frontend
      exit 1
    fi
  fi

  sleep 1
  echo -n "."

  if [ $((i % 15)) -eq 0 ]; then
    echo ""
    echo -n "   Still starting (${i}s)... "
  fi

  if [ $i -eq 120 ]; then
    echo ""
    log_error "Frontend failed to start within 2 minutes"
    echo ""
    echo "📋 Frontend logs:"
    $DOCKER_COMPOSE logs frontend
    exit 1
  fi
done

echo ""

log_info "Service Status:"
$DOCKER_COMPOSE ps
echo ""

log_success "Application is ready!"
echo ""
echo "📍 Access Points:"
echo "   🌐 Chat Interface:  http://localhost:3001"
echo "   🔧 Backend API:     http://localhost:8000"
echo "   📚 API Docs:        http://localhost:8000/docs"
echo "   🏥 Health Check:    http://localhost:8000/health"
echo ""
log_info "Running quick diagnostics..."
# Check if backend has an OpenAI key set
BACKEND_KEY_LEN=$($DOCKER_COMPOSE exec -T mcp-backend /bin/sh -lc 'printf "%s" "$OPENAI_API_KEY" | wc -c' 2>/dev/null || echo 0)
# Check conversation count via health endpoint (more stable than parsing /conversations)
HEALTH_JSON=$(curl -sf http://localhost:8000/health || true)
CONV_COUNT=$(printf "%s" "$HEALTH_JSON" | grep -o '"conversation_count":[0-9]*' | sed 's/[^0-9]//g')
[ -z "$CONV_COUNT" ] && CONV_COUNT=0

if [ "$CONV_COUNT" -eq 0 ]; then
  log_warning "No conversations found yet; chat may show fallback due to no context."
  echo "   Tip: POST a small dataset to /ingest or use sample-data.json to seed content."
fi

if [ "$BACKEND_KEY_LEN" -gt 1 ]; then
  # If key exists but recent logs show insufficient_quota, inform the user
  if $DOCKER_COMPOSE logs --tail=300 mcp-backend 2>/dev/null | grep -qi "insufficient_quota"; then
    log_warning "OpenAI API key is configured, but requests are failing due to insufficient quota."
    echo "   LLM answers will fall back to context summaries until quota/billing is resolved."
    echo "   See: https://platform.openai.com/account/billing"
  fi
else
  log_warning "OPENAI_API_KEY is not set in the backend container; chat will use fallback answers."
  echo "   Set OPENAI_API_KEY in your .env and rerun this script to enable LLM answers."
fi

echo "📋 Quick Commands:"
echo "   View logs:          $DOCKER_COMPOSE logs -f"
echo "   View frontend logs: $DOCKER_COMPOSE logs -f frontend"
echo "   Stop services:      $DOCKER_COMPOSE down"
echo "   Restart:            $DOCKER_COMPOSE restart"
echo ""
echo "💡 Next Steps:"
echo "   1. Open http://localhost:3001 in your browser"
echo "   2. Try asking: 'How do I fix connection errors?'"
echo "   3. Check logs if you encounter issues: $DOCKER_COMPOSE logs -f"
echo ""

if command -v open &> /dev/null; then
    read -p "Open browser now? (y/n): " answer
    if [ "$answer" = "y" ]; then
        open http://localhost:3001
    fi
fi