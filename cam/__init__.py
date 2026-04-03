"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Computer Aided Manufacturing
Engenharia CAD - Sistema de Geração de G-code para Corte Plasma CNC
═══════════════════════════════════════════════════════════════════════════════

Este módulo fornece funcionalidades para:
- Parsing de geometria DXF/SVG
- Geração de toolpaths otimizados para corte plasma
- Geração de G-code compatível com CNCs plasma
- Otimizações industriais (kerf, lead-in/out, sequenciamento)
- Sistema de pós-processamento profissional
- Controle avançado de piercing
- Controle dinâmico de velocidade
- Lead-in/Lead-out editável
- Micro-joints (tabs)
- Simulação física real
- IA operacional

Desenvolvido para máquinas CNC Plasma Edge e compatíveis.
"""

from .geometry_parser import GeometryParser, Geometry, Line, Arc, Polyline, Circle
from .toolpath_generator import ToolpathGenerator, Toolpath, CuttingPath
from .gcode_generator import GCodeGenerator, GCodeConfig, PlasmaConfig
from .plasma_optimizer import PlasmaOptimizer, OptimizationConfig
from .nesting_engine import (
    NestingEngine, NestingAlgorithm, NestingPriority, 
    NestingPiece, NestingSheet, NestingResult, PieceLibrary,
    create_rectangle_piece, create_circle_piece, create_flange_piece
)
from .dxf_exporter import DXFExporter, export_geometry_to_dxf
from .geometry_validator import GeometryValidator, ValidationConfig, validate_for_plasma_cutting

# Módulos industriais avançados
from .post_processor import (
    PostProcessor, MachineProfile, MachineProfiles, MachineType,
    OutputFormat, MCodeMapping, GCodeSyntax, MachinePhysicalLimits,
)
from .piercing_control import (
    PierceGenerator, PierceType, PierceParameters, PierceTable,
    PierceResult, PierceQuality, MaterialCategory,
)
from .speed_control import (
    SpeedController, SpeedConfig, SpeedMode, SpeedProfile,
)
from .lead_inout import (
    LeadGenerator, LeadConfig, LeadType, LeadPosition, LeadPresets,
)
from .microjoint import (
    TabGenerator, TabConfig, TabType, TabDistribution, Tab,
)
from .machine_database import (
    MachineDatabase, Machine, MachineCategory, ControllerType,
)
from .physics_simulation import (
    PhysicsSimulator, MachinePhysics, MachinePhysicsPresets,
    SimulationMode, simulate_gcode, estimate_job_time,
)
from .operational_ai import (
    OperationalAI, CuttingDatabase, CuttingParameters,
    NestingStrategy, ToolpathOptimization, GeometryProblem,
    get_cutting_parameters, analyze_and_fix_geometry,
    suggest_all_optimizations, AIConfidence, OptimizationType,
)

__version__ = "2.0.0"
__all__ = [
    "GeometryParser",
    "Geometry",
    "Line",
    "Arc",
    "Polyline",
    "Circle",
    "ToolpathGenerator",
    "Toolpath",
    "CuttingPath",
    "GCodeGenerator",
    "GCodeConfig",
    "PlasmaConfig",
    "PlasmaOptimizer",
    "OptimizationConfig",
    # Nesting
    "NestingEngine",
    "NestingAlgorithm",
    "NestingPriority",
    "NestingPiece",
    "NestingSheet",
    "NestingResult",
    "PieceLibrary",
    "create_rectangle_piece",
    "create_circle_piece",
    "create_flange_piece",
    # DXF Export
    "DXFExporter",
    "export_geometry_to_dxf",
    # Validation
    "GeometryValidator",
    "ValidationConfig",
    "validate_for_plasma_cutting",
    # Post Processor
    "PostProcessor",
    "MachineProfile",
    "MachineProfiles",
    "MachineType",
    "OutputFormat",
    "MCodeMapping",
    "GCodeSyntax",
    "MachinePhysicalLimits",
    # Pierce Control
    "PierceGenerator",
    "PierceType",
    "PierceParameters",
    "PierceTable",
    "PierceResult",
    "PierceQuality",
    "MaterialCategory",
    # Speed Control
    "SpeedController",
    "SpeedConfig",
    "SpeedMode",
    "SpeedProfile",
    # Lead In/Out
    "LeadGenerator",
    "LeadConfig",
    "LeadType",
    "LeadPosition",
    "LeadPresets",
    # Tab/Microjoint
    "TabGenerator",
    "TabConfig",
    "TabType",
    "TabDistribution",
    "Tab",
    # Machine Database
    "MachineDatabase",
    "Machine",
    "MachineCategory",
    "ControllerType",
    # Physics Simulation
    "PhysicsSimulator",
    "MachinePhysics",
    "MachinePhysicsPresets",
    "SimulationMode",
    "simulate_gcode",
    "estimate_job_time",
    # Operational AI
    "OperationalAI",
    "CuttingDatabase",
    "CuttingParameters",
    "NestingStrategy",
    "ToolpathOptimization",
    "GeometryProblem",
    "get_cutting_parameters",
    "analyze_and_fix_geometry",
    "suggest_all_optimizations",
    "AIConfidence",
    "OptimizationType",
]
