#!/bin/bash
// filepath: fix-npm-issues.sh

echo "🔧 Fixing NPM Issues"
echo "===================="
echo ""

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    DC="docker compose"
fi

# Stop frontend container
echo "1️⃣ Stopping frontend container..."
$DC stop frontend
$DC rm -f frontend

# Remove node_modules volume
echo "2️⃣ Removing node_modules..."
docker volume ls | grep node_modules && docker volume rm $(docker volume ls -q | grep node_modules) || echo "No node_modules volume found"

# Clear npm cache in new container
echo "3️⃣ Clearing npm cache..."
docker run --rm -v $(pwd)/frontend:/app -w /app node:18-alpine npm cache clean --force

# Remove package-lock.json
echo "4️⃣ Removing package-lock.json..."
rm -f frontend/package-lock.json

# Rebuild without cache
echo "5️⃣ Rebuilding frontend image..."
$DC build --no-cache frontend

# Start frontend
echo "6️⃣ Starting frontend..."
$DC up -d frontend

# Follow logs
echo "7️⃣ Watching frontend logs (Ctrl+C to exit)..."
$DC logs -f frontend