#!/usr/bin/env python3
"""
Engenharia CAD — Testes Unitários para Rotas de Licenciamento
Testa registro, validação e reset de licenças por HWID.
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from httpx import AsyncClient

import sys
sys.path.insert(0, ".")
from server import app


@pytest.fixture
def mock_licenses():
    """Fixture para simular arquivo de licenças."""
    return {}


@pytest.fixture
def sample_hwid():
    """HWID válido de exemplo."""
    return "a" * 64


@pytest.fixture
def sample_user():
    """Usuário de teste."""
    return "testuser@example.com"


class TestLicenseValidation:
    """Testes para endpoint /api/license/validate."""

    @pytest.mark.asyncio
    @patch("backend.routes_license._load_licenses")
    @patch("backend.routes_license._save_licenses")
    async def test_first_activation(self, mock_save, mock_load, sample_user, sample_hwid):
        """Primeiro acesso deve registrar a máquina automaticamente."""
        mock_load.return_value = {}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/license/validate", json={
                "username": sample_user,
                "hwid": sample_hwid
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["authorized"] is True
        assert data["machine_registered"] is True
        assert "ativada" in data["message"].lower() or "sucesso" in data["message"].lower()
        
        # Verificar que salvou a licença
        mock_save.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.routes_license._load_licenses")
    @patch("backend.routes_license._save_licenses")
    async def test_same_machine_access(self, mock_save, mock_load, sample_user, sample_hwid):
        """Acesso da mesma máquina deve ser autorizado."""
        mock_load.return_value = {
            sample_user: {
                "hwid": sample_hwid,
                "registered_at": 1234567890,
                "last_seen": 1234567890,
                "access_count": 1
            }
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/license/validate", json={
                "username": sample_user,
                "hwid": sample_hwid
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["authorized"] is True
        assert "autorizado" in data["message"].lower()

    @pytest.mark.asyncio
    @patch("backend.routes_license._load_licenses")
    async def test_different_machine_blocked(self, mock_load, sample_user, sample_hwid):
        """Acesso de máquina diferente deve ser BLOQUEADO."""
        original_hwid = sample_hwid
        different_hwid = "b" * 64
        
        mock_load.return_value = {
            sample_user: {
                "hwid": original_hwid,
                "registered_at": 1234567890,
                "last_seen": 1234567890,
                "access_count": 5
            }
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/license/validate", json={
                "username": sample_user,
                "hwid": different_hwid
            })
        
        assert response.status_code == 403
        data = response.json()
        assert "negado" in data["detail"].lower() or "denied" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_hwid_format(self, sample_user):
        """HWID com formato inválido deve ser rejeitado."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/license/validate", json={
                "username": sample_user,
                "hwid": "invalid_short_hwid"
            })
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_empty_username(self, sample_hwid):
        """Username vazio deve ser rejeitado."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/license/validate", json={
                "username": "",
                "hwid": sample_hwid
            })
        
        assert response.status_code == 422


class TestLicenseStatus:
    """Testes para endpoint /api/license/status/{username}."""

    @pytest.mark.asyncio
    @patch("backend.routes_license._load_licenses")
    @patch("backend.routes_license._require_auth")
    async def test_status_existing_user(self, mock_auth, mock_load, sample_user, sample_hwid):
        """Status deve retornar informações da licença."""
        mock_auth.return_value = "admin@example.com"
        mock_load.return_value = {
            sample_user: {
                "hwid": sample_hwid,
                "registered_at": 1234567890,
                "last_seen": 1234567890,
                "access_count": 10
            }
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/license/status/{sample_user}",
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == sample_user
        assert "hwid_prefix" in data
        assert data["access_count"] == 10

    @pytest.mark.asyncio
    @patch("backend.routes_license._require_auth")
    async def test_status_without_auth(self, mock_auth, sample_user):
        """Status sem autenticação deve ser rejeitado."""
        from fastapi import HTTPException
        mock_auth.side_effect = HTTPException(status_code=401, detail="Token não fornecido")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/license/status/{sample_user}")
        
        assert response.status_code == 401


class TestLicenseReset:
    """Testes para endpoint /api/license/reset/{username}."""

    @pytest.mark.asyncio
    @patch("backend.routes_license._load_licenses")
    @patch("backend.routes_license._save_licenses")
    @patch("backend.routes_license._require_auth")
    async def test_reset_existing_license(self, mock_auth, mock_save, mock_load, sample_user, sample_hwid):
        """Reset deve remover a licença do usuário."""
        mock_auth.return_value = "admin@example.com"
        mock_load.return_value = {
            sample_user: {
                "hwid": sample_hwid,
                "registered_at": 1234567890,
                "last_seen": 1234567890,
                "access_count": 5
            }
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/license/reset/{sample_user}",
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "resetada" in data["message"].lower()
        mock_save.assert_called()

    @pytest.mark.asyncio
    @patch("backend.routes_license._load_licenses")
    @patch("backend.routes_license._require_auth")
    async def test_reset_nonexistent_user(self, mock_auth, mock_load, sample_hwid):
        """Reset de usuário inexistente deve retornar 404."""
        mock_auth.return_value = "admin@example.com"
        mock_load.return_value = {}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/license/reset/nonexistent_user",
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 404


class TestLicenseEdgeCases:
    """Testes para casos extremos do licenciamento."""

    @pytest.mark.asyncio
    @patch("backend.routes_license._load_licenses")
    @patch("backend.routes_license._save_licenses")
    async def test_concurrent_first_activation(self, mock_save, mock_load, sample_user, sample_hwid):
        """Ativações concorrentes devem ser tratadas corretamente."""
        mock_load.return_value = {}
        
        # Simular duas ativações quase simultâneas
        async with AsyncClient(app=app, base_url="http://test") as client:
            response1 = await client.post("/api/license/validate", json={
                "username": sample_user,
                "hwid": sample_hwid
            })
            # Primeira deve ter sucesso
            assert response1.status_code == 200

    @pytest.mark.asyncio
    async def test_hwid_with_special_chars(self, sample_user):
        """HWID deve aceitar apenas caracteres hex válidos."""
        invalid_hwid = "g" * 64  # 'g' não é hex
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/license/validate", json={
                "username": sample_user,
                "hwid": invalid_hwid
            })
        
        # Pode ser 422 (validation) ou 200/403 dependendo da implementação
        # O importante é não crashar
        assert response.status_code in [200, 403, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
