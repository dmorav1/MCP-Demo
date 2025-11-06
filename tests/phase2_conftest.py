"""
Conftest for Phase 2 application layer tests.

These are pure unit tests that don't require database connections.
"""
import pytest

# Disable the autouse session fixture from the main conftest for these tests
@pytest.fixture(scope="session", autouse=False)
def ensure_schema():
    """Override to disable automatic database schema setup for unit tests."""
    pass
