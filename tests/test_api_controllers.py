"""
Comprehensive tests for the new hexagonal architecture API controllers.

Tests cover:
- Conversation endpoints (ingest, list, get, delete)
- Search endpoints (POST and GET)
- RAG endpoints (ask, ask-stream, health)
- Error handling
- Input validation
- Edge cases
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch, AsyncMock
import os
import json

from app.main import app as fastapi_app
from app.database import get_db, Base
from app.adapters.inbound.api.dependencies import (
    get_ingest_use_case, get_search_use_case, get_rag_service
)
from app.application.dto import (
    IngestConversationResponse, ConversationMetadataDTO,
    SearchConversationResponse, SearchResultDTO
)


# Test database URL
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://mcp_user:mcp_password@localhost:5433/mcp_db"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def setup_database():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(setup_database):
    """Provide a TestClient with DB dependency override."""
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.pop(get_db, None)


# ============================================================================
# Conversation Endpoints Tests
# ============================================================================

class TestConversationIngest:
    """Tests for POST /conversations/ingest endpoint."""
    
    def test_ingest_basic_conversation(self, client):
        """Test ingesting a basic conversation."""
        data = {
            "messages": [
                {"text": "Hello, I need help", "author_name": "User", "author_type": "user"},
                {"text": "How can I help you?", "author_name": "Assistant", "author_type": "assistant"}
            ],
            "scenario_title": "Basic Help"
        }
        response = client.post("/conversations/ingest", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["success"] is True
        assert "conversation_id" in result
        assert result["chunks_created"] >= 1
    
    def test_ingest_with_all_metadata(self, client):
        """Test ingesting conversation with all metadata fields."""
        data = {
            "messages": [
                {"text": "Test message", "author_name": "User", "author_type": "user"}
            ],
            "scenario_title": "Test Scenario",
            "original_title": "Original Title",
            "url": "https://example.com/conversation/123"
        }
        response = client.post("/conversations/ingest", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["success"] is True
        assert result["metadata"]["scenario_title"] == "Test Scenario"
        assert result["metadata"]["url"] == "https://example.com/conversation/123"
    
    def test_ingest_empty_messages(self, client):
        """Test ingesting conversation with empty messages."""
        data = {
            "messages": [],
            "scenario_title": "Empty Test"
        }
        response = client.post("/conversations/ingest", json=data)
        # Should fail validation
        assert response.status_code in [400, 422]
    
    def test_ingest_missing_required_fields(self, client):
        """Test ingesting conversation without required fields."""
        data = {
            "scenario_title": "Missing Messages"
        }
        response = client.post("/conversations/ingest", json=data)
        assert response.status_code == 422
    
    def test_ingest_long_messages(self, client):
        """Test ingesting conversation with very long messages."""
        long_text = "This is a long message. " * 200  # ~5000 characters
        data = {
            "messages": [
                {"text": long_text, "author_name": "User", "author_type": "user"}
            ]
        }
        response = client.post("/conversations/ingest", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["success"] is True


class TestConversationList:
    """Tests for GET /conversations endpoint."""
    
    def test_list_conversations_default_pagination(self, client):
        """Test listing conversations with default pagination."""
        # Ingest a test conversation first
        data = {
            "messages": [{"text": "Test", "author_name": "User"}],
            "scenario_title": "List Test"
        }
        client.post("/conversations/ingest", json=data)
        
        response = client.get("/conversations")
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        if len(result) > 0:
            assert "id" in result[0]
            assert "chunk_count" in result[0]
    
    def test_list_conversations_custom_pagination(self, client):
        """Test listing conversations with custom pagination."""
        response = client.get("/conversations?skip=0&limit=10")
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) <= 10
    
    def test_list_conversations_invalid_pagination(self, client):
        """Test listing conversations with invalid pagination."""
        response = client.get("/conversations?skip=-1")
        assert response.status_code == 422
        
        response = client.get("/conversations?limit=0")
        assert response.status_code == 422
        
        response = client.get("/conversations?limit=101")
        assert response.status_code == 422


class TestConversationGet:
    """Tests for GET /conversations/{id} endpoint."""
    
    def test_get_existing_conversation(self, client):
        """Test getting an existing conversation."""
        # Ingest a conversation first
        data = {
            "messages": [
                {"text": "Message 1", "author_name": "User"},
                {"text": "Message 2", "author_name": "Assistant"}
            ],
            "scenario_title": "Get Test"
        }
        ingest_response = client.post("/conversations/ingest", json=data)
        conv_id = ingest_response.json()["conversation_id"]
        
        response = client.get(f"/conversations/{conv_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == int(conv_id)
        assert "chunks" in result
        assert len(result["chunks"]) >= 1
    
    def test_get_nonexistent_conversation(self, client):
        """Test getting a non-existent conversation."""
        response = client.get("/conversations/999999")
        assert response.status_code == 404
        result = response.json()
        assert "error" in result
    
    def test_get_conversation_invalid_id(self, client):
        """Test getting conversation with invalid ID."""
        response = client.get("/conversations/invalid")
        assert response.status_code == 422


class TestConversationDelete:
    """Tests for DELETE /conversations/{id} endpoint."""
    
    def test_delete_existing_conversation(self, client):
        """Test deleting an existing conversation."""
        # Ingest a conversation first
        data = {
            "messages": [{"text": "To be deleted", "author_name": "User"}],
            "scenario_title": "Delete Test"
        }
        ingest_response = client.post("/conversations/ingest", json=data)
        conv_id = ingest_response.json()["conversation_id"]
        
        # Delete it
        response = client.delete(f"/conversations/{conv_id}")
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert result["conversation_id"] == int(conv_id)
        
        # Verify it's deleted
        get_response = client.get(f"/conversations/{conv_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_conversation(self, client):
        """Test deleting a non-existent conversation."""
        response = client.delete("/conversations/999999")
        assert response.status_code == 404
        result = response.json()
        assert "error" in result


# ============================================================================
# Search Endpoints Tests
# ============================================================================

class TestSearchPost:
    """Tests for POST /search endpoint."""
    
    def test_search_basic_query(self, client):
        """Test basic search query."""
        # Ingest test data first
        data = {
            "messages": [
                {"text": "Python programming is great for data science", "author_name": "User"}
            ]
        }
        client.post("/conversations/ingest", json=data)
        
        search_data = {
            "query": "Python programming",
            "top_k": 5
        }
        response = client.post("/search", json=search_data)
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert "query" in result
        assert result["query"] == "Python programming"
    
    def test_search_with_filters(self, client):
        """Test search with filters."""
        search_data = {
            "query": "test query",
            "top_k": 5,
            "filters": {
                "author_type": "user",
                "min_score": 0.5
            }
        }
        response = client.post("/search", json=search_data)
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
    
    def test_search_empty_query(self, client):
        """Test search with empty query."""
        search_data = {
            "query": "",
            "top_k": 5
        }
        response = client.post("/search", json=search_data)
        # Should fail validation
        assert response.status_code in [400, 422]
    
    def test_search_invalid_top_k(self, client):
        """Test search with invalid top_k."""
        search_data = {
            "query": "test",
            "top_k": 0
        }
        response = client.post("/search", json=search_data)
        assert response.status_code == 422
        
        search_data["top_k"] = 101
        response = client.post("/search", json=search_data)
        assert response.status_code == 422


class TestSearchGet:
    """Tests for GET /search endpoint."""
    
    def test_search_get_basic(self, client):
        """Test basic GET search."""
        # Ingest test data
        data = {
            "messages": [{"text": "Machine learning tutorial", "author_name": "User"}]
        }
        client.post("/conversations/ingest", json=data)
        
        response = client.get("/search?q=machine learning&top_k=5")
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert result["query"] == "machine learning"
    
    def test_search_get_with_filters(self, client):
        """Test GET search with filters."""
        response = client.get("/search?q=test&top_k=5&author_type=user&min_score=0.7")
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
    
    def test_search_get_missing_query(self, client):
        """Test GET search without query."""
        response = client.get("/search")
        assert response.status_code == 422


# ============================================================================
# RAG Endpoints Tests
# ============================================================================

class TestRAGAsk:
    """Tests for POST /rag/ask endpoint."""
    
    def test_rag_ask_basic(self, client):
        """Test basic RAG ask."""
        # Mock RAG service
        mock_result = {
            "answer": "Test answer",
            "sources": [],
            "confidence": 0.8,
            "metadata": {}
        }
        
        mock_rag = AsyncMock()
        mock_rag.ask = AsyncMock(return_value=mock_result)
        
        fastapi_app.dependency_overrides[get_rag_service] = lambda: mock_rag
        
        data = {
            "query": "How do I use Python?",
            "top_k": 5
        }
        response = client.post("/rag/ask", json=data)
        
        # Clean up
        fastapi_app.dependency_overrides.pop(get_rag_service, None)
        
        assert response.status_code == 200
        result = response.json()
        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result
    
    def test_rag_ask_with_conversation_id(self, client):
        """Test RAG ask with conversation ID."""
        mock_result = {
            "answer": "Test answer",
            "sources": [],
            "confidence": 0.8,
            "metadata": {}
        }
        
        mock_rag = AsyncMock()
        mock_rag.ask = AsyncMock(return_value=mock_result)
        
        fastapi_app.dependency_overrides[get_rag_service] = lambda: mock_rag
        
        data = {
            "query": "Follow-up question",
            "conversation_id": "test-conv-123"
        }
        response = client.post("/rag/ask", json=data)
        
        fastapi_app.dependency_overrides.pop(get_rag_service, None)
        
        assert response.status_code == 200
    
    def test_rag_ask_empty_query(self, client):
        """Test RAG ask with empty query."""
        data = {
            "query": ""
        }
        response = client.post("/rag/ask", json=data)
        assert response.status_code == 422


class TestRAGStream:
    """Tests for POST /rag/ask-stream endpoint."""
    
    def test_rag_stream_basic(self, client):
        """Test RAG streaming response."""
        async def mock_stream():
            yield "Test "
            yield "streaming "
            yield "response"
        
        mock_rag = AsyncMock()
        mock_rag.ask_streaming = AsyncMock(return_value=mock_stream())
        
        fastapi_app.dependency_overrides[get_rag_service] = lambda: mock_rag
        
        data = {
            "query": "Streaming test"
        }
        response = client.post("/rag/ask-stream", json=data)
        
        fastapi_app.dependency_overrides.pop(get_rag_service, None)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestRAGHealth:
    """Tests for GET /rag/health endpoint."""
    
    def test_rag_health_configured(self, client):
        """Test RAG health when service is configured."""
        mock_config = Mock()
        mock_config.provider = "openai"
        mock_config.model = "gpt-3.5-turbo"
        
        mock_rag = Mock()
        mock_rag.config = mock_config
        mock_rag._get_llm = Mock(return_value=Mock())
        
        fastapi_app.dependency_overrides[get_rag_service] = lambda: mock_rag
        
        response = client.get("/rag/health")
        
        fastapi_app.dependency_overrides.pop(get_rag_service, None)
        
        assert response.status_code == 200
        result = response.json()
        assert "status" in result
        assert "provider" in result
    
    def test_rag_health_not_configured(self, client):
        """Test RAG health when service is not configured."""
        mock_rag = Mock()
        mock_rag.config = None
        
        fastapi_app.dependency_overrides[get_rag_service] = lambda: mock_rag
        
        response = client.get("/rag/health")
        
        fastapi_app.dependency_overrides.pop(get_rag_service, None)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "degraded"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    def test_validation_error_format(self, client):
        """Test validation error response format."""
        data = {
            "messages": []  # Invalid: empty messages
        }
        response = client.post("/conversations/ingest", json=data)
        assert response.status_code in [400, 422]
    
    def test_not_found_error_format(self, client):
        """Test not found error response format."""
        response = client.get("/conversations/999999")
        assert response.status_code == 404
        result = response.json()
        assert "error" in result
        assert "type" in result["error"]
        assert "message" in result["error"]
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/conversations/ingest",
            data="{invalid json}",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_complete_conversation_workflow(self, client):
        """Test complete workflow: ingest -> list -> get -> search -> delete."""
        # 1. Ingest conversation
        ingest_data = {
            "messages": [
                {"text": "I need help with Django", "author_name": "User", "author_type": "user"},
                {"text": "I can help you with Django", "author_name": "Assistant", "author_type": "assistant"}
            ],
            "scenario_title": "Django Help"
        }
        ingest_response = client.post("/conversations/ingest", json=ingest_data)
        assert ingest_response.status_code == 201
        conv_id = ingest_response.json()["conversation_id"]
        
        # 2. List conversations
        list_response = client.get("/conversations")
        assert list_response.status_code == 200
        conversations = list_response.json()
        assert any(c["id"] == int(conv_id) for c in conversations)
        
        # 3. Get specific conversation
        get_response = client.get(f"/conversations/{conv_id}")
        assert get_response.status_code == 200
        conversation = get_response.json()
        assert conversation["id"] == int(conv_id)
        
        # 4. Search for content
        search_response = client.get("/search?q=Django&top_k=5")
        assert search_response.status_code == 200
        
        # 5. Delete conversation
        delete_response = client.delete(f"/conversations/{conv_id}")
        assert delete_response.status_code == 200
        
        # 6. Verify deletion
        verify_response = client.get(f"/conversations/{conv_id}")
        assert verify_response.status_code == 404
    
    def test_search_after_multiple_ingests(self, client):
        """Test search functionality after ingesting multiple conversations."""
        # Ingest multiple conversations
        topics = ["Python", "JavaScript", "Go"]
        for topic in topics:
            data = {
                "messages": [
                    {"text": f"Tell me about {topic} programming", "author_name": "User"}
                ],
                "scenario_title": f"{topic} Discussion"
            }
            response = client.post("/conversations/ingest", json=data)
            assert response.status_code == 201
        
        # Search for each topic
        for topic in topics:
            response = client.get(f"/search?q={topic}&top_k=10")
            assert response.status_code == 200


# ============================================================================
# Performance and Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_max_pagination_limit(self, client):
        """Test maximum pagination limit."""
        response = client.get("/conversations?limit=100")
        assert response.status_code == 200
    
    def test_unicode_content(self, client):
        """Test handling of Unicode content."""
        data = {
            "messages": [
                {"text": "Hello 你好 مرحبا שלום", "author_name": "User"}
            ]
        }
        response = client.post("/conversations/ingest", json=data)
        assert response.status_code == 201
    
    def test_special_characters_in_search(self, client):
        """Test search with special characters."""
        response = client.get("/search?q=test@#$%&top_k=5")
        assert response.status_code == 200
    
    def test_very_long_url(self, client):
        """Test conversation with very long URL."""
        long_url = "https://example.com/" + "a" * 1000
        data = {
            "messages": [{"text": "Test", "author_name": "User"}],
            "url": long_url
        }
        response = client.post("/conversations/ingest", json=data)
        # Should either accept or reject gracefully
        assert response.status_code in [200, 201, 400, 422]
