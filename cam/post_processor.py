"""
═══════════════════════════════════════════════════════════════════════════════
POST PROCESSOR ENGINE - Sistema de Pós-Processamento Industrial
═══════════════════════════════════════════════════════════════════════════════

Sistema profissional de pós-processamento para geração de G-code específico
por máquina CNC plasma.

Recursos:
- Suporte a múltiplos perfis de máquina (Mach3, LinuxCNC, Hypertherm, etc.)
- Templates configuráveis por máquina
- Customização de M-codes e G-codes
- Validação de código gerado
- Exportação para múltiplos formatos (NC, TAP, ESSI, ISO)

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from abc import ABC, abstractmethod

logger = logging.getLogger("engcad.cam.post_processor")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

class MachineType(Enum):
    """Tipos de máquina suportados."""
    MACH3 = "mach3"
    MACH4 = "mach4"
    LINUXCNC = "linuxcnc"
    HYPERTHERM_PHOENIX = "hypertherm_phoenix"
    HYPERTHERM_EDGE = "hypertherm_edge"
    FANUC = "fanuc"
    SIEMENS = "siemens"
    HAAS = "haas"
    PLASMACAM = "plasmacam"
    SHEETCAM = "sheetcam"
    TORCHMATE = "torchmate"
    GENERIC = "generic"
    CUSTOM = "custom"


class OutputFormat(Enum):
    """Formatos de saída suportados."""
    GCODE_NC = "nc"           # G-code padrão .nc
    GCODE_TAP = "tap"         # G-code .tap
    GCODE_NGC = "ngc"         # LinuxCNC .ngc
    GCODE_CNC = "cnc"         # Generic .cnc
    ESSI = "essi"             # Formato ESSI (EIA-494)
    ISO_6983 = "iso"          # ISO 6983 padrão
    HPGL = "plt"              # HP-GL/2 para plotters
    DXF_TOOLPATH = "dxf"      # DXF com toolpath


class CoordinateSystem(Enum):
    """Sistemas de coordenadas."""
    ABSOLUTE = "absolute"     # G90
    INCREMENTAL = "incremental"  # G91


class PlaneSelection(Enum):
    """Planos de trabalho."""
    XY = "xy"   # G17
    XZ = "xz"   # G18
    YZ = "yz"   # G19


class Units(Enum):
    """Unidades de medida."""
    METRIC = "metric"         # G21 - milímetros
    IMPERIAL = "imperial"     # G20 - polegadas


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - CONFIGURAÇÃO DE MÁQUINA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MCodeMapping:
    """Mapeamento de M-codes por função."""
    plasma_on: str = "M03"
    plasma_off: str = "M05"
    thc_on: str = "M52 P1"     # Torch Height Control ON
    thc_off: str = "M52 P0"   # Torch Height Control OFF
    arc_ok: str = "M53 P1"    # Arc OK signal
    arc_ok_off: str = "M53 P0"
    program_stop: str = "M00"
    optional_stop: str = "M01"
    program_end: str = "M02"
    end_and_rewind: str = "M30"
    spindle_cw: str = "M03"
    spindle_ccw: str = "M04"
    coolant_on: str = "M08"
    coolant_off: str = "M09"
    
    # Códigos específicos de plasma
    pierce_start: str = ""     # Alguns controladores têm M-code específico
    pierce_end: str = ""
    corner_lock: str = ""      # THC disable em cantos
    corner_unlock: str = ""
    kerf_left: str = "G41"
    kerf_right: str = "G42"
    kerf_off: str = "G40"
    
    # Códigos de gas/assist
    gas_pre_flow: str = ""
    gas_post_flow: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "plasma_on": self.plasma_on,
            "plasma_off": self.plasma_off,
            "thc_on": self.thc_on,
            "thc_off": self.thc_off,
            "arc_ok": self.arc_ok,
            "program_end": self.program_end,
            "kerf_left": self.kerf_left,
            "kerf_right": self.kerf_right,
            "kerf_off": self.kerf_off,
        }


@dataclass
class GCodeSyntax:
    """Sintaxe de G-code específica por máquina."""
    # Formato de números
    decimal_places: int = 3
    leading_zeros: bool = False
    trailing_zeros: bool = True
    decimal_separator: str = "."
    
    # Formato de coordenadas
    x_prefix: str = "X"
    y_prefix: str = "Y"
    z_prefix: str = "Z"
    i_prefix: str = "I"       # Centro de arco X
    j_prefix: str = "J"       # Centro de arco Y
    k_prefix: str = "K"       # Centro de arco Z
    r_prefix: str = "R"       # Raio de arco
    
    # Formato de feed/speed
    feed_prefix: str = "F"
    speed_prefix: str = "S"
    
    # Formato de delays
    dwell_format: str = "G04 P{ms}"  # {ms} = milissegundos, {s} = segundos
    dwell_unit: str = "ms"           # "ms" ou "s"
    
    # Comentários
    comment_start: str = "("
    comment_end: str = ")"
    line_comment: str = ";"
    
    # Estrutura de linha
    line_number_enabled: bool = True
    line_number_prefix: str = "N"
    line_number_increment: int = 10
    space_between_words: bool = True
    uppercase: bool = True
    
    # Terminadores
    line_ending: str = "\n"
    block_skip: str = "/"
    
    # Arcos
    arc_center_absolute: bool = False  # Se True, I/J são absolutos
    arc_radius_mode: bool = False      # Se True, usa R em vez de I/J
    
    def format_number(self, value: float, precision: int = None) -> str:
        """Formata um número de acordo com a sintaxe."""
        prec = precision if precision is not None else self.decimal_places
        
        if self.trailing_zeros:
            formatted = f"{value:.{prec}f}"
        else:
            formatted = f"{value:.{prec}f}".rstrip('0').rstrip('.')
        
        if self.leading_zeros:
            parts = formatted.split('.')
            if len(parts) == 2:
                formatted = parts[0].zfill(4) + '.' + parts[1]
        
        if self.decimal_separator != ".":
            formatted = formatted.replace(".", self.decimal_separator)
        
        if self.uppercase:
            formatted = formatted.upper()
        
        return formatted


@dataclass
class MachinePhysicalLimits:
    """Limites físicos da máquina."""
    # Área de trabalho
    max_x: float = 3000.0     # mm
    max_y: float = 1500.0     # mm
    max_z: float = 100.0      # mm
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = -50.0
    
    # Velocidades
    max_rapid_speed: float = 20000.0    # mm/min
    max_cutting_speed: float = 15000.0  # mm/min
    min_cutting_speed: float = 100.0    # mm/min
    
    # Aceleração
    max_acceleration: float = 5000.0    # mm/s²
    max_jerk: float = 50.0              # mm/s³
    
    # Plasma
    max_amperage: int = 200
    min_amperage: int = 15
    
    # Precisão
    position_tolerance: float = 0.01    # mm
    
    def validate_position(self, x: float, y: float, z: float = 0) -> Tuple[bool, str]:
        """Valida se uma posição está dentro dos limites."""
        errors = []
        
        if x < self.min_x or x > self.max_x:
            errors.append(f"X={x:.2f} fora do limite [{self.min_x}, {self.max_x}]")
        if y < self.min_y or y > self.max_y:
            errors.append(f"Y={y:.2f} fora do limite [{self.min_y}, {self.max_y}]")
        if z < self.min_z or z > self.max_z:
            errors.append(f"Z={z:.2f} fora do limite [{self.min_z}, {self.max_z}]")
        
        return (len(errors) == 0, "; ".join(errors))
    
    def clamp_speed(self, speed: float, is_cutting: bool = True) -> float:
        """Limita velocidade aos limites da máquina."""
        if is_cutting:
            return max(self.min_cutting_speed, min(speed, self.max_cutting_speed))
        return min(speed, self.max_rapid_speed)


@dataclass
class PlasmaParameters:
    """Parâmetros de plasma específicos da máquina."""
    # Alturas
    default_pierce_height: float = 3.0     # mm
    default_cut_height: float = 1.5        # mm
    default_safe_height: float = 15.0      # mm
    
    # Pierce
    default_pierce_delay: float = 0.5      # segundos
    max_pierce_delay: float = 5.0          # segundos
    
    # THC
    thc_enabled: bool = True
    thc_up_speed: float = 500.0           # mm/min
    thc_down_speed: float = 500.0         # mm/min
    thc_threshold_voltage: float = 0.5    # V
    
    # Arc
    arc_voltage_offset: float = 0.0       # V
    default_arc_voltage: float = 120.0    # V
    
    # Kerf
    default_kerf: float = 1.5             # mm


@dataclass
class MachineProfile:
    """Perfil completo de uma máquina CNC."""
    # Identificação
    name: str
    machine_type: MachineType
    description: str = ""
    manufacturer: str = ""
    model: str = ""
    version: str = "1.0"
    
    # Configurações de código
    m_codes: MCodeMapping = field(default_factory=MCodeMapping)
    syntax: GCodeSyntax = field(default_factory=GCodeSyntax)
    
    # Limites físicos
    limits: MachinePhysicalLimits = field(default_factory=MachinePhysicalLimits)
    
    # Parâmetros de plasma
    plasma: PlasmaParameters = field(default_factory=PlasmaParameters)
    
    # Configurações de arquivo
    output_format: OutputFormat = OutputFormat.GCODE_NC
    file_extension: str = ".nc"
    
    # Sistema de coordenadas padrão
    default_coord_system: CoordinateSystem = CoordinateSystem.ABSOLUTE
    default_plane: PlaneSelection = PlaneSelection.XY
    default_units: Units = Units.METRIC
    
    # Cabeçalho/rodapé customizados
    custom_header: List[str] = field(default_factory=list)
    custom_footer: List[str] = field(default_factory=list)
    
    # Recursos suportados
    supports_thc: bool = True
    supports_arc_ok: bool = True
    supports_cutter_comp: bool = True
    supports_subroutines: bool = False
    supports_variables: bool = False
    supports_macros: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte perfil para dicionário."""
        return {
            "name": self.name,
            "machine_type": self.machine_type.value,
            "description": self.description,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "version": self.version,
            "m_codes": self.m_codes.to_dict(),
            "output_format": self.output_format.value,
            "file_extension": self.file_extension,
            "supports": {
                "thc": self.supports_thc,
                "arc_ok": self.supports_arc_ok,
                "cutter_comp": self.supports_cutter_comp,
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MachineProfile":
        """Cria perfil a partir de dicionário."""
        return cls(
            name=data.get("name", "Custom"),
            machine_type=MachineType(data.get("machine_type", "generic")),
            description=data.get("description", ""),
            manufacturer=data.get("manufacturer", ""),
            model=data.get("model", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PERFIS PRÉ-CONFIGURADOS
# ═══════════════════════════════════════════════════════════════════════════════

class MachineProfiles:
    """Repositório de perfis de máquinas pré-configurados."""
    
    @staticmethod
    def get_mach3() -> MachineProfile:
        """Perfil para Mach3."""
        return MachineProfile(
            name="Mach3 Standard",
            machine_type=MachineType.MACH3,
            description="Perfil padrão para Mach3 com suporte a plasma",
            manufacturer="Newfangled Solutions",
            m_codes=MCodeMapping(
                plasma_on="M03",
                plasma_off="M05",
                thc_on="M52 P1",
                thc_off="M52 P0",
            ),
            syntax=GCodeSyntax(
                decimal_places=4,
                line_number_enabled=False,
                comment_start="(",
                comment_end=")",
            ),
            output_format=OutputFormat.GCODE_TAP,
            file_extension=".tap",
        )
    
    @staticmethod
    def get_mach4() -> MachineProfile:
        """Perfil para Mach4."""
        profile = MachineProfiles.get_mach3()
        profile.name = "Mach4 Standard"
        profile.machine_type = MachineType.MACH4
        profile.description = "Perfil padrão para Mach4 com suporte a plasma"
        profile.supports_macros = True
        profile.supports_variables = True
        return profile
    
    @staticmethod
    def get_linuxcnc() -> MachineProfile:
        """Perfil para LinuxCNC."""
        return MachineProfile(
            name="LinuxCNC Plasma",
            machine_type=MachineType.LINUXCNC,
            description="Perfil para LinuxCNC com componente plasmac",
            m_codes=MCodeMapping(
                plasma_on="M03 S1",
                plasma_off="M05",
                thc_on="M62 P2",
                thc_off="M63 P2",
                arc_ok="M66 P3 L3 Q0.5",
            ),
            syntax=GCodeSyntax(
                decimal_places=4,
                line_number_enabled=False,
                dwell_format="G04 P{s}",
                dwell_unit="s",
            ),
            output_format=OutputFormat.GCODE_NGC,
            file_extension=".ngc",
            supports_subroutines=True,
            supports_variables=True,
        )
    
    @staticmethod
    def get_hypertherm_phoenix() -> MachineProfile:
        """Perfil para Hypertherm Phoenix."""
        return MachineProfile(
            name="Hypertherm Phoenix",
            machine_type=MachineType.HYPERTHERM_PHOENIX,
            description="Perfil para controladores Hypertherm Phoenix",
            manufacturer="Hypertherm",
            m_codes=MCodeMapping(
                plasma_on="M07",
                plasma_off="M08",
                thc_on="M50",
                thc_off="M51",
            ),
            syntax=GCodeSyntax(
                decimal_places=3,
                line_number_enabled=True,
                line_number_increment=5,
            ),
            plasma=PlasmaParameters(
                thc_enabled=True,
                default_pierce_delay=0.3,
            ),
            output_format=OutputFormat.GCODE_NC,
            file_extension=".nc",
            custom_header=[
                "(HYPERTHERM PHOENIX PLASMA)",
                "(TRUE HOLE TECHNOLOGY ENABLED)",
            ],
        )
    
    @staticmethod
    def get_hypertherm_edge() -> MachineProfile:
        """Perfil para Hypertherm Edge Pro."""
        return MachineProfile(
            name="Hypertherm Edge Pro",
            machine_type=MachineType.HYPERTHERM_EDGE,
            description="Perfil para Hypertherm Edge Pro com True Hole",
            manufacturer="Hypertherm",
            m_codes=MCodeMapping(
                plasma_on="M03",
                plasma_off="M05",
            ),
            syntax=GCodeSyntax(
                decimal_places=4,
                line_number_enabled=True,
            ),
            output_format=OutputFormat.ESSI,
            file_extension=".essi",
        )
    
    @staticmethod
    def get_fanuc() -> MachineProfile:
        """Perfil para controladores FANUC."""
        return MachineProfile(
            name="FANUC Standard",
            machine_type=MachineType.FANUC,
            description="Perfil para controladores FANUC série 0i/30i",
            manufacturer="FANUC",
            m_codes=MCodeMapping(
                plasma_on="M03",
                plasma_off="M05",
                program_end="M30",
            ),
            syntax=GCodeSyntax(
                decimal_places=3,
                leading_zeros=True,
                line_number_enabled=True,
                line_number_increment=10,
            ),
            output_format=OutputFormat.GCODE_NC,
            file_extension=".nc",
            supports_macros=True,
            supports_subroutines=True,
        )
    
    @staticmethod
    def get_plasmacam() -> MachineProfile:
        """Perfil para PlasmaCam."""
        return MachineProfile(
            name="PlasmaCam",
            machine_type=MachineType.PLASMACAM,
            description="Perfil para mesas PlasmaCam",
            manufacturer="PlasmaCam",
            m_codes=MCodeMapping(
                plasma_on="M12",
                plasma_off="M13",
            ),
            syntax=GCodeSyntax(
                decimal_places=3,
                line_number_enabled=False,
            ),
            output_format=OutputFormat.GCODE_NC,
            file_extension=".dnc",
        )
    
    @staticmethod
    def get_torchmate() -> MachineProfile:
        """Perfil para Torchmate."""
        return MachineProfile(
            name="Torchmate",
            machine_type=MachineType.TORCHMATE,
            description="Perfil para mesas Torchmate",
            manufacturer="Lincoln Electric",
            m_codes=MCodeMapping(
                plasma_on="M03",
                plasma_off="M05",
            ),
            output_format=OutputFormat.GCODE_TAP,
            file_extension=".tap",
        )
    
    @staticmethod
    def get_generic() -> MachineProfile:
        """Perfil genérico."""
        return MachineProfile(
            name="Generic CNC Plasma",
            machine_type=MachineType.GENERIC,
            description="Perfil genérico para CNC plasma com G-code padrão",
            output_format=OutputFormat.GCODE_NC,
            file_extension=".nc",
        )
    
    @staticmethod
    def get_all_profiles() -> Dict[str, MachineProfile]:
        """Retorna todos os perfis disponíveis."""
        return {
            "mach3": MachineProfiles.get_mach3(),
            "mach4": MachineProfiles.get_mach4(),
            "linuxcnc": MachineProfiles.get_linuxcnc(),
            "hypertherm_phoenix": MachineProfiles.get_hypertherm_phoenix(),
            "hypertherm_edge": MachineProfiles.get_hypertherm_edge(),
            "fanuc": MachineProfiles.get_fanuc(),
            "plasmacam": MachineProfiles.get_plasmacam(),
            "torchmate": MachineProfiles.get_torchmate(),
            "generic": MachineProfiles.get_generic(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# POST PROCESSOR BASE
# ═══════════════════════════════════════════════════════════════════════════════

class PostProcessorBase(ABC):
    """Classe base abstrata para pós-processadores."""
    
    def __init__(self, profile: MachineProfile):
        self.profile = profile
        self.line_number = 0
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.current_feed = 0.0
        self.plasma_on = False
        self.thc_on = False
        
    @abstractmethod
    def generate_header(self, job_info: Dict[str, Any]) -> List[str]:
        """Gera cabeçalho do programa."""
        pass
    
    @abstractmethod
    def generate_footer(self) -> List[str]:
        """Gera rodapé do programa."""
        pass
    
    @abstractmethod
    def generate_pierce_sequence(self, params: Dict[str, Any]) -> List[str]:
        """Gera sequência de perfuração."""
        pass
    
    @abstractmethod
    def generate_move(self, move_type: str, x: float, y: float, 
                      z: float = None, feed: float = None,
                      arc_params: Dict = None) -> List[str]:
        """Gera código de movimento."""
        pass
    
    def format_line(self, code: str, comment: str = None) -> str:
        """Formata uma linha de código."""
        syntax = self.profile.syntax
        
        line = ""
        
        # Número de linha
        if syntax.line_number_enabled:
            line = f"{syntax.line_number_prefix}{self.line_number} "
            self.line_number += syntax.line_number_increment
        
        # Código
        line += code
        
        # Comentário
        if comment and self.profile.syntax.comment_start:
            line += f" {syntax.comment_start}{comment}{syntax.comment_end}"
        
        return line.strip()
    
    def format_coord(self, prefix: str, value: float) -> str:
        """Formata uma coordenada."""
        formatted = self.profile.syntax.format_number(value)
        return f"{prefix}{formatted}"


# ═══════════════════════════════════════════════════════════════════════════════
# POST PROCESSOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class PostProcessor(PostProcessorBase):
    """
    Pós-processador principal para G-code.
    
    Converte toolpaths em G-code específico para cada máquina.
    """
    
    def __init__(self, profile: MachineProfile = None):
        if profile is None:
            profile = MachineProfiles.get_generic()
        super().__init__(profile)
        self.output_lines: List[str] = []
        self.statistics = {
            "total_moves": 0,
            "rapid_moves": 0,
            "cutting_moves": 0,
            "arc_moves": 0,
            "pierces": 0,
            "total_cutting_length": 0.0,
            "total_rapid_length": 0.0,
            "estimated_time": 0.0,
        }
    
    def generate_header(self, job_info: Dict[str, Any] = None) -> List[str]:
        """Gera cabeçalho do programa."""
        lines = []
        syntax = self.profile.syntax
        job = job_info or {}
        
        # Número do programa (se aplicável)
        if job.get("program_number"):
            lines.append(f"O{job['program_number']}")
        
        # Cabeçalho customizado do perfil
        for custom_line in self.profile.custom_header:
            lines.append(custom_line)
        
        # Informações do job
        lines.append(f"{syntax.comment_start}{'='*50}{syntax.comment_end}")
        lines.append(f"{syntax.comment_start} ENGENHARIA CAD - PLASMA CNC {syntax.comment_end}")
        lines.append(f"{syntax.comment_start} Máquina: {self.profile.name} {syntax.comment_end}")
        lines.append(f"{syntax.comment_start} Gerado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {syntax.comment_end}")
        
        if job.get("material"):
            lines.append(f"{syntax.comment_start} Material: {job['material']} {syntax.comment_end}")
        if job.get("thickness"):
            lines.append(f"{syntax.comment_start} Espessura: {job['thickness']}mm {syntax.comment_end}")
        if job.get("total_parts"):
            lines.append(f"{syntax.comment_start} Peças: {job['total_parts']} {syntax.comment_end}")
            
        lines.append(f"{syntax.comment_start}{'='*50}{syntax.comment_end}")
        lines.append("")
        
        # Inicialização
        if self.profile.default_units == Units.METRIC:
            lines.append(self.format_line("G21", "Unidades: milímetros"))
        else:
            lines.append(self.format_line("G20", "Unidades: polegadas"))
        
        if self.profile.default_coord_system == CoordinateSystem.ABSOLUTE:
            lines.append(self.format_line("G90", "Coordenadas absolutas"))
        else:
            lines.append(self.format_line("G91", "Coordenadas incrementais"))
        
        # Plano de trabalho
        if self.profile.default_plane == PlaneSelection.XY:
            lines.append(self.format_line("G17", "Plano XY"))
        
        # Sistema de coordenadas da peça
        lines.append(self.format_line("G54", "Sistema de coordenadas"))
        
        # Garantir plasma desligado
        lines.append(self.format_line(self.profile.m_codes.plasma_off, "Plasma OFF"))
        
        # THC desligado
        if self.profile.supports_thc and self.profile.m_codes.thc_off:
            lines.append(self.format_line(self.profile.m_codes.thc_off, "THC OFF"))
        
        # Mover para altura segura
        safe_z = self.profile.plasma.default_safe_height
        lines.append(self.format_line(f"G00 Z{syntax.format_number(safe_z)}", "Altura segura"))
        
        lines.append("")
        
        return lines
    
    def generate_footer(self) -> List[str]:
        """Gera rodapé do programa."""
        lines = []
        syntax = self.profile.syntax
        
        lines.append("")
        lines.append(f"{syntax.comment_start}{'='*50}{syntax.comment_end}")
        lines.append(f"{syntax.comment_start} FIM DO PROGRAMA {syntax.comment_end}")
        lines.append(f"{syntax.comment_start}{'='*50}{syntax.comment_end}")
        
        # Garantir plasma desligado
        lines.append(self.format_line(self.profile.m_codes.plasma_off, "Plasma OFF"))
        
        # THC desligado
        if self.profile.supports_thc and self.profile.m_codes.thc_off:
            lines.append(self.format_line(self.profile.m_codes.thc_off, "THC OFF"))
        
        # Mover para origem
        safe_z = self.profile.plasma.default_safe_height
        lines.append(self.format_line(f"G00 Z{syntax.format_number(safe_z)}", "Altura segura"))
        lines.append(self.format_line("G00 X0 Y0", "Retornar à origem"))
        
        # Rodapé customizado
        for custom_line in self.profile.custom_footer:
            lines.append(custom_line)
        
        # Fim do programa
        lines.append(self.format_line(self.profile.m_codes.program_end, "Fim do programa"))
        
        return lines
    
    def generate_pierce_sequence(
        self,
        x: float,
        y: float,
        pierce_height: float = None,
        cut_height: float = None,
        pierce_delay: float = None,
        arc_voltage: float = None
    ) -> List[str]:
        """Gera sequência completa de perfuração."""
        lines = []
        syntax = self.profile.syntax
        plasma = self.profile.plasma
        m_codes = self.profile.m_codes
        
        # Valores padrão
        p_height = pierce_height or plasma.default_pierce_height
        c_height = cut_height or plasma.default_cut_height
        p_delay = pierce_delay or plasma.default_pierce_delay
        
        # Movimento rápido para posição XY
        lines.append(self.format_line(
            f"G00 X{syntax.format_number(x)} Y{syntax.format_number(y)}",
            "Posição de pierce"
        ))
        
        # Descer para altura de pierce
        lines.append(self.format_line(
            f"G00 Z{syntax.format_number(p_height)}",
            "Altura de pierce"
        ))
        
        # Ligar plasma
        lines.append(self.format_line(m_codes.plasma_on, "Plasma ON"))
        
        # Pierce delay
        if syntax.dwell_unit == "ms":
            delay_value = int(p_delay * 1000)
        else:
            delay_value = p_delay
        
        dwell_cmd = syntax.dwell_format.format(ms=delay_value, s=p_delay)
        lines.append(self.format_line(dwell_cmd, f"Pierce delay: {p_delay}s"))
        
        # Ligar THC após pierce
        if self.profile.supports_thc and m_codes.thc_on:
            lines.append(self.format_line(m_codes.thc_on, "THC ON"))
        
        # Descer para altura de corte
        lines.append(self.format_line(
            f"G01 Z{syntax.format_number(c_height)} F300",
            "Altura de corte"
        ))
        
        self.statistics["pierces"] += 1
        self.plasma_on = True
        self.thc_on = True
        
        return lines
    
    def generate_plasma_off(self) -> List[str]:
        """Gera sequência de desligamento do plasma."""
        lines = []
        m_codes = self.profile.m_codes
        syntax = self.profile.syntax
        
        # Desligar plasma
        lines.append(self.format_line(m_codes.plasma_off, "Plasma OFF"))
        
        # Desligar THC
        if self.profile.supports_thc and m_codes.thc_off:
            lines.append(self.format_line(m_codes.thc_off, "THC OFF"))
        
        # Subir para altura segura
        safe_z = self.profile.plasma.default_safe_height
        lines.append(self.format_line(
            f"G00 Z{syntax.format_number(safe_z)}",
            "Altura segura"
        ))
        
        self.plasma_on = False
        self.thc_on = False
        
        return lines
    
    def generate_move(
        self,
        move_type: str,
        x: float,
        y: float,
        z: float = None,
        feed: float = None,
        arc_params: Dict = None
    ) -> List[str]:
        """
        Gera código de movimento.
        
        Args:
            move_type: "rapid", "linear", "arc_cw", "arc_ccw"
            x, y: Coordenadas de destino
            z: Coordenada Z (opcional)
            feed: Feed rate (opcional)
            arc_params: Parâmetros do arco {"i": float, "j": float} ou {"r": float}
        """
        lines = []
        syntax = self.profile.syntax
        
        # Calcular distância
        dx = x - self.current_x
        dy = y - self.current_y
        distance = (dx*dx + dy*dy) ** 0.5
        
        # Construir comando
        if move_type == "rapid":
            cmd = f"G00 X{syntax.format_number(x)} Y{syntax.format_number(y)}"
            if z is not None:
                cmd += f" Z{syntax.format_number(z)}"
            self.statistics["rapid_moves"] += 1
            self.statistics["total_rapid_length"] += distance
            
        elif move_type == "linear":
            cmd = f"G01 X{syntax.format_number(x)} Y{syntax.format_number(y)}"
            if z is not None:
                cmd += f" Z{syntax.format_number(z)}"
            if feed:
                cmd += f" F{int(feed)}"
            self.statistics["cutting_moves"] += 1
            self.statistics["total_cutting_length"] += distance
            
        elif move_type in ("arc_cw", "arc_ccw"):
            g_code = "G02" if move_type == "arc_cw" else "G03"
            cmd = f"{g_code} X{syntax.format_number(x)} Y{syntax.format_number(y)}"
            
            if arc_params:
                if syntax.arc_radius_mode and "r" in arc_params:
                    cmd += f" R{syntax.format_number(arc_params['r'])}"
                else:
                    if "i" in arc_params:
                        cmd += f" I{syntax.format_number(arc_params['i'])}"
                    if "j" in arc_params:
                        cmd += f" J{syntax.format_number(arc_params['j'])}"
            
            if feed:
                cmd += f" F{int(feed)}"
            
            self.statistics["arc_moves"] += 1
            self.statistics["cutting_moves"] += 1
            # Aproximação para comprimento do arco
            self.statistics["total_cutting_length"] += distance * 1.2
        
        else:
            raise ValueError(f"Tipo de movimento desconhecido: {move_type}")
        
        lines.append(self.format_line(cmd))
        self.statistics["total_moves"] += 1
        
        # Atualizar posição atual
        self.current_x = x
        self.current_y = y
        if z is not None:
            self.current_z = z
        if feed:
            self.current_feed = feed
        
        return lines
    
    def generate_comment(self, text: str) -> str:
        """Gera uma linha de comentário."""
        syntax = self.profile.syntax
        return f"{syntax.comment_start} {text} {syntax.comment_end}"
    
    def generate_section_comment(self, title: str) -> List[str]:
        """Gera comentários de seção."""
        syntax = self.profile.syntax
        return [
            "",
            f"{syntax.comment_start}{'='*30}{syntax.comment_end}",
            f"{syntax.comment_start} {title} {syntax.comment_end}",
            f"{syntax.comment_start}{'='*30}{syntax.comment_end}",
        ]
    
    def process_toolpath(
        self,
        toolpath: Any,
        job_info: Dict[str, Any] = None,
        cutting_params: Dict[str, Any] = None
    ) -> str:
        """
        Processa um toolpath completo e gera G-code.
        
        Args:
            toolpath: Objeto Toolpath do módulo toolpath_generator
            job_info: Informações do job
            cutting_params: Parâmetros de corte
        
        Returns:
            str: G-code gerado
        """
        self.output_lines = []
        self.line_number = 10
        params = cutting_params or {}
        
        # Cabeçalho
        self.output_lines.extend(self.generate_header(job_info))
        
        # Processar cada caminho de corte
        for i, path in enumerate(toolpath.paths):
            # Comentário de seção
            contour_type = "INTERNO" if hasattr(path, 'contour_type') and \
                           str(path.contour_type) == 'ContourType.INTERNAL' else "EXTERNO"
            self.output_lines.extend(
                self.generate_section_comment(f"CORTE {i+1} - {contour_type}")
            )
            
            # Encontrar ponto de entrada
            entry_point = None
            if path.lead_in:
                entry_point = path.lead_in[0].start_point
            elif path.moves:
                entry_point = path.moves[0].start_point
            
            if entry_point:
                # Sequência de pierce
                self.output_lines.extend(
                    self.generate_pierce_sequence(
                        x=entry_point.x,
                        y=entry_point.y,
                        pierce_height=params.get('pierce_height'),
                        cut_height=params.get('cut_height'),
                        pierce_delay=params.get('pierce_delay'),
                    )
                )
                
                # Lead-in
                for move in path.lead_in:
                    self.output_lines.extend(
                        self._process_move(move, params.get('cutting_speed'))
                    )
                
                # Movimentos de corte
                for move in path.moves:
                    self.output_lines.extend(
                        self._process_move(move, params.get('cutting_speed'))
                    )
                
                # Lead-out
                for move in path.lead_out:
                    self.output_lines.extend(
                        self._process_move(move, params.get('cutting_speed'))
                    )
                
                # Desligar plasma
                self.output_lines.extend(self.generate_plasma_off())
        
        # Rodapé
        self.output_lines.extend(self.generate_footer())
        
        return "\n".join(self.output_lines)
    
    def _process_move(self, move: Any, default_speed: float = None) -> List[str]:
        """Processa um movimento individual."""
        move_type_map = {
            "MoveType.RAPID": "rapid",
            "MoveType.LINEAR": "linear",
            "MoveType.ARC_CW": "arc_cw",
            "MoveType.ARC_CCW": "arc_ccw",
        }
        
        move_type = move_type_map.get(str(move.move_type), "linear")
        feed = move.feed_rate or default_speed
        
        arc_params = None
        if move_type in ("arc_cw", "arc_ccw") and move.center and move.start_point:
            arc_params = {
                "i": move.center.x - move.start_point.x,
                "j": move.center.y - move.start_point.y,
            }
        
        return self.generate_move(
            move_type=move_type,
            x=move.end_point.x,
            y=move.end_point.y,
            feed=feed,
            arc_params=arc_params,
        )
    
    def validate_output(self, gcode: str) -> Tuple[bool, List[str]]:
        """
        Valida o G-code gerado.
        
        Returns:
            Tuple[bool, List[str]]: (válido, lista de erros/warnings)
        """
        errors = []
        warnings = []
        lines = gcode.split('\n')
        
        # Verificar linhas básicas
        has_init = False
        has_end = False
        plasma_state = False
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('(') or line.startswith(';'):
                continue
            
            # Verificar inicialização
            if 'G21' in line or 'G20' in line:
                has_init = True
            
            # Verificar fim
            if 'M02' in line or 'M30' in line:
                has_end = True
            
            # Verificar estado do plasma
            if self.profile.m_codes.plasma_on in line:
                if plasma_state:
                    warnings.append(f"Linha {i}: Plasma ligado quando já estava ligado")
                plasma_state = True
            if self.profile.m_codes.plasma_off in line:
                plasma_state = False
            
            # Verificar limites de coordenadas
            x_match = re.search(r'X(-?\d+\.?\d*)', line)
            y_match = re.search(r'Y(-?\d+\.?\d*)', line)
            
            if x_match:
                x_val = float(x_match.group(1))
                valid, msg = self.profile.limits.validate_position(x_val, 0, 0)
                if not valid:
                    errors.append(f"Linha {i}: {msg}")
            
            if y_match:
                y_val = float(y_match.group(1))
                valid, msg = self.profile.limits.validate_position(0, y_val, 0)
                if not valid:
                    errors.append(f"Linha {i}: {msg}")
        
        if not has_init:
            warnings.append("Código não possui inicialização de unidades (G20/G21)")
        
        if not has_end:
            warnings.append("Código não possui comando de fim de programa (M02/M30)")
        
        if plasma_state:
            errors.append("Plasma ainda ligado ao final do programa")
        
        return (len(errors) == 0, errors + warnings)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do código gerado."""
        return {
            **self.statistics,
            "machine": self.profile.name,
            "format": self.profile.output_format.value,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# POST PROCESSOR ESSI
# ═══════════════════════════════════════════════════════════════════════════════

class ESSIPostProcessor(PostProcessorBase):
    """
    Pós-processador para formato ESSI (EIA-494).
    
    O formato ESSI é usado por sistemas Hypertherm e outros
    controladores industriais de plasma.
    """
    
    def __init__(self, profile: MachineProfile = None):
        if profile is None:
            profile = MachineProfiles.get_hypertherm_edge()
        super().__init__(profile)
        self.block_number = 0
    
    def generate_header(self, job_info: Dict[str, Any] = None) -> List[str]:
        """Gera cabeçalho ESSI."""
        lines = []
        job = job_info or {}
        
        lines.append("%%")  # Início do arquivo ESSI
        lines.append(f"0={job.get('program_number', '1')}")  # Número do programa
        lines.append("1=1")  # Tipo de programa (1=corte)
        lines.append(f"2={job.get('material', 'STEEL')}")  # Material
        lines.append(f"3={job.get('thickness', '6.0')}")  # Espessura
        lines.append(f"4={job.get('units', 'MM')}")  # Unidades
        lines.append("5=1")  # Sistema de coordenadas
        lines.append("%%")  # Fim do cabeçalho
        
        return lines
    
    def generate_footer(self) -> List[str]:
        """Gera rodapé ESSI."""
        lines = []
        lines.append("E")  # End of program
        lines.append("%%")
        return lines
    
    def generate_pierce_sequence(self, params: Dict[str, Any]) -> List[str]:
        """Gera sequência de pierce ESSI."""
        lines = []
        x = params.get('x', 0)
        y = params.get('y', 0)
        
        # Movimento e pierce
        lines.append(f"M P{self.block_number} X{x:.3f} Y{y:.3f}")
        self.block_number += 1
        lines.append(f"C P{self.block_number}")  # Start cut
        self.block_number += 1
        
        return lines
    
    def generate_move(
        self,
        move_type: str,
        x: float,
        y: float,
        z: float = None,
        feed: float = None,
        arc_params: Dict = None
    ) -> List[str]:
        """Gera movimento ESSI."""
        lines = []
        
        if move_type == "rapid":
            lines.append(f"M P{self.block_number} X{x:.3f} Y{y:.3f}")
        elif move_type == "linear":
            lines.append(f"L P{self.block_number} X{x:.3f} Y{y:.3f}")
        elif move_type in ("arc_cw", "arc_ccw"):
            direction = "CW" if move_type == "arc_cw" else "CCW"
            if arc_params:
                i = arc_params.get('i', 0)
                j = arc_params.get('j', 0)
                lines.append(
                    f"A P{self.block_number} X{x:.3f} Y{y:.3f} "
                    f"I{i:.3f} J{j:.3f} {direction}"
                )
        
        self.block_number += 1
        return lines


# ═══════════════════════════════════════════════════════════════════════════════
# GERENCIADOR DE PÓS-PROCESSADORES
# ═══════════════════════════════════════════════════════════════════════════════

class PostProcessorManager:
    """
    Gerenciador centralizado de pós-processadores.
    
    Permite:
    - Carregar perfis de máquinas
    - Criar pós-processadores
    - Salvar/carregar perfis customizados
    """
    
    def __init__(self, profiles_dir: str = None):
        self.profiles_dir = profiles_dir or os.path.join(
            os.path.dirname(__file__), 'machine_profiles'
        )
        self.profiles = MachineProfiles.get_all_profiles()
        self._load_custom_profiles()
    
    def _load_custom_profiles(self):
        """Carrega perfis customizados do diretório."""
        if not os.path.exists(self.profiles_dir):
            try:
                os.makedirs(self.profiles_dir, exist_ok=True)
            except OSError:
                # Read-only filesystem (serverless environment)
                return
            return
        
        try:
            for filename in os.listdir(self.profiles_dir):
                if filename.endswith('.json'):
                    try:
                        filepath = os.path.join(self.profiles_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        profile = MachineProfile.from_dict(data)
                        self.profiles[profile.name.lower().replace(' ', '_')] = profile
                        logger.info(f"Perfil customizado carregado: {profile.name}")
                    except Exception as e:
                        logger.error(f"Erro ao carregar perfil {filename}: {e}")
        except OSError:
            # Read-only or inaccessible directory
            pass
    
    def get_profile(self, name: str) -> Optional[MachineProfile]:
        """Obtém um perfil pelo nome."""
        return self.profiles.get(name.lower().replace(' ', '_'))
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """Lista todos os perfis disponíveis."""
        return [
            {
                "name": p.name,
                "key": key,
                "type": p.machine_type.value,
                "description": p.description,
                "format": p.output_format.value,
            }
            for key, p in self.profiles.items()
        ]
    
    def create_post_processor(
        self,
        profile_name: str = "generic",
        output_format: OutputFormat = None
    ) -> PostProcessorBase:
        """
        Cria um pós-processador para o perfil especificado.
        
        Args:
            profile_name: Nome do perfil
            output_format: Formato de saída (opcional, sobrescreve o do perfil)
        
        Returns:
            PostProcessorBase: Instância do pós-processador
        """
        profile = self.get_profile(profile_name)
        if profile is None:
            logger.warning(f"Perfil '{profile_name}' não encontrado, usando genérico")
            profile = MachineProfiles.get_generic()
        
        if output_format:
            profile.output_format = output_format
        
        # Escolher implementação baseada no formato
        if profile.output_format == OutputFormat.ESSI:
            return ESSIPostProcessor(profile)
        else:
            return PostProcessor(profile)
    
    def save_custom_profile(self, profile: MachineProfile) -> bool:
        """Salva um perfil customizado."""
        try:
            filename = profile.name.lower().replace(' ', '_') + '.json'
            filepath = os.path.join(self.profiles_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.profiles[profile.name.lower().replace(' ', '_')] = profile
            logger.info(f"Perfil salvo: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar perfil: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# INSTÂNCIA GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

# Instância global para uso conveniente
post_processor_manager = PostProcessorManager()


def get_post_processor(profile_name: str = "generic") -> PostProcessorBase:
    """Função auxiliar para obter um pós-processador."""
    return post_processor_manager.create_post_processor(profile_name)


def list_available_machines() -> List[Dict[str, Any]]:
    """Lista máquinas disponíveis."""
    return post_processor_manager.list_profiles()
