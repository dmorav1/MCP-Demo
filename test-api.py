#!/usr/bin/env python3
"""
Simple test script to verify the MCP Backend API functionality
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed!")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the API. Is the server running?")
        return False

def test_ingest_conversation():
    """Test conversation ingestion"""
    print("\n📥 Testing conversation ingestion...")
    
    # Load sample data
    try:
        with open("sample-data.json", "r") as f:
            sample_data = json.load(f)
    except FileNotFoundError:
        print("❌ sample-data.json not found. Please ensure it exists in the current directory.")
        return None
    
    try:
        response = requests.post(f"{BASE_URL}/ingest", json=sample_data)
        if response.status_code == 201:
            conversation_data = response.json()
            print(f"✅ Conversation ingested successfully! ID: {conversation_data['id']}")
            return conversation_data['id']
        else:
            print(f"❌ Ingestion failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during ingestion: {e}")
        return None

def test_search_conversations(conversation_id):
    """Test conversation search"""
    print("\n🔍 Testing conversation search...")
    
    test_queries = [
        "mobile app crashes",
        "iOS 17.2",
        "reinstall app",
        "settings page",
        "support chat"
    ]
    
    for query in test_queries:
        try:
            response = requests.get(f"{BASE_URL}/search", params={"q": query, "top_k": 3})
            if response.status_code == 200:
                search_results = response.json()
                print(f"✅ Search for '{query}' returned {search_results['total_results']} results")
                if search_results['total_results'] > 0:
                    print(f"   Top result relevance: {search_results['results'][0]['relevance_score']:.3f}")
            else:
                print(f"❌ Search failed for '{query}' with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error during search for '{query}': {e}")

def test_get_conversation(conversation_id):
    """Test getting a specific conversation"""
    print(f"\n📖 Testing get conversation by ID ({conversation_id})...")
    
    try:
        response = requests.get(f"{BASE_URL}/conversations/{conversation_id}")
        if response.status_code == 200:
            conversation = response.json()
            print(f"✅ Retrieved conversation: {conversation['scenario_title']}")
            print(f"   Number of chunks: {len(conversation['chunks'])}")
            return True
        else:
            print(f"❌ Get conversation failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting conversation: {e}")
        return False

def test_list_conversations():
    """Test listing all conversations"""
    print("\n📋 Testing list conversations...")
    
    try:
        response = requests.get(f"{BASE_URL}/conversations")
        if response.status_code == 200:
            conversations = response.json()
            print(f"✅ Retrieved {len(conversations)} conversations")
            return True
        else:
            print(f"❌ List conversations failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing conversations: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 MCP Backend API Test Suite")
    print("=" * 40)
    
    # Test health check first
    if not test_health_check():
        print("\n❌ Cannot proceed without a healthy API connection.")
        sys.exit(1)
    
    # Wait a moment for embeddings service to be ready
    print("\n⏳ Waiting for services to be fully ready...")
    time.sleep(2)
    
    # Test conversation ingestion
    conversation_id = test_ingest_conversation()
    if conversation_id is None:
        print("\n❌ Cannot proceed without successful ingestion.")
        sys.exit(1)
    
    # Wait for embedding processing
    print("\n⏳ Waiting for embedding processing...")
    time.sleep(3)
    
    # Test search functionality
    test_search_conversations(conversation_id)
    
    # Test get conversation
    test_get_conversation(conversation_id)
    
    # Test list conversations
    test_list_conversations()
    
    print("\n🎉 Test suite completed!")
    print("\n📖 You can also test the API interactively at: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
