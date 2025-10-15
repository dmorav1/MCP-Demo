#!/bin/bash
// filepath: verify-all-services.sh

echo "🔍 Verifying All Services"
echo "========================="
echo ""

# Test backend health
echo "1️⃣ Backend Health:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

# Test conversations endpoint
echo "2️⃣ Conversations Endpoint:"
curl -s http://localhost:8000/conversations | python3 -m json.tool | head -30
echo ""

# Test search endpoint
echo "3️⃣ Search Endpoint:"
curl -s "http://localhost:8000/search?q=test&top_k=1" | python3 -m json.tool
echo ""

# Test frontend
echo "4️⃣ Frontend:"
if curl -sf http://localhost:3001 >/dev/null 2>&1; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend is not accessible"
fi
echo ""

# Check container status
echo "5️⃣ Container Status:"
if command -v docker-compose &> /dev/null; then
    docker-compose ps
else
    docker compose ps
fi
echo ""

echo "✅ Verification complete!"