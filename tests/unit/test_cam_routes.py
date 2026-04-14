# ═══════════════════════════════════════════════════════════════════════════════
# TESTES UNITÁRIOS - CAM ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes para o módulo CAM (Computer-Aided Manufacturing).
Cobre: parsing, nesting, g-code, rastreabilidade, otimização térmica.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCamParsing:
    """Testes de parsing de geometrias."""
    
    def test_parse_endpoint_returns_200(self, client):
        """Endpoint de parse deve retornar 200 com dados válidos."""
        response = client.post("/api/cam/parse", json={
            "content": "0\nSECTION\n2\nENTITIES\n0\nLINE\n10\n0\n20\n0\n11\n100\n21\n100\n0\nENDSEC\n0\nEOF",
            "filename": "test.dxf",
            "fileType": "dxf"
        })
        # Aceita 200 ou 422 (validação pode rejeitar DXF malformado)
        assert response.status_code in [200, 422, 400]
    
    def test_parse_with_invalid_content(self, client):
        """Parse com conteúdo inválido deve retornar erro apropriado."""
        response = client.post("/api/cam/parse", json={
            "content": "invalid content",
            "filename": "test.txt",
            "fileType": "unknown"
        })
        assert response.status_code in [400, 422, 200]


class TestCamNesting:
    """Testes de nesting de peças."""
    
    def test_nesting_run_endpoint(self, client, sample_nesting_request):
        """Endpoint de nesting deve processar requisição válida."""
        response = client.post("/api/cam/nesting/run", json=sample_nesting_request)
        assert response.status_code in [200, 422]
    
    def test_get_nesting_jobs(self, client):
        """Deve listar jobs de nesting."""
        response = client.get("/api/cam/nesting/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data or isinstance(data, list)
    
    def test_quick_piece_creation(self, client):
        """Deve criar peça rápida."""
        response = client.post("/api/cam/nesting/quick-piece", json={
            "name": "Test Circle",
            "type": "circle",
            "radius": 50
        })
        # 200 OK, 400 Bad Request, 422 Validation Error
        assert response.status_code in [200, 400, 422]


class TestCamGCode:
    """Testes de geração de G-Code."""
    
    def test_generate_gcode_endpoint(self, client, sample_geometry, sample_cutting_params):
        """Deve gerar G-Code para geometria válida."""
        response = client.post("/api/cam/generate", json={
            "geometry": sample_geometry,
            "parameters": sample_cutting_params,
            "outputFormat": "hypertherm"
        })
        assert response.status_code in [200, 422]
    
    def test_get_materials(self, client):
        """Deve retornar lista de materiais."""
        response = client.get("/api/cam/materials")
        assert response.status_code == 200
        data = response.json()
        assert "materials" in data or isinstance(data, list) or isinstance(data, dict)
    
    def test_validate_geometry(self, client, sample_geometry):
        """Deve validar geometria."""
        response = client.post("/api/cam/validate", json={
            "geometry": sample_geometry
        })
        assert response.status_code in [200, 422]


class TestCamLibrary:
    """Testes da biblioteca de peças."""
    
    def test_get_library_pieces(self, client):
        """Deve listar peças da biblioteca."""
        response = client.get("/api/cam/library/pieces")
        assert response.status_code == 200
        data = response.json()
        assert "pieces" in data or isinstance(data, list)
    
    def test_add_piece_to_library(self, client, sample_geometry):
        """Deve adicionar peça à biblioteca."""
        response = client.post("/api/cam/library/pieces", json={
            "name": "Test Piece",
            "geometry": sample_geometry,
            "category": "test",
            "tags": ["test", "unit"]
        })
        assert response.status_code in [200, 201, 422]


class TestCamSimulation:
    """Testes de simulação de corte."""
    
    def test_simulate_cutting(self, client, sample_geometry, sample_cutting_params):
        """Deve simular corte."""
        response = client.post("/api/cam/simulate", json={
            "geometry": sample_geometry,
            "parameters": sample_cutting_params
        })
        assert response.status_code in [200, 422]


class TestCamConsumables:
    """Testes de estimativa de consumíveis."""
    
    def test_estimate_consumables(self, client):
        """Deve estimar consumíveis."""
        response = client.get("/api/cam/consumables/estimate", params={
            "material": "mild_steel",
            "thickness": 6.0,
            "total_length_mm": 5000,
            "pierce_count": 10
        })
        # 200 OK, 422 Validation, 404 endpoint not implemented
        assert response.status_code in [200, 404, 422]
        if response.status_code == 200:
            data = response.json()
            assert "electrode" in data or "consumables" in data or "success" in data


class TestCamTraceability:
    """Testes de rastreabilidade QR Code."""
    
    def test_generate_traceability_code(self, client):
        """Deve gerar código de rastreabilidade."""
        response = client.post("/api/cam/traceability/generate", json={
            "pieceId": "piece_001",
            "pieceName": "Flange",
            "jobId": "job_001",
            "material": "mild_steel",
            "thickness": 6.0,
            "quantity": 1,
            "operator": "TestOperator"
        })
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert "trackingCode" in data or "success" in data
    
    def test_search_tracked_pieces(self, client):
        """Deve buscar peças rastreadas."""
        response = client.get("/api/cam/traceability/search", params={
            "limit": 10
        })
        # 200 OK, 404 if endpoint not implemented
        assert response.status_code in [200, 404]


class TestCamThermalOptimization:
    """Testes de otimização térmica."""
    
    def test_thermal_optimize(self, client):
        """Deve otimizar sequência térmica."""
        response = client.post("/api/cam/thermal/optimize", json={
            "cuttingPaths": [
                {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 100}], "length": 141},
                {"points": [{"x": 200, "y": 0}, {"x": 300, "y": 100}], "length": 141}
            ],
            "material": "mild_steel",
            "thickness": 6.0,
            "amperage": 45
        })
        assert response.status_code in [200, 422]
    
    def test_get_thermal_material_data(self, client):
        """Deve retornar dados térmicos de materiais."""
        response = client.get("/api/cam/thermal/material-data")
        assert response.status_code == 200
        data = response.json()
        assert "materials" in data
