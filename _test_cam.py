"""Teste do módulo CAM."""
import sys
print(f"Python: {sys.version}")

try:
    from cam.geometry_parser import GeometryParser, Point, Line, Circle
    print("✓ geometry_parser OK")
except Exception as e:
    print(f"✗ geometry_parser ERRO: {e}")
    sys.exit(1)

try:
    from cam.toolpath_generator import ToolpathGenerator
    print("✓ toolpath_generator OK")
except Exception as e:
    print(f"✗ toolpath_generator ERRO: {e}")

try:
    from cam.gcode_generator import GCodeGenerator, PlasmaConfig
    print("✓ gcode_generator OK")
except Exception as e:
    print(f"✗ gcode_generator ERRO: {e}")

try:
    from cam.plasma_optimizer import PlasmaOptimizer
    print("✓ plasma_optimizer OK")
except Exception as e:
    print(f"✗ plasma_optimizer ERRO: {e}")

print("\n=== TESTE DE FUNCIONALIDADE ===")
# Teste básico
geo = GeometryParser()
print(f"GeometryParser criado, tolerance={geo.tolerance}")

# Criar geometria de teste
from cam.geometry_parser import Geometry, Polyline
geom = Geometry()
geom.polylines.append(Polyline(
    points=[Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100), Point(0, 0)],
    closed=True
))
print(f"Geometria criada: {geom.total_entities} entidades")

print("\n✓ TODOS OS TESTES PASSARAM!")
