"""
═══════════════════════════════════════════════════════════════════════════════
SIMULAÇÃO FÍSICA REAL - Motor de Simulação Industrial para CNC Plasma
═══════════════════════════════════════════════════════════════════════════════

Sistema avançado de simulação física considerando:
- Aceleração e desaceleração reais da máquina
- Inércia do sistema de eixos
- Tempo real de execução preciso
- Previsão de desgaste de consumíveis
- Análise térmica e distorção
- Heatmap de acumulação de calor

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Generator

logger = logging.getLogger("engcad.cam.physics_simulation")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class SimulationMode(Enum):
    """Modos de simulação disponíveis."""
    FAST = "fast"               # Simulação rápida (sem física detalhada)
    STANDARD = "standard"       # Simulação padrão (física básica)
    ACCURATE = "accurate"       # Simulação precisa (física completa)
    REALTIME = "realtime"       # Simulação em tempo real


class MotionState(Enum):
    """Estados de movimento do eixo."""
    IDLE = "idle"
    ACCELERATING = "accelerating"
    CONSTANT_VELOCITY = "constant_velocity"
    DECELERATING = "decelerating"
    DWELLING = "dwelling"


class ThermalZone(Enum):
    """Zonas térmicas para análise de calor."""
    COLD = "cold"               # < 100°C
    WARM = "warm"               # 100-200°C
    HOT = "hot"                 # 200-400°C
    CRITICAL = "critical"       # > 400°C (risco de distorção)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - FÍSICA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Point3D:
    """Ponto 3D."""
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: "Point3D") -> float:
        return math.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )
    
    def distance_xy(self, other: "Point3D") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def copy(self) -> "Point3D":
        return Point3D(self.x, self.y, self.z)


@dataclass
class MachinePhysics:
    """Parâmetros físicos da máquina CNC."""
    
    # Massas dos eixos (kg)
    x_axis_mass: float = 50.0
    y_axis_mass: float = 80.0       # Gantry completo
    z_axis_mass: float = 15.0       # Tocha e suporte
    
    # Acelerações máximas (mm/s²)
    x_max_accel: float = 3000.0
    y_max_accel: float = 2000.0     # Mais pesado = mais lento
    z_max_accel: float = 5000.0
    
    # Velocidades máximas (mm/s)
    x_max_velocity: float = 500.0   # 30000 mm/min
    y_max_velocity: float = 500.0
    z_max_velocity: float = 100.0
    
    # Jerk (mm/s³) - mudança de aceleração
    max_jerk: float = 50000.0
    
    # Atrito e inércia
    friction_coefficient: float = 0.02
    
    # Backlash (folga mecânica) em mm
    x_backlash: float = 0.05
    y_backlash: float = 0.05
    z_backlash: float = 0.02
    
    # Precisão de posicionamento
    position_accuracy: float = 0.01  # mm
    repeatability: float = 0.005     # mm
    
    # Limites de trabalho (mm)
    x_min: float = 0.0
    x_max: float = 3000.0
    y_min: float = 0.0
    y_max: float = 1500.0
    z_min: float = -50.0
    z_max: float = 100.0
    
    def calculate_accel_time(self, axis: str, target_velocity: float) -> float:
        """Calcula tempo para acelerar até velocidade alvo."""
        accel = getattr(self, f"{axis}_max_accel")
        return abs(target_velocity) / accel
    
    def calculate_accel_distance(self, axis: str, target_velocity: float) -> float:
        """Calcula distância percorrida durante aceleração."""
        accel = getattr(self, f"{axis}_max_accel")
        t = self.calculate_accel_time(axis, target_velocity)
        return 0.5 * accel * t * t


@dataclass
class TorchState:
    """Estado da tocha plasma."""
    
    position: Point3D = field(default_factory=lambda: Point3D(0, 0, 50))
    velocity: Point3D = field(default_factory=lambda: Point3D(0, 0, 0))
    
    # Estado do plasma
    arc_on: bool = False
    arc_voltage: float = 0.0
    amperage: float = 0.0
    
    # THC
    thc_enabled: bool = False
    thc_target_voltage: float = 120.0
    
    # Temperaturas estimadas
    torch_temperature: float = 25.0     # °C
    material_temperature: float = 25.0  # °C na posição atual
    
    # Consumíveis
    electrode_wear: float = 0.0         # 0-100%
    nozzle_wear: float = 0.0            # 0-100%
    shield_wear: float = 0.0            # 0-100%


@dataclass
class MotionSegment:
    """Segmento de movimento com perfil de velocidade."""
    
    start: Point3D
    end: Point3D
    
    # Velocidade planejada
    entry_velocity: float = 0.0         # mm/s
    cruise_velocity: float = 0.0        # mm/s
    exit_velocity: float = 0.0          # mm/s
    
    # Tempos calculados (segundos)
    accel_time: float = 0.0
    cruise_time: float = 0.0
    decel_time: float = 0.0
    total_time: float = 0.0
    
    # Distâncias (mm)
    accel_distance: float = 0.0
    cruise_distance: float = 0.0
    decel_distance: float = 0.0
    total_distance: float = 0.0
    
    # Tipo de movimento
    is_rapid: bool = False
    is_cutting: bool = False
    
    # Metadados
    feed_rate: float = 0.0              # mm/min (original do G-code)
    gcode_line: int = 0


@dataclass
class HeatPoint:
    """Ponto de acumulação de calor."""
    x: float
    y: float
    temperature: float              # °C estimados
    time_at_location: float         # segundos que a tocha ficou na área
    
    def decay(self, elapsed_seconds: float, ambient: float = 25.0) -> None:
        """Aplica decaimento térmico."""
        # Modelo simplificado de resfriamento de Newton
        decay_rate = 0.05  # Taxa de resfriamento
        self.temperature = ambient + (self.temperature - ambient) * math.exp(-decay_rate * elapsed_seconds)


@dataclass
class CuttingEvent:
    """Evento durante simulação de corte."""
    time: float                     # Tempo desde início (segundos)
    position: Point3D
    event_type: str                 # "pierce", "cut_start", "cut_end", "rapid", etc.
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsumableState:
    """Estado dos consumíveis."""
    
    # Vida útil estimada em horas
    electrode_hours: float = 0.0
    nozzle_hours: float = 0.0
    shield_hours: float = 0.0
    
    # Número de pierces
    total_pierces: int = 0
    
    # Tempo de arco
    arc_on_time: float = 0.0        # segundos
    
    # Estimativas de vida restante (%)
    electrode_life: float = 100.0
    nozzle_life: float = 100.0
    shield_life: float = 100.0
    
    # Consumíveis típicos por tipo
    CONSUMABLE_LIFE = {
        # (pierces_max, arc_hours_max)
        "electrode": (800, 4.0),
        "nozzle": (600, 3.0),
        "shield": (400, 2.0),
    }
    
    def add_pierce(self, amperage: float = 45):
        """Registra um pierce."""
        self.total_pierces += 1
        
        # Desgaste aumenta com amperagem
        wear_factor = amperage / 45.0
        
        self.electrode_life -= (100 / self.CONSUMABLE_LIFE["electrode"][0]) * wear_factor
        self.nozzle_life -= (100 / self.CONSUMABLE_LIFE["nozzle"][0]) * wear_factor * 1.2
        self.shield_life -= (100 / self.CONSUMABLE_LIFE["shield"][0]) * wear_factor * 0.5
        
        self._clamp_lives()
    
    def add_arc_time(self, seconds: float, amperage: float = 45):
        """Registra tempo de arco."""
        self.arc_on_time += seconds
        hours = seconds / 3600.0
        
        wear_factor = amperage / 45.0
        
        self.electrode_hours += hours
        self.nozzle_hours += hours
        self.shield_hours += hours
        
        # Reduzir vida com base em horas
        self.electrode_life -= (hours / self.CONSUMABLE_LIFE["electrode"][1]) * 100 * wear_factor
        self.nozzle_life -= (hours / self.CONSUMABLE_LIFE["nozzle"][1]) * 100 * wear_factor
        self.shield_life -= (hours / self.CONSUMABLE_LIFE["shield"][1]) * 100 * wear_factor * 0.8
        
        self._clamp_lives()
    
    def _clamp_lives(self):
        self.electrode_life = max(0, min(100, self.electrode_life))
        self.nozzle_life = max(0, min(100, self.nozzle_life))
        self.shield_life = max(0, min(100, self.shield_life))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_pierces": self.total_pierces,
            "arc_on_time_seconds": round(self.arc_on_time, 1),
            "arc_on_time_minutes": round(self.arc_on_time / 60, 2),
            "electrode_life_percent": round(self.electrode_life, 1),
            "nozzle_life_percent": round(self.nozzle_life, 1),
            "shield_life_percent": round(self.shield_life, 1),
            "needs_replacement": {
                "electrode": self.electrode_life < 10,
                "nozzle": self.nozzle_life < 10,
                "shield": self.shield_life < 10,
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class PhysicsSimulator:
    """
    Simulador físico de máquina CNC plasma.
    
    Considera física real da máquina para previsões precisas de tempo,
    desgaste de consumíveis e análise térmica.
    """
    
    def __init__(
        self,
        physics: Optional[MachinePhysics] = None,
        mode: SimulationMode = SimulationMode.STANDARD
    ):
        self.physics = physics or MachinePhysics()
        self.mode = mode
        
        # Estado da simulação
        self.torch = TorchState()
        self.consumables = ConsumableState()
        
        # Histórico
        self.motion_segments: List[MotionSegment] = []
        self.events: List[CuttingEvent] = []
        self.heatmap: List[HeatPoint] = []
        
        # Tempos acumulados
        self.total_time: float = 0.0
        self.cutting_time: float = 0.0
        self.rapid_time: float = 0.0
        self.dwell_time: float = 0.0
        
        # Distâncias
        self.total_distance: float = 0.0
        self.cutting_distance: float = 0.0
        self.rapid_distance: float = 0.0
        
        # Configuração de plasma
        self.current_amperage: float = 45.0
        self.pierce_delay: float = 0.5
        
        # Grid de calor (resolução 10mm)
        self.heat_grid_resolution: float = 10.0
        self.heat_grid: Dict[Tuple[int, int], float] = {}
    
    def reset(self):
        """Reseta estado da simulação."""
        self.torch = TorchState()
        self.consumables = ConsumableState()
        self.motion_segments = []
        self.events = []
        self.heatmap = []
        self.heat_grid = {}
        self.total_time = 0.0
        self.cutting_time = 0.0
        self.rapid_time = 0.0
        self.dwell_time = 0.0
        self.total_distance = 0.0
        self.cutting_distance = 0.0
        self.rapid_distance = 0.0
    
    def parse_gcode(self, gcode: str) -> List[Dict[str, Any]]:
        """
        Parse G-code para comandos estruturados.
        
        Returns:
            Lista de comandos com parâmetros
        """
        commands = []
        current_pos = Point3D(0, 0, 50)
        current_feed = 2000.0  # mm/min
        absolute_mode = True
        metric = True
        
        lines = gcode.strip().split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('('):
                continue
            
            # Remover comentários
            if '(' in line:
                line = line[:line.index('(')]
            if ';' in line:
                line = line[:line.index(';')]
            
            line = line.strip().upper()
            if not line:
                continue
            
            cmd = self._parse_gcode_line(line, current_pos, current_feed, line_num)
            if cmd:
                commands.append(cmd)
                
                # Atualizar estado
                if 'x' in cmd or 'y' in cmd or 'z' in cmd:
                    if 'x' in cmd:
                        current_pos.x = cmd['x']
                    if 'y' in cmd:
                        current_pos.y = cmd['y']
                    if 'z' in cmd:
                        current_pos.z = cmd['z']
                
                if 'f' in cmd:
                    current_feed = cmd['f']
        
        return commands
    
    def _parse_gcode_line(
        self, 
        line: str, 
        current_pos: Point3D, 
        current_feed: float,
        line_num: int
    ) -> Optional[Dict[str, Any]]:
        """Parse uma linha de G-code."""
        cmd = {'line': line_num, 'raw': line}
        
        # Extrair código G/M
        import re
        
        g_match = re.search(r'G(\d+\.?\d*)', line)
        m_match = re.search(r'M(\d+)', line)
        
        if g_match:
            cmd['g'] = float(g_match.group(1))
        if m_match:
            cmd['m'] = int(m_match.group(1))
        
        # Extrair parâmetros
        for axis in ['X', 'Y', 'Z', 'I', 'J', 'K', 'R', 'F', 'S', 'P']:
            match = re.search(rf'{axis}(-?\d+\.?\d*)', line)
            if match:
                cmd[axis.lower()] = float(match.group(1))
        
        return cmd if len(cmd) > 2 else None
    
    def simulate(
        self, 
        gcode: str,
        amperage: float = 45.0,
        pierce_delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executa simulação completa do G-code.
        
        Args:
            gcode: Código G-code completo
            amperage: Amperagem de corte
            pierce_delay: Delay de pierce em segundos
            
        Returns:
            Resultado completo da simulação
        """
        self.reset()
        self.current_amperage = amperage
        self.pierce_delay = pierce_delay
        
        commands = self.parse_gcode(gcode)
        
        arc_on = False
        current_feed = 2000.0
        
        for cmd in commands:
            g_code = cmd.get('g')
            m_code = cmd.get('m')
            
            # Processar M-codes
            if m_code is not None:
                if m_code in [3, 7]:  # Plasma ON
                    if not arc_on:
                        arc_on = True
                        self._process_pierce()
                elif m_code in [5, 8]:  # Plasma OFF
                    arc_on = False
                    self.torch.arc_on = False
            
            # Processar G-codes de movimento
            if g_code is not None:
                if 'f' in cmd:
                    current_feed = cmd['f']
                
                if g_code == 0:  # Rapid
                    self._process_rapid(cmd)
                elif g_code == 1:  # Linear
                    self._process_linear(cmd, current_feed, arc_on)
                elif g_code in [2, 3]:  # Arc
                    self._process_arc(cmd, g_code == 2, current_feed, arc_on)
                elif g_code == 4:  # Dwell
                    self._process_dwell(cmd)
        
        return self._generate_results()
    
    def _process_pierce(self):
        """Processa sequência de pierce."""
        # Adicionar evento
        self.events.append(CuttingEvent(
            time=self.total_time,
            position=self.torch.position.copy(),
            event_type="pierce",
            details={"delay": self.pierce_delay, "amperage": self.current_amperage}
        ))
        
        # Tempo de pierce
        self.total_time += self.pierce_delay
        self.dwell_time += self.pierce_delay
        
        # Desgaste de consumíveis
        self.consumables.add_pierce(self.current_amperage)
        
        # Calor inicial
        self._add_heat(self.torch.position.x, self.torch.position.y, 400.0)
        
        self.torch.arc_on = True
        self.torch.amperage = self.current_amperage
    
    def _process_rapid(self, cmd: Dict[str, Any]):
        """Processa movimento rápido."""
        target = Point3D(
            cmd.get('x', self.torch.position.x),
            cmd.get('y', self.torch.position.y),
            cmd.get('z', self.torch.position.z)
        )
        
        segment = self._calculate_motion_segment(
            self.torch.position.copy(),
            target,
            is_rapid=True
        )
        
        self.motion_segments.append(segment)
        self.total_time += segment.total_time
        self.rapid_time += segment.total_time
        self.total_distance += segment.total_distance
        self.rapid_distance += segment.total_distance
        
        self.torch.position = target
        
        self.events.append(CuttingEvent(
            time=self.total_time,
            position=target.copy(),
            event_type="rapid",
            details={"distance": segment.total_distance, "time": segment.total_time}
        ))
    
    def _process_linear(self, cmd: Dict[str, Any], feed_rate: float, cutting: bool):
        """Processa movimento linear."""
        target = Point3D(
            cmd.get('x', self.torch.position.x),
            cmd.get('y', self.torch.position.y),
            cmd.get('z', self.torch.position.z)
        )
        
        feed = cmd.get('f', feed_rate)
        
        segment = self._calculate_motion_segment(
            self.torch.position.copy(),
            target,
            is_rapid=False,
            feed_rate=feed,
            is_cutting=cutting
        )
        
        self.motion_segments.append(segment)
        self.total_time += segment.total_time
        self.total_distance += segment.total_distance
        
        if cutting:
            self.cutting_time += segment.total_time
            self.cutting_distance += segment.total_distance
            self.consumables.add_arc_time(segment.total_time, self.current_amperage)
            self._add_heat_along_path(self.torch.position, target)
        else:
            self.rapid_time += segment.total_time
            self.rapid_distance += segment.total_distance
        
        self.torch.position = target
    
    def _process_arc(
        self, 
        cmd: Dict[str, Any], 
        clockwise: bool, 
        feed_rate: float, 
        cutting: bool
    ):
        """Processa movimento em arco."""
        start = self.torch.position.copy()
        end = Point3D(
            cmd.get('x', start.x),
            cmd.get('y', start.y),
            cmd.get('z', start.z)
        )
        
        # Calcular centro do arco
        i = cmd.get('i', 0.0)
        j = cmd.get('j', 0.0)
        center = Point3D(start.x + i, start.y + j, start.z)
        
        radius = math.sqrt(i*i + j*j)
        
        # Calcular ângulo do arco
        start_angle = math.atan2(start.y - center.y, start.x - center.x)
        end_angle = math.atan2(end.y - center.y, end.x - center.x)
        
        if clockwise:
            if end_angle >= start_angle:
                end_angle -= 2 * math.pi
        else:
            if end_angle <= start_angle:
                end_angle += 2 * math.pi
        
        arc_length = abs(end_angle - start_angle) * radius
        
        # Calcular tempo com física
        feed = cmd.get('f', feed_rate)
        feed_mm_s = feed / 60.0
        
        # Velocidade reduzida em arcos pequenos
        if radius < 5:
            feed_mm_s *= 0.4
        elif radius < 15:
            feed_mm_s *= 0.7
        elif radius < 30:
            feed_mm_s *= 0.85
        
        # Considerar aceleração
        segment_time = self._calculate_arc_time(arc_length, feed_mm_s)
        
        self.total_time += segment_time
        self.total_distance += arc_length
        
        if cutting:
            self.cutting_time += segment_time
            self.cutting_distance += arc_length
            self.consumables.add_arc_time(segment_time, self.current_amperage)
            self._add_heat_along_arc(center, radius, start_angle, end_angle)
        else:
            self.rapid_time += segment_time
        
        self.torch.position = end
    
    def _process_dwell(self, cmd: Dict[str, Any]):
        """Processa pausa (G04)."""
        p_value = cmd.get('p', 0)
        
        # P pode ser segundos ou milissegundos dependendo do controlador
        if p_value > 100:  # Provavelmente milissegundos
            dwell_seconds = p_value / 1000.0
        else:
            dwell_seconds = p_value
        
        self.total_time += dwell_seconds
        self.dwell_time += dwell_seconds
        
        self.events.append(CuttingEvent(
            time=self.total_time,
            position=self.torch.position.copy(),
            event_type="dwell",
            details={"duration": dwell_seconds}
        ))
    
    def _calculate_motion_segment(
        self,
        start: Point3D,
        end: Point3D,
        is_rapid: bool = False,
        feed_rate: float = 2000.0,
        is_cutting: bool = False
    ) -> MotionSegment:
        """Calcula perfil de movimento considerando física."""
        segment = MotionSegment(start=start, end=end, is_rapid=is_rapid, is_cutting=is_cutting)
        
        # Distância total
        dx = end.x - start.x
        dy = end.y - start.y
        dz = end.z - start.z
        segment.total_distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if segment.total_distance < 0.001:
            return segment
        
        # Velocidade alvo
        if is_rapid:
            # Usar velocidade mínima entre eixos
            v_target = min(
                self.physics.x_max_velocity,
                self.physics.y_max_velocity,
                self.physics.z_max_velocity
            ) * 60  # Converter para mm/min
        else:
            v_target = feed_rate
        
        v_target_mm_s = v_target / 60.0
        
        # Aceleração média ponderada pelos eixos
        total_move = abs(dx) + abs(dy) + abs(dz)
        if total_move > 0:
            accel = (
                (abs(dx) / total_move) * self.physics.x_max_accel +
                (abs(dy) / total_move) * self.physics.y_max_accel +
                (abs(dz) / total_move) * self.physics.z_max_accel
            )
        else:
            accel = self.physics.x_max_accel
        
        # Perfil trapezoidal de velocidade
        accel_distance = (v_target_mm_s ** 2) / (2 * accel)
        
        if 2 * accel_distance > segment.total_distance:
            # Perfil triangular (não atinge velocidade máxima)
            accel_distance = segment.total_distance / 2
            v_peak = math.sqrt(2 * accel * accel_distance)
            segment.accel_time = v_peak / accel
            segment.decel_time = segment.accel_time
            segment.cruise_time = 0
            segment.accel_distance = accel_distance
            segment.decel_distance = accel_distance
            segment.cruise_distance = 0
            segment.cruise_velocity = v_peak
        else:
            # Perfil trapezoidal
            segment.accel_distance = accel_distance
            segment.decel_distance = accel_distance
            segment.cruise_distance = segment.total_distance - 2 * accel_distance
            segment.accel_time = v_target_mm_s / accel
            segment.decel_time = segment.accel_time
            segment.cruise_time = segment.cruise_distance / v_target_mm_s
            segment.cruise_velocity = v_target_mm_s
        
        segment.total_time = segment.accel_time + segment.cruise_time + segment.decel_time
        segment.entry_velocity = 0
        segment.exit_velocity = 0
        segment.feed_rate = feed_rate
        
        return segment
    
    def _calculate_arc_time(self, arc_length: float, feed_mm_s: float) -> float:
        """Calcula tempo de arco considerando aceleração."""
        if arc_length < 0.001:
            return 0.0
        
        # Tempo básico
        basic_time = arc_length / feed_mm_s
        
        # Adicionar overhead de aceleração em arcos
        accel_overhead = 0.1  # 100ms para estabilização em arco
        
        return basic_time + accel_overhead
    
    def _add_heat(self, x: float, y: float, temperature: float):
        """Adiciona ponto de calor."""
        grid_x = int(x / self.heat_grid_resolution)
        grid_y = int(y / self.heat_grid_resolution)
        
        key = (grid_x, grid_y)
        current = self.heat_grid.get(key, 25.0)
        
        # Modelo de acúmulo de calor
        new_temp = current + (temperature - current) * 0.3
        self.heat_grid[key] = new_temp
    
    def _add_heat_along_path(self, start: Point3D, end: Point3D):
        """Adiciona calor ao longo de uma trajetória linear."""
        length = start.distance_xy(end)
        steps = max(1, int(length / self.heat_grid_resolution))
        
        for i in range(steps + 1):
            t = i / steps
            x = start.x + (end.x - start.x) * t
            y = start.y + (end.y - start.y) * t
            
            # Temperatura baseada na amperagem
            temp = 200 + self.current_amperage * 3
            self._add_heat(x, y, temp)
    
    def _add_heat_along_arc(
        self, 
        center: Point3D, 
        radius: float, 
        start_angle: float, 
        end_angle: float
    ):
        """Adiciona calor ao longo de um arco."""
        arc_length = abs(end_angle - start_angle) * radius
        steps = max(1, int(arc_length / self.heat_grid_resolution))
        
        for i in range(steps + 1):
            t = i / steps
            angle = start_angle + (end_angle - start_angle) * t
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            
            temp = 200 + self.current_amperage * 3
            self._add_heat(x, y, temp)
    
    def get_heatmap_data(self) -> List[Dict[str, Any]]:
        """Retorna dados do heatmap para visualização."""
        heatmap = []
        
        for (gx, gy), temp in self.heat_grid.items():
            x = gx * self.heat_grid_resolution
            y = gy * self.heat_grid_resolution
            
            # Determinar zona térmica
            if temp < 100:
                zone = ThermalZone.COLD
            elif temp < 200:
                zone = ThermalZone.WARM
            elif temp < 400:
                zone = ThermalZone.HOT
            else:
                zone = ThermalZone.CRITICAL
            
            heatmap.append({
                "x": x,
                "y": y,
                "temperature": round(temp, 1),
                "zone": zone.value,
                "distortion_risk": temp > 350
            })
        
        return heatmap
    
    def _generate_results(self) -> Dict[str, Any]:
        """Gera resultado final da simulação."""
        # Formatar tempo total
        total_minutes = self.total_time / 60.0
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        seconds = int((self.total_time % 60))
        
        time_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return {
            "success": True,
            "simulation_mode": self.mode.value,
            "time": {
                "total_seconds": round(self.total_time, 2),
                "total_minutes": round(total_minutes, 2),
                "formatted": time_formatted,
                "cutting_seconds": round(self.cutting_time, 2),
                "cutting_percent": round(self.cutting_time / max(self.total_time, 0.001) * 100, 1),
                "rapid_seconds": round(self.rapid_time, 2),
                "rapid_percent": round(self.rapid_time / max(self.total_time, 0.001) * 100, 1),
                "dwell_seconds": round(self.dwell_time, 2),
                "pierce_count": self.consumables.total_pierces,
            },
            "distance": {
                "total_mm": round(self.total_distance, 2),
                "total_meters": round(self.total_distance / 1000, 3),
                "cutting_mm": round(self.cutting_distance, 2),
                "rapid_mm": round(self.rapid_distance, 2),
            },
            "consumables": self.consumables.to_dict(),
            "thermal": {
                "max_temperature": round(max(self.heat_grid.values(), default=25.0), 1),
                "hot_spots_count": sum(1 for t in self.heat_grid.values() if t > 350),
                "distortion_risk_areas": sum(1 for t in self.heat_grid.values() if t > 400),
            },
            "heatmap": self.get_heatmap_data(),
            "events_count": len(self.events),
            "segments_count": len(self.motion_segments),
            "physics_parameters": {
                "x_max_accel": self.physics.x_max_accel,
                "y_max_accel": self.physics.y_max_accel,
                "work_area": f"{self.physics.x_max}mm x {self.physics.y_max}mm",
            }
        }
    
    def get_timeline(self) -> List[Dict[str, Any]]:
        """Retorna timeline de eventos para visualização."""
        timeline = []
        
        for event in self.events:
            timeline.append({
                "time": round(event.time, 3),
                "type": event.event_type,
                "position": event.position.to_tuple(),
                "details": event.details
            })
        
        return sorted(timeline, key=lambda x: x["time"])
    
    def get_motion_profile(self) -> List[Dict[str, Any]]:
        """Retorna perfil de movimento para gráfico de velocidade."""
        profile = []
        current_time = 0.0
        
        for segment in self.motion_segments:
            # Ponto de entrada
            profile.append({
                "time": round(current_time, 3),
                "velocity": round(segment.entry_velocity * 60, 1),  # mm/min
                "position": segment.start.to_tuple(),
                "state": "entry"
            })
            
            # Fim da aceleração
            current_time += segment.accel_time
            profile.append({
                "time": round(current_time, 3),
                "velocity": round(segment.cruise_velocity * 60, 1),
                "position": None,
                "state": "cruise"
            })
            
            # Fim do cruise
            current_time += segment.cruise_time
            profile.append({
                "time": round(current_time, 3),
                "velocity": round(segment.cruise_velocity * 60, 1),
                "position": None,
                "state": "decel_start"
            })
            
            # Fim da desaceleração
            current_time += segment.decel_time
            profile.append({
                "time": round(current_time, 3),
                "velocity": round(segment.exit_velocity * 60, 1),
                "position": segment.end.to_tuple(),
                "state": "exit"
            })
        
        return profile


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES UTILITÁRIAS
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_gcode(
    gcode: str,
    mode: SimulationMode = SimulationMode.STANDARD,
    physics: Optional[MachinePhysics] = None,
    amperage: float = 45.0,
    pierce_delay: float = 0.5
) -> Dict[str, Any]:
    """
    Função utilitária para simular G-code.
    
    Args:
        gcode: Código G-code
        mode: Modo de simulação
        physics: Parâmetros físicos da máquina (opcional)
        amperage: Amperagem de corte
        pierce_delay: Delay de pierce
        
    Returns:
        Resultado da simulação
    """
    simulator = PhysicsSimulator(physics=physics, mode=mode)
    return simulator.simulate(gcode, amperage, pierce_delay)


