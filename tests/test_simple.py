import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_simple_health_check():
    """Simple test without complex dependency injection."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_simple_root():
    """Simple test of root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
