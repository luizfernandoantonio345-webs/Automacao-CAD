"""
═══════════════════════════════════════════════════════════════════════════════
BANCO DE DADOS DE MÁQUINAS - Parâmetros por Equipamento CNC
═══════════════════════════════════════════════════════════════════════════════

Sistema completo de banco de dados de máquinas CNC plasma com:
- Parâmetros físicos (aceleração, velocidade, delays)
- Limitações por modelo
- Capacidades específicas
- Histórico de manutenção
- Calibração automática

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engcad.cam.machine_database")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class MachineCategory(Enum):
    """Categorias de máquinas."""
    PLASMA_TABLE = "plasma_table"       # Mesa plasma CNC
    PLASMA_GANTRY = "plasma_gantry"     # Pórtico plasma
    PLASMA_ROBOT = "plasma_robot"       # Robô de corte
    LASER_CO2 = "laser_co2"             # Laser CO2
    LASER_FIBER = "laser_fiber"         # Laser fibra
    WATERJET = "waterjet"               # Jato d'água
    OXYFUEL = "oxyfuel"                 # Oxicorte


class ControllerType(Enum):
    """Tipos de controlador."""
    MACH3 = "mach3"
    MACH4 = "mach4"
    LINUXCNC = "linuxcnc"
    HYPERTHERM = "hypertherm"
    FANUC = "fanuc"
    SIEMENS = "siemens"
    CUSTOM = "custom"


class MotorType(Enum):
    """Tipos de motor."""
    STEPPER = "stepper"
    SERVO_AC = "servo_ac"
    SERVO_DC = "servo_dc"
    LINEAR = "linear"


class DriveSystem(Enum):
    """Sistema de acionamento."""
    RACK_PINION = "rack_pinion"     # Cremalheira e pinhão
    BALL_SCREW = "ball_screw"       # Fuso de esferas
    BELT = "belt"                    # Correia
    LINEAR_MOTOR = "linear_motor"    # Motor linear


class MaintenanceStatus(Enum):
    """Status de manutenção."""
    OK = "ok"
    ATTENTION = "attention"
    WARNING = "warning"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AxisConfig:
    """Configuração de um eixo."""
    
    # Identificação
    name: str                           # "X", "Y", "Z", "A", etc.
    
    # Limites físicos
    min_position: float = 0.0           # mm
    max_position: float = 1000.0        # mm
    
    # Velocidades
    max_velocity: float = 20000.0       # mm/min
    max_rapid_velocity: float = 30000.0 # mm/min
    homing_velocity: float = 5000.0     # mm/min
    
    # Aceleração
    max_acceleration: float = 5000.0    # mm/s²
    max_jerk: float = 50.0              # mm/s³
    
    # Motor e drive
    motor_type: MotorType = MotorType.STEPPER
    drive_system: DriveSystem = DriveSystem.RACK_PINION
    steps_per_mm: float = 200.0         # Para stepper
    encoder_resolution: float = 0.01    # mm por pulso
    
    # Backlash e compensação
    backlash: float = 0.0               # mm
    backlash_compensation: bool = False
    
    # Soft limits
    soft_limit_enabled: bool = True
    soft_limit_margin: float = 5.0      # mm de margem
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "range": [self.min_position, self.max_position],
            "max_velocity": self.max_velocity,
            "max_acceleration": self.max_acceleration,
            "motor_type": self.motor_type.value,
            "drive_system": self.drive_system.value,
            "backlash": self.backlash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AxisConfig":
        range_data = data.get("range", [0, 1000])
        return cls(
            name=data.get("name", "X"),
            min_position=range_data[0] if len(range_data) > 0 else 0,
            max_position=range_data[1] if len(range_data) > 1 else 1000,
            max_velocity=data.get("max_velocity", 20000),
            max_acceleration=data.get("max_acceleration", 5000),
            motor_type=MotorType(data.get("motor_type", "stepper")),
            drive_system=DriveSystem(data.get("drive_system", "rack_pinion")),
            backlash=data.get("backlash", 0),
        )


@dataclass
class PlasmaSourceConfig:
    """Configuração da fonte plasma."""
    
    # Identificação
    manufacturer: str = "Generic"
    model: str = "Standard"
    
    # Capacidades
    max_amperage: int = 200             # A
    min_amperage: int = 15              # A
    max_thickness_mild_steel: float = 32.0  # mm
    
    # Características
    thc_capable: bool = True
    arc_voltage_range: Tuple[float, float] = (80.0, 180.0)
    
    # Consumíveis
    consumable_set: str = "standard"
    
    # Tempos
    pilot_arc_timeout: float = 3.0      # segundos
    transfer_timeout: float = 0.5       # segundos
    
    # Gases
    plasma_gas: str = "air"             # air, oxygen, nitrogen, etc.
    shield_gas: str = "air"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "max_amperage": self.max_amperage,
            "min_amperage": self.min_amperage,
            "max_thickness": self.max_thickness_mild_steel,
            "thc_capable": self.thc_capable,
        }


@dataclass
class THCConfig:
    """Configuração do Torch Height Control."""
    
    enabled: bool = True
    
    # Velocidades
    up_speed: float = 500.0             # mm/min
    down_speed: float = 500.0           # mm/min
    
    # Limites
    max_correction: float = 5.0         # mm
    sample_time: float = 0.1            # segundos
    
    # Tensões
    voltage_offset: float = 0.0         # V
    voltage_threshold: float = 0.5      # V - sensibilidade
    
    # Corner lockout (desativa em cantos)
    corner_lockout_enabled: bool = True
    corner_lockout_angle: float = 60.0  # graus
    corner_lockout_distance: float = 3.0  # mm
    
    # Anti-dive
    anti_dive_enabled: bool = True
    anti_dive_delay: float = 0.2        # segundos


@dataclass
class MachineTimings:
    """Tempos e delays da máquina."""
    
    # Pierce
    min_pierce_delay: float = 0.1       # segundos
    max_pierce_delay: float = 5.0       # segundos
    default_pierce_delay: float = 0.5   # segundos
    
    # THC
    thc_delay_after_pierce: float = 0.3 # segundos
    thc_corner_lock_time: float = 0.2   # segundos
    
    # Arco
    arc_on_delay: float = 0.0           # segundos
    arc_off_delay: float = 0.0          # segundos
    
    # Movimento
    motion_delay: float = 0.0           # segundos entre movimentos
    
    # Gás
    pre_flow_time: float = 0.5          # segundos
    post_flow_time: float = 1.0         # segundos
    
    # Probe
    probe_feed: float = 1000.0          # mm/min
    probe_retract: float = 3.0          # mm


@dataclass
class MaintenanceRecord:
    """Registro de manutenção."""
    
    date: str                           # ISO date string
    type: str                           # "scheduled", "corrective", "calibration"
    description: str
    technician: str = ""
    parts_replaced: List[str] = field(default_factory=list)
    cost: float = 0.0
    next_maintenance: str = ""          # ISO date string


@dataclass
class ConsumableStatus:
    """Status de consumíveis."""
    
    electrode_pierces: int = 0          # Pierces desde último troca
    electrode_max_pierces: int = 1000   # Vida esperada
    nozzle_pierces: int = 0
    nozzle_max_pierces: int = 500
    shield_hours: float = 0.0
    shield_max_hours: float = 8.0
    
    @property
    def electrode_life_percent(self) -> float:
        return max(0, 100 - (self.electrode_pierces / self.electrode_max_pierces * 100))
    
    @property
    def nozzle_life_percent(self) -> float:
        return max(0, 100 - (self.nozzle_pierces / self.nozzle_max_pierces * 100))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "electrode": {
                "pierces": self.electrode_pierces,
                "max": self.electrode_max_pierces,
                "life_percent": self.electrode_life_percent,
            },
            "nozzle": {
                "pierces": self.nozzle_pierces,
                "max": self.nozzle_max_pierces,
                "life_percent": self.nozzle_life_percent,
            },
            "shield_hours": self.shield_hours,
        }


@dataclass
class MachineStatistics:
    """Estatísticas de uso da máquina."""
    
    total_runtime_hours: float = 0.0
    total_cutting_meters: float = 0.0
    total_pierces: int = 0
    total_jobs: int = 0
    
    # Por período
    runtime_this_month: float = 0.0
    cutting_this_month: float = 0.0
    pierces_this_month: int = 0
    jobs_this_month: int = 0
    
    # Erros
    error_count: int = 0
    last_error: str = ""
    last_error_date: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runtime_hours": self.total_runtime_hours,
            "total_cutting_meters": self.total_cutting_meters,
            "total_pierces": self.total_pierces,
            "total_jobs": self.total_jobs,
            "this_month": {
                "runtime": self.runtime_this_month,
                "cutting": self.cutting_this_month,
                "pierces": self.pierces_this_month,
                "jobs": self.jobs_this_month,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MÁQUINA COMPLETA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Machine:
    """Definição completa de uma máquina CNC."""
    
    # Identificação
    id: str
    name: str
    description: str = ""
    category: MachineCategory = MachineCategory.PLASMA_TABLE
    
    # Fabricante/Modelo
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    year: int = 2024
    
    # Controlador
    controller_type: ControllerType = ControllerType.MACH3
    controller_version: str = ""
    
    # Área de trabalho
    work_area_x: float = 3000.0         # mm
    work_area_y: float = 1500.0         # mm
    work_area_z: float = 100.0          # mm
    
    # Configuração de eixos
    axis_x: AxisConfig = field(default_factory=lambda: AxisConfig(name="X", max_position=3000))
    axis_y: AxisConfig = field(default_factory=lambda: AxisConfig(name="Y", max_position=1500))
    axis_z: AxisConfig = field(default_factory=lambda: AxisConfig(name="Z", max_position=100))
    
    # Fonte plasma
    plasma_source: PlasmaSourceConfig = field(default_factory=PlasmaSourceConfig)
    
    # THC
    thc_config: THCConfig = field(default_factory=THCConfig)
    
    # Tempos
    timings: MachineTimings = field(default_factory=MachineTimings)
    
    # Status e manutenção
    maintenance_status: MaintenanceStatus = MaintenanceStatus.OK
    maintenance_history: List[MaintenanceRecord] = field(default_factory=list)
    consumables: ConsumableStatus = field(default_factory=ConsumableStatus)
    statistics: MachineStatistics = field(default_factory=MachineStatistics)
    
    # Calibração
    last_calibration: str = ""          # ISO date
    calibration_due: str = ""           # ISO date
    
    # Limites dinâmicos (ajustados por operação)
    current_max_speed: float = 0.0      # Limitação atual
    current_speed_factor: float = 1.0   # Fator de ajuste
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_max_speed(self) -> float:
        """Retorna velocidade máxima considerando limitações atuais."""
        base = min(self.axis_x.max_velocity, self.axis_y.max_velocity)
        return base * self.current_speed_factor
    
    def get_max_acceleration(self) -> float:
        """Retorna aceleração máxima."""
        return min(self.axis_x.max_acceleration, self.axis_y.max_acceleration)
    
    def validate_position(self, x: float, y: float, z: float = 0) -> Tuple[bool, str]:
        """Valida se posição está dentro dos limites."""
        errors = []
        
        if x < self.axis_x.min_position or x > self.axis_x.max_position:
            errors.append(f"X={x:.2f} fora do limite")
        if y < self.axis_y.min_position or y > self.axis_y.max_position:
            errors.append(f"Y={y:.2f} fora do limite")
        if z < self.axis_z.min_position or z > self.axis_z.max_position:
            errors.append(f"Z={z:.2f} fora do limite")
        
        return (len(errors) == 0, "; ".join(errors))
    
    def get_pierce_delay(self, thickness: float) -> float:
        """Calcula pierce delay recomendado para espessura."""
        # Base: timings.default_pierce_delay
        # Ajusta por espessura
        base = self.timings.default_pierce_delay
        factor = 1.0 + (thickness - 6) * 0.1  # +10% por mm acima de 6mm
        
        delay = base * max(0.5, min(3.0, factor))
        
        return max(
            self.timings.min_pierce_delay,
            min(delay, self.timings.max_pierce_delay)
        )
    
    def estimate_job_time(
        self,
        cutting_length: float,  # mm
        rapid_length: float,    # mm
        pierce_count: int,
        cutting_speed: float    # mm/min
    ) -> float:
        """Estima tempo de execução de um job (segundos)."""
        # Tempo de corte
        cut_time = (cutting_length / cutting_speed) * 60
        
        # Tempo de rapids
        rapid_speed = min(self.axis_x.max_rapid_velocity, self.axis_y.max_rapid_velocity)
        rapid_time = (rapid_length / rapid_speed) * 60
        
        # Tempo de pierce
        avg_pierce_delay = self.timings.default_pierce_delay
        pierce_time = pierce_count * avg_pierce_delay
        
        # Tempos adicionais (aceleração/desaceleração, etc.)
        overhead = pierce_count * 0.5  # ~0.5s por pierce para posicionamento
        
        return cut_time + rapid_time + pierce_time + overhead
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "year": self.year,
            "controller": {
                "type": self.controller_type.value,
                "version": self.controller_version,
            },
            "work_area": {
                "x": self.work_area_x,
                "y": self.work_area_y,
                "z": self.work_area_z,
            },
            "axes": {
                "x": self.axis_x.to_dict(),
                "y": self.axis_y.to_dict(),
                "z": self.axis_z.to_dict(),
            },
            "plasma_source": self.plasma_source.to_dict(),
            "thc_enabled": self.thc_config.enabled,
            "maintenance_status": self.maintenance_status.value,
            "consumables": self.consumables.to_dict(),
            "statistics": self.statistics.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Machine":
        """Cria máquina a partir de dicionário."""
        work_area = data.get("work_area", {})
        axes = data.get("axes", {})
        
        machine = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=MachineCategory(data.get("category", "plasma_table")),
            manufacturer=data.get("manufacturer", ""),
            model=data.get("model", ""),
            work_area_x=work_area.get("x", 3000),
            work_area_y=work_area.get("y", 1500),
            work_area_z=work_area.get("z", 100),
        )
        
        if "x" in axes:
            machine.axis_x = AxisConfig.from_dict(axes["x"])
        if "y" in axes:
            machine.axis_y = AxisConfig.from_dict(axes["y"])
        if "z" in axes:
            machine.axis_z = AxisConfig.from_dict(axes["z"])
        
        return machine


# ═══════════════════════════════════════════════════════════════════════════════
# BANCO DE DADOS
# ═══════════════════════════════════════════════════════════════════════════════

class MachineDatabase:
    """
    Banco de dados de máquinas CNC.
    
    Gerencia:
    - Cadastro de máquinas
    - Parâmetros por modelo
    - Histórico de uso
    - Manutenção e calibração
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa o banco de dados.
        
        Args:
            db_path: Caminho para arquivo JSON do banco
        """
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), 'data', 'machines.json'
        )
        self.machines: Dict[str, Machine] = {}
        self._load_builtin_machines()
        self._load_from_file()
    
    def _load_builtin_machines(self):
        """Carrega máquinas pré-configuradas."""
        # Mesa plasma básica
        basic_table = Machine(
            id="plasma_basic",
            name="Mesa Plasma Básica",
            description="Configuração básica para mesas plasma CNC com Mach3",
            category=MachineCategory.PLASMA_TABLE,
            manufacturer="Generic",
            model="Basic Table",
            controller_type=ControllerType.MACH3,
            work_area_x=1500,
            work_area_y=1000,
            axis_x=AxisConfig(
                name="X",
                max_position=1500,
                max_velocity=15000,
                max_acceleration=3000,
                motor_type=MotorType.STEPPER,
                drive_system=DriveSystem.RACK_PINION,
            ),
            axis_y=AxisConfig(
                name="Y",
                max_position=1000,
                max_velocity=15000,
                max_acceleration=3000,
                motor_type=MotorType.STEPPER,
                drive_system=DriveSystem.RACK_PINION,
            ),
            axis_z=AxisConfig(
                name="Z",
                max_position=75,
                max_velocity=5000,
                max_acceleration=2000,
            ),
            plasma_source=PlasmaSourceConfig(
                manufacturer="Generic",
                max_amperage=60,
                thc_capable=True,
            ),
        )
        self.machines[basic_table.id] = basic_table
        
        # Mesa industrial
        industrial_table = Machine(
            id="plasma_industrial",
            name="Mesa Plasma Industrial",
            description="Configuração para mesas plasma industriais com servo motores",
            category=MachineCategory.PLASMA_TABLE,
            manufacturer="Industrial",
            model="Heavy Duty",
            controller_type=ControllerType.LINUXCNC,
            work_area_x=3000,
            work_area_y=1500,
            axis_x=AxisConfig(
                name="X",
                max_position=3000,
                max_velocity=25000,
                max_acceleration=6000,
                motor_type=MotorType.SERVO_AC,
                drive_system=DriveSystem.RACK_PINION,
            ),
            axis_y=AxisConfig(
                name="Y",
                max_position=1500,
                max_velocity=25000,
                max_acceleration=6000,
                motor_type=MotorType.SERVO_AC,
                drive_system=DriveSystem.RACK_PINION,
            ),
            axis_z=AxisConfig(
                name="Z",
                max_position=100,
                max_velocity=8000,
                max_acceleration=4000,
                motor_type=MotorType.SERVO_AC,
            ),
            plasma_source=PlasmaSourceConfig(
                manufacturer="Hypertherm",
                model="PowerMax 125",
                max_amperage=125,
                thc_capable=True,
            ),
        )
        self.machines[industrial_table.id] = industrial_table
        
        # Hypertherm HD
        hypertherm_hd = Machine(
            id="hypertherm_hd",
            name="Hypertherm HD System",
            description="Sistema Hypertherm de alta definição",
            category=MachineCategory.PLASMA_GANTRY,
            manufacturer="Hypertherm",
            model="HPR400XD",
            controller_type=ControllerType.HYPERTHERM,
            work_area_x=6000,
            work_area_y=2000,
            axis_x=AxisConfig(
                name="X",
                max_position=6000,
                max_velocity=35000,
                max_acceleration=8000,
                motor_type=MotorType.SERVO_AC,
                drive_system=DriveSystem.RACK_PINION,
            ),
            axis_y=AxisConfig(
                name="Y",
                max_position=2000,
                max_velocity=35000,
                max_acceleration=8000,
                motor_type=MotorType.SERVO_AC,
                drive_system=DriveSystem.RACK_PINION,
            ),
            plasma_source=PlasmaSourceConfig(
                manufacturer="Hypertherm",
                model="HPR400XD",
                max_amperage=400,
                max_thickness_mild_steel=50,
                thc_capable=True,
            ),
        )
        self.machines[hypertherm_hd.id] = hypertherm_hd
        
        # Torchmate
        torchmate = Machine(
            id="torchmate_4x4",
            name="Torchmate 4x4",
            description="Mesa Torchmate 4x4 Lincoln Electric",
            category=MachineCategory.PLASMA_TABLE,
            manufacturer="Lincoln Electric",
            model="Torchmate 4x4",
            controller_type=ControllerType.MACH3,
            work_area_x=1200,
            work_area_y=1200,
            axis_x=AxisConfig(
                name="X",
                max_position=1200,
                max_velocity=12000,
                max_acceleration=2500,
            ),
            axis_y=AxisConfig(
                name="Y",
                max_position=1200,
                max_velocity=12000,
                max_acceleration=2500,
            ),
        )
        self.machines[torchmate.id] = torchmate
    
    def _load_from_file(self):
        """Carrega máquinas customizadas do arquivo."""
        if not os.path.exists(self.db_path):
            return
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for machine_data in data.get("machines", []):
                machine = Machine.from_dict(machine_data)
                self.machines[machine.id] = machine
            
            logger.info(f"Carregadas {len(data.get('machines', []))} máquinas customizadas")
        except Exception as e:
            logger.error(f"Erro ao carregar banco de dados: {e}")
    
    def save(self):
        """Salva banco de dados em arquivo."""
        # Criar diretório se não existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Salvar apenas máquinas não-builtin
        custom_machines = [
            m.to_dict() for id, m in self.machines.items()
            if id not in ["plasma_basic", "plasma_industrial", "hypertherm_hd", "torchmate_4x4"]
        ]
        
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "machines": custom_machines,
        }
        
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Banco de dados salvo: {self.db_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar banco de dados: {e}")
    
    def get_machine(self, machine_id: str) -> Optional[Machine]:
        """Obtém uma máquina pelo ID."""
        return self.machines.get(machine_id)
    
    def list_machines(self) -> List[Dict[str, Any]]:
        """Lista todas as máquinas disponíveis."""
        return [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "category": m.category.value,
                "manufacturer": m.manufacturer,
                "model": m.model,
                "work_area": f"{m.work_area_x}x{m.work_area_y}mm",
                "max_speed": m.get_max_speed(),
                "status": m.maintenance_status.value,
            }
            for m in self.machines.values()
        ]
    
    def add_machine(self, machine: Machine) -> bool:
        """Adiciona uma nova máquina."""
        if machine.id in self.machines:
            logger.warning(f"Máquina {machine.id} já existe")
            return False
        
        self.machines[machine.id] = machine
        self.save()
        return True
    
    def update_machine(self, machine: Machine) -> bool:
        """Atualiza uma máquina existente."""
        if machine.id not in self.machines:
            logger.warning(f"Máquina {machine.id} não encontrada")
            return False
        
        machine.updated_at = datetime.now().isoformat()
        self.machines[machine.id] = machine
        self.save()
        return True
    
    def delete_machine(self, machine_id: str) -> bool:
        """Remove uma máquina."""
        if machine_id not in self.machines:
            return False
        
        del self.machines[machine_id]
        self.save()
        return True
    
    def get_machines_by_category(
        self,
        category: MachineCategory
    ) -> List[Machine]:
        """Filtra máquinas por categoria."""
        return [m for m in self.machines.values() if m.category == category]
    
    def get_machines_by_capability(
        self,
        min_thickness: float = None,
        min_work_area: Tuple[float, float] = None,
        thc_required: bool = False
    ) -> List[Machine]:
        """Filtra máquinas por capacidade."""
        result = []
        
        for machine in self.machines.values():
            # Verificar espessura máxima
            if min_thickness and machine.plasma_source.max_thickness_mild_steel < min_thickness:
                continue
            
            # Verificar área de trabalho
            if min_work_area:
                if machine.work_area_x < min_work_area[0] or \
                   machine.work_area_y < min_work_area[1]:
                    continue
            
            # Verificar THC
            if thc_required and not machine.thc_config.enabled:
                continue
            
            result.append(machine)
        
        return result
    
    def update_consumables(
        self,
        machine_id: str,
        electrode_pierces: int = 0,
        nozzle_pierces: int = 0,
        shield_hours: float = 0.0
    ):
        """Atualiza contadores de consumíveis."""
        machine = self.get_machine(machine_id)
        if not machine:
            return
        
        machine.consumables.electrode_pierces += electrode_pierces
        machine.consumables.nozzle_pierces += nozzle_pierces
        machine.consumables.shield_hours += shield_hours
        
        # Verificar alertas
        if machine.consumables.electrode_life_percent < 10:
            machine.maintenance_status = MaintenanceStatus.WARNING
        elif machine.consumables.electrode_life_percent < 20:
            machine.maintenance_status = MaintenanceStatus.ATTENTION
        
        machine.updated_at = datetime.now().isoformat()
        self.save()
    
    def reset_consumables(self, machine_id: str, consumable: str = "all"):
        """Reseta contadores de consumíveis após troca."""
        machine = self.get_machine(machine_id)
        if not machine:
            return
        
        if consumable in ["electrode", "all"]:
            machine.consumables.electrode_pierces = 0
        if consumable in ["nozzle", "all"]:
            machine.consumables.nozzle_pierces = 0
        if consumable in ["shield", "all"]:
            machine.consumables.shield_hours = 0.0
        
        machine.maintenance_status = MaintenanceStatus.OK
        machine.updated_at = datetime.now().isoformat()
        self.save()
    
    def add_maintenance_record(
        self,
        machine_id: str,
        record: MaintenanceRecord
    ):
        """Adiciona registro de manutenção."""
        machine = self.get_machine(machine_id)
        if not machine:
            return
        
        machine.maintenance_history.append(record)
        machine.maintenance_status = MaintenanceStatus.OK
        machine.updated_at = datetime.now().isoformat()
        self.save()
    
    def update_statistics(
        self,
        machine_id: str,
        runtime_hours: float = 0,
        cutting_meters: float = 0,
        pierces: int = 0,
        jobs: int = 0
    ):
        """Atualiza estatísticas de uso."""
        machine = self.get_machine(machine_id)
        if not machine:
            return
        
        stats = machine.statistics
        stats.total_runtime_hours += runtime_hours
        stats.total_cutting_meters += cutting_meters
        stats.total_pierces += pierces
        stats.total_jobs += jobs
        
        stats.runtime_this_month += runtime_hours
        stats.cutting_this_month += cutting_meters
        stats.pierces_this_month += pierces
        stats.jobs_this_month += jobs
        
        machine.updated_at = datetime.now().isoformat()
        self.save()


# ═══════════════════════════════════════════════════════════════════════════════
# INSTÂNCIA GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

# Instância singleton do banco de dados
_machine_db: Optional[MachineDatabase] = None


def get_machine_database() -> MachineDatabase:
    """Obtém instância do banco de dados de máquinas."""
    global _machine_db
    if _machine_db is None:
        _machine_db = MachineDatabase()
    return _machine_db


def get_machine(machine_id: str) -> Optional[Machine]:
    """Função auxiliar para obter uma máquina."""
    return get_machine_database().get_machine(machine_id)


def list_machines() -> List[Dict[str, Any]]:
    """Função auxiliar para listar máquinas."""
    return get_machine_database().list_machines()
