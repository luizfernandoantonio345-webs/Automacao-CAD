"""
Testes de integração para endpoints de saúde do sistema.

- test_healthz_smoke: Verifica que o sistema está no ar (aceita healthy ou degraded)
- test_healthz_strict: Verifica que o sistema está 100% funcional (só healthy)
- test_health_endpoint: Verifica endpoint /health com detalhes
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from server import app

@pytest.mark.asyncio
async def test_healthz_smoke():
    """Smoke test: verifica que o sistema responde (pode estar degradado)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]

@pytest.mark.asyncio
async def test_healthz_strict():
    """
    Teste estrito: verifica que o sistema está 100% saudável.
    Pule este teste em CI se STRICT_HEALTH_CHECK não estiver definido.
    """
    if not os.getenv("STRICT_HEALTH_CHECK"):
        pytest.skip("STRICT_HEALTH_CHECK não definido - pulando teste estrito")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy", f"Sistema não está healthy: {data}"

@pytest.mark.asyncio
async def test_health_endpoint():
    """Verifica endpoint /health com informações detalhadas."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        # Deve ter campos informativos
        assert isinstance(data, dict)
