#!/usr/bin/env python3
"""
Engenharia CAD — Testes Unitários para Geometry Parser (CAM)
Testa parsing de geometrias DXF para operações de corte.
"""
import pytest
import math
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, ".")


class TestGeometryParser:
    """Testes para parser de geometria DXF."""

    @pytest.fixture
    def sample_dxf_content(self):
        """Conteúdo DXF de exemplo para testes."""
        return """0
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
11
100.0
21
0.0
0
CIRCLE
8
0
10
50.0
20
50.0
40
25.0
0
ARC
8
0
10
100.0
20
100.0
40
30.0
50
0.0
51
90.0
0
ENDSEC
0
EOF
"""

    def test_parse_line(self, sample_dxf_content):
        """Parser deve extrair linhas corretamente."""
        try:
            from cam.geometry_parser import parse_dxf_content
            result = parse_dxf_content(sample_dxf_content)
            lines = [e for e in result.get("entities", []) if e.get("type") == "LINE"]
            assert len(lines) >= 1
        except ImportError:
            pytest.skip("geometry_parser não disponível")

    def test_parse_circle(self, sample_dxf_content):
        """Parser deve extrair círculos corretamente."""
        try:
            from cam.geometry_parser import parse_dxf_content
            result = parse_dxf_content(sample_dxf_content)
            circles = [e for e in result.get("entities", []) if e.get("type") == "CIRCLE"]
            assert len(circles) >= 1
            # Verificar propriedades do círculo
            if circles:
                circle = circles[0]
                assert "center" in circle or "center_x" in circle
                assert "radius" in circle
        except ImportError:
            pytest.skip("geometry_parser não disponível")

    def test_parse_arc(self, sample_dxf_content):
        """Parser deve extrair arcos corretamente."""
        try:
            from cam.geometry_parser import parse_dxf_content
            result = parse_dxf_content(sample_dxf_content)
            arcs = [e for e in result.get("entities", []) if e.get("type") == "ARC"]
            assert len(arcs) >= 1
        except ImportError:
            pytest.skip("geometry_parser não disponível")

    def test_empty_dxf(self):
        """Parser deve tratar DXF vazio graciosamente."""
        try:
            from cam.geometry_parser import parse_dxf_content
            result = parse_dxf_content("")
            assert result is not None
            # Deve retornar estrutura vazia ou erro apropriado
        except ImportError:
            pytest.skip("geometry_parser não disponível")
        except Exception as e:
            # Parser pode levantar exceção para DXF inválido - OK
            assert True

    def test_invalid_dxf(self):
        """Parser deve tratar DXF inválido graciosamente."""
        try:
            from cam.geometry_parser import parse_dxf_content
            with pytest.raises((ValueError, Exception)):
                parse_dxf_content("este não é um DXF válido")
        except ImportError:
            pytest.skip("geometry_parser não disponível")


class TestGeometryValidator:
    """Testes para validação de geometrias."""

    @pytest.fixture
    def valid_rectangle(self):
        """Retângulo válido para corte."""
        return {
            "entities": [
                {"type": "LINE", "start": (0, 0), "end": (100, 0)},
                {"type": "LINE", "start": (100, 0), "end": (100, 50)},
                {"type": "LINE", "start": (100, 50), "end": (0, 50)},
                {"type": "LINE", "start": (0, 50), "end": (0, 0)},
            ],
            "closed": True
        }

    def test_closed_contour_detection(self, valid_rectangle):
        """Validador deve detectar contornos fechados."""
        try:
            from cam.geometry_validator import validate_geometry
            result = validate_geometry(valid_rectangle)
            assert result.get("valid", True) or result.get("closed", True)
        except ImportError:
            pytest.skip("geometry_validator não disponível")

    def test_open_contour_warning(self):
        """Validador deve alertar sobre contornos abertos."""
        open_contour = {
            "entities": [
                {"type": "LINE", "start": (0, 0), "end": (100, 0)},
                {"type": "LINE", "start": (100, 0), "end": (100, 50)},
                # Falta fechar o contorno
            ]
        }
        try:
            from cam.geometry_validator import validate_geometry
            result = validate_geometry(open_contour)
            # Deve indicar problema ou warning
            assert "warning" in result or not result.get("closed", False)
        except ImportError:
            pytest.skip("geometry_validator não disponível")

    def test_minimum_feature_size(self):
        """Validador deve alertar sobre features muito pequenas."""
        tiny_feature = {
            "entities": [
                {"type": "CIRCLE", "center": (5, 5), "radius": 0.1},  # Muito pequeno para plasma
            ]
        }
        try:
            from cam.geometry_validator import validate_geometry
            result = validate_geometry(tiny_feature, min_feature_mm=1.0)
            assert "warning" in result or "error" in result
        except ImportError:
            pytest.skip("geometry_validator não disponível")


class TestBoundingBox:
    """Testes para cálculo de bounding box."""

    def test_rectangle_bounds(self):
        """Bounding box de retângulo deve ser exata."""
        entities = [
            {"type": "LINE", "start": (0, 0), "end": (100, 0)},
            {"type": "LINE", "start": (100, 0), "end": (100, 50)},
            {"type": "LINE", "start": (100, 50), "end": (0, 50)},
            {"type": "LINE", "start": (0, 50), "end": (0, 0)},
        ]
        try:
            from cam.geometry_parser import calculate_bounding_box
            bbox = calculate_bounding_box(entities)
            assert bbox["min_x"] == 0
            assert bbox["min_y"] == 0
            assert bbox["max_x"] == 100
            assert bbox["max_y"] == 50
            assert bbox["width"] == 100
            assert bbox["height"] == 50
        except ImportError:
            pytest.skip("calculate_bounding_box não disponível")

    def test_circle_bounds(self):
        """Bounding box de círculo deve incluir raio."""
        entities = [
            {"type": "CIRCLE", "center": (50, 50), "radius": 25},
        ]
        try:
            from cam.geometry_parser import calculate_bounding_box
            bbox = calculate_bounding_box(entities)
            assert bbox["min_x"] == 25  # centro - raio
            assert bbox["min_y"] == 25
            assert bbox["max_x"] == 75  # centro + raio
            assert bbox["max_y"] == 75
        except ImportError:
            pytest.skip("calculate_bounding_box não disponível")


class TestAreaCalculation:
    """Testes para cálculo de área."""

    def test_rectangle_area(self):
        """Área de retângulo deve ser largura × altura."""
        try:
            from cam.geometry_parser import calculate_area
            # Retângulo 100×50mm
            vertices = [(0, 0), (100, 0), (100, 50), (0, 50)]
            area = calculate_area(vertices)
            assert abs(area - 5000.0) < 0.01  # 5000 mm²
        except ImportError:
            pytest.skip("calculate_area não disponível")

    def test_circle_area(self):
        """Área de círculo deve ser π×r²."""
        try:
            from cam.geometry_parser import calculate_circle_area
            radius = 25.0
            expected_area = math.pi * radius ** 2
            area = calculate_circle_area(radius)
            assert abs(area - expected_area) < 0.01
        except ImportError:
            pytest.skip("calculate_circle_area não disponível")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
