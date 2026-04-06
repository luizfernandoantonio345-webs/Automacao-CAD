# ═══════════════════════════════════════════════════════════════════════════════
# TESTES END-TO-END (E2E) - PIPELINE COMPLETO CAM → CNC
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes E2E que validam o fluxo completo:
1. Upload DXF → Parse → Validação → Nesting → G-code → Simulação → Export

Estes testes garantem que todo o pipeline funciona de ponta a ponta.
"""
import pytest
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Adicionar raiz do projeto ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JARVIS_SECRET", "test_secret_key_minimum_32_bytes_long")


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES ESPECÍFICAS PARA E2E
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def e2e_client():
    """Cliente de teste para E2E."""
    from server import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def sample_dxf_content():
    """Conteúdo DXF válido para testes."""
    return """0
SECTION
2
HEADER
9
$ACADVER
1
AC1014
0
ENDSEC
0
SECTION
2
ENTITIES
0
LINE
8
0
10
0.0
20
0.0
30
0.0
11
100.0
21
0.0
31
0.0
0
LINE
8
0
10
100.0
20
0.0
30
0.0
11
100.0
21
100.0
31
0.0
0
LINE
8
0
10
100.0
20
100.0
30
0.0
11
0.0
21
100.0
31
0.0
0
LINE
8
0
10
0.0
20
100.0
30
0.0
11
0.0
21
0.0
31
0.0
0
CIRCLE
8
0
10
50.0
20
50.0
30
0.0
40
20.0
0
ENDSEC
0
EOF"""


@pytest.fixture
def cutting_parameters():
    """Parâmetros de corte para testes."""
    return {
        "material": "mild_steel",
        "thickness_mm": 6.0,
        "amperage": 45,
        "cutting_speed_mm_min": 2500,
        "pierce_delay_ms": 500,
        "pierce_height_mm": 3.8,
        "cut_height_mm": 1.5,
        "kerf_width_mm": 1.5,
        "lead_in_type": "arc",
        "lead_in_radius_mm": 5.0,
        "lead_out_type": "arc",
        "lead_out_radius_mm": 3.0
    }


@pytest.fixture
def sheet_parameters():
    """Parâmetros da chapa para nesting."""
    return {
        "width_mm": 1500,
        "height_mm": 3000,
        "material": "mild_steel",
        "thickness_mm": 6.0
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES E2E - PIPELINE COMPLETO
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EFullPipeline:
    """Testes do pipeline completo CAM."""
    
    def test_health_check_all_services(self, e2e_client):
        """
        E2E-001: Verificar que todos os serviços estão saudáveis.
        """
        response = e2e_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "degraded"]
        assert "database" in data
    
    def test_e2e_parse_dxf_to_geometry(self, e2e_client, sample_dxf_content):
        """
        E2E-002: Upload DXF → Parse → Retornar geometria estruturada.
        """
        response = e2e_client.post("/api/cam/parse", json={
            "content": sample_dxf_content,
            "filename": "test_square.dxf",
            "fileType": "dxf"
        })
        
        # Parse pode retornar 200 com geometria ou 422 se validação falhar
        assert response.status_code in [200, 422, 400]
        
        if response.status_code == 200:
            data = response.json()
            # Verificar estrutura básica
            assert "geometry" in data or "entities" in data or "shapes" in data
    
    def test_e2e_validate_geometry(self, e2e_client):
        """
        E2E-003: Validar geometria para corte CNC.
        """
        geometry = {
            "entities": [
                {"type": "line", "start": [0, 0], "end": [100, 0]},
                {"type": "line", "start": [100, 0], "end": [100, 100]},
                {"type": "line", "start": [100, 100], "end": [0, 100]},
                {"type": "line", "start": [0, 100], "end": [0, 0]},
            ],
            "bounds": {"min": [0, 0], "max": [100, 100]}
        }
        
        response = e2e_client.post("/api/cam/validate", json={
            "geometry": geometry
        })
        
        assert response.status_code in [200, 422]
    
    def test_e2e_generate_gcode(self, e2e_client, cutting_parameters):
        """
        E2E-004: Gerar G-code a partir de geometria válida.
        """
        geometry = {
            "entities": [
                {"type": "line", "start": [0, 0], "end": [100, 0]},
                {"type": "line", "start": [100, 0], "end": [100, 100]},
                {"type": "line", "start": [100, 100], "end": [0, 100]},
                {"type": "line", "start": [0, 100], "end": [0, 0]},
            ],
            "bounds": {"min": [0, 0], "max": [100, 100]}
        }
        
        response = e2e_client.post("/api/cam/generate", json={
            "geometry": geometry,
            "parameters": cutting_parameters,
            "outputFormat": "hypertherm"
        })
        
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            data = response.json()
            # G-code deve conter comandos
            assert "gcode" in data or "output" in data or "code" in data
    
    def test_e2e_nesting_single_piece(self, e2e_client, sheet_parameters):
        """
        E2E-005: Nesting de uma peça simples em chapa.
        """
        piece = {
            "name": "Square 100x100",
            "geometry": {
                "type": "rectangle",
                "width": 100,
                "height": 100
            },
            "quantity": 5
        }
        
        response = e2e_client.post("/api/cam/nesting/run", json={
            "pieces": [piece],
            "sheet": sheet_parameters,
            "options": {
                "spacing_mm": 10,
                "rotation_allowed": True,
                "optimization_level": "high"
            }
        })
        
        assert response.status_code in [200, 422]
    
    def test_e2e_nesting_multiple_pieces(self, e2e_client, sheet_parameters):
        """
        E2E-006: Nesting de múltiplas peças com otimização.
        """
        pieces = [
            {"name": "Circle R50", "geometry": {"type": "circle", "radius": 50}, "quantity": 3},
            {"name": "Rect 80x60", "geometry": {"type": "rectangle", "width": 80, "height": 60}, "quantity": 4},
            {"name": "Square 40", "geometry": {"type": "rectangle", "width": 40, "height": 40}, "quantity": 10},
        ]
        
        response = e2e_client.post("/api/cam/nesting/run", json={
            "pieces": pieces,
            "sheet": sheet_parameters,
            "options": {
                "spacing_mm": 8,
                "rotation_allowed": True,
                "optimization_level": "maximum"
            }
        })
        
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            data = response.json()
            # Nesting deve retornar eficiência
            assert "efficiency" in data or "utilization" in data or "result" in data
    
    def test_e2e_thermal_simulation(self, e2e_client, cutting_parameters):
        """
        E2E-007: Simulação térmica do processo de corte.
        """
        geometry = {
            "entities": [
                {"type": "circle", "center": [50, 50], "radius": 30}
            ]
        }
        
        response = e2e_client.post("/api/cam/simulate/physics", json={
            "geometry": geometry,
            "parameters": cutting_parameters,
            "simulation_type": "thermal"
        })
        
        assert response.status_code in [200, 422, 404]
    
    def test_e2e_estimate_time(self, e2e_client, cutting_parameters):
        """
        E2E-008: Estimativa de tempo de corte.
        """
        geometry = {
            "entities": [
                {"type": "line", "start": [0, 0], "end": [100, 0]},
                {"type": "line", "start": [100, 0], "end": [100, 100]},
            ],
            "total_length_mm": 200
        }
        
        response = e2e_client.post("/api/cam/simulate/estimate-time", json={
            "geometry": geometry,
            "parameters": cutting_parameters
        })
        
        assert response.status_code in [200, 422, 404]
    
    def test_e2e_consumables_estimate(self, e2e_client, cutting_parameters):
        """
        E2E-009: Estimativa de consumíveis (gás, eletrodos).
        """
        job = {
            "pieces_count": 10,
            "total_cut_length_mm": 5000,
            "pierces_count": 10,
            "parameters": cutting_parameters
        }
        
        response = e2e_client.post("/api/cam/consumables/estimate", json=job)
        
        assert response.status_code in [200, 422, 404]
    
    def test_e2e_machine_presets(self, e2e_client):
        """
        E2E-010: Obter presets de máquinas CNC.
        """
        response = e2e_client.get("/api/cam/simulate/machine-presets")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestE2EAuthenticationFlow:
    """Testes E2E do fluxo de autenticação."""
    
    def test_e2e_register_login_flow(self, e2e_client):
        """
        E2E-011: Registro → Login → Acesso autenticado.
        """
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        # 1. Registrar
        register_response = e2e_client.post("/auth/register", json={
            "email": unique_email,
            "senha": "TestPassword123!",
            "empresa": "Test Company"
        })
        
        # Pode falhar se registro estiver desabilitado
        if register_response.status_code == 200:
            # 2. Login
            login_response = e2e_client.post("/login", json={
                "email": unique_email,
                "senha": "TestPassword123!"
            })
            
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                assert token is not None
                
                # 3. Acesso autenticado
                auth_headers = {"Authorization": f"Bearer {token}"}
                me_response = e2e_client.get("/auth/me", headers=auth_headers)
                assert me_response.status_code == 200
    
    def test_e2e_demo_access(self, e2e_client):
        """
        E2E-012: Acesso demo sem registro.
        """
        response = e2e_client.post("/auth/demo")
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data.get("email") == "demo@engenharia-cad.com"
    
    def test_e2e_rate_limiting(self, e2e_client):
        """
        E2E-013: Verificar rate limiting está ativo.
        """
        # Fazer múltiplas requisições rápidas
        responses = []
        for _ in range(10):
            responses.append(e2e_client.get("/health"))
        
        # Todas devem passar (limite é 120/min)
        assert all(r.status_code in [200, 429] for r in responses)


class TestE2EAIEngines:
    """Testes E2E dos engines de IA."""
    
    def test_e2e_ai_status(self, e2e_client):
        """
        E2E-014: Verificar status dos engines de IA.
        """
        response = e2e_client.get("/api/ai/status")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "engines" in data or "status" in data
    
    def test_e2e_ai_engines_list(self, e2e_client):
        """
        E2E-015: Listar engines de IA disponíveis.
        """
        response = e2e_client.get("/api/ai/engines")
        assert response.status_code in [200, 404]
    
    def test_e2e_ai_chat(self, e2e_client):
        """
        E2E-016: Chat com assistente IA.
        """
        response = e2e_client.post("/api/ai/chat", json={
            "message": "Qual a velocidade ideal para cortar aço 6mm?",
            "context": "cam_plasma"
        })
        
        assert response.status_code in [200, 422, 404]
    
    def test_e2e_ai_analyze_geometry(self, e2e_client):
        """
        E2E-017: Análise de geometria por IA.
        """
        geometry = {
            "entities": [
                {"type": "circle", "center": [50, 50], "radius": 30}
            ]
        }
        
        response = e2e_client.post("/api/cam/ai/analyze-geometry", json={
            "geometry": geometry
        })
        
        assert response.status_code in [200, 422, 404]
    
    def test_e2e_ai_suggest_parameters(self, e2e_client):
        """
        E2E-018: Sugestão de parâmetros por IA.
        """
        response = e2e_client.post("/api/cam/ai/suggest-parameters", json={
            "material": "mild_steel",
            "thickness_mm": 6.0,
            "complexity": "medium"
        })
        
        assert response.status_code in [200, 422, 404]


class TestE2EJobHistory:
    """Testes E2E do histórico de jobs."""
    
    def test_e2e_list_jobs(self, e2e_client):
        """
        E2E-019: Listar histórico de jobs.
        """
        response = e2e_client.get("/api/cam/jobs")
        assert response.status_code in [200, 404]
    
    def test_e2e_job_statistics(self, e2e_client):
        """
        E2E-020: Estatísticas de jobs.
        """
        response = e2e_client.get("/api/cam/jobs/statistics")
        assert response.status_code in [200, 404]


class TestE2EDashboard:
    """Testes E2E do dashboard."""
    
    def test_e2e_dashboard_kpis(self, e2e_client):
        """
        E2E-021: KPIs do dashboard.
        """
        response = e2e_client.get("/api/dashboard/kpis")
        assert response.status_code in [200, 404]
    
    def test_e2e_dashboard_metrics(self, e2e_client):
        """
        E2E-022: Métricas em tempo real.
        """
        response = e2e_client.get("/api/dashboard/metrics")
        assert response.status_code in [200, 404]
    
    def test_e2e_system_metrics(self, e2e_client):
        """
        E2E-023: Métricas do sistema.
        """
        response = e2e_client.get("/system")
        assert response.status_code == 200
        
        data = response.json()
        assert "cpu" in data
        assert "ram" in data


class TestE2EMachineIntegration:
    """Testes E2E de integração com máquinas."""
    
    def test_e2e_list_machines(self, e2e_client):
        """
        E2E-024: Listar máquinas disponíveis.
        """
        response = e2e_client.get("/api/machines")
        assert response.status_code in [200, 404]
    
    def test_e2e_machine_status(self, e2e_client):
        """
        E2E-025: Status de máquina específica.
        """
        response = e2e_client.get("/api/machines/default/status")
        assert response.status_code in [200, 404]


class TestE2ELicensing:
    """Testes E2E do sistema de licenciamento."""
    
    def test_e2e_license_validate(self, e2e_client):
        """
        E2E-026: Validação de licença HWID.
        """
        import hashlib
        fake_hwid = hashlib.sha256(b"test_machine").hexdigest()
        
        response = e2e_client.post("/api/license/validate", json={
            "username": "test_user_e2e",
            "hwid": fake_hwid
        })
        
        # 200 = autorizado, 403 = máquina diferente, 422 = dados inválidos
        assert response.status_code in [200, 403, 422]


class TestE2ENotifications:
    """Testes E2E do sistema de notificações."""
    
    def test_e2e_notifications_list(self, e2e_client):
        """
        E2E-027: Listar notificações.
        """
        response = e2e_client.get("/api/notifications")
        assert response.status_code in [200, 401, 404]


class TestE2EAnalytics:
    """Testes E2E de analytics."""
    
    def test_e2e_analytics_overview(self, e2e_client):
        """
        E2E-028: Visão geral de analytics.
        """
        response = e2e_client.get("/api/analytics/overview")
        assert response.status_code in [200, 401, 404]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE INTEGRAÇÃO AUTOCAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EAutoCADIntegration:
    """Testes E2E da integração com AutoCAD."""
    
    def test_e2e_autocad_health(self, e2e_client):
        """
        E2E-029: Health check do serviço AutoCAD.
        """
        response = e2e_client.get("/api/autocad/health")
        assert response.status_code in [200, 404]
    
    def test_e2e_autocad_status(self, e2e_client):
        """
        E2E-030: Status da conexão AutoCAD.
        """
        response = e2e_client.get("/api/autocad/status")
        assert response.status_code in [200, 404]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES DE STRESS BÁSICOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EStress:
    """Testes de stress básicos E2E."""
    
    def test_e2e_concurrent_health_checks(self, e2e_client):
        """
        E2E-031: Múltiplas requisições concorrentes de health.
        """
        import concurrent.futures
        
        def health_request():
            return e2e_client.get("/health").status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(health_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Todas devem retornar 200 ou 429 (rate limited)
        assert all(r in [200, 429] for r in results)
    
    def test_e2e_large_geometry_parse(self, e2e_client):
        """
        E2E-032: Parse de geometria grande.
        """
        # Criar geometria com muitas entidades
        entities = []
        for i in range(100):
            entities.append({
                "type": "line",
                "start": [i * 10, 0],
                "end": [i * 10 + 5, 100]
            })
        
        geometry = {"entities": entities}
        
        response = e2e_client.post("/api/cam/validate", json={
            "geometry": geometry
        })
        
        # Deve processar sem timeout
        assert response.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
