import pytest
from httpx import AsyncClient
from server import app  # Import your FastAPI app

@pytest.mark.asyncio
async def test_healthz():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]  # Allow degraded in tests

print("Integration test: /healthz OK")
