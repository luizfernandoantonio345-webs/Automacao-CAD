"""
Módulo de Isométricos de Tubulação
==================================
Gera desenhos isométricos com:
  • Geometria 3D completa (tubos, válvulas, suportes)
  • Transformação isométrica automática
  • Exportação para DXF
  • Cotação ponta-a-ponta e centro-a-centro
  • Lista de Materiais (BOM) integrada
  • Detecção e inserção automática de suportes
"""

from .geometry import (
    Ponto3D,
    Vetor3D,
    TipoValvula,
    Tubo,
    Valvula,
    Suporte,
    SistemaIsometrico,
)
from .simbologia import SimbologiaValvulas, ElementoDXF
from .cotacao import Cota, GeradorCotas, EstilosCota
from .dxf import GeradorDXF

__all__ = [
    "Ponto3D",
    "Vetor3D",
    "TipoValvula",
    "Tubo",
    "Valvula",
    "Suporte",
    "SistemaIsometrico",
    "SimbologiaValvulas",
    "ElementoDXF",
    "Cota",
    "GeradorCotas",
    "EstilosCota",
    "GeradorDXF",
]
