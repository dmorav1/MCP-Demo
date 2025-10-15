"""
Tests for Slack channel reading and ingestion into MCP backend.
Validates the complete flow: Slack → Ingest → Database → Search
"""
import pytest
import os
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app as fastapi_app
from app.database import get_db, Base
from app.slack.tools.slack_ingest_processor import (
    build_ingest_payload,
    resolve_channel_id,
    build_user_names
)

# Test database URL (use a dedicated test database/port)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://mcp_user:mcp_password@localhost:5433/mcp_db"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def setup_database():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(setup_database):
    """Provide a TestClient with DB dependency override for Slack tests."""
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    # Cleanup override
    fastapi_app.dependency_overrides.pop(get_db, None)


class MockSlackClient:
    """Mock Slack WebClient for testing"""
    
    def __init__(self, channels: List[Dict], messages: List[Dict], users: Dict[str, str]):
        self.channels = channels
        self.messages = messages
        self.users = users
    
    def conversations_list(self, types: str = "", limit: int = 1000, cursor: str = None):
        """Mock conversations_list API call"""
        return {
            "channels": self.channels,
            "response_metadata": {"next_cursor": None}
        }
    
    def conversations_history(self, channel: str, limit: int = 200, **kwargs):
        """Mock conversations_history API call"""
        filtered_messages = self.messages.copy()
        
        # Filter by oldest timestamp if provided
        if "oldest" in kwargs:
            oldest = float(kwargs["oldest"])
            filtered_messages = [
                m for m in filtered_messages 
                if float(m.get("ts", "0")) > oldest
            ]
        
        return {
            "messages": filtered_messages,
            "has_more": False,
            "response_metadata": {"next_cursor": None}
        }
    
    def users_info(self, user: str):
        """Mock users_info API call"""
        return {
            "user": {
                "name": self.users.get(user, user),
                "real_name": self.users.get(user, user)
            }
        }


def test_resolve_channel_id_success():
    """Test resolving channel name to ID"""
    mock_client = MockSlackClient(
        channels=[
            {"id": "C123456", "name": "warchan-ai"},
            {"id": "C789012", "name": "general"}
        ],
        messages=[],
        users={}
    )
    
    channel_id = resolve_channel_id(mock_client, "warchan-ai")
    assert channel_id == "C123456"


def test_resolve_channel_id_with_hash_prefix():
    """Test resolving channel name with # prefix"""
    mock_client = MockSlackClient(
        channels=[{"id": "C123456", "name": "warchan-ai"}],
        messages=[],
        users={}
    )
    
    channel_id = resolve_channel_id(mock_client, "#warchan-ai")
    assert channel_id == "C123456"


def test_resolve_channel_id_not_found():
    """Test resolving non-existent channel"""
    mock_client = MockSlackClient(
        channels=[{"id": "C123456", "name": "other-channel"}],
        messages=[],
        users={}
    )
    
    channel_id = resolve_channel_id(mock_client, "nonexistent")
    assert channel_id is None


def test_build_user_names():
    """Test building user name mapping"""
    mock_client = MockSlackClient(
        channels=[],
        messages=[],
        users={
            "U123": "Alice",
            "U456": "Bob"
        }
    )
    
    user_map = build_user_names(mock_client, {"U123", "U456"})
    assert user_map["U123"] == "Alice"
    assert user_map["U456"] == "Bob"


def test_build_ingest_payload_with_valid_messages():
    """Test building ingest payload with valid Slack messages"""
    now = datetime.now(tz=timezone.utc).timestamp()
    messages = [
        {
            "ts": str(now - 120),
            "user": "U123",
            "user_name": "Alice",
            "text": "Hello, this is a test message"
        },
        {
            "ts": str(now - 60),
            "user": "U456",
            "user_name": "Bob",
            "text": "This is a reply to the test"
        },
        {
            "ts": str(now),
            "user": "U123",
            "user_name": "Alice",
            "text": "Thanks for the reply!"
        }
    ]
    
    payload = build_ingest_payload(messages, "warchan-ai", min_messages=2)
    
    assert payload is not None
    assert payload["scenario_title"].startswith("#warchan-ai conversation")
    assert payload["url"] == "slack://channel/warchan-ai"
    assert len(payload["messages"]) == 3
    assert payload["messages"][0]["author_name"] == "Alice"
    assert payload["messages"][0]["content"] == "Hello, this is a test message"


def test_build_ingest_payload_filters_empty_messages():
    """Test that empty messages are filtered out"""
    now = datetime.now(tz=timezone.utc).timestamp()
    messages = [
        {
            "ts": str(now - 60),
            "user": "U123",
            "user_name": "Alice",
            "text": "Valid message"
        },
        {
            "ts": str(now),
            "user": "U456",
            "user_name": "Bob",
            "text": ""  # Empty message should be filtered
        }
    ]
    
    payload = build_ingest_payload(messages, "warchan-ai", min_messages=1)
    
    assert payload is not None
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["content"] == "Valid message"


def test_build_ingest_payload_respects_min_messages():
    """Test that min_messages threshold is respected"""
    now = datetime.now(tz=timezone.utc).timestamp()
    messages = [
        {
            "ts": str(now),
            "user": "U123",
            "user_name": "Alice",
            "text": "Only one message"
        }
    ]
    
    # Should return None if below threshold
    payload = build_ingest_payload(messages, "warchan-ai", min_messages=5)
    assert payload is None
    
    # Should return payload if at threshold
    payload = build_ingest_payload(messages, "warchan-ai", min_messages=1)
    assert payload is not None


