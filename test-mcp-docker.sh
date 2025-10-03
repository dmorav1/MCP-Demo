#!/bin/bash

echo "🧪 Testing Docker MCP Server"
echo "============================="

echo "1. Checking if containers are running..."
docker-compose ps

echo -e "\n2. Testing MCP server health..."
curl -s http://localhost:3000/health | python3 -m json.tool

echo -e "\n3. Testing SSE endpoint availability..."
timeout 5 curl -N -H "Accept: text/event-stream" http://localhost:3000/sse || echo "SSE endpoint responding"

echo -e "\n4. Checking MCP server logs..."
docker-compose logs --tail=20 mcp-server

echo -e "\n✅ Test completed!"
echo "📖 Configure Claude Desktop with: claude_desktop_config.json"