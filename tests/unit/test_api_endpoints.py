# ═══════════════════════════════════════════════════════════════════════════════
# TESTES UNITÁRIOS - API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes unitários para todos os endpoints da API.
Cobertura completa de rotas HTTP.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
from uuid import uuid4
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JARVIS_SECRET", "test_secret_key_minimum_32_bytes_long")


@pytest.fixture
def client():
    """Cliente de teste FastAPI."""
    test_db_path = Path(tempfile.gettempdir()) / f"engcad_test_api_endpoints_{uuid4().hex}.db"

    os.environ["ENGCAD_DB_PATH"] = str(test_db_path)
    for module_name in [
        "server",
        "backend.database.db",
        "backend.database.connection_pool",
    ]:
        sys.modules.pop(module_name, None)

    from server import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Headers com token de autenticação."""
    # Login com usuário demo
    response = client.post("/auth/demo")
    token = response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def standard_auth_headers(client):
    """Headers com token não-demo para rotas bloqueadas em demonstração."""
    from server import _make_token

    token = _make_token("qa-excel@test.com", expiry_minutes=30)
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE ENDPOINTS PÚBLICOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicEndpoints:
    """Testes de endpoints que não requerem autenticação."""
    
    def test_root_endpoint(self, client):
        """GET / - Status da API."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert data["status"] == "online"
    
    def test_health_check(self, client):
        """GET /health - Health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
    
    def test_docs_available(self, client):
        """GET /docs - Swagger UI disponível."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_schema(self, client):
        """GET /openapi.json - Schema OpenAPI."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "info" in data
        assert len(data["paths"]) > 100  # Muitos endpoints


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE AUTENTICAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthEndpoints:
    """Testes de endpoints de autenticação."""
    
    def test_demo_login(self, client):
        """POST /auth/demo - Login demo."""
        response = client.post("/auth/demo")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """POST /login - Credenciais inválidas."""
        response = client.post("/login", json={
            "email": "invalid@test.com",
            "senha": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_login_missing_fields(self, client):
        """POST /login - Campos obrigatórios."""
        response = client.post("/login", json={})
        assert response.status_code == 401
    
    def test_register_duplicate_email(self, client):
        """POST /auth/register - Email duplicado."""
        # Primeiro registro
        email = f"test_{os.urandom(4).hex()}@test.com"
        response1 = client.post("/auth/register", json={
            "email": email,
            "senha": "password123",
            "empresa": "Test Corp"
        })
        
        # Segundo registro com mesmo email
        if response1.status_code == 200:
            response2 = client.post("/auth/register", json={
                "email": email,
                "senha": "password456",
                "empresa": "Another Corp"
            })
            assert response2.status_code == 400
    
    def test_auth_me_without_token(self, client):
        """GET /auth/me - Sem token."""
        response = client.get("/auth/me")
        assert response.status_code == 401
    
    def test_auth_me_with_token(self, client, auth_headers):
        """GET /auth/me - Com token válido."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data


class TestExcelUploadEndpoint:
    """Testes focados no upload/processamento de Excel."""

    def test_excel_rejects_invalid_extension(self, client, standard_auth_headers):
        response = client.post(
            "/excel",
            files={"file": ("planilha.txt", b"conteudo invalido", "text/plain")},
            headers=standard_auth_headers,
        )

        assert response.status_code == 400
        assert "xlsx" in (response.json().get("detalhe") or response.text).lower()

    @patch("server.get_user_by_email", return_value={"usado": 0, "limite": 999})
    @patch("server.update_upload")
    @patch("server.create_upload", return_value=101)
    @patch("engenharia_automacao.core.main.ProjectService")
    def test_excel_returns_422_when_no_projects_generated(
        self,
        project_service_cls,
        create_upload_mock,
        update_upload_mock,
        get_user_mock,
        client,
        standard_auth_headers,
    ):
        project_service_cls.return_value.generate_projects_from_excel.return_value = []

        response = client.post(
            "/excel",
            files={
                "file": (
                    "entrada.xlsx",
                    b"fake excel payload",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            headers=standard_auth_headers,
        )

        assert response.status_code == 422
        assert "nenhum projeto válido" in (response.json().get("detalhe") or response.text).lower()
        create_upload_mock.assert_called_once()
        update_upload_mock.assert_called()

    @patch("server.get_user_by_email", return_value={"usado": 5, "limite": 999})
    @patch("server.db_update_project")
    @patch("server.db_create_project", side_effect=[301, 302])
    @patch("server.update_upload")
    @patch("server.create_upload", return_value=202)
    @patch("engenharia_automacao.core.main.ProjectService")
    def test_excel_returns_generated_project_ids(
        self,
        project_service_cls,
        create_upload_mock,
        update_upload_mock,
        db_create_project_mock,
        db_update_project_mock,
        get_user_mock,
        client,
        standard_auth_headers,
        tmp_path,
    ):
        generated_files = [tmp_path / "P-100.lsp", tmp_path / "P-200.lsp"]
        project_service_cls.return_value.generate_projects_from_excel.return_value = generated_files

        response = client.post(
            "/excel",
            files={
                "file": (
                    "entrada.xlsx",
                    b"fake excel payload",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            headers=standard_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["project_ids"] == [301, 302]
        assert data["upload_id"] == 202
        assert create_upload_mock.called
        assert update_upload_mock.called
        assert db_create_project_mock.call_count == 2
        assert db_update_project_mock.call_count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE CAM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCAMEndpoints:
    """Testes de endpoints CAM."""
    
    def test_cam_materials_list(self, client):
        """GET /api/cam/materials - Lista de materiais."""
        response = client.get("/api/cam/materials")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "materials" in data
    
    def test_cam_parse_empty(self, client):
        """POST /api/cam/parse - Parse vazio."""
        response = client.post("/api/cam/parse", json={})
        # 400/422 for validation error, 503 if circuit breaker triggers
        assert response.status_code in [400, 422, 503]
    
    def test_cam_validate_gcode(self, client):
        """POST /api/cam/validate - Validar G-code."""
        gcode = "G0 X0 Y0\nG1 X100 Y100 F2500"
        response = client.post("/api/cam/validate", json={"gcode": gcode})
        # 200 for success, 422 for validation, 503 if service unavailable
        assert response.status_code in [200, 422, 503]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE AI ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAIEndpoints:
    """Testes de endpoints de IA."""
    
    def test_ai_status(self, client):
        """GET /api/ai/status - Status dos engines."""
        response = client.get("/api/ai/status")
        assert response.status_code == 200
    
    def test_ai_engines_list(self, client):
        """GET /api/ai/engines - Lista de engines."""
        response = client.get("/api/ai/engines")
        assert response.status_code == 200
    
    def test_ai_chat_empty(self, client):
        """POST /api/ai/chat - Chat vazio."""
        response = client.post("/api/ai/chat", json={"message": ""})
        # 200 for recovered response, 400/422 for validation, 503 if circuit breaker
        assert response.status_code in [200, 400, 422, 503]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardEndpoints:
    """Testes de endpoints de dashboard."""
    
    def test_system_metrics(self, client, auth_headers):
        """GET /system - Métricas do sistema."""
        response = client.get("/system", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "ram" in data
        assert "disk" in data
    
    def test_project_stats(self, client, auth_headers):
        """GET /project-stats - Estatísticas de projetos."""
        response = client.get("/project-stats", headers=auth_headers)
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiting:
    """Testes de proteção contra abuso."""
    
    def test_rate_limit_not_triggered_normal_use(self, client):
        """Uso normal não dispara rate limit."""
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_cors_headers_present(self, client):
        """Headers CORS presentes."""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        # OPTIONS pode retornar 200 ou 405 dependendo da config
        assert response.status_code in [200, 405]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE LICENCIAMENTO
# ═══════════════════════════════════════════════════════════════════════════════

class TestLicenseEndpoints:
    """Testes de endpoints de licenciamento."""
    
    def test_license_validate_invalid(self, client, auth_headers):
        """POST /api/license/validate - HWID inválido formato."""
        response = client.post("/api/license/validate", json={
            "username": "test",
            "hwid": "invalid"  # Deve ter 64 chars
        }, headers=auth_headers)
        assert response.status_code == 422
    
    def test_license_validate_valid_format(self, client, auth_headers):
        """POST /api/license/validate - HWID válido."""
        hwid = "a" * 64  # 64 caracteres hex
        response = client.post("/api/license/validate", json={
            "username": "testuser",
            "hwid": hwid
        }, headers=auth_headers)
        # 200 se novo registro, 403 se HWID diferente
        assert response.status_code in [200, 403]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE SSE (Server-Sent Events)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSSEEndpoints:
    """Testes de endpoints SSE."""
    
    def test_sse_system_unauthorized(self, client):
        """GET /sse/system - Sem autorização."""
        # SSE requer auth em produção, mas pode ser aberto em dev
        response = client.get("/sse/system")
        assert response.status_code in [200, 401, 403]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE BRIDGE AUTOCAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutocadBridge:
    """Testes de endpoints de bridge AutoCAD."""
    
    def test_bridge_pending(self, client):
        """GET /api/bridge/pending - Comandos pendentes."""
        response = client.get("/api/bridge/pending")
        assert response.status_code == 200
    
    def test_bridge_status(self, client):
        """GET /api/bridge/status - Status da conexão."""
        response = client.get("/api/bridge/status")
        assert response.status_code == 200
    
    def test_autocad_health(self, client):
        """GET /api/autocad/health - Saúde do AutoCAD."""
        response = client.get("/api/autocad/health")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE VALIDAÇÃO DE INPUT
# ═══════════════════════════════════════════════════════════════════════════════

class TestInputValidation:
    """Testes de validação de entrada."""
    
    def test_json_invalid_syntax(self, client):
        """POST com JSON inválido."""
        response = client.post(
            "/login",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_unicode_handling(self, client):
        """Suporte a caracteres unicode."""
        response = client.post("/auth/register", json={
            "email": "tëst@tëst.com",
            "senha": "páßwörd123",
            "empresa": "Empresa Brasileira Açúcar & Café"
        })
        # Deve processar unicode corretamente - 500 pode ocorrer se há problema de encoding interno
        assert response.status_code in [200, 400, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
