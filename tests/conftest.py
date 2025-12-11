"""Test configuration & shared fixtures.

Previously this file was intentionally minimal. Integration tests were failing
with `psycopg.errors.UndefinedTable` because they rely on the application's
default database dependency (engine from `app.database`) while no automatic
schema creation occurred inside the test process (the import of `app.main`
may happen before the database is ready or against an empty instance).

To make integration tests deterministic we create (once per session) the
database schema for the engine used by the production dependency injection.
Unit-style tests in `test_api.py` already override the dependency and manage
their own schema lifecycle; this global fixture is lightweight and safe.

PERFORMANCE OPTIMIZATION:
The sentence-transformers model loading is expensive (~2-3 seconds per load).
To prevent CI timeouts, we:
1. Cache the model at session scope (load once for all tests)
2. Provide mock fixtures for unit tests that don't need real embeddings
3. Pre-warm the model cache before tests run
"""

from app.database import Base, engine
import importlib
import pytest
import threading
import os
from sqlalchemy import text
from app.logging_config import get_logger
from unittest.mock import Mock, patch, MagicMock, AsyncMock

logger = get_logger(__name__)

# Thread-safe schema creation
_schema_lock = threading.Lock()
_schema_created = False

# Global model cache for sentence-transformers (prevents repeated loading)
_sentence_transformer_model = None
_model_load_lock = threading.Lock()


def get_cached_sentence_transformer(model_name: str = "all-MiniLM-L6-v2"):
    """
    Get a cached sentence-transformers model instance.
    
    This prevents repeated model loading during tests, which is the main
    cause of CI timeouts (each load takes ~2-3 seconds).
    """
    global _sentence_transformer_model
    
    with _model_load_lock:
        if _sentence_transformer_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"🔄 Loading sentence-transformers model (ONE TIME): {model_name}")
                _sentence_transformer_model = SentenceTransformer(model_name)
                logger.info(f"✅ Model {model_name} cached for all tests")
            except Exception as e:
                logger.warning(f"⚠️ Could not load sentence-transformers model: {e}")
                return None
        return _sentence_transformer_model


@pytest.fixture(scope="session")
def cached_embedding_model():
    """
    Session-scoped fixture providing a cached sentence-transformers model.
    
    Load the model ONCE per test session to avoid repeated ~2-3 second loads
    that cause CI timeouts.
    """
    return get_cached_sentence_transformer()


@pytest.fixture(scope="session", autouse=True)
def prewarm_embedding_model():
    """
    Pre-warm the embedding model cache at session start.
    
    This ensures the model is loaded once at the beginning of the test session,
    not during individual test execution where it might cause timeouts.
    """
    # Only pre-warm if not running in fast/unit-only mode
    if os.getenv("SKIP_MODEL_PREWARM", "0") != "1":
        model = get_cached_sentence_transformer()
        if model:
            logger.info("🚀 Embedding model pre-warmed for test session")
    yield


@pytest.fixture
def mock_embedding_service():
    """
    Mock embedding service for unit tests that don't need real embeddings.
    
    Returns a mock that provides consistent fake embeddings, avoiding
    the overhead of loading sentence-transformers.
    """
    mock_service = AsyncMock()
    
    # Return a consistent fake embedding (1536 dimensions)
    fake_embedding = [0.1] * 1536
    mock_service.generate_embedding = AsyncMock(return_value=fake_embedding)
    mock_service.generate_embeddings_batch = AsyncMock(
        side_effect=lambda texts: [fake_embedding for _ in texts]
    )
    
    return mock_service


@pytest.fixture
def mock_sentence_transformer():
    """
    Mock for sentence_transformers.SentenceTransformer.
    
    Use this to patch model loading in tests that don't need real embeddings.
    """
    mock_model = Mock()
    mock_model.encode = Mock(return_value=MagicMock(tolist=lambda: [[0.1] * 384]))
    return mock_model


@pytest.fixture
def fast_embedding_patch(mock_sentence_transformer):
    """
    Context manager fixture that patches embedding model loading.
    
    Use in tests to avoid slow model loading:
    
        def test_something(fast_embedding_patch):
            with fast_embedding_patch:
                # Your test code here - embeddings will be mocked
    """
    return patch(
        'sentence_transformers.SentenceTransformer',
        return_value=mock_sentence_transformer
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_schema():
	"""Create all tables for integration tests then drop after session.

	Using autouse ensures any test importing FastAPI app and using the default
	`get_db` dependency has a valid schema. Dropping at the end keeps the test
	environment clean without affecting separately managed test databases that
	use overrides (those bind a different engine and maintain their own schema).

	Skips setup if database is not available (for unit tests).
	Thread-safe to prevent race conditions when tests run in parallel.
	"""
	global _schema_created

	with _schema_lock:
		if _schema_created:
			logger.info("✓ Schema already created by another test")
			yield
			return

		# Ensure models are imported so SQLAlchemy metadata is populated regardless of
		# test module import order.
		importlib.import_module("app.models")

		# Proactively ensure pgvector extension exists (needed for Vector column type)
		try:
			with engine.connect() as conn:
				conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
				conn.commit()
			logger.info("🧩 Ensured pgvector extension is present for tests")
		except Exception as ext_err:
			# If database is not available, skip (for unit tests)
			logger.warning(f"⚠️ Database not available, skipping schema setup (OK for unit tests): {ext_err}")
			yield
			return

		# Create all tables
		try:
			Base.metadata.create_all(bind=engine, checkfirst=True)
			logger.info("🛠️ Test database schema created")
			_schema_created = True
		except Exception as schema_err:
			logger.warning(f"⚠️ Could not create test schema (OK for unit tests): {schema_err}")
			yield
			return

	yield

	yield

	with _schema_lock:
		try:
			Base.metadata.drop_all(bind=engine)
			_schema_created = False
		except Exception:
			# Dropping is best-effort; ignore teardown errors to not mask test results.
			pass


@pytest.fixture(autouse=True)
def reset_di_container():
    """Reset the DI container and configuration state before each test.
    
    This prevents state pollution between tests, ensuring that tests relying on
    fresh container initialization (like integration tests using TestClient)
    don't inherit a corrupted or partial container from unit tests.
    """
    import app.infrastructure.container as container_module
    import os
    
    # Force new architecture for tests
    os.environ["USE_NEW_ARCHITECTURE"] = "true"
    
    # Reset configuration flag to allow re-initialization
    container_module._configured = False
    
    # Clear registered services
    container_module._container._services = {}
    
    yield
    
    # Clean up after test as well
    container_module._configured = False
    container_module._container._services = {}

