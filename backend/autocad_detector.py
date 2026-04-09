#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD — AutoCAD Detection Service (Nível Enterprise)

Detecta, lança e conecta automaticamente ao AutoCAD/GstarCAD no computador.
Inspirado nas melhores práticas de:
  - Autodesk Platform Services
  - SolidWorks API Connection Manager
  - Bentley MicroStation ConnectSDK

═══════════════════════════════════════════════════════════════════════════════

FUNCIONALIDADES:
  1. Detectar instalações de CAD (Registry + filesystem)
  2. Verificar se CAD está em execução
  3. Lançar CAD automaticamente
  4. Aguardar inicialização completa
  5. Conectar via COM e validar conexão
  6. Auto-carregar LSP de automação
  7. Retornar status detalhado

USO:
    detector = AutoCADDetector()
    result = detector.detect_and_launch()  # Detecta, lança e conecta
    result = detector.quick_status()       # Apenas verifica status atual

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("engcad.autocad_detector")

# ── Importação condicional para Windows ──────────────────────────────────────
_WIN32_AVAILABLE = False
_WINREG_AVAILABLE = False

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    pass

try:
    import win32com.client
    import pythoncom
    import psutil
    _WIN32_AVAILABLE = True
except ImportError:
    logger.info("Módulos Windows não disponíveis - modo cloud/simulação")


# ═══════════════════════════════════════════════════════════════════════════════
# TIPOS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

class CADType(str, Enum):
    AUTOCAD = "AutoCAD"
    GSTARCAD = "GstarCAD"
    BRICSCAD = "BricsCAD"
    ZWCAD = "ZWCAD"
    UNKNOWN = "Unknown"


class DetectionStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLED_NOT_RUNNING = "installed_not_running"
    RUNNING_NOT_CONNECTED = "running_not_connected"
    CONNECTED = "connected"
    LAUNCHING = "launching"
    ERROR = "error"


@dataclass
class CADInstallation:
    """Representa uma instalação de CAD detectada no sistema."""
    cad_type: CADType
    version: str
    exe_path: str
    installed_date: Optional[str] = None
    progid: Optional[str] = None
    is_64bit: bool = True
    
    def to_dict(self) -> dict:
        return {
            "type": self.cad_type.value,
            "version": self.version,
            "exe_path": self.exe_path,
            "progid": self.progid,
            "is_64bit": self.is_64bit,
        }