def estimate_job_time(
    cutting_length: float,
    rapid_length: float,
    pierce_count: int,
    feed_rate: float = 2000.0,
    rapid_rate: float = 15000.0,
    pierce_delay: float = 0.5,
    physics: Optional[MachinePhysics] = None
) -> Dict[str, float]:
    """
    Estima tempo de job sem simular G-code completo.
    
    Args:
        cutting_length: Comprimento total de corte (mm)
        rapid_length: Comprimento total de rapids (mm)
        pierce_count: Número de pierces
        feed_rate: Velocidade de corte (mm/min)
        rapid_rate: Velocidade de rapid (mm/min)
        pierce_delay: Delay de pierce (segundos)
        physics: Parâmetros físicos (opcional)
        
    Returns:
        Estimativa de tempos
    """
    # Tempos básicos
    cutting_time = (cutting_length / feed_rate) * 60  # segundos
    rapid_time = (rapid_length / rapid_rate) * 60
    pierce_time = pierce_count * pierce_delay
    
    # Adicionar overhead de aceleração/desaceleração
    if physics:
        avg_accel = (physics.x_max_accel + physics.y_max_accel) / 2
        # Tempo extra para aceleração em cada movimento
        accel_overhead = pierce_count * 2 * (feed_rate / 60) / avg_accel
    else:
        accel_overhead = pierce_count * 0.2  # 200ms por movimento
    
    total_time = cutting_time + rapid_time + pierce_time + accel_overhead
    
    return {
        "cutting_time": round(cutting_time, 2),
        "rapid_time": round(rapid_time, 2),
        "pierce_time": round(pierce_time, 2),
        "accel_overhead": round(accel_overhead, 2),
        "total_time": round(total_time, 2),
        "total_minutes": round(total_time / 60, 2),
        "formatted": f"{int(total_time // 60)}:{int(total_time % 60):02d}"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PRESETS DE MÁQUINAS
# ═══════════════════════════════════════════════════════════════════════════════

class MachinePhysicsPresets:
    """Presets de física para máquinas comuns."""
    
    @staticmethod
    def small_hobby() -> MachinePhysics:
        """Máquina hobby pequena (área ~600x600mm)."""
        return MachinePhysics(
            x_axis_mass=15.0,
            y_axis_mass=25.0,
            z_axis_mass=5.0,
            x_max_accel=5000.0,
            y_max_accel=4000.0,
            z_max_accel=8000.0,
            x_max_velocity=300.0,
            y_max_velocity=300.0,
            z_max_velocity=80.0,
            x_max=600.0,
            y_max=600.0,
        )
    
    @staticmethod
    def medium_industrial() -> MachinePhysics:
        """Máquina industrial média (área ~1500x3000mm)."""
        return MachinePhysics(
            x_axis_mass=50.0,
            y_axis_mass=100.0,
            z_axis_mass=15.0,
            x_max_accel=3000.0,
            y_max_accel=2000.0,
            z_max_accel=5000.0,
            x_max_velocity=500.0,
            y_max_velocity=500.0,
            z_max_velocity=100.0,
            x_max=3000.0,
            y_max=1500.0,
        )
    
    @staticmethod
    def large_production() -> MachinePhysics:
        """Máquina de produção grande (área ~6000x2000mm)."""
        return MachinePhysics(
            x_axis_mass=100.0,
            y_axis_mass=200.0,
            z_axis_mass=25.0,
            x_max_accel=2000.0,
            y_max_accel=1500.0,
            z_max_accel=4000.0,
            x_max_velocity=600.0,
            y_max_velocity=500.0,
            z_max_velocity=120.0,
            x_max=6000.0,
            y_max=2000.0,
        )
    
    @staticmethod
    def hypertherm_hpr() -> MachinePhysics:
        """Perfil típico para Hypertherm HPR (alta definição)."""
        return MachinePhysics(
            x_axis_mass=80.0,
            y_axis_mass=150.0,
            z_axis_mass=20.0,
            x_max_accel=4000.0,
            y_max_accel=3000.0,
            z_max_accel=6000.0,
            x_max_velocity=600.0,
            y_max_velocity=600.0,
            z_max_velocity=150.0,
            x_max=4000.0,
            y_max=2000.0,
            position_accuracy=0.005,
            repeatability=0.002,
        )
