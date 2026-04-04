"""
═══════════════════════════════════════════════════════════════════════════════
Módulo CAM - Gerador de G-code para Corte Plasma
Engenharia CAD - Sistema de Geração de G-code para Corte Plasma CNC
═══════════════════════════════════════════════════════════════════════════════

Responsável por:
- Converter toolpaths em G-code
- Gerar código compatível com CNCs plasma (Mach3, LinuxCNC, etc.)
- Incluir comandos específicos de plasma (THC, pierce delay, etc.)
- Suporte a múltiplos dialetos de G-code
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from .toolpath_generator import Toolpath, CuttingPath, ToolpathMove, MoveType, ContourType
from .geometry_parser import Point

logger = logging.getLogger("engcad.cam.gcode_generator")


class GCodeDialect(Enum):
    """Dialetos de G-code suportados."""
    STANDARD = "standard"     # G-code padrão (Mach3, LinuxCNC)
    FANUC = "fanuc"           # Estilo Fanuc
    EDGE = "edge"             # Plasma Edge específico
    HYPERTHERM = "hypertherm" # Hypertherm Phoenix


class MaterialType(Enum):
    """Tipos de material suportados."""
    MILD_STEEL = "mild_steel"
    STAINLESS = "stainless"
    ALUMINUM = "aluminum"
    COPPER = "copper"
    BRASS = "brass"


@dataclass
class PlasmaConfig:
    """Configuração específica para corte plasma."""
    
    # Material
    material: MaterialType = MaterialType.MILD_STEEL
    thickness: float = 6.0  # mm
    
    # Corrente e velocidade
    amperage: int = 45  # Amperes
    cutting_speed: float = 2000  # mm/min
    
    # Alturas
    pierce_height: float = 3.0  # mm
    cut_height: float = 1.5  # mm
    safe_height: float = 10.0  # mm
    
    # Tempos
    pierce_delay: float = 0.5  # segundos
    
    # THC (Torch Height Control)
    thc_enabled: bool = True
    arc_voltage: float = 120.0  # Volts
    
    # Kerf
    kerf_width: float = 1.5  # mm
    
    @classmethod
    def for_material(cls, material: MaterialType, thickness: float) -> "PlasmaConfig":
        """Retorna configuração padrão para um material e espessura."""
        
        # Tabelas de corte típicas (simplificadas)
        CUTTING_TABLES = {
            MaterialType.MILD_STEEL: {
                # espessura: (amperagem, velocidade, kerf)
                3.0: (30, 3500, 1.0),
                6.0: (45, 2000, 1.5),
                10.0: (65, 1200, 1.8),
                12.0: (80, 900, 2.0),
                16.0: (100, 600, 2.2),
                20.0: (130, 450, 2.5),
                25.0: (200, 350, 3.0),
            },
            MaterialType.STAINLESS: {
                3.0: (40, 2800, 1.2),
                6.0: (60, 1600, 1.8),
                10.0: (80, 900, 2.2),
                12.0: (100, 700, 2.5),
            },
            MaterialType.ALUMINUM: {
                3.0: (40, 4000, 1.5),
                6.0: (65, 2500, 2.0),
                10.0: (100, 1500, 2.5),
            },
        }
        
        table = CUTTING_TABLES.get(material, CUTTING_TABLES[MaterialType.MILD_STEEL])
        
        # Encontrar configuração mais próxima da espessura
        thicknesses = sorted(table.keys())
        closest = min(thicknesses, key=lambda t: abs(t - thickness))
        
        amp, speed, kerf = table[closest]
        
        # Ajustar velocidade proporcionalmente à diferença de espessura
        if thickness != closest:
            ratio = closest / thickness if thickness > 0 else 1
            speed = int(speed * ratio)
        
        # Pierce delay baseado na espessura
        pierce_delay = 0.3 + (thickness * 0.05)
        
        return cls(
            material=material,
            thickness=thickness,
            amperage=amp,
            cutting_speed=speed,
            kerf_width=kerf,
            pierce_delay=pierce_delay,
            cut_height=1.0 + (thickness * 0.05),
            pierce_height=2.0 + (thickness * 0.1),
        )


@dataclass
class GCodeConfig:
    """Configuração geral do gerador de G-code."""
    
    # Unidades e coordenadas
    units: str = "mm"  # "mm" ou "inch"
    absolute_coords: bool = True
    
    # Dialeto
    dialect: GCodeDialect = GCodeDialect.STANDARD
    
    # Formato de números
    decimal_places: int = 3
    
    # Cabeçalho/rodapé
    include_header: bool = True
    include_comments: bool = True
    program_number: Optional[str] = None
    
    # Códigos M personalizados
    plasma_on_code: str = "M03"
    plasma_off_code: str = "M05"
    thc_on_code: str = "M65"
    thc_off_code: str = "M67"
    
    # Arquivo
    file_extension: str = ".nc"


class GCodeGenerator:
    """Gerador de G-code para corte plasma."""
    
    def __init__(
        self,
        gcode_config: Optional[GCodeConfig] = None,
        plasma_config: Optional[PlasmaConfig] = None
    ):
        """
        Inicializa o gerador.
        
        Args:
            gcode_config: Configuração de G-code
            plasma_config: Configuração de plasma
        """
        self.gcode_config = gcode_config or GCodeConfig()
        self.plasma_config = plasma_config or PlasmaConfig()
    
    def generate(self, toolpath: Toolpath) -> str:
        """
        Gera G-code a partir de um toolpath.
        
        Args:
            toolpath: Toolpath completo
            
        Returns:
            str: G-code gerado
        """
        logger.info(f"Gerando G-code para {len(toolpath.paths)} caminhos de corte")
        
        lines: List[str] = []
        
        # Cabeçalho
        if self.gcode_config.include_header:
            lines.extend(self._generate_header(toolpath))
        
        # Inicialização
        lines.extend(self._generate_init())
        
        # Processar cada caminho de corte
        for i, path in enumerate(toolpath.paths):
            if self.gcode_config.include_comments:
                contour_type = "INTERNO" if path.contour_type == ContourType.INTERNAL else "EXTERNO"
                lines.append(f"")
                lines.append(f"(=== CORTE {i+1}/{len(toolpath.paths)} - {contour_type} ===)")
            
            lines.extend(self._generate_path(path))
        
        # Finalização
        lines.extend(self._generate_end())
        
        gcode = "\n".join(lines)
        logger.info(f"G-code gerado: {len(lines)} linhas")
        
        return gcode
    
    def _generate_header(self, toolpath: Toolpath) -> List[str]:
        """Gera cabeçalho do programa."""
        lines = []
        
        # Número do programa
        if self.gcode_config.program_number:
            lines.append(f"O{self.gcode_config.program_number}")
        
        # Comentários de informação
        lines.append(f"(===================================================)")
        lines.append(f"(  ENGENHARIA CAD - CORTE PLASMA CNC)")
        lines.append(f"(===================================================)")
        lines.append(f"(  Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        lines.append(f"(  Material: {self.plasma_config.material.value})")
        lines.append(f"(  Espessura: {self.plasma_config.thickness}mm)")
        lines.append(f"(  Amperagem: {self.plasma_config.amperage}A)")
        lines.append(f"(  Velocidade: {self.plasma_config.cutting_speed}mm/min)")
        lines.append(f"(  Kerf: {self.plasma_config.kerf_width}mm)")
        lines.append(f"(===================================================)")
        lines.append(f"(  Cortes: {len(toolpath.paths)})")
        lines.append(f"(  Comprimento de corte: {toolpath.total_cutting_length:.1f}mm)")
        lines.append(f"(  Deslocamento rapido: {toolpath.total_rapid_length:.1f}mm)")
        lines.append(f"(  Tempo estimado: {toolpath.total_time/60:.1f} min)")
        lines.append(f"(===================================================)")
        lines.append("")
        
        return lines
    
    def _generate_init(self) -> List[str]:
        """Gera código de inicialização."""
        lines = []
        
        # Unidades
        if self.gcode_config.units == "mm":
            lines.append("G21 (Unidades: milimetros)")
        else:
            lines.append("G20 (Unidades: polegadas)")
        
        # Sistema de coordenadas
        if self.gcode_config.absolute_coords:
            lines.append("G90 (Coordenadas absolutas)")
        else:
            lines.append("G91 (Coordenadas incrementais)")
        
        # Plano de trabalho
        lines.append("G17 (Plano XY)")
        
        # Zero da peça
        lines.append("G54 (Sistema de coordenadas da peça)")
        
        # Desligar plasma e THC
        lines.append(f"{self.gcode_config.plasma_off_code} (Plasma desligado)")
        if self.plasma_config.thc_enabled:
            lines.append(f"{self.gcode_config.thc_off_code} (THC desligado)")
        
        # Mover para altura segura
        lines.append(f"G00 Z{self._fmt(self.plasma_config.safe_height)} (Altura segura)")
        
        return lines
    
    def _generate_path(self, path: CuttingPath) -> List[str]:
        """Gera G-code para um caminho de corte."""
        lines = []
        
        if not path.moves and not path.lead_in:
            return lines
        
        # Processar lead-in (inclui movimento rápido para posição)
        for move in path.lead_in:
            lines.extend(self._move_to_gcode(move, is_lead=True))
        
        # Se não tem lead-in, fazer movimento rápido direto
        if not path.lead_in and path.moves:
            first_move = path.moves[0]
            if first_move.start_point:
                # Mover para altura segura
                lines.append(f"G00 Z{self._fmt(self.plasma_config.safe_height)}")
                # Mover para posição XY
                lines.append(
                    f"G00 X{self._fmt(first_move.start_point.x)} "
                    f"Y{self._fmt(first_move.start_point.y)}"
                )
        
        # Sequência de pierce (perfuração)
        lines.extend(self._generate_pierce_sequence())
        
        # Processar movimentos de corte
        for move in path.moves:
            lines.extend(self._move_to_gcode(move))
        
        # Processar lead-out
        for move in path.lead_out:
            lines.extend(self._move_to_gcode(move, is_lead=True))
        
        # Desligar plasma
        lines.append(f"{self.gcode_config.plasma_off_code} (Plasma OFF)")
        
        # Desligar THC
        if self.plasma_config.thc_enabled:
            lines.append(f"{self.gcode_config.thc_off_code} (THC OFF)")
        
        # Subir para altura segura
        lines.append(f"G00 Z{self._fmt(self.plasma_config.safe_height)}")
        
        return lines
    
    def _generate_pierce_sequence(self) -> List[str]:
        """Gera sequência de perfuração (pierce)."""
        lines = []
        
        # Descer para altura de pierce
        lines.append(f"G00 Z{self._fmt(self.plasma_config.pierce_height)} (Altura de pierce)")
        
        # Ligar plasma
        lines.append(f"{self.gcode_config.plasma_on_code} (Plasma ON)")
        
        # Delay de pierce
        delay_ms = int(self.plasma_config.pierce_delay * 1000)
        lines.append(f"G04 P{delay_ms} (Pierce delay: {self.plasma_config.pierce_delay}s)")
        
        # Ligar THC
        if self.plasma_config.thc_enabled:
            lines.append(f"{self.gcode_config.thc_on_code} (THC ON)")
        
        # Descer para altura de corte
        lines.append(f"G01 Z{self._fmt(self.plasma_config.cut_height)} F500 (Altura de corte)")
        
        return lines
    
    def _move_to_gcode(self, move: ToolpathMove, is_lead: bool = False) -> List[str]:
        """Converte um movimento em G-code."""
        lines = []
        
        feed_rate = move.feed_rate or self.plasma_config.cutting_speed
        
        if move.move_type == MoveType.RAPID:
            # G00 - Movimento rápido
            cmd = f"G00 X{self._fmt(move.end_point.x)} Y{self._fmt(move.end_point.y)}"
            if self.gcode_config.include_comments:
                cmd += " (Movimento rapido)"
            lines.append(cmd)
        
        elif move.move_type == MoveType.LINEAR:
            # G01 - Movimento linear de corte
            cmd = f"G01 X{self._fmt(move.end_point.x)} Y{self._fmt(move.end_point.y)} F{int(feed_rate)}"
            if is_lead and self.gcode_config.include_comments:
                cmd += " (Lead)"
            lines.append(cmd)
        
        elif move.move_type == MoveType.ARC_CW:
            # G02 - Arco horário
            if move.center and move.start_point:
                i = move.center.x - move.start_point.x
                j = move.center.y - move.start_point.y
                cmd = (
                    f"G02 X{self._fmt(move.end_point.x)} Y{self._fmt(move.end_point.y)} "
                    f"I{self._fmt(i)} J{self._fmt(j)} F{int(feed_rate)}"
                )
                if is_lead and self.gcode_config.include_comments:
                    cmd += " (Lead-in arco)"
                lines.append(cmd)
        
        elif move.move_type == MoveType.ARC_CCW:
            # G03 - Arco anti-horário
            if move.center and move.start_point:
                i = move.center.x - move.start_point.x
                j = move.center.y - move.start_point.y
                cmd = (
                    f"G03 X{self._fmt(move.end_point.x)} Y{self._fmt(move.end_point.y)} "
                    f"I{self._fmt(i)} J{self._fmt(j)} F{int(feed_rate)}"
                )
                if is_lead and self.gcode_config.include_comments:
                    cmd += " (Lead arco)"
                lines.append(cmd)
        
        return lines
    
    def _generate_end(self) -> List[str]:
        """Gera código de finalização."""
        lines = []
        
        lines.append("")
        lines.append("(=== FIM DO PROGRAMA ===)")
        
        # Garantir que plasma está desligado
        lines.append(f"{self.gcode_config.plasma_off_code} (Plasma OFF)")
        
        # Desligar THC
        if self.plasma_config.thc_enabled:
            lines.append(f"{self.gcode_config.thc_off_code} (THC OFF)")
        
        # Ir para home ou posição segura
        lines.append(f"G00 Z{self._fmt(self.plasma_config.safe_height)} (Altura segura)")
        lines.append("G00 X0 Y0 (Retorno ao zero)")
        
        # Fim do programa
        if self.gcode_config.dialect == GCodeDialect.FANUC:
            lines.append("M30 (Fim do programa)")
        else:
            lines.append("M02 (Fim do programa)")
        
        lines.append("%")
        
        return lines
    
    def _fmt(self, value: float) -> str:
        """Formata número para G-code."""
        fmt = f"{{:.{self.gcode_config.decimal_places}f}}"
        return fmt.format(value)
    
    def generate_to_file(
        self, 
        toolpath: Toolpath, 
        output_path: str,
        extension: Optional[str] = None
    ) -> str:
        """
        Gera G-code e salva em arquivo.
        
        Args:
            toolpath: Toolpath completo
            output_path: Caminho do arquivo de saída
            extension: Extensão do arquivo (padrão: .nc)
            
        Returns:
            str: Caminho do arquivo gerado
        """
        import os
        
        gcode = self.generate(toolpath)
        
        # Ajustar extensão
        ext = extension or self.gcode_config.file_extension
        if not output_path.endswith(ext):
            base, _ = os.path.splitext(output_path)
            output_path = base + ext
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(gcode)
        
        logger.info(f"G-code salvo em: {output_path}")
        return output_path