@dataclass 
class DetectionResult:
    """Resultado completo de uma operação de detecção/conexão."""
    success: bool
    status: DetectionStatus
    message: str
    installations: List[CADInstallation] = field(default_factory=list)
    active_installation: Optional[CADInstallation] = None
    process_id: Optional[int] = None
    document_name: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "installations": [i.to_dict() for i in self.installations],
            "active_installation": self.active_installation.to_dict() if self.active_installation else None,
            "process_id": self.process_id,
            "document_name": self.document_name,
            "details": self.details,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class AutoCADDetector:
    """
    Serviço de detecção e lançamento de AutoCAD/CAD compatíveis.
    
    Padrão Enterprise: Detecta todas as instalações, permite escolher,
    lança automaticamente, aguarda inicialização, conecta via COM.
    """
    
    # Caminhos padrão de instalação
    _AUTOCAD_PATHS = [
        r"C:\Program Files\Autodesk\AutoCAD 2025",
        r"C:\Program Files\Autodesk\AutoCAD 2024",
        r"C:\Program Files\Autodesk\AutoCAD 2023",
        r"C:\Program Files\Autodesk\AutoCAD 2022",
        r"C:\Program Files\Autodesk\AutoCAD 2021",
        r"C:\Program Files\Autodesk\AutoCAD 2020",
        r"C:\Program Files\Autodesk\AutoCAD LT 2025",
        r"C:\Program Files\Autodesk\AutoCAD LT 2024",
        r"C:\Program Files\Autodesk\AutoCAD LT 2023",
    ]
    
    _GSTARCAD_PATHS = [
        r"C:\Program Files\Gstarsoft\GstarCAD 2024",
        r"C:\Program Files\Gstarsoft\GstarCAD 2023",
        r"C:\Program Files\Gstarsoft\GstarCAD 2022",
        r"C:\Program Files\Gstarsoft\GstarCAD Pro",
    ]
    
    # ProgIDs para conexão COM
    _PROGIDS = {
        CADType.AUTOCAD: ["AutoCAD.Application", "AutoCAD.Application.24", "AutoCAD.Application.23"],
        CADType.GSTARCAD: ["Gcad.Application", "GstarCAD.Application"],
    }
    
    # Nomes de processos
    _PROCESS_NAMES = {
        CADType.AUTOCAD: ["acad.exe", "acadlt.exe"],
        CADType.GSTARCAD: ["gcad.exe"],
    }
    
    def __init__(self, lsp_path: Optional[str] = None, drop_path: Optional[str] = None):
        """
        Inicializa o detector.
        
        Args:
            lsp_path: Caminho do forge_vigilante.lsp para auto-carregar
            drop_path: Pasta onde os comandos .lsp serão gravados
        """
        self.lsp_path = lsp_path or r"C:\EngenhariaCAD\forge_vigilante.lsp"
        self.drop_path = drop_path or r"C:\AutoCAD_Drop"
        self._installations: List[CADInstallation] = []
        self._com_app = None
        self._com_doc = None
        
    # ─── Detecção ────────────────────────────────────────────────────────────
    
    def scan_installations(self) -> List[CADInstallation]:
        """Escaneia o sistema em busca de instalações de CAD."""
        self._installations = []
        
        if not _WINREG_AVAILABLE:
            logger.info("Windows Registry não disponível - retornando lista vazia")
            return []
        
        # 1. Busca por caminhos padrão
        self._scan_standard_paths()
        
        # 2. Busca no Registry
        self._scan_registry()
        
        # 3. Remove duplicatas
        seen_paths = set()
        unique = []
        for inst in self._installations:
            if inst.exe_path.lower() not in seen_paths:
                seen_paths.add(inst.exe_path.lower())
                unique.append(inst)
        
        self._installations = unique
        logger.info(f"Detectadas {len(self._installations)} instalações de CAD")
        
        return self._installations
    
    def _scan_standard_paths(self):
        """Verifica caminhos padrão de instalação."""
        # AutoCAD
        for base_path in self._AUTOCAD_PATHS:
            exe_path = os.path.join(base_path, "acad.exe")
            if os.path.isfile(exe_path):
                version = self._extract_version_from_path(base_path)
                self._installations.append(CADInstallation(
                    cad_type=CADType.AUTOCAD,
                    version=version,
                    exe_path=exe_path,
                    progid="AutoCAD.Application",
                ))
        
        # GstarCAD
        for base_path in self._GSTARCAD_PATHS:
            exe_path = os.path.join(base_path, "gcad.exe")
            if os.path.isfile(exe_path):
                version = self._extract_version_from_path(base_path)
                self._installations.append(CADInstallation(
                    cad_type=CADType.GSTARCAD,
                    version=version,
                    exe_path=exe_path,
                    progid="Gcad.Application",
                ))
    
    def _scan_registry(self):
        """Busca instalações no Windows Registry."""
        if not _WINREG_AVAILABLE:
            return
            
        # AutoCAD Registry keys
        autocad_keys = [
            r"SOFTWARE\Autodesk\AutoCAD",
            r"SOFTWARE\WOW6432Node\Autodesk\AutoCAD",
        ]
        
        for key_path in autocad_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey_path = f"{key_path}\\{subkey_name}"
                            self._scan_autocad_version_key(subkey_path)
                            i += 1
                        except OSError:
                            break
            except OSError:
                pass
    
    def _scan_autocad_version_key(self, key_path: str):
        """Escaneia uma chave de versão específica do AutoCAD."""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        version_path = f"{key_path}\\{subkey_name}"
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, version_path) as version_key:
                            try:
                                location, _ = winreg.QueryValueEx(version_key, "Location")
                                exe_path = os.path.join(location, "acad.exe")
                                if os.path.isfile(exe_path):
                                    version = self._extract_version_from_path(location)
                                    self._installations.append(CADInstallation(
                                        cad_type=CADType.AUTOCAD,
                                        version=version,
                                        exe_path=exe_path,
                                        progid="AutoCAD.Application",
                                    ))
                            except OSError:
                                pass
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
    
    @staticmethod
    def _extract_version_from_path(path: str) -> str:
        """Extrai versão do caminho de instalação (ex: 'AutoCAD 2024' → '2024')."""
        import re
        match = re.search(r'(\d{4})', path)
        return match.group(1) if match else "Unknown"
    
    # ─── Status do Processo ──────────────────────────────────────────────────
    
    def is_cad_running(self) -> tuple[bool, Optional[int], Optional[CADType]]:
        """
        Verifica se algum CAD está em execução.
        
        Returns:
            (is_running, process_id, cad_type)
        """
        if not _WIN32_AVAILABLE:
            return False, None, None
            
        for cad_type, proc_names in self._PROCESS_NAMES.items():
            for proc_name in proc_names:
                for proc in psutil.process_iter(['name', 'pid']):
                    try:
                        if proc.info['name'].lower() == proc_name.lower():
                            return True, proc.info['pid'], cad_type
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        
        return False, None, None
    
    def is_connected(self) -> bool:
        """Verifica se há conexão COM ativa."""
        if not self._com_app:
            return False
        try:
            _ = self._com_doc.Name
            return True
        except Exception:
            return False
    
    # ─── Lançamento e Conexão ────────────────────────────────────────────────
    
    def launch_cad(self, installation: Optional[CADInstallation] = None, 
                   wait_seconds: int = 60) -> DetectionResult:
        """
        Lança o CAD e aguarda inicialização.
        
        Args:
            installation: Instalação específica a lançar (ou usa a primeira disponível)
            wait_seconds: Tempo máximo para aguardar inicialização
            
        Returns:
            DetectionResult com status do lançamento
        """
        if not _WIN32_AVAILABLE:
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message="Ambiente Windows não disponível",
            )
        
        # Verificar se já está rodando
        is_running, pid, cad_type = self.is_cad_running()
        if is_running:
            logger.info(f"{cad_type.value} já está em execução (PID: {pid})")
            return DetectionResult(
                success=True,
                status=DetectionStatus.RUNNING_NOT_CONNECTED,
                message=f"{cad_type.value} já em execução",
                process_id=pid,
            )
        
        # Escolher instalação
        if not installation:
            if not self._installations:
                self.scan_installations()
            if not self._installations:
                return DetectionResult(
                    success=False,
                    status=DetectionStatus.NOT_INSTALLED,
                    message="Nenhum CAD instalado encontrado",
                )
            installation = self._installations[0]
        
        # Lançar o processo
        logger.info(f"Lançando {installation.cad_type.value} {installation.version}...")
        
        try:
            proc = subprocess.Popen(
                [installation.exe_path],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # Aguardar inicialização
            started = time.time()
            while time.time() - started < wait_seconds:
                is_running, pid, _ = self.is_cad_running()
                if is_running:
                    # Aguardar mais um pouco para o COM estar disponível
                    time.sleep(5)
                    logger.info(f"{installation.cad_type.value} iniciado com sucesso (PID: {pid})")
                    return DetectionResult(
                        success=True,
                        status=DetectionStatus.RUNNING_NOT_CONNECTED,
                        message=f"{installation.cad_type.value} {installation.version} iniciado",
                        active_installation=installation,
                        process_id=pid,
                    )
                time.sleep(2)
            
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message=f"Timeout aguardando {installation.cad_type.value} inicializar",
            )
            
        except Exception as e:
            logger.error(f"Erro ao lançar CAD: {e}")
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message=f"Erro ao lançar: {str(e)}",
            )
    
    def connect_com(self, installation: Optional[CADInstallation] = None) -> DetectionResult:
        """
        Conecta ao CAD via COM.
        
        Args:
            installation: Instalação específica (para determinar ProgID)
            
        Returns:
            DetectionResult com status da conexão
        """
        if not _WIN32_AVAILABLE:
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message="pywin32 não disponível",
            )
        
        pythoncom.CoInitialize()
        
        try:
            # Determinar ProgIDs a tentar
            if installation:
                progids = [installation.progid] if installation.progid else self._PROGIDS.get(installation.cad_type, [])
            else:
                # Tentar todos os ProgIDs conhecidos
                progids = []
                for pids in self._PROGIDS.values():
                    progids.extend(pids)
            
            # Tentar cada ProgID
            for progid in progids:
                try:
                    # Primeiro tentar conectar a instância existente
                    self._com_app = win32com.client.GetActiveObject(progid)
                    self._com_app.Visible = True
                    self._com_doc = self._com_app.ActiveDocument
                    
                    doc_name = self._com_doc.Name if self._com_doc else "Sem documento"
                    
                    logger.info(f"Conectado via COM (ProgID: {progid}): {doc_name}")
                    
                    return DetectionResult(
                        success=True,
                        status=DetectionStatus.CONNECTED,
                        message=f"Conectado ao CAD: {doc_name}",
                        document_name=doc_name,
                        details={"progid": progid},
                    )
                    
                except Exception as e:
                    logger.debug(f"ProgID {progid} falhou: {e}")
                    continue
            
            return DetectionResult(
                success=False,
                status=DetectionStatus.RUNNING_NOT_CONNECTED,
                message="CAD em execução mas conexão COM falhou",
            )
            
        except Exception as e:
            logger.error(f"Erro na conexão COM: {e}")
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message=f"Erro COM: {str(e)}",
            )
        finally:
            pythoncom.CoUninitialize()
    
    def load_automation_lsp(self) -> DetectionResult:
        """
        Carrega o forge_vigilante.lsp no CAD conectado.
        
        Returns:
            DetectionResult com status do carregamento
        """
        if not self.is_connected():
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message="Não conectado ao CAD",
            )
        
        # Verificar se o LSP existe
        if not os.path.isfile(self.lsp_path):
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message=f"LSP não encontrado: {self.lsp_path}",
            )
        
        try:
            pythoncom.CoInitialize()
            
            # Carregar o LSP via APPLOAD
            lsp_path_escaped = self.lsp_path.replace("\\", "/")
            self._com_doc.SendCommand(f'(load "{lsp_path_escaped}") ')
            time.sleep(1)
            
            # Iniciar o vigilante
            self._com_doc.SendCommand("(FORGE_START) ")
            time.sleep(1)
            
            logger.info("LSP carregado e FORGE_START executado")
            
            return DetectionResult(
                success=True,
                status=DetectionStatus.CONNECTED,
                message="Automação LSP carregada com sucesso",
                details={
                    "lsp_path": self.lsp_path,
                    "forge_start": True,
                },
            )
            
        except Exception as e:
            logger.error(f"Erro ao carregar LSP: {e}")
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message=f"Erro ao carregar LSP: {str(e)}",
            )
        finally:
            pythoncom.CoUninitialize()
    
    def setup_drop_folder(self) -> DetectionResult:
        """Configura a pasta de drop para comandos LSP."""
        try:
            os.makedirs(self.drop_path, exist_ok=True)
            os.makedirs(os.path.dirname(self.lsp_path), exist_ok=True)
            
            return DetectionResult(
                success=True,
                status=DetectionStatus.CONNECTED,
                message="Pastas de automação configuradas",
                details={
                    "drop_path": self.drop_path,
                    "lsp_folder": os.path.dirname(self.lsp_path),
                },
            )
        except Exception as e:
            return DetectionResult(
                success=False,
                status=DetectionStatus.ERROR,
                message=f"Erro ao criar pastas: {str(e)}",
            )
    
    # ─── Operações de Alto Nível ─────────────────────────────────────────────
    
    def detect_and_launch(self, auto_connect: bool = True, 
                          auto_load_lsp: bool = True) -> DetectionResult:
        """
        Operação completa: detecta, lança, conecta e carrega automação.
        
        Este é o método principal que deve ser chamado pelo frontend
        quando o usuário clica em "Conectar ao AutoCAD".
        
        Args:
            auto_connect: Se True, conecta automaticamente via COM
            auto_load_lsp: Se True, carrega o LSP de automação
            
        Returns:
            DetectionResult com status completo
        """
        # 1. Escanear instalações
        installations = self.scan_installations()
        
        if not installations:
            return DetectionResult(
                success=False,
                status=DetectionStatus.NOT_INSTALLED,
                message="Nenhum AutoCAD ou CAD compatível encontrado",
                installations=[],
            )
        
        # 2. Verificar se já está rodando ou lançar
        is_running, pid, cad_type = self.is_cad_running()
        
        if not is_running:
            # Lançar o primeiro CAD disponível
            launch_result = self.launch_cad(installations[0])
            if not launch_result.success:
                return launch_result
            pid = launch_result.process_id
        
        result = DetectionResult(
            success=True,
            status=DetectionStatus.RUNNING_NOT_CONNECTED,
            message="CAD em execução",
            installations=installations,
            process_id=pid,
        )
        
        # 3. Conectar via COM
        if auto_connect:
            connect_result = self.connect_com(installations[0])
            if connect_result.success:
                result.status = DetectionStatus.CONNECTED
                result.message = connect_result.message
                result.document_name = connect_result.document_name
                result.details.update(connect_result.details)
                
                # 4. Configurar pastas
                self.setup_drop_folder()
                
                # 5. Carregar LSP
                if auto_load_lsp and os.path.isfile(self.lsp_path):
                    lsp_result = self.load_automation_lsp()
                    result.details["lsp_loaded"] = lsp_result.success
                    result.details["lsp_message"] = lsp_result.message
        
        return result
    
    def quick_status(self) -> DetectionResult:
        """
        Retorna status rápido sem tentar lançar ou conectar.
        
        Útil para o frontend mostrar status atual.
        """
        installations = self.scan_installations()
        is_running, pid, cad_type = self.is_cad_running()
        
        if not installations:
            return DetectionResult(
                success=False,
                status=DetectionStatus.NOT_INSTALLED,
                message="Nenhum CAD instalado",
                installations=[],
            )
        
        if not is_running:
            return DetectionResult(
                success=True,
                status=DetectionStatus.INSTALLED_NOT_RUNNING,
                message=f"{len(installations)} instalação(ões) de CAD encontrada(s)",
                installations=installations,
            )
        
        # Tentar conectar para verificar
        try:
            connect_result = self.connect_com()
            if connect_result.success:
                return DetectionResult(
                    success=True,
                    status=DetectionStatus.CONNECTED,
                    message=f"Conectado: {connect_result.document_name}",
                    installations=installations,
                    process_id=pid,
                    document_name=connect_result.document_name,
                )
        except Exception:
            pass
        
        return DetectionResult(
            success=True,
            status=DetectionStatus.RUNNING_NOT_CONNECTED,
            message=f"{cad_type.value if cad_type else 'CAD'} em execução (PID: {pid})",
            installations=installations,
            process_id=pid,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# INSTÂNCIA GLOBAL (singleton)
# ═══════════════════════════════════════════════════════════════════════════════

cad_detector = AutoCADDetector()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    detector = AutoCADDetector()
    
    print("\n=== Escaneando instalações ===")
    installations = detector.scan_installations()
    for inst in installations:
        print(f"  - {inst.cad_type.value} {inst.version}: {inst.exe_path}")
    
    print("\n=== Status rápido ===")
    status = detector.quick_status()
    print(f"  Status: {status.status.value}")
    print(f"  Mensagem: {status.message}")
    
    print("\n=== Operação completa ===")
    result = detector.detect_and_launch()
    print(f"  Sucesso: {result.success}")
    print(f"  Status: {result.status.value}")
    print(f"  Mensagem: {result.message}")
