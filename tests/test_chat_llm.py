import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine
import importlib


@pytest.fixture(scope="module", autouse=True)
def _module_schema():
    """Ensure production engine schema exists for this module.

    Redundant with session-level ensure_schema but added defensively because
    earlier full-suite runs showed race/ordering issues where tables were
    absent for this module while present for others. Creating with checkfirst
    is idempotent and inexpensive for the small schema we have.
    """
    importlib.import_module("app.models")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    yield
    # Do not drop here; session-level teardown handles cleanup.


class DummyChoice:
    def __init__(self, content: str):
        class Msg:  # minimal message wrapper
            def __init__(self, c):
                self.content = c
        self.message = Msg(content)

class DummyCompletionResponse:
    def __init__(self, answer: str):
        self.choices = [DummyChoice(answer)]

@pytest.fixture(autouse=True)
def set_openai_key(monkeypatch):
    # Ensure key is present so gateway attempts OpenAI path
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    # Patch AsyncOpenAI client used in mcp_gateway.get_openai_client
    from app import mcp_gateway

    class DummyChatCompletions:
        async def create(self, model, messages, temperature=0.7, max_tokens=800, stream=False):
            assert not stream
            # Return deterministic response
            return DummyCompletionResponse("This is a mocked LLM answer.")

    class DummyChat:
        def __init__(self):
            self.completions = DummyChatCompletions()

    class DummyClient:
        def __init__(self):
            self.chat = DummyChat()

    # Force regeneration each test
    mcp_gateway._cached_openai_client = DummyClient()
    mcp_gateway._cached_openai_key = "sk-test-key"
    yield
    # Cleanup
    mcp_gateway._cached_openai_client = None
    mcp_gateway._cached_openai_key = None


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_uses_llm_path(client):
    # Ingest a tiny conversation so context exists
    ing = client.post("/ingest", json={
        "scenario_title": "LLM Test",
        "messages": [
            {"author_name": "User", "author_type": "human", "content": "Install packages with pip"}
        ]
    })
    assert ing.status_code == 200

    resp = client.post("/chat/ask", json={"content": "How do I install?", "conversation_history": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"].startswith("This is a mocked LLM answer.")
    # Ensure fallback marker absent
    assert "Fallback answer" not in data["answer"]
    assert isinstance(data.get("context_used"), list)