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
"""

from app.database import Base, engine
import importlib
import pytest
from sqlalchemy import text
from app.logging_config import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def ensure_schema():
	"""Create all tables for integration tests then drop after session.

	Using autouse ensures any test importing FastAPI app and using the default
	`get_db` dependency has a valid schema. Dropping at the end keeps the test
	environment clean without affecting separately managed test databases that
	use overrides (those bind a different engine and maintain their own schema).
	
	Skips setup if database is not available (for unit tests).
	"""
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
	except Exception as schema_err:
		logger.warning(f"⚠️ Could not create test schema (OK for unit tests): {schema_err}")
		yield
		return
		
	yield
	
	try:
		Base.metadata.drop_all(bind=engine)
	except Exception:
		# Dropping is best-effort; ignore teardown errors to not mask test results.
		pass

