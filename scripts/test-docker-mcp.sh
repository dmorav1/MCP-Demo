#!/bin/bash

echo "🧪 Testing Docker MCP Server Setup"
echo "===================================="
echo ""

# Check if docker-compose command exists
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif command -v /usr/local/bin/docker-compose &> /dev/null; then
    DOCKER_COMPOSE="/usr/local/bin/docker-compose"
else
    echo "❌ docker-compose not found"
    exit 1
fi

echo "✅ Using: $DOCKER_COMPOSE"
echo ""

echo "1️⃣  Checking if containers are running..."
$DOCKER_COMPOSE ps
echo ""

echo "2️⃣  Testing FastAPI backend health..."
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo "❌ Backend is not responding"
fi
echo ""

echo "3️⃣  Checking MCP server logs (last 10 lines)..."
$DOCKER_COMPOSE logs --tail=10 mcp-server
echo ""

echo "4️⃣  Testing conversation ingestion..."
curl -s -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_title": "Docker Test",
    "messages": [
      {
        "author_name": "User",
        "content": "Testing Docker MCP setup",
        "timestamp": "2025-01-15T10:00:00Z"
      }
    ]
  }' | python3 -m json.tool
echo ""

echo "5️⃣  Testing search..."
curl -s "http://localhost:8000/search?q=docker&top_k=3" | python3 -m json.tool
echo ""

echo "6️⃣  Checking Claude Desktop configuration..."
if [ -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json" ]; then
    echo "✅ macOS Claude Desktop config exists"
elif [ -f "$HOME/.config/Claude/claude_desktop_config.json" ]; then
    echo "✅ Linux Claude Desktop config exists"
else
    echo "⚠️  Claude Desktop config not found. Run:"
    echo "   mkdir -p ~/Library/Application\\ Support/Claude  # macOS"
    echo "   cp claude_desktop_config.json ~/Library/Application\\ Support/Claude/claude_desktop_config.json"
fi
echo ""

echo "✅ Test completed!"
echo ""
echo "📖 Next steps:"
echo "   1. If not already done, copy claude_desktop_config.json to Claude Desktop config directory"
echo "   2. Restart Claude Desktop completely"
echo "   3. Try asking Claude: 'Search for conversations about docker'"
echo ""
echo "📚 For more information, see: DOCKER_MCP_SETUP.md"
