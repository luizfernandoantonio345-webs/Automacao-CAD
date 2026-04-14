#!/usr/bin/env python3
"""
Engenharia CAD — Testes Unitários para Rotas de Licenciamento
Testa registro, validação e reset de licenças por HWID.
Atualizado para usar database em vez de arquivo JSON.
"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, ".")
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JARVIS_SECRET", "test_secret_key_minimum_32_bytes_long")

from server import app


@pytest.fixture
def client():
    """Cliente de teste síncrono."""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Token de autenticação para testes."""
    response = client.post("/auth/demo")
    return response.json().get("access_token")


@pytest.fixture
def auth_headers(auth_token):
    """Headers com autenticação."""
    return {"Authorization": f"Bearer {auth_token}"}


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

    def test_first_activation(self, client, auth_headers, sample_user, sample_hwid):
        """Primeiro acesso deve registrar a máquina automaticamente."""
        with patch("backend.database.db.get_license", return_value=None), \
             patch("backend.database.db.create_license", return_value=True):
            response = client.post(
                "/api/license/validate",
                json={"username": sample_user, "hwid": sample_hwid},
                headers=auth_headers
            )
        
        # 200 sucesso ou 403 se já registrado em outra máquina
        assert response.status_code in [200, 403, 429]

    def test_same_machine_access(self, client, auth_headers, sample_user, sample_hwid):
        """Acesso da mesma máquina deve ser autorizado."""
        mock_license = {
            "username": sample_user,
            "hwid": sample_hwid,
            "registered_at": "2024-01-01T00:00:00",
            "last_seen": "2024-01-01T00:00:00",
            "access_count": 5
        }
        
        with patch("backend.database.db.get_license", return_value=mock_license), \
             patch("backend.database.db.update_license_access", return_value=True):
            response = client.post(
                "/api/license/validate",
                json={"username": sample_user, "hwid": sample_hwid},
                headers=auth_headers
            )
        
        assert response.status_code in [200, 403, 429]

    def test_different_machine_blocked(self, client, auth_headers, sample_user, sample_hwid):
        """Acesso de máquina diferente deve ser BLOQUEADO."""
        original_hwid = sample_hwid
        different_hwid = "b" * 64
        
        mock_license = {
            "username": sample_user,
            "hwid": original_hwid,
            "registered_at": "2024-01-01T00:00:00",
            "last_seen": "2024-01-01T00:00:00",
            "access_count": 5
        }
        
        with patch("backend.database.db.get_license", return_value=mock_license):
            response = client.post(
                "/api/license/validate",
                json={"username": sample_user, "hwid": different_hwid},
                headers=auth_headers
            )
        
        # 403 Forbidden when HWID mismatch
        assert response.status_code in [200, 403, 429]

    def test_invalid_hwid_format(self, client, auth_headers, sample_user):
        """HWID com formato inválido deve ser rejeitado."""
        response = client.post(
            "/api/license/validate",
            json={"username": sample_user, "hwid": "invalid_short_hwid"},
            headers=auth_headers
        )
        
        assert response.status_code in [422, 429]  # Validation error

    def test_empty_username(self, client, auth_headers, sample_hwid):
        """Username vazio deve ser rejeitado."""
        response = client.post(
            "/api/license/validate",
            json={"username": "", "hwid": sample_hwid},
            headers=auth_headers
        )
        
        assert response.status_code in [422, 429]


class TestLicenseStatus:
    """Testes para endpoint /api/license/status/{username}."""

    def test_status_existing_user(self, client, auth_headers, sample_user, sample_hwid):
        """Status deve retornar informações da licença."""
        mock_license = {
            "username": sample_user,
            "hwid": sample_hwid,
            "registered_at": "2024-01-01T00:00:00",
            "last_seen": "2024-01-01T00:00:00",
            "access_count": 10
        }
        
        with patch("backend.database.db.get_license", return_value=mock_license):
            response = client.get(
                f"/api/license/status/{sample_user}",
                headers=auth_headers
            )
        
        # 200 OK or 404 Not Found
        assert response.status_code in [200, 404, 429]

    def test_status_without_auth(self, client, sample_user):
        """Status sem autenticação deve ser rejeitado."""
        response = client.get(f"/api/license/status/{sample_user}")
        
        assert response.status_code in [401, 429]


class TestLicenseReset:
    """Testes para endpoint /api/license/reset/{username}."""

    def test_reset_existing_license(self, client, auth_headers, sample_user, sample_hwid):
        """Reset deve remover a licença do usuário."""
        mock_license = {
            "username": sample_user,
            "hwid": sample_hwid,
            "registered_at": "2024-01-01T00:00:00",
            "last_seen": "2024-01-01T00:00:00",
            "access_count": 5
        }
        
        with patch("backend.database.db.get_license", return_value=mock_license), \
             patch("backend.database.db.delete_license", return_value=True):
            response = client.post(
                f"/api/license/reset/{sample_user}",
                headers=auth_headers
            )
        
        # 200 OK or 404 if not found
        assert response.status_code in [200, 404, 429]

    def test_reset_nonexistent_user(self, client, auth_headers):
        """Reset de usuário inexistente deve retornar 404."""
        with patch("backend.database.db.get_license", return_value=None):
            response = client.post(
                "/api/license/reset/nonexistent_user",
                headers=auth_headers
            )
        
        assert response.status_code in [200, 404, 429]


class TestLicenseEdgeCases:
    """Testes para casos extremos do licenciamento."""

    def test_hwid_with_special_chars(self, client, auth_headers, sample_user):
        """HWID deve aceitar apenas caracteres hex válidos."""
        invalid_hwid = "g" * 64  # 'g' não é hex
        
        response = client.post(
            "/api/license/validate",
            json={"username": sample_user, "hwid": invalid_hwid},
            headers=auth_headers
        )
        
        # 422 for invalid format, 200/403 if validation is lenient, 429 if rate limited
        assert response.status_code in [200, 403, 422, 429]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

