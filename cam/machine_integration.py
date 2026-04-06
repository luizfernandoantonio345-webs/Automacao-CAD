# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                  MACHINE INTEGRATION - Comunicação CNC                         ║
║                                                                               ║
║  Sistema de comunicação com máquinas CNC plasma via Serial/USB/TCP.           ║
║  Suporta envio de G-code, monitoramento e controle em tempo real.             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import queue

logger = logging.getLogger(__name__)


class ConnectionType(str, Enum):
    """Tipos de conexão suportados."""
    SERIAL = "serial"
    USB = "usb"
    TCP = "tcp"
    GRBL = "grbl"
    MACH3 = "mach3"
    LINUXCNC = "linuxcnc"


class MachineStatus(str, Enum):
    """Status possíveis da máquina."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ALARM = "alarm"
    ERROR = "error"
    HOMING = "homing"
    JOG = "jog"


class CommandPriority(int, Enum):
    """Prioridade de comandos."""
    IMMEDIATE = 0  # Stop, pause, emergency
    HIGH = 1       # Movement
    NORMAL = 2     # G-code lines
    LOW = 3        # Status queries


@dataclass
class MachinePosition:
    """Posição atual da máquina."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    unit: str = "mm"
    
    # Offsets de trabalho
    work_offset_x: float = 0.0
    work_offset_y: float = 0.0
    work_offset_z: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MachineState:
    """Estado completo da máquina."""
    status: MachineStatus = MachineStatus.DISCONNECTED
    position: MachinePosition = field(default_factory=MachinePosition)
    
    # Plasma específico
    arc_on: bool = False
    thc_active: bool = False
    torch_height: float = 0.0
    arc_voltage: float = 0.0
    amperage: int = 0
    
    # Velocidades
    feed_rate: float = 0.0
    feed_override: int = 100
    rapid_override: int = 100
    
    # G-code
    current_line: int = 0
    total_lines: int = 0
    progress_percent: float = 0.0
    elapsed_time: float = 0.0
    
    # Flags
    torch_ok: bool = True
    coolant_ok: bool = True
    limits_triggered: List[str] = field(default_factory=list)
    
    # Erros
    error_code: int = 0
    error_message: str = ""
    alarm_code: int = 0
    alarm_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['position'] = self.position.to_dict()
        return data


@dataclass
class MachineConfig:
    """Configuração de uma máquina."""
    id: str = ""
    name: str = ""
    connection_type: ConnectionType = ConnectionType.SERIAL
    
    # Conexão serial
    port: str = ""  # COM3, /dev/ttyUSB0
    baud_rate: int = 115200
    
    # Conexão TCP
    ip_address: str = ""
    tcp_port: int = 5000
    
    # Capacidades
    has_thc: bool = True
    has_ohmic_probe: bool = True
    max_x: float = 1500  # mm
    max_y: float = 3000  # mm
    max_z: float = 150   # mm
    max_speed: float = 15000  # mm/min
    
    # Tempos
    connection_timeout: float = 5.0
    response_timeout: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['connection_type'] = self.connection_type.value
        return data


class SerialDriver:
    """
    Driver para comunicação serial com CNC.
    
    Suporta GRBL e controladores compatíveis.
    """
    
    def __init__(self, config: MachineConfig):
        self.config = config
        self._serial = None
        self._connected = False
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        self._command_queue = queue.Queue()
        self._response_callbacks: List[Callable] = []
    
    def connect(self) -> bool:
        """
        Conecta à máquina via serial.
        
        Returns:
            True se conectado com sucesso
        """
        try:
            import serial
            
            logger.info(f"Conectando a {self.config.port} @ {self.config.baud_rate}")
            
            self._serial = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                timeout=self.config.response_timeout
            )
            
            time.sleep(2)  # Aguardar inicialização
            
            # Limpar buffer
            self._serial.reset_input_buffer()
            
            # Testar comunicação
            self._serial.write(b"\r\n\r\n")
            time.sleep(0.5)
            response = self._serial.read_all().decode('utf-8', errors='ignore')
            
            if 'Grbl' in response or 'ok' in response:
                self._connected = True
                self._start_read_thread()
                logger.info(f"Conectado: {response.strip()}")
                return True
            else:
                logger.warning(f"Resposta inesperada: {response}")
                return False
                
        except ImportError:
            logger.error("pyserial não instalado. Execute: pip install pyserial")
            return False
        except Exception as e:
            logger.error(f"Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta da máquina."""
        self._running = False
        
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2)
        
        if self._serial:
            self._serial.close()
            self._serial = None
        
        self._connected = False
        logger.info("Desconectado")
    
    def _start_read_thread(self):
        """Inicia thread de leitura contínua."""
        self._running = True
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()
    
    def _read_loop(self):
        """Loop de leitura de respostas."""
        while self._running and self._serial:
            try:
                if self._serial.in_waiting > 0:
                    line = self._serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._handle_response(line)
            except Exception as e:
                logger.error(f"Erro na leitura: {e}")
                time.sleep(0.1)
    
    def _handle_response(self, response: str):
        """Processa resposta da máquina."""
        for callback in self._response_callbacks:
            try:
                callback(response)
            except Exception as e:
                logger.error(f"Erro no callback: {e}")
    
    def send_command(self, command: str, wait_response: bool = True) -> Optional[str]:
        """
        Envia comando para a máquina.
        
        Args:
            command: Comando G-code ou especial
            wait_response: Se deve aguardar resposta
            
        Returns:
            Resposta da máquina ou None
        """
        if not self._connected or not self._serial:
            logger.warning("Não conectado")
            return None
        
        try:
            cmd = command.strip() + "\n"
            self._serial.write(cmd.encode('utf-8'))
            
            if wait_response:
                time.sleep(0.05)
                response = self._serial.readline().decode('utf-8', errors='ignore').strip()
                return response
            
            return "sent"
            
        except Exception as e:
            logger.error(f"Erro ao enviar: {e}")
            return None
    
    def add_response_callback(self, callback: Callable):
        """Adiciona callback para respostas."""
        self._response_callbacks.append(callback)
    
    @property
    def is_connected(self) -> bool:
        return self._connected


class VirtualDriver:
    """
    Driver virtual para testes sem máquina física.
    
    Simula comportamento de CNC plasma.
    """
    
    def __init__(self, config: MachineConfig):
        self.config = config
        self._connected = False
        self._state = MachineState()
        self._gcode_lines: List[str] = []
        self._current_line = 0
        self._running = False
        self._response_callbacks: List[Callable] = []
    
    def connect(self) -> bool:
        """Simula conexão."""
        logger.info(f"[VIRTUAL] Conectando máquina {self.config.name}")
        self._connected = True
        self._state.status = MachineStatus.IDLE
        return True
    
    def disconnect(self):
        """Simula desconexão."""
        self._connected = False
        self._running = False
        self._state.status = MachineStatus.DISCONNECTED
        logger.info("[VIRTUAL] Desconectado")
    
    def send_command(self, command: str, wait_response: bool = True) -> Optional[str]:
        """Simula envio de comando."""
        if not self._connected:
            return None
        
        cmd = command.strip().upper()
        
        # Comandos especiais
        if cmd == '?':
            return self._get_status_report()
        elif cmd == '!':
            self._state.status = MachineStatus.PAUSED
            return "ok"
        elif cmd == '~':
            self._state.status = MachineStatus.RUNNING
            return "ok"
        elif cmd.startswith('$H'):
            self._state.status = MachineStatus.HOMING
            # Simular homing
            self._state.position = MachinePosition()
            self._state.status = MachineStatus.IDLE
            return "ok"
        elif cmd.startswith('G0') or cmd.startswith('G1'):
            # Simular movimento
            self._parse_move(cmd)
            return "ok"
        elif cmd.startswith('M3'):
            self._state.arc_on = True
            return "ok"
        elif cmd.startswith('M5'):
            self._state.arc_on = False
            return "ok"
        
        return "ok"
    
    def _get_status_report(self) -> str:
        """Gera relatório de status GRBL."""
        status = self._state.status.value.capitalize()
        x = self._state.position.x
        y = self._state.position.y
        z = self._state.position.z
        
        return f"<{status}|MPos:{x:.3f},{y:.3f},{z:.3f}|FS:{self._state.feed_rate},0>"
    
    def _parse_move(self, cmd: str):
        """Simula parsing de movimento."""
        import re
        
        x_match = re.search(r'X([-\d.]+)', cmd)
        y_match = re.search(r'Y([-\d.]+)', cmd)
        z_match = re.search(r'Z([-\d.]+)', cmd)
        f_match = re.search(r'F([\d.]+)', cmd)
        
        if x_match:
            self._state.position.x = float(x_match.group(1))
        if y_match:
            self._state.position.y = float(y_match.group(1))
        if z_match:
            self._state.position.z = float(z_match.group(1))
        if f_match:
            self._state.feed_rate = float(f_match.group(1))
    
    def add_response_callback(self, callback: Callable):
        """Adiciona callback."""
        self._response_callbacks.append(callback)
    
    @property
    def is_connected(self) -> bool:
        return self._connected


