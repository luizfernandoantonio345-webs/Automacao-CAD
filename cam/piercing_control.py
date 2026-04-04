"""
═══════════════════════════════════════════════════════════════════════════════
PIERCING AVANÇADO - Sistema de Controle de Perfuração Industrial
═══════════════════════════════════════════════════════════════════════════════

Sistema profissional de controle de piercing para corte plasma, incluindo:
- Pierce delay configurável por material/espessura
- Multi-pierce strategy (perfuração em múltiplas etapas)
- Ramp piercing (entrada inclinada para materiais espessos)
- Edge start (início na borda da chapa)
- Flying pierce (pierce em movimento)
- Pre-pierce (sequência de pré-aquecimento)

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engcad.cam.piercing")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class PierceType(Enum):
    """Tipos de perfuração suportados."""
    STANDARD = "standard"           # Pierce padrão (estacionário)
    RAMP = "ramp"                   # Pierce com rampa inclinada
    MULTI_STEP = "multi_step"       # Pierce em múltiplas etapas
    EDGE_START = "edge_start"       # Início na borda da chapa
    FLYING = "flying"               # Pierce em movimento
    PRE_PIERCE = "pre_pierce"       # Com pré-aquecimento
    STATIONARY_AND_MOVE = "stat_move"  # Estacionário depois move


class MaterialCategory(Enum):
    """Categorias de material para cálculo de pierce."""
    THIN = "thin"               # Fina (até 3mm)
    MEDIUM = "medium"           # Média (3-10mm)
    THICK = "thick"             # Grossa (10-20mm)
    VERY_THICK = "very_thick"   # Muito grossa (>20mm)


class PierceQuality(Enum):
    """Qualidade/modo de pierce."""
    PRODUCTION = "production"   # Modo produção (mais rápido)
    QUALITY = "quality"         # Modo qualidade (mais lento, melhor acabamento)
    CONSUMABLE_SAVE = "save"    # Modo economia de consumíveis


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PierceParameters:
    """Parâmetros completos de perfuração."""
    
    # Tipo de pierce
    pierce_type: PierceType = PierceType.STANDARD
    quality_mode: PierceQuality = PierceQuality.PRODUCTION
    
    # Alturas (mm)
    pierce_height: float = 3.0          # Altura de perfuração
    cut_height: float = 1.5             # Altura de corte
    safe_height: float = 15.0           # Altura segura
    
    # Tempos (segundos)
    pierce_delay: float = 0.5           # Tempo de perfuração
    pre_flow_time: float = 0.0          # Tempo de pré-fluxo de gás
    post_flow_time: float = 0.0         # Tempo de pós-fluxo
    
    # Correntes/potências
    pierce_amperage: int = 0            # Amperagem de pierce (0 = igual ao corte)
    cut_amperage: int = 45              # Amperagem de corte
    
    # Velocidades (mm/min)
    plunge_rate: float = 500.0          # Velocidade de descida Z
    
    # Para Ramp Pierce
    ramp_angle: float = 15.0            # Ângulo da rampa (graus)
    ramp_length: float = 10.0           # Comprimento da rampa
    ramp_speed: float = 500.0           # Velocidade na rampa
    
    # Para Multi-Step Pierce
    steps: int = 1                      # Número de etapas
    step_delay: float = 0.2             # Delay entre etapas
    step_height_increment: float = 0.5  # Incremento de altura por etapa
    
    # Para Flying Pierce
    flying_speed: float = 1000.0        # Velocidade durante pierce voador
    
    # THC (Torch Height Control)
    thc_delay: float = 0.2              # Delay antes de ligar THC
    thc_sample_voltage: float = 0.0     # Tensão de referência (0 = automático)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pierce_type": self.pierce_type.value,
            "quality_mode": self.quality_mode.value,
            "pierce_height": self.pierce_height,
            "cut_height": self.cut_height,
            "pierce_delay": self.pierce_delay,
            "pierce_amperage": self.pierce_amperage,
            "cut_amperage": self.cut_amperage,
            "ramp_angle": self.ramp_angle,
            "ramp_length": self.ramp_length,
            "steps": self.steps,
        }


@dataclass
class PierceResult:
    """Resultado da geração de sequência de pierce."""
    gcode_lines: List[str] = field(default_factory=list)
    total_time: float = 0.0             # Tempo total estimado (segundos)
    z_final: float = 0.0                # Altura Z final
    x_offset: float = 0.0               # Offset X após rampa
    y_offset: float = 0.0               # Offset Y após rampa
    warnings: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# TABELA DE PARÂMETROS POR MATERIAL
# ═══════════════════════════════════════════════════════════════════════════════

class PierceTable:
    """
    Tabela de parâmetros de pierce por material e espessura.
    
    Baseado em valores típicos de Hypertherm PowerMax e similares.
    """
    
    # Formato: {material: {espessura: (pierce_height, pierce_delay, amperage)}}
    PIERCE_TABLE = {
        "mild_steel": {
            1.5: (2.0, 0.0, 25),     # Chapas finas - pierce instantâneo
            3.0: (2.5, 0.2, 30),
            4.5: (3.0, 0.3, 35),
            6.0: (3.5, 0.4, 45),
            8.0: (4.0, 0.5, 55),
            10.0: (5.0, 0.7, 65),
            12.0: (5.5, 1.0, 80),
            16.0: (6.0, 1.5, 100),
            20.0: (7.0, 2.0, 130),
            25.0: (8.0, 3.0, 170),
            32.0: (10.0, 4.0, 200),
        },
        "stainless": {
            1.5: (2.0, 0.1, 30),
            3.0: (3.0, 0.3, 40),
            4.5: (3.5, 0.5, 50),
            6.0: (4.0, 0.7, 60),
            8.0: (5.0, 1.0, 80),
            10.0: (6.0, 1.5, 100),
            12.0: (7.0, 2.0, 120),
        },
        "aluminum": {
            1.5: (2.5, 0.1, 30),
            3.0: (3.0, 0.2, 45),
            4.5: (3.5, 0.3, 55),
            6.0: (4.0, 0.5, 70),
            8.0: (5.0, 0.7, 90),
            10.0: (6.0, 1.0, 110),
        },
        "copper": {
            1.5: (2.5, 0.2, 35),
            3.0: (3.5, 0.4, 50),
            4.5: (4.0, 0.6, 65),
            6.0: (5.0, 0.8, 80),
        },
        "brass": {
            1.5: (2.5, 0.2, 35),
            3.0: (3.5, 0.4, 50),
            6.0: (5.0, 0.7, 75),
        },
    }
    
    # Recomendação de tipo de pierce por categoria de espessura
    PIERCE_TYPE_RECOMMENDATIONS = {
        MaterialCategory.THIN: PierceType.STANDARD,
        MaterialCategory.MEDIUM: PierceType.STANDARD,
        MaterialCategory.THICK: PierceType.RAMP,
        MaterialCategory.VERY_THICK: PierceType.MULTI_STEP,
    }
    
    @classmethod
    def get_material_category(cls, thickness: float) -> MaterialCategory:
        """Determina categoria do material pela espessura."""
        if thickness <= 3.0:
            return MaterialCategory.THIN
        elif thickness <= 10.0:
            return MaterialCategory.MEDIUM
        elif thickness <= 20.0:
            return MaterialCategory.THICK
        else:
            return MaterialCategory.VERY_THICK
    
    @classmethod
    def get_pierce_params(
        cls,
        material: str,
        thickness: float,
        amperage: int = None
    ) -> PierceParameters:
        """
        Obtém parâmetros de pierce recomendados.
        
        Args:
            material: Tipo de material
            thickness: Espessura em mm
            amperage: Amperagem (opcional, será calculada)
        
        Returns:
            PierceParameters com valores recomendados
        """
        material = material.lower().replace(' ', '_')
        table = cls.PIERCE_TABLE.get(material, cls.PIERCE_TABLE["mild_steel"])
        
        # Encontrar espessura mais próxima
        thicknesses = sorted(table.keys())
        closest = min(thicknesses, key=lambda t: abs(t - thickness))
        
        pierce_height, pierce_delay, default_amp = table[closest]
        
        # Ajustar valores proporcionalmente
        ratio = thickness / closest if closest > 0 else 1.0
        
        # Categoria e tipo recomendado
        category = cls.get_material_category(thickness)
        recommended_type = cls.PIERCE_TYPE_RECOMMENDATIONS[category]
        
        params = PierceParameters(
            pierce_type=recommended_type,
            pierce_height=pierce_height * (0.9 + ratio * 0.1),
            cut_height=1.0 + thickness * 0.05,
            pierce_delay=pierce_delay * ratio,
            pierce_amperage=amperage or default_amp,
            cut_amperage=amperage or default_amp,
        )
        
        # Parâmetros específicos para chapas grossas
        if category == MaterialCategory.THICK:
            params.ramp_length = thickness * 0.8
            params.ramp_angle = 12.0
            params.ramp_speed = 400.0
        
        elif category == MaterialCategory.VERY_THICK:
            params.steps = min(3, int(thickness / 10))
            params.step_delay = 0.5
            params.step_height_increment = 0.5
            params.quality_mode = PierceQuality.QUALITY
        
        return params
    
    @classmethod
    def get_recommended_pierce_type(
        cls,
        material: str,
        thickness: float
    ) -> Tuple[PierceType, str]:
        """
        Retorna o tipo de pierce recomendado com justificativa.
        
        Returns:
            Tuple[PierceType, str]: tipo e justificativa
        """
        category = cls.get_material_category(thickness)
        pierce_type = cls.PIERCE_TYPE_RECOMMENDATIONS[category]
        
        justifications = {
            MaterialCategory.THIN: (
                "Chapas finas (≤3mm) permitem pierce padrão rápido "
                "sem risco de voltar material"
            ),
            MaterialCategory.MEDIUM: (
                "Espessura média (3-10mm): pierce padrão é adequado "
                "com delay apropriado"
            ),
            MaterialCategory.THICK: (
                "Chapas grossas (10-20mm): ramp pierce recomendado "
                "para evitar respingos e danos aos consumíveis"
            ),
            MaterialCategory.VERY_THICK: (
                "Material muito espesso (>20mm): multi-step pierce "
                "necessário para perfuração gradual e segura"
            ),
        }
        
        return pierce_type, justifications[category]


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR DE SEQUÊNCIA DE PIERCE
# ═══════════════════════════════════════════════════════════════════════════════

class PierceGenerator:
    """
    Gerador de sequências de perfuração.
    
    Gera G-code otimizado para diferentes tipos de pierce,
    considerando material, espessura e capacidades da máquina.
    """
    
    def __init__(
        self,
        m_codes: Dict[str, str] = None,
        decimal_places: int = 3
    ):
        """
        Inicializa o gerador.
        
        Args:
            m_codes: Mapeamento de M-codes da máquina
            decimal_places: Casas decimais para coordenadas
        """
        self.m_codes = m_codes or {
            "plasma_on": "M03",
            "plasma_off": "M05",
            "thc_on": "M52 P1",
            "thc_off": "M52 P0",
        }
        self.decimal_places = decimal_places
    
    def _fmt(self, value: float) -> str:
        """Formata número."""
        return f"{value:.{self.decimal_places}f}"
    
    def generate(
        self,
        x: float,
        y: float,
        params: PierceParameters,
        approach_angle: float = 0.0  # Ângulo de aproximação (graus)
    ) -> PierceResult:
        """
        Gera sequência completa de pierce.
        
        Args:
            x, y: Posição de pierce
            params: Parâmetros de pierce
            approach_angle: Ângulo de aproximação para ramp pierce
        
        Returns:
            PierceResult com G-code e estatísticas
        """
        if params.pierce_type == PierceType.STANDARD:
            return self._generate_standard(x, y, params)
        
        elif params.pierce_type == PierceType.RAMP:
            return self._generate_ramp(x, y, params, approach_angle)
        
        elif params.pierce_type == PierceType.MULTI_STEP:
            return self._generate_multi_step(x, y, params)
        
        elif params.pierce_type == PierceType.EDGE_START:
            return self._generate_edge_start(x, y, params)
        
        elif params.pierce_type == PierceType.FLYING:
            return self._generate_flying(x, y, params, approach_angle)
        
        elif params.pierce_type == PierceType.PRE_PIERCE:
            return self._generate_pre_pierce(x, y, params)
        
        else:
            return self._generate_standard(x, y, params)
    
    def _generate_standard(
        self,
        x: float,
        y: float,
        params: PierceParameters
    ) -> PierceResult:
        """Gera pierce padrão estacionário."""
        result = PierceResult()
        lines = result.gcode_lines
        
        # Comentário
        lines.append(f"(PIERCE PADRÃO em X{self._fmt(x)} Y{self._fmt(y)})")
        
        # Movimento rápido para posição XY
        lines.append(f"G00 X{self._fmt(x)} Y{self._fmt(y)}")
        
        # Descer para altura de pierce
        lines.append(f"G00 Z{self._fmt(params.pierce_height)}")
        
        # Pré-fluxo de gás (se configurado)
        if params.pre_flow_time > 0:
            delay_ms = int(params.pre_flow_time * 1000)
            lines.append(f"G04 P{delay_ms} (Pre-flow)")
            result.total_time += params.pre_flow_time
        
        # Ligar plasma
        plasma_cmd = self.m_codes.get("plasma_on", "M03")
        lines.append(f"{plasma_cmd} (Plasma ON)")
        
        # Pierce delay
        delay_ms = int(params.pierce_delay * 1000)
        lines.append(f"G04 P{delay_ms} (Pierce delay {params.pierce_delay}s)")
        result.total_time += params.pierce_delay
        
        # THC delay (se configurado)
        if params.thc_delay > 0:
            thc_delay_ms = int(params.thc_delay * 1000)
            lines.append(f"G04 P{thc_delay_ms} (THC stabilization)")
            result.total_time += params.thc_delay
        
        # Ligar THC
        thc_on = self.m_codes.get("thc_on", "")
        if thc_on:
            lines.append(f"{thc_on} (THC ON)")
        
        # Descer para altura de corte
        lines.append(
            f"G01 Z{self._fmt(params.cut_height)} "
            f"F{int(params.plunge_rate)}"
        )
        
        result.z_final = params.cut_height
        
        # Calcular tempo de descida
        z_travel = params.pierce_height - params.cut_height
        result.total_time += (z_travel / params.plunge_rate) * 60
        
        return result
    
    def _generate_ramp(
        self,
        x: float,
        y: float,
        params: PierceParameters,
        approach_angle: float
    ) -> PierceResult:
        """
        Gera pierce com rampa inclinada.
        
        A tocha desce enquanto se move, criando uma entrada
        inclinada que reduz respingos em materiais espessos.
        """
        result = PierceResult()
        lines = result.gcode_lines
        
        # Calcular ponto de início da rampa
        angle_rad = math.radians(approach_angle)
        ramp_rad = math.radians(params.ramp_angle)
        
        # Ponto inicial (recuado do ponto de pierce)
        start_x = x - params.ramp_length * math.cos(angle_rad)
        start_y = y - params.ramp_length * math.sin(angle_rad)
        start_z = params.cut_height + params.ramp_length * math.tan(ramp_rad)
        
        lines.append(f"(RAMP PIERCE - Ângulo: {params.ramp_angle}°)")
        
        # Mover para posição inicial da rampa em altura segura
        lines.append(f"G00 X{self._fmt(start_x)} Y{self._fmt(start_y)}")
        lines.append(f"G00 Z{self._fmt(params.pierce_height)}")
        
        # Ligar plasma
        plasma_cmd = self.m_codes.get("plasma_on", "M03")
        lines.append(f"{plasma_cmd} (Plasma ON)")
        
        # Delay inicial mais curto (rampa permite)
        delay_ms = int(params.pierce_delay * 0.5 * 1000)
        lines.append(f"G04 P{delay_ms} (Pierce delay reduzido)")
        result.total_time += params.pierce_delay * 0.5
        
        # Início da rampa - descer gradualmente enquanto move
        lines.append(f"(Início da rampa)")
        
        # Movimento de rampa (linear com Z)
        lines.append(
            f"G01 X{self._fmt(x)} Y{self._fmt(y)} "
            f"Z{self._fmt(params.cut_height)} "
            f"F{int(params.ramp_speed)}"
        )
        
        # Ligar THC após rampa
        thc_on = self.m_codes.get("thc_on", "")
        if thc_on:
            lines.append(f"{thc_on} (THC ON)")
        
        result.z_final = params.cut_height
        result.x_offset = x - start_x
        result.y_offset = y - start_y
        
        # Tempo da rampa
        ramp_distance = math.sqrt(
            params.ramp_length**2 + (start_z - params.cut_height)**2
        )
        result.total_time += (ramp_distance / params.ramp_speed) * 60
        
        return result
    
    def _generate_multi_step(
        self,
        x: float,
        y: float,
        params: PierceParameters
    ) -> PierceResult:
        """
        Gera pierce em múltiplas etapas.
        
        Para materiais muito espessos, perfura em etapas
        progressivas, permitindo que o material esfrie entre elas.
        """
        result = PierceResult()
        lines = result.gcode_lines
        
        lines.append(f"(MULTI-STEP PIERCE - {params.steps} etapas)")
        
        # Posicionar
        lines.append(f"G00 X{self._fmt(x)} Y{self._fmt(y)}")
        
        # Altura inicial
        current_height = params.pierce_height
        target_height = params.cut_height
        step_drop = (current_height - target_height) / params.steps
        
        for step in range(params.steps):
            step_num = step + 1
            
            # Ir para altura da etapa
            step_height = current_height - (step_drop * step)
            lines.append(f"G00 Z{self._fmt(step_height)} (Etapa {step_num})")
            
            if step == 0:
                # Primeira etapa - ligar plasma
                plasma_cmd = self.m_codes.get("plasma_on", "M03")
                lines.append(f"{plasma_cmd} (Plasma ON)")
            
            # Delay de pierce
            delay = params.pierce_delay if step == 0 else params.step_delay
            delay_ms = int(delay * 1000)
            lines.append(f"G04 P{delay_ms} (Delay etapa {step_num})")
            result.total_time += delay
            
            if step < params.steps - 1:
                # Etapas intermediárias - subir ligeiramente
                lift_height = step_height + params.step_height_increment
                lines.append(f"G00 Z{self._fmt(lift_height)} (Lift)")
        
        # Etapa final - ir para altura de corte
        lines.append(
            f"G01 Z{self._fmt(target_height)} "
            f"F{int(params.plunge_rate)} (Altura de corte)"
        )
        
        # Ligar THC
        thc_on = self.m_codes.get("thc_on", "")
        if thc_on:
            lines.append(f"{thc_on} (THC ON)")
        
        result.z_final = target_height
        
        return result
    
    def _generate_edge_start(
        self,
        x: float,
        y: float,
        params: PierceParameters
    ) -> PierceResult:
        """
        Gera edge start (início na borda).
        
        Para quando o ponto de início está na borda da chapa,
        não necessita pierce.
        """
        result = PierceResult()
        lines = result.gcode_lines
        
        lines.append(f"(EDGE START - Início na borda)")
        
        # Posicionar
        lines.append(f"G00 X{self._fmt(x)} Y{self._fmt(y)}")
        
        # Descer para altura de corte diretamente
        lines.append(f"G00 Z{self._fmt(params.cut_height)}")
        
        # Ligar plasma
        plasma_cmd = self.m_codes.get("plasma_on", "M03")
        lines.append(f"{plasma_cmd} (Plasma ON)")
        
        # Delay mínimo para estabilização do arco
        delay_ms = max(100, int(params.pierce_delay * 0.2 * 1000))
        lines.append(f"G04 P{delay_ms} (Arc stabilization)")
        result.total_time += delay_ms / 1000
        
        # Ligar THC
        thc_on = self.m_codes.get("thc_on", "")
        if thc_on:
            lines.append(f"{thc_on} (THC ON)")
        
        result.z_final = params.cut_height
        
        # Sem pierce, tempo significativamente menor
        result.warnings.append("Edge start: verificar se posição está realmente na borda")
        
        return result
    
    def _generate_flying(
        self,
        x: float,
        y: float,
        params: PierceParameters,
        approach_angle: float
    ) -> PierceResult:
        """
        Gera flying pierce (pierce em movimento).
        
        A tocha começa a se mover durante o pierce,
        útil para alta produtividade em materiais finos.
        """
        result = PierceResult()
        lines = result.gcode_lines
        
        if params.pierce_delay > 0.3:
            result.warnings.append(
                "Flying pierce recomendado apenas para materiais finos "
                f"(pierce_delay atual: {params.pierce_delay}s)"
            )
        
        lines.append(f"(FLYING PIERCE)")
        
        # Calcular ponto de início
        angle_rad = math.radians(approach_angle)
        fly_distance = params.flying_speed * params.pierce_delay / 60
        
        start_x = x - fly_distance * math.cos(angle_rad)
        start_y = y - fly_distance * math.sin(angle_rad)
        
        # Posicionar no início
        lines.append(f"G00 X{self._fmt(start_x)} Y{self._fmt(start_y)}")
        lines.append(f"G00 Z{self._fmt(params.pierce_height)}")
        
        # Ligar plasma
        plasma_cmd = self.m_codes.get("plasma_on", "M03")
        lines.append(f"{plasma_cmd} (Plasma ON)")
        
        # Começar movimento imediatamente
        lines.append(
            f"G01 X{self._fmt(x)} Y{self._fmt(y)} "
            f"Z{self._fmt(params.cut_height)} "
            f"F{int(params.flying_speed)} (Flying pierce)"
        )
        
        # THC ligado após pierce
        thc_on = self.m_codes.get("thc_on", "")
        if thc_on:
            lines.append(f"{thc_on} (THC ON)")
        
        result.z_final = params.cut_height
        result.total_time += params.pierce_delay
        
        return result
    
    def _generate_pre_pierce(
        self,
        x: float,
        y: float,
        params: PierceParameters
    ) -> PierceResult:
        """
        Gera pierce com pré-aquecimento.
        
        Usa corrente mais baixa inicialmente para
        pré-aquecer o material antes do pierce principal.
        """
        result = PierceResult()
        lines = result.gcode_lines
        
        lines.append(f"(PRE-PIERCE - Pré-aquecimento)")
        
        # Posicionar
        lines.append(f"G00 X{self._fmt(x)} Y{self._fmt(y)}")
        lines.append(f"G00 Z{self._fmt(params.pierce_height * 1.5)}")
        
        # Fase de pré-aquecimento (se suportado pela máquina)
        if params.pierce_amperage > 0:
            lines.append(f"(Pré-aquecimento com amperagem reduzida)")
            # Alguns controladores permitem ajuste de amperagem via G-code
            preheat_amp = int(params.pierce_amperage * 0.5)
            lines.append(f"S{preheat_amp} (Amperagem de pré-aquecimento)")
        
        # Ligar plasma
        plasma_cmd = self.m_codes.get("plasma_on", "M03")
        lines.append(f"{plasma_cmd} (Plasma ON - pré-aquecimento)")
        
        # Delay de pré-aquecimento
        preheat_delay_ms = int(params.pierce_delay * 0.3 * 1000)
        lines.append(f"G04 P{preheat_delay_ms} (Pré-aquecimento)")
        result.total_time += preheat_delay_ms / 1000
        
        # Aumentar para amperagem de pierce
        if params.pierce_amperage > 0:
            lines.append(f"S{params.pierce_amperage} (Amperagem de pierce)")
        
        # Descer para altura de pierce
        lines.append(f"G01 Z{self._fmt(params.pierce_height)} F{int(params.plunge_rate)}")
        
        # Pierce delay principal
        delay_ms = int(params.pierce_delay * 1000)
        lines.append(f"G04 P{delay_ms} (Pierce delay)")
        result.total_time += params.pierce_delay
        
        # THC e altura de corte
        thc_on = self.m_codes.get("thc_on", "")
        if thc_on:
            lines.append(f"{thc_on} (THC ON)")
        
        lines.append(
            f"G01 Z{self._fmt(params.cut_height)} "
            f"F{int(params.plunge_rate)} (Altura de corte)"
        )
        
        result.z_final = params.cut_height
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# ANALISADOR DE PIERCE
# ═══════════════════════════════════════════════════════════════════════════════

class PierceAnalyzer:
    """
    Analisa e otimiza sequências de pierce.
    
    Fornece:
    - Análise de eficiência
    - Sugestões de otimização
    - Estimativas de tempo e consumo
    """
    
    @staticmethod
    def analyze_pierce_sequence(
        params: PierceParameters,
        material: str,
        thickness: float
    ) -> Dict[str, Any]:
        """
        Analisa uma sequência de pierce.
        
        Returns:
            Dict com análise e sugestões
        """
        analysis = {
            "params": params.to_dict(),
            "warnings": [],
            "suggestions": [],
            "efficiency": 0.0,
            "consumable_impact": "normal",
        }
        
        # Verificar tipo de pierce vs espessura
        category = PierceTable.get_material_category(thickness)
        recommended, reason = PierceTable.get_recommended_pierce_type(
            material, thickness
        )
        
        if params.pierce_type != recommended:
            analysis["suggestions"].append({
                "type": "pierce_type",
                "current": params.pierce_type.value,
                "recommended": recommended.value,
                "reason": reason,
            })
        
        # Verificar pierce delay
        default_params = PierceTable.get_pierce_params(material, thickness)
        
        if params.pierce_delay < default_params.pierce_delay * 0.7:
            analysis["warnings"].append(
                f"Pierce delay muito curto ({params.pierce_delay}s). "
                f"Recomendado: {default_params.pierce_delay}s para {thickness}mm"
            )
        elif params.pierce_delay > default_params.pierce_delay * 1.5:
            analysis["warnings"].append(
                f"Pierce delay muito longo ({params.pierce_delay}s). "
                "Pode causar desgaste excessivo de consumíveis."
            )
            analysis["consumable_impact"] = "high"
        
        # Verificar altura de pierce
        if params.pierce_height < default_params.pierce_height * 0.8:
            analysis["warnings"].append(
                f"Altura de pierce muito baixa ({params.pierce_height}mm). "
                "Risco de respingos danificarem a tocha."
            )
        
        # Calcular eficiência
        efficiency = 100.0
        
        # Penalidade por pierce delay excessivo
        delay_ratio = params.pierce_delay / max(default_params.pierce_delay, 0.1)
        if delay_ratio > 1.0:
            efficiency -= (delay_ratio - 1.0) * 20
        
        # Penalidade por tipo de pierce inadequado
        if params.pierce_type != recommended:
            efficiency -= 10
        
        analysis["efficiency"] = max(0, min(100, efficiency))
        
        return analysis
    
    @staticmethod
    def estimate_consumable_life(
        params: PierceParameters,
        num_pierces: int,
        thickness: float
    ) -> Dict[str, Any]:
        """
        Estima impacto nos consumíveis.
        
        Returns:
            Dict com estimativas de vida útil
        """
        # Vida base de consumíveis (número de pierces)
        BASE_ELECTRODE_LIFE = 1000  # pierces
        BASE_NOZZLE_LIFE = 500      # pierces
        BASE_SHIELD_LIFE = 800      # pierces
        
        # Fatores de degradação
        delay_factor = 1 + (params.pierce_delay - 0.5) * 0.3
        thickness_factor = 1 + (thickness - 6) * 0.05
        
        # Para cada tipo de pierce
        type_factors = {
            PierceType.STANDARD: 1.0,
            PierceType.RAMP: 0.8,       # Menor desgaste
            PierceType.MULTI_STEP: 1.2,  # Mais desgaste
            PierceType.EDGE_START: 0.3,  # Muito menos desgaste
            PierceType.FLYING: 0.9,
            PierceType.PRE_PIERCE: 1.1,
        }
        
        type_factor = type_factors.get(params.pierce_type, 1.0)
        
        total_factor = delay_factor * thickness_factor * type_factor
        
        return {
            "electrode_life_pierces": int(BASE_ELECTRODE_LIFE / total_factor),
            "nozzle_life_pierces": int(BASE_NOZZLE_LIFE / total_factor),
            "shield_life_pierces": int(BASE_SHIELD_LIFE / total_factor),
            "estimated_electrode_usage": num_pierces / (BASE_ELECTRODE_LIFE / total_factor),
            "estimated_nozzle_usage": num_pierces / (BASE_NOZZLE_LIFE / total_factor),
            "impact_factor": total_factor,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def get_recommended_pierce(
    material: str,
    thickness: float,
    amperage: int = None
) -> PierceParameters:
    """Função auxiliar para obter parâmetros de pierce recomendados."""
    return PierceTable.get_pierce_params(material, thickness, amperage)


def generate_pierce_sequence(
    x: float,
    y: float,
    material: str,
    thickness: float,
    pierce_type: PierceType = None,
    m_codes: Dict[str, str] = None
) -> PierceResult:
    """
    Função auxiliar para gerar sequência de pierce.
    
    Args:
        x, y: Posição de pierce
        material: Tipo de material
        thickness: Espessura em mm
        pierce_type: Tipo de pierce (opcional, será calculado)
        m_codes: Mapeamento de M-codes
    
    Returns:
        PierceResult com G-code gerado
    """
    params = PierceTable.get_pierce_params(material, thickness)
    
    if pierce_type:
        params.pierce_type = pierce_type
    
    generator = PierceGenerator(m_codes)
    return generator.generate(x, y, params)
