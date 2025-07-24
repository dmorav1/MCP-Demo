#!/usr/bin/env python3
"""
Quick verification test for the MCP Backend API
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_basic_endpoints():
    """Test basic endpoints without embeddings"""
    print("🧪 Quick MCP Backend API Test")
    print("=" * 40)
    
    # Test health check
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed!")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test root endpoint
    print("\n🏠 Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ Root endpoint works!")
            data = response.json()
            print(f"   Available endpoints: {list(data.get('endpoints', {}).keys())}")
        else:
            print(f"❌ Root endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test list conversations (should be empty initially)
    print("\n📋 Testing list conversations...")
    try:
        response = requests.get(f"{BASE_URL}/conversations", timeout=5)
        if response.status_code == 200:
            conversations = response.json()
            print(f"✅ List conversations works! Found {len(conversations)} conversations")
        else:
            print(f"❌ List conversations failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ List conversations error: {e}")
    
    print(f"\n🎉 Quick test completed!")
    print(f"📖 API Documentation: {BASE_URL}/docs")
    print(f"🏥 Health Check: {BASE_URL}/health")
    
    return True

if __name__ == "__main__":
    test_basic_endpoints()
