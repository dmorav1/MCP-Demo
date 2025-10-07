#!/bin/bash
// filepath: diagnose-docker.sh

echo "🔍 Docker Compose Diagnostics"
echo "=============================="
echo ""

# Check Docker installation
echo "1️⃣ Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi
echo "✅ Docker version: $(docker --version)"
echo ""

# Check Docker Compose
echo "2️⃣ Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo "✅ docker-compose version: $(docker-compose --version)"
elif command -v /usr/local/bin/docker-compose &> /dev/null; then
    DOCKER_COMPOSE="/usr/local/bin/docker-compose"
    echo "✅ docker-compose version: $(/usr/local/bin/docker-compose --version)"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    echo "✅ docker compose (plugin) version: $(docker compose version)"
else
    echo "❌ Docker Compose not found"
    exit 1
fi
echo ""

# Check .env file
echo "3️⃣ Checking .env file..."
if [ ! -f .env ]; then
    echo "⚠️ .env file not found - creating from .env.example"
    cp .env.example .env
    echo "📝 Please edit .env and add your OPENAI_API_KEY"
else
    echo "✅ .env file exists"
    if grep -q "OPENAI_API_KEY=sk-" .env; then
        echo "✅ OPENAI_API_KEY is set"
    else
        echo "⚠️ OPENAI_API_KEY may not be set correctly"
    fi
fi
echo ""

# Validate docker-compose.yml
echo "4️⃣ Validating docker-compose.yml..."
$DOCKER_COMPOSE config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors:"
    $DOCKER_COMPOSE config
    exit 1
fi
echo ""

# Check for port conflicts
echo "5️⃣ Checking for port conflicts..."
PORTS=(5433 8000 3001)
for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️ Port $port is already in use:"
        lsof -Pi :$port -sTCP:LISTEN
    else
        echo "✅ Port $port is available"
    fi
done
echo ""

# Check Docker daemon
echo "6️⃣ Checking Docker daemon..."
if docker info >/dev/null 2>&1; then
    echo "✅ Docker daemon is running"
else
    echo "❌ Docker daemon is not running"
    echo "   Start Docker Desktop or run: sudo systemctl start docker"
    exit 1
fi
echo ""

# Try to start services
echo "7️⃣ Attempting to start services..."
$DOCKER_COMPOSE up -d 2>&1 | tee docker-compose-output.log

if [ $? -eq 0 ]; then
    echo "✅ Services started successfully"
    echo ""
    echo "8️⃣ Checking service status..."
    $DOCKER_COMPOSE ps
else
    echo "❌ Failed to start services"
    echo ""
    echo "📋 Error details saved to docker-compose-output.log"
    echo ""
    echo "🔍 Showing last 50 lines of logs:"
    $DOCKER_COMPOSE logs --tail=50
fi