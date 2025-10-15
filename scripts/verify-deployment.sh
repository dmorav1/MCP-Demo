#!/bin/bash
// filepath: verify-deployment.sh

echo "🔍 Verifying Deployment"
echo "======================="
echo ""

# Check PostgreSQL
echo "1️⃣ PostgreSQL:"
docker-compose exec -T postgres psql -U mcp_user -d mcp_db -c "SELECT version();" 2>/dev/null && echo "✅ Connected" || echo "❌ Failed"
echo ""

# Check Backend Health
echo "2️⃣ Backend API:"
curl -sf http://localhost:8000/health | python3 -m json.tool 2>/dev/null && echo "✅ Healthy" || echo "❌ Failed"
echo ""

# Check Frontend
echo "3️⃣ Frontend:"
curl -sf http://localhost:3001 >/dev/null && echo "✅ Accessible" || echo "❌ Failed"
echo ""

# Test Ingestion
echo "4️⃣ Testing ingestion..."
curl -sf -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_title": "Test",
    "messages": [{"author_name": "User", "content": "Test message"}]
  }' | python3 -m json.tool 2>/dev/null && echo "✅ Working" || echo "❌ Failed"
echo ""

# Test Search
echo "5️⃣ Testing search..."
curl -sf "http://localhost:8000/search?q=test&top_k=1" | python3 -m json.tool 2>/dev/null && echo "✅ Working" || echo "❌ Failed"
echo ""

echo "🎉 Verification complete!"
echo ""
echo "Open http://localhost:3001 to use the chat interface"