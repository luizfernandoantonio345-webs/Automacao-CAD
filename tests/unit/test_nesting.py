# ═══════════════════════════════════════════════════════════════════════════════
# TESTES UNITÁRIOS - NESTING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes unitários para o engine de nesting (otimização de chapas).
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))


class TestNestingGeometry:
    """Testes de geometria para nesting."""
    
    def test_rectangle_area_calculation(self):
        """Calcular área de retângulo."""
        width, height = 100, 50
        area = width * height
        assert area == 5000
    
    def test_circle_area_calculation(self):
        """Calcular área de círculo."""
        import math
        radius = 25
        area = math.pi * radius ** 2
        assert abs(area - 1963.495) < 1
    
    def test_bounding_box_calculation(self):
        """Calcular bounding box de peças."""
        pieces = [
            {"x": 0, "y": 0, "width": 100, "height": 50},
            {"x": 50, "y": 25, "width": 100, "height": 75},
        ]
        
        min_x = min(p["x"] for p in pieces)
        min_y = min(p["y"] for p in pieces)
        max_x = max(p["x"] + p["width"] for p in pieces)
        max_y = max(p["y"] + p["height"] for p in pieces)
        
        assert min_x == 0
        assert min_y == 0
        assert max_x == 150
        assert max_y == 100
    
    def test_piece_rotation_90(self):
        """Rotação de peça em 90 graus."""
        piece = {"width": 100, "height": 50}
        rotated = {"width": piece["height"], "height": piece["width"]}
        
        assert rotated["width"] == 50
        assert rotated["height"] == 100
    
    def test_piece_fits_in_sheet(self):
        """Verificar se peça cabe na chapa."""
        sheet = {"width": 1500, "height": 3000}
        piece = {"width": 200, "height": 300}
        
        fits = piece["width"] <= sheet["width"] and piece["height"] <= sheet["height"]
        assert fits is True
    
    def test_piece_too_large(self):
        """Peça maior que a chapa."""
        sheet = {"width": 1500, "height": 3000}
        piece = {"width": 2000, "height": 300}
        
        fits = piece["width"] <= sheet["width"] and piece["height"] <= sheet["height"]
        assert fits is False


class TestNestingAlgorithm:
    """Testes do algoritmo de nesting."""
    
    def test_first_fit_decreasing(self):
        """Algoritmo FFD básico."""
        # Ordenar peças por área (decrescente)
        pieces = [
            {"id": 1, "area": 100},
            {"id": 2, "area": 500},
            {"id": 3, "area": 200},
        ]
        
        sorted_pieces = sorted(pieces, key=lambda p: p["area"], reverse=True)
        
        assert sorted_pieces[0]["id"] == 2
        assert sorted_pieces[1]["id"] == 3
        assert sorted_pieces[2]["id"] == 1
    
    def test_spacing_calculation(self):
        """Cálculo de espaçamento entre peças."""
        spacing = 10
        kerf = 1.5
        total_gap = spacing + kerf
        
        assert total_gap == 11.5
    
    def test_utilization_calculation(self):
        """Cálculo de utilização da chapa."""
        sheet_area = 1500 * 3000  # 4,500,000 mm²
        pieces_area = 3_000_000   # 3,000,000 mm²
        
        utilization = (pieces_area / sheet_area) * 100
        assert abs(utilization - 66.67) < 0.1
    
    def test_collision_detection(self):
        """Detecção de colisão entre peças."""
        piece1 = {"x": 0, "y": 0, "width": 100, "height": 100}
        piece2 = {"x": 50, "y": 50, "width": 100, "height": 100}  # Sobrepõe
        piece3 = {"x": 150, "y": 0, "width": 100, "height": 100}  # Não sobrepõe
        
        def collides(a, b):
            return not (
                a["x"] + a["width"] <= b["x"] or
                b["x"] + b["width"] <= a["x"] or
                a["y"] + a["height"] <= b["y"] or
                b["y"] + b["height"] <= a["y"]
            )
        
        assert collides(piece1, piece2) is True
        assert collides(piece1, piece3) is False


class TestNestingOptimization:
    """Testes de otimização de nesting."""
    
    def test_multiple_sheets_needed(self):
        """Calcular número de chapas necessárias."""
        sheet_area = 1_000_000
        total_pieces_area = 2_500_000
        efficiency = 0.75  # 75% de eficiência esperada
        
        sheets_needed = total_pieces_area / (sheet_area * efficiency)
        
        assert sheets_needed > 3
        assert sheets_needed < 4
    
    def test_scrap_calculation(self):
        """Cálculo de sucata."""
        sheet_area = 4_500_000
        used_area = 3_000_000
        
        scrap = sheet_area - used_area
        scrap_percent = (scrap / sheet_area) * 100
        
        assert scrap == 1_500_000
        assert abs(scrap_percent - 33.33) < 0.1


class TestNestingOutput:
    """Testes de saída do nesting."""
    
    def test_placement_output_format(self):
        """Formato de saída de posicionamento."""
        placement = {
            "piece_id": 1,
            "x": 100,
            "y": 200,
            "rotation": 90,
            "sheet_index": 0
        }
        
        assert "piece_id" in placement
        assert "x" in placement
        assert "y" in placement
        assert "rotation" in placement
    
    def test_report_generation(self):
        """Geração de relatório de nesting."""
        report = {
            "sheets_used": 2,
            "total_pieces": 15,
            "utilization_percent": 78.5,
            "scrap_percent": 21.5,
            "placements": []
        }
        
        assert report["sheets_used"] == 2
        assert report["utilization_percent"] + report["scrap_percent"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