@pytest.mark.integration
def test_slack_ingest_end_to_end(client, setup_database):
    """
    Integration test: Simulate Slack messages → Ingest → Verify in database
    This tests the complete flow without actually connecting to Slack
    """
    # Simulate Slack message data
    now = datetime.now(tz=timezone.utc)
    ingest_payload = {
        "scenario_title": f"#warchan-ai conversation ({now.strftime('%Y-%m-%d %H:%M')})",
        "original_title": f"Slack #warchan-ai - {now.strftime('%Y-%m-%d')}",
        "url": "slack://channel/warchan-ai",
        "messages": [
            {
                "author_name": "Alice",
                "author_type": "human",
                "content": "How do I fix the database connection error?",
                "timestamp": now.isoformat()
            },
            {
                "author_name": "Bob",
                "author_type": "human",
                "content": "Check your DATABASE_URL environment variable",
                "timestamp": now.isoformat()
            },
            {
                "author_name": "Alice",
                "author_type": "human",
                "content": "Thanks! That fixed it.",
                "timestamp": now.isoformat()
            }
        ]
    }
    
    # Ingest the conversation
    ingest_response = client.post("/ingest", json=ingest_payload)
    assert ingest_response.status_code == 200
    
    ingest_data = ingest_response.json()
    assert ingest_data["chunks"] == 3
    conversation_id = ingest_data["conversation_id"]
    
    # Verify conversation was stored
    get_response = client.get(f"/conversations/{conversation_id}")
    assert get_response.status_code == 200
    
    conversation = get_response.json()
    assert conversation["scenario_title"] == ingest_payload["scenario_title"]
    assert len(conversation["chunks"]) == 3
    
    # Verify search finds the conversation
    search_response = client.get("/search?q=database+connection&top_k=5")
    assert search_response.status_code == 200
    
    search_data = search_response.json()
    assert len(search_data["results"]) > 0
    
    # Verify at least one result matches our conversation
    conversation_ids = [r["conversation_id"] for r in search_data["results"]]
    assert conversation_id in conversation_ids


@pytest.mark.integration
def test_multiple_slack_channels(client, setup_database):
    """Test ingesting messages from multiple Slack channels"""
    now = datetime.now(tz=timezone.utc)
    
    channels = ["warchan-ai", "tech-support", "dev-team"]
    conversation_ids = []
    
    for channel in channels:
        payload = {
            "scenario_title": f"#{channel} conversation ({now.strftime('%Y-%m-%d %H:%M')})",
            "original_title": f"Slack #{channel}",
            "url": f"slack://channel/{channel}",
            "messages": [
                {
                    "author_name": "User1",
                    "author_type": "human",
                    "content": f"Message from {channel}",
                    "timestamp": now.isoformat()
                }
            ]
        }
        
        response = client.post("/ingest", json=payload)
        assert response.status_code == 200
        conversation_ids.append(response.json()["conversation_id"])
    
    # Verify all conversations were stored
    for conv_id in conversation_ids:
        response = client.get(f"/conversations/{conv_id}")
        assert response.status_code == 200



@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("SLACK_CHANNEL"),
    reason="SLACK_BOT_TOKEN and SLACK_CHANNEL must be set for live Slack tests"
)
def test_live_slack_connection():
    """
    Live test against actual Slack API (only runs if credentials are provided)
    This test validates real Slack connectivity
    """
    import ssl
    import certifi
    from slack_sdk import WebClient
    
    token = os.getenv("SLACK_BOT_TOKEN")
    channel_name = os.getenv("SLACK_CHANNEL", "warchan-ai")
    
    # Create Slack client with proper SSL context
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    client = WebClient(token=token, ssl=ssl_context)
    
    # Test 1: Resolve channel ID
    channel_id = resolve_channel_id(client, channel_name)
    assert channel_id is not None, f"Could not resolve channel #{channel_name}"
    
    # Test 2: Fetch recent messages
    try:
        response = client.conversations_history(channel=channel_id, limit=10)
        messages = response.get("messages", [])
        assert isinstance(messages, list), "Expected messages list from Slack"
        print(f"✅ Successfully fetched {len(messages)} messages from #{channel_name}")
    except Exception as e:
        pytest.fail(f"Failed to fetch messages: {e}")


def test_slack_message_timestamp_ordering():
    """Test that Slack messages are correctly ordered by timestamp"""
    t1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc).timestamp()
    t2 = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc).timestamp()
    t3 = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc).timestamp()
    
    # Messages in random order
    messages = [
        {"ts": str(t2), "user": "U1", "user_name": "Bob", "text": "Second"},
        {"ts": str(t1), "user": "U2", "user_name": "Alice", "text": "First"},
        {"ts": str(t3), "user": "U1", "user_name": "Bob", "text": "Third"}
    ]
    
    payload = build_ingest_payload(messages, "test-channel", min_messages=1)
    assert payload is not None
    
    # Verify messages are chronologically ordered
    assert payload["messages"][0]["content"] == "First"
    assert payload["messages"][1]["content"] == "Second"
    assert payload["messages"][2]["content"] == "Third"


def test_slack_state_file_operations():
    """Test loading and saving Slack ingestion state"""
    from app.slack.tools.slack_ingest_processor import load_state, save_state
    import tempfile
    import os
    
    # Create temporary state file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        state_file = f.name
    
    try:
        # Test saving state
        test_timestamp = "1234567890.123456"
        save_state(state_file, test_timestamp)
        
        # Test loading state
        loaded_timestamp = load_state(state_file)
        assert loaded_timestamp == test_timestamp
        
        # Test loading non-existent file
        non_existent_state = load_state("/tmp/nonexistent_state.json")
        assert non_existent_state is None
        
    finally:
        # Cleanup
        if os.path.exists(state_file):
            os.remove(state_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])