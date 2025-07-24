#!/bin/bash

echo "🧪 MCP Backend API Quick Test"
echo "================================"

echo "🏥 Testing health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool

echo -e "\n🏠 Testing root endpoint..."
curl -s http://localhost:8000/ | python3 -m json.tool

echo -e "\n📋 Testing conversations list..."
curl -s http://localhost:8000/conversations | python3 -m json.tool

echo -e "\n✅ Test completed!"
echo "📖 API Documentation: http://localhost:8000/docs"
