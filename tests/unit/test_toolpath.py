# ═══════════════════════════════════════════════════════════════════════════════
# TESTES UNITÁRIOS - TOOLPATH GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
"""
Testes unitários para geração de toolpaths.
"""
import pytest
import math
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))


class TestToolpathCalculations:
    """Testes de cálculos de toolpath."""
    
    def test_line_length(self):
        """Calcular comprimento de linha."""
        start = (0, 0)
        end = (100, 0)
        
        length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        assert length == 100
    
    def test_diagonal_line_length(self):
        """Calcular comprimento de linha diagonal."""
        start = (0, 0)
        end = (100, 100)
        
        length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        assert abs(length - 141.42) < 0.01
    
    def test_arc_length(self):
        """Calcular comprimento de arco."""
        radius = 50
        angle = 90  # graus
        
        arc_length = 2 * math.pi * radius * (angle / 360)
        assert abs(arc_length - 78.54) < 0.01
    
    def test_full_circle_length(self):
        """Calcular perímetro de círculo."""
        radius = 50
        
        perimeter = 2 * math.pi * radius
        assert abs(perimeter - 314.16) < 0.01
    
    def test_rectangle_perimeter(self):
        """Calcular perímetro de retângulo."""
        width = 100
        height = 50
        
        perimeter = 2 * (width + height)
        assert perimeter == 300
    
    def test_total_cut_length(self):
        """Calcular comprimento total de corte."""
        shapes = [
            {"type": "rect", "width": 100, "height": 50},  # perimeter = 300
            {"type": "circle", "radius": 25},  # perimeter ≈ 157
        ]
        
        total = 0
        for shape in shapes:
            if shape["type"] == "rect":
                total += 2 * (shape["width"] + shape["height"])
            elif shape["type"] == "circle":
                total += 2 * math.pi * shape["radius"]
        
        assert abs(total - 457.08) < 0.1


class TestToolpathOrdering:
    """Testes de ordenação de toolpath."""
    
    def test_sort_by_distance(self):
        """Ordenar peças por distância do ponto atual."""
        current_pos = (0, 0)
        pieces = [
            {"id": 1, "x": 500, "y": 500},
            {"id": 2, "x": 100, "y": 100},
            {"id": 3, "x": 200, "y": 0},
        ]
        
        def distance(piece):
            return math.sqrt((piece["x"] - current_pos[0])**2 + (piece["y"] - current_pos[1])**2)
        
        sorted_pieces = sorted(pieces, key=distance)
        
        assert sorted_pieces[0]["id"] == 2  # Mais próximo
    
    def test_tsp_simple(self):
        """TSP simplificado (nearest neighbor)."""
        points = [(0, 0), (100, 0), (100, 100), (0, 100)]
        visited = [False] * len(points)
        path = [0]
        visited[0] = True
        
        for _ in range(len(points) - 1):
            current = path[-1]
            nearest = None
            min_dist = float('inf')
            
            for i, point in enumerate(points):
                if not visited[i]:
                    dist = math.sqrt((points[current][0] - point[0])**2 + 
                                    (points[current][1] - point[1])**2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest = i
            
            path.append(nearest)
            visited[nearest] = True
        
        assert len(path) == 4
        assert path == [0, 1, 2, 3]  # Ordem ótima para quadrado


class TestToolpathDirection:
    """Testes de direção do toolpath."""
    
    def test_clockwise_detection(self):
        """Detectar direção horária."""
        # Quadrado em sentido horário
        points = [(0, 0), (100, 0), (100, 100), (0, 100)]
        
        # Shoelace formula para determinar direção
        area = 0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        clockwise = area < 0
        assert clockwise is True
    
    def test_counterclockwise_detection(self):
        """Detectar direção anti-horária."""
        # Quadrado em sentido anti-horário
        points = [(0, 0), (0, 100), (100, 100), (100, 0)]
        
        area = 0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        counterclockwise = area > 0
        assert counterclockwise is True


class TestKerf:
    """Testes de compensação de kerf."""
    
    def test_kerf_offset_calculation(self):
        """Calcular offset de kerf."""
        kerf_width = 1.5  # mm
        offset = kerf_width / 2
        
        assert offset == 0.75
    
    def test_kerf_compensation_outside(self):
        """Compensação de kerf para corte externo."""
        original = {"x": 0, "y": 0, "width": 100, "height": 100}
        kerf = 1.5
        offset = kerf / 2
        
        # Para corte externo, expandir a peça
        compensated = {
            "x": original["x"] - offset,
            "y": original["y"] - offset,
            "width": original["width"] + kerf,
            "height": original["height"] + kerf,
        }
        
        assert compensated["x"] == -0.75
        assert compensated["width"] == 101.5
    
    def test_kerf_compensation_inside(self):
        """Compensação de kerf para corte interno (furo)."""
        original_radius = 50
        kerf = 1.5
        offset = kerf / 2
        
        # Para furo, reduzir o raio
        compensated_radius = original_radius + offset
        
        assert compensated_radius == 50.75


class TestLeadInOut:
    """Testes de lead-in/lead-out."""
    
    def test_arc_lead_in_point(self):
        """Calcular ponto de entrada do lead-in em arco."""
        entry_point = (0, 0)
        lead_radius = 5.0
        entry_angle = 45  # graus
        
        # Ponto de início do arco
        start_x = entry_point[0] - lead_radius * math.cos(math.radians(entry_angle))
        start_y = entry_point[1] - lead_radius * math.sin(math.radians(entry_angle))
        
        assert abs(start_x - (-3.54)) < 0.01
        assert abs(start_y - (-3.54)) < 0.01
    
    def test_linear_lead_in(self):
        """Lead-in linear."""
        entry_point = (0, 0)
        lead_length = 10.0
        entry_angle = 90  # perpendicular
        
        start_x = entry_point[0] - lead_length * math.cos(math.radians(entry_angle))
        start_y = entry_point[1] - lead_length * math.sin(math.radians(entry_angle))
        
        assert abs(start_x - 0) < 0.01
        assert abs(start_y - (-10)) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