class MachineController:
    """
    Controlador de máquina CNC.
    
    Gerencia conexão, estado e execução de jobs.
    """
    
    def __init__(self, config: MachineConfig, use_virtual: bool = False):
        self.config = config
        self.use_virtual = use_virtual
        
        # Criar driver apropriado
        if use_virtual:
            self._driver = VirtualDriver(config)
        else:
            self._driver = SerialDriver(config)
        
        self._state = MachineState()
        self._gcode_lines: List[str] = []
        self._execution_thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # Não pausado
        self._stop_flag = False
        
        # Callbacks
        self._state_callbacks: List[Callable] = []
        self._progress_callbacks: List[Callable] = []
        
        # Adicionar callback de resposta
        self._driver.add_response_callback(self._on_response)
    
    def connect(self) -> bool:
        """Conecta à máquina."""
        self._state.status = MachineStatus.CONNECTING
        self._notify_state()
        
        if self._driver.connect():
            self._state.status = MachineStatus.IDLE
            self._notify_state()
            return True
        else:
            self._state.status = MachineStatus.ERROR
            self._state.error_message = "Falha na conexão"
            self._notify_state()
            return False
    
    def disconnect(self):
        """Desconecta da máquina."""
        self.stop()
        self._driver.disconnect()
        self._state.status = MachineStatus.DISCONNECTED
        self._notify_state()
    
    def _on_response(self, response: str):
        """Processa resposta do driver."""
        if response.startswith('<') and response.endswith('>'):
            self._parse_status_report(response)
        elif response == 'ok':
            pass  # Comando aceito
        elif response.startswith('error:'):
            self._state.error_code = int(response.split(':')[1])
            self._state.error_message = f"Erro GRBL: {self._state.error_code}"
            logger.error(self._state.error_message)
        elif response.startswith('ALARM:'):
            self._state.alarm_code = int(response.split(':')[1])
            self._state.alarm_message = f"Alarme: {self._state.alarm_code}"
            self._state.status = MachineStatus.ALARM
            logger.warning(self._state.alarm_message)
    
    def _parse_status_report(self, report: str):
        """Parseia relatório de status GRBL."""
        import re
        
        # Extrair status
        status_match = re.search(r'<(\w+)', report)
        if status_match:
            status_str = status_match.group(1).lower()
            try:
                self._state.status = MachineStatus(status_str)
            except ValueError:
                if status_str == 'run':
                    self._state.status = MachineStatus.RUNNING
                elif status_str == 'hold':
                    self._state.status = MachineStatus.PAUSED
        
        # Extrair posição
        pos_match = re.search(r'MPos:([-\d.]+),([-\d.]+),([-\d.]+)', report)
        if pos_match:
            self._state.position.x = float(pos_match.group(1))
            self._state.position.y = float(pos_match.group(2))
            self._state.position.z = float(pos_match.group(3))
        
        # Extrair feed/speed
        fs_match = re.search(r'FS:(\d+),', report)
        if fs_match:
            self._state.feed_rate = float(fs_match.group(1))
        
        self._notify_state()
    
    def request_status(self):
        """Solicita status da máquina."""
        self._driver.send_command('?', wait_response=False)
    
    def home(self) -> bool:
        """Executa homing da máquina."""
        if self._state.status not in [MachineStatus.IDLE, MachineStatus.ALARM]:
            logger.warning("Máquina não está pronta para homing")
            return False
        
        self._state.status = MachineStatus.HOMING
        self._notify_state()
        
        response = self._driver.send_command('$H')
        
        if response == 'ok':
            self._state.status = MachineStatus.IDLE
            self._state.position = MachinePosition()
            self._notify_state()
            return True
        
        return False
    
    def jog(self, x: float = 0, y: float = 0, z: float = 0, feed: float = 1000):
        """
        Move máquina em modo jog.
        
        Args:
            x, y, z: Distância relativa em mm
            feed: Feed rate em mm/min
        """
        if self._state.status != MachineStatus.IDLE:
            logger.warning("Máquina não está idle")
            return
        
        cmd = f"$J=G91 X{x} Y{y} Z{z} F{feed}"
        self._driver.send_command(cmd, wait_response=False)
    
    def jog_cancel(self):
        """Cancela movimento jog."""
        self._driver.send_command(chr(0x85), wait_response=False)
    
    def load_gcode(self, gcode: str) -> int:
        """
        Carrega G-code para execução.
        
        Args:
            gcode: Programa G-code completo
            
        Returns:
            Número de linhas carregadas
        """
        lines = []
        for line in gcode.split('\n'):
            line = line.strip()
            # Remover comentários
            if ';' in line:
                line = line[:line.index(';')].strip()
            if '(' in line:
                line = line[:line.index('(')].strip()
            if line:
                lines.append(line)
        
        self._gcode_lines = lines
        self._state.total_lines = len(lines)
        self._state.current_line = 0
        self._state.progress_percent = 0
        
        logger.info(f"Carregadas {len(lines)} linhas de G-code")
        return len(lines)
    
    def start(self) -> bool:
        """Inicia execução do G-code."""
        if not self._gcode_lines:
            logger.warning("Nenhum G-code carregado")
            return False
        
        if self._state.status != MachineStatus.IDLE:
            logger.warning("Máquina não está pronta")
            return False
        
        self._stop_flag = False
        self._pause_event.set()
        
        self._execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self._execution_thread.start()
        
        return True
    
    def _execution_loop(self):
        """Loop de execução do G-code."""
        self._state.status = MachineStatus.RUNNING
        self._state.elapsed_time = 0
        start_time = time.time()
        
        self._notify_state()
        
        for i, line in enumerate(self._gcode_lines):
            if self._stop_flag:
                break
            
            # Aguardar se pausado
            self._pause_event.wait()
            
            if self._stop_flag:
                break
            
            # Enviar linha
            response = self._driver.send_command(line)
            
            if response and response.startswith('error'):
                logger.error(f"Erro na linha {i}: {response}")
                self._state.status = MachineStatus.ERROR
                self._notify_state()
                return
            
            # Atualizar progresso
            self._state.current_line = i + 1
            self._state.progress_percent = ((i + 1) / len(self._gcode_lines)) * 100
            self._state.elapsed_time = time.time() - start_time
            
            self._notify_progress()
            
            # Pequeno delay para não sobrecarregar
            time.sleep(0.01)
        
        if not self._stop_flag:
            self._state.status = MachineStatus.IDLE
            self._state.progress_percent = 100
            logger.info(f"Execução concluída em {self._state.elapsed_time:.1f}s")
        else:
            self._state.status = MachineStatus.IDLE
            logger.info("Execução cancelada")
        
        self._notify_state()
    
    def pause(self):
        """Pausa execução."""
        if self._state.status == MachineStatus.RUNNING:
            self._pause_event.clear()
            self._driver.send_command('!', wait_response=False)
            self._state.status = MachineStatus.PAUSED
            self._notify_state()
    
    def resume(self):
        """Retoma execução pausada."""
        if self._state.status == MachineStatus.PAUSED:
            self._pause_event.set()
            self._driver.send_command('~', wait_response=False)
            self._state.status = MachineStatus.RUNNING
            self._notify_state()
    
    def stop(self):
        """Para execução (soft stop)."""
        self._stop_flag = True
        self._pause_event.set()  # Liberar pause para encerrar
        
        # Aguardar thread encerrar
        if self._execution_thread and self._execution_thread.is_alive():
            self._execution_thread.join(timeout=2)
    
    def emergency_stop(self):
        """Parada de emergência."""
        self._stop_flag = True
        self._pause_event.set()
        
        # Enviar reset imediato
        self._driver.send_command(chr(0x18), wait_response=False)  # Ctrl-X
        
        self._state.status = MachineStatus.ALARM
        self._state.alarm_message = "Parada de emergência"
        self._notify_state()
    
    def clear_alarm(self):
        """Limpa alarmes."""
        response = self._driver.send_command('$X')
        if response == 'ok':
            self._state.status = MachineStatus.IDLE
            self._state.alarm_code = 0
            self._state.alarm_message = ""
            self._notify_state()
            return True
        return False
    
    def on_state_change(self, callback: Callable):
        """Registra callback para mudanças de estado."""
        self._state_callbacks.append(callback)
    
    def on_progress(self, callback: Callable):
        """Registra callback para progresso."""
        self._progress_callbacks.append(callback)
    
    def _notify_state(self):
        """Notifica mudança de estado."""
        for cb in self._state_callbacks:
            try:
                cb(self._state)
            except Exception as e:
                logger.error(f"Erro no callback de estado: {e}")
    
    def _notify_progress(self):
        """Notifica progresso."""
        progress = {
            "line": self._state.current_line,
            "total": self._state.total_lines,
            "percent": self._state.progress_percent,
            "elapsed": self._state.elapsed_time
        }
        for cb in self._progress_callbacks:
            try:
                cb(progress)
            except Exception as e:
                logger.error(f"Erro no callback de progresso: {e}")
    
    @property
    def state(self) -> MachineState:
        return self._state
    
    @property
    def is_connected(self) -> bool:
        return self._driver.is_connected


# ═══════════════════════════════════════════════════════════════════════════════
# GERENCIADOR DE MÁQUINAS
# ═══════════════════════════════════════════════════════════════════════════════

class MachineManager:
    """
    Gerenciador de múltiplas máquinas.
    """
    
    def __init__(self, config_path: str = "data/machines"):
        self.config_path = config_path
        self.machines: Dict[str, MachineController] = {}
        self._configs: Dict[str, MachineConfig] = {}
        self._ensure_storage()
        self._load_configs()
    
    def _ensure_storage(self):
        """Cria diretório de configuração."""
        try:
            os.makedirs(self.config_path, exist_ok=True)
        except OSError:
            pass
    
    def _load_configs(self):
        """Carrega configurações salvas."""
        try:
            config_file = os.path.join(self.config_path, "machines.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cfg_data in data.get('machines', []):
                        config = MachineConfig()
                        config.id = cfg_data.get('id', '')
                        config.name = cfg_data.get('name', '')
                        config.connection_type = ConnectionType(cfg_data.get('connection_type', 'serial'))
                        config.port = cfg_data.get('port', '')
                        config.baud_rate = cfg_data.get('baud_rate', 115200)
                        config.ip_address = cfg_data.get('ip_address', '')
                        config.tcp_port = cfg_data.get('tcp_port', 5000)
                        config.max_x = cfg_data.get('max_x', 1500)
                        config.max_y = cfg_data.get('max_y', 3000)
                        config.max_z = cfg_data.get('max_z', 150)
                        
                        self._configs[config.id] = config
        except Exception as e:
            logger.warning(f"Erro ao carregar configs: {e}")
    
    def _save_configs(self):
        """Salva configurações."""
        try:
            config_file = os.path.join(self.config_path, "machines.json")
            data = {
                "machines": [cfg.to_dict() for cfg in self._configs.values()]
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar configs: {e}")
    
    def add_machine(self, 
                    name: str,
                    port: str = "",
                    connection_type: str = "serial",
                    **kwargs) -> MachineConfig:
        """
        Adiciona nova máquina.
        
        Args:
            name: Nome da máquina
            port: Porta serial ou IP
            connection_type: Tipo de conexão
            **kwargs: Outras configurações
        """
        import uuid
        
        config = MachineConfig()
        config.id = str(uuid.uuid4())[:8]
        config.name = name
        config.connection_type = ConnectionType(connection_type)
        config.port = port
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self._configs[config.id] = config
        self._save_configs()
        
        logger.info(f"Máquina adicionada: {config.id} - {name}")
        return config
    
    def remove_machine(self, machine_id: str) -> bool:
        """Remove uma máquina."""
        if machine_id in self.machines:
            self.machines[machine_id].disconnect()
            del self.machines[machine_id]
        
        if machine_id in self._configs:
            del self._configs[machine_id]
            self._save_configs()
            return True
        
        return False
    
    def list_machines(self) -> List[Dict[str, Any]]:
        """Lista máquinas configuradas."""
        machines = []
        for config in self._configs.values():
            status = "disconnected"
            if config.id in self.machines:
                status = self.machines[config.id].state.status.value
            
            machines.append({
                "id": config.id,
                "name": config.name,
                "connection_type": config.connection_type.value,
                "port": config.port,
                "status": status
            })
        
        return machines
    
    def connect(self, machine_id: str, use_virtual: bool = False) -> bool:
        """Conecta a uma máquina."""
        if machine_id not in self._configs:
            logger.error(f"Máquina não encontrada: {machine_id}")
            return False
        
        config = self._configs[machine_id]
        controller = MachineController(config, use_virtual=use_virtual)
        
        if controller.connect():
            self.machines[machine_id] = controller
            return True
        
        return False
    
    def disconnect(self, machine_id: str):
        """Desconecta de uma máquina."""
        if machine_id in self.machines:
            self.machines[machine_id].disconnect()
            del self.machines[machine_id]
    
    def get_controller(self, machine_id: str) -> Optional[MachineController]:
        """Retorna controlador de uma máquina."""
        return self.machines.get(machine_id)
    
    def scan_ports(self) -> List[Dict[str, str]]:
        """
        Escaneia portas seriais disponíveis.
        
        Returns:
            Lista de portas encontradas
        """
        try:
            import serial.tools.list_ports
            
            ports = []
            for port in serial.tools.list_ports.comports():
                ports.append({
                    "port": port.device,
                    "description": port.description,
                    "manufacturer": port.manufacturer or ""
                })
            
            return ports
            
        except ImportError:
            logger.warning("pyserial não instalado")
            return []
        except Exception as e:
            logger.error(f"Erro ao escanear portas: {e}")
            return []


# Instância global
_machine_manager: Optional[MachineManager] = None


def get_machine_manager() -> MachineManager:
    """Retorna instância do gerenciador de máquinas."""
    global _machine_manager
    if _machine_manager is None:
        _machine_manager = MachineManager()
    return _machine_manager


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS FastAPI
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter(prefix="/api/machines", tags=["Machines"])


class AddMachineRequest(BaseModel):
    """Request para adicionar máquina."""
    name: str = Field(..., min_length=1, max_length=100)
    connection_type: str = Field(default="serial")
    port: str = Field(default="")
    ip_address: str = Field(default="")
    tcp_port: int = Field(default=5000)
    baud_rate: int = Field(default=115200)
    max_x: float = Field(default=1500)
    max_y: float = Field(default=3000)
    max_z: float = Field(default=150)


class JogRequest(BaseModel):
    """Request para movimento jog."""
    x: float = Field(default=0)
    y: float = Field(default=0)
    z: float = Field(default=0)
    feed: float = Field(default=1000, gt=0)


class LoadGcodeRequest(BaseModel):
    """Request para carregar G-code."""
    gcode: str = Field(..., min_length=1)


class SendCommandRequest(BaseModel):
    """Request para enviar comando."""
    command: str = Field(..., min_length=1)


@router.get("/")
async def list_machines():
    """Lista todas as máquinas configuradas."""
    manager = get_machine_manager()
    machines = manager.list_machines()
    
    return {
        "success": True,
        "machines": machines
    }


@router.post("/")
async def add_machine(request: AddMachineRequest):
    """Adiciona uma nova máquina."""
    manager = get_machine_manager()
    
    config = manager.add_machine(
        name=request.name,
        port=request.port,
        connection_type=request.connection_type,
        ip_address=request.ip_address,
        tcp_port=request.tcp_port,
        baud_rate=request.baud_rate,
        max_x=request.max_x,
        max_y=request.max_y,
        max_z=request.max_z
    )
    
    return {
        "success": True,
        "machine": config.to_dict()
    }


@router.delete("/{machine_id}")
async def remove_machine(machine_id: str):
    """Remove uma máquina."""
    manager = get_machine_manager()
    
    if not manager.remove_machine(machine_id):
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    
    return {
        "success": True,
        "message": "Máquina removida"
    }


@router.post("/{machine_id}/connect")
async def connect_machine(
    machine_id: str,
    virtual: bool = Query(False, description="Usar driver virtual para testes")
):
    """Conecta a uma máquina."""
    manager = get_machine_manager()
    
    if manager.connect(machine_id, use_virtual=virtual):
        return {
            "success": True,
            "message": "Conectado com sucesso"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Falha ao conectar. Verifique a porta e configurações."
        )


@router.post("/{machine_id}/disconnect")
async def disconnect_machine(machine_id: str):
    """Desconecta de uma máquina."""
    manager = get_machine_manager()
    manager.disconnect(machine_id)
    
    return {
        "success": True,
        "message": "Desconectado"
    }


@router.get("/{machine_id}/status")
async def get_machine_status(machine_id: str):
    """Retorna status atual da máquina."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    controller.request_status()
    
    return {
        "success": True,
        "status": controller.state.to_dict()
    }


@router.post("/{machine_id}/home")
async def home_machine(machine_id: str):
    """Executa homing da máquina."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    if controller.home():
        return {
            "success": True,
            "message": "Homing concluído",
            "position": controller.state.position.to_dict()
        }
    else:
        raise HTTPException(status_code=500, detail="Falha no homing")


@router.post("/{machine_id}/jog")
async def jog_machine(machine_id: str, request: JogRequest):
    """Movimento jog da máquina."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    controller.jog(request.x, request.y, request.z, request.feed)
    
    return {
        "success": True,
        "message": "Jog iniciado"
    }


@router.post("/{machine_id}/jog/cancel")
async def cancel_jog(machine_id: str):
    """Cancela movimento jog."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    controller.jog_cancel()
    
    return {
        "success": True,
        "message": "Jog cancelado"
    }


@router.post("/{machine_id}/gcode/load")
async def load_gcode(machine_id: str, request: LoadGcodeRequest):
    """Carrega G-code para execução."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    lines = controller.load_gcode(request.gcode)
    
    return {
        "success": True,
        "lines": lines,
        "message": f"Carregadas {lines} linhas de G-code"
    }


@router.post("/{machine_id}/start")
async def start_execution(machine_id: str):
    """Inicia execução do G-code."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    if controller.start():
        return {
            "success": True,
            "message": "Execução iniciada"
        }
    else:
        raise HTTPException(status_code=400, detail="Não foi possível iniciar. Verifique se há G-code carregado.")


@router.post("/{machine_id}/pause")
async def pause_execution(machine_id: str):
    """Pausa execução."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    controller.pause()
    
    return {
        "success": True,
        "message": "Execução pausada"
    }


@router.post("/{machine_id}/resume")
async def resume_execution(machine_id: str):
    """Retoma execução."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    controller.resume()
    
    return {
        "success": True,
        "message": "Execução retomada"
    }


@router.post("/{machine_id}/stop")
async def stop_execution(machine_id: str):
    """Para execução."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    controller.stop()
    
    return {
        "success": True,
        "message": "Execução parada"
    }


@router.post("/{machine_id}/emergency")
async def emergency_stop(machine_id: str):
    """Parada de emergência."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    controller.emergency_stop()
    
    return {
        "success": True,
        "message": "Parada de emergência ativada"
    }


@router.post("/{machine_id}/clear-alarm")
async def clear_alarm(machine_id: str):
    """Limpa alarmes."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    if controller.clear_alarm():
        return {
            "success": True,
            "message": "Alarme limpo"
        }
    else:
        raise HTTPException(status_code=500, detail="Não foi possível limpar o alarme")


@router.post("/{machine_id}/command")
async def send_command(machine_id: str, request: SendCommandRequest):
    """Envia comando manual para a máquina."""
    manager = get_machine_manager()
    controller = manager.get_controller(machine_id)
    
    if not controller:
        raise HTTPException(status_code=404, detail="Máquina não conectada")
    
    response = controller._driver.send_command(request.command)
    
    return {
        "success": True,
        "command": request.command,
        "response": response
    }


@router.get("/ports/scan")
async def scan_ports():
    """Escaneia portas seriais disponíveis."""
    manager = get_machine_manager()
    ports = manager.scan_ports()
    
    return {
        "success": True,
        "ports": ports
    }
