#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD — AutoCAD Hybrid Driver (Nível 4: Operador Direto + Ponte de Rede)
Driver híbrido que opera em dois modos:

  MODO COM (Direto)  — Controla o AutoCAD na mesma máquina via COM/OLE.
  MODO PONTE (Rede)  — Gera arquivos .lsp em pasta compartilhada para que
                        o AutoCAD remoto (PC B com script vigilante) execute.

═══════════════════════════════════════════════════════════════════════════════

ARQUITETURA:
    ┌─── Modo COM (local) ───────────────────────────────────────────────┐
    │  FastAPI ──→ autocad_driver.py ──→ AutoCAD.Application (COM)       │
    └────────────────────────────────────────────────────────────────────┘
    ┌─── Modo Ponte (rede) ──────────────────────────────────────────────┐
    │  FastAPI ──→ autocad_driver.py ──→ buffer LISP ──→ Z:/Drop/*.lsp  │
    │                                                        │           │
    │                              PC B (Vigilante AutoLISP) ◄           │
    └────────────────────────────────────────────────────────────────────┘

REGRAS:
    - AutoCAD é single-threaded: toda chamada COM exige CoInitialize()
    - Conexão COM é recuperável: se perder, reconecta automaticamente
    - Modo Ponte: buffer acumula comandos AutoLISP → commit() grava .lsp
    - Todas as operações retornam DriverResult para rastreabilidade
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engcad.autocad_driver")

# ─── Importação condicional do win32com (só disponível no Windows) ───────────
_COM_AVAILABLE = False
try:
    import pythoncom
    import win32com.client
    _COM_AVAILABLE = True
except ImportError:
    logger.warning("pywin32 não instalado — AutoCAD Driver operará em modo simulação")


# ═══════════════════════════════════════════════════════════════════════════════
# TIPOS E CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

class DriverStatus(str, Enum):
    DISCONNECTED = "Disconnected"
    CONNECTED = "Connected"
    RECOVERING = "Recovering"
    SIMULATION = "Simulation"
    BRIDGE = "Bridge"
    ERROR = "Error"


class CADEngine(str, Enum):
    AUTOCAD = "AutoCAD"
    GSTARCAD = "GstarCAD"
    UNKNOWN = "Unknown"


# ── Mapeamento de ProgIDs COM para cada engine ──────────────────────────────
_ENGINE_PROGIDS: Dict[CADEngine, List[str]] = {
    CADEngine.AUTOCAD: ["AutoCAD.Application"],
    CADEngine.GSTARCAD: ["Gcad.Application", "GstarCAD.Application"],
}

# ── Normalização de constantes entre AutoCAD e GstarCAD ─────────────────────
# Algumas constantes COM têm nomes diferentes entre os dois engines.
# Este mapeamento traduz nomes canônicos (AutoCAD) para equivalentes GstarCAD.
_ACAD_CONST_ALIASES: Dict[str, Dict[CADEngine, Any]] = {
    "acRed":              {CADEngine.AUTOCAD: 1, CADEngine.GSTARCAD: 1},
    "acYellow":           {CADEngine.AUTOCAD: 2, CADEngine.GSTARCAD: 2},
    "acGreen":            {CADEngine.AUTOCAD: 3, CADEngine.GSTARCAD: 3},
    "acCyan":             {CADEngine.AUTOCAD: 4, CADEngine.GSTARCAD: 4},
    "acBlue":             {CADEngine.AUTOCAD: 5, CADEngine.GSTARCAD: 5},
    "acMagenta":          {CADEngine.AUTOCAD: 6, CADEngine.GSTARCAD: 6},
    "acWhite":            {CADEngine.AUTOCAD: 7, CADEngine.GSTARCAD: 7},
    # Regen type: AutoCAD usa acActiveViewport=0 / acAllViewports=1
    # GstarCAD pode usar constantes numéricas equivalentes
    "acActiveViewport":   {CADEngine.AUTOCAD: 0, CADEngine.GSTARCAD: 0},
    "acAllViewports":     {CADEngine.AUTOCAD: 1, CADEngine.GSTARCAD: 1},
    # Linetype load file: AutoCAD usa 'acad.lin', GstarCAD usa 'gcad.lin'
    "linetypeFile":       {CADEngine.AUTOCAD: "acad.lin", CADEngine.GSTARCAD: "gcad.lin"},
}


# Norma N-58 Petrobras — cores padrão por layer
N58_LAYER_SPEC: Dict[str, Dict[str, Any]] = {
    "PIPE-PROCESS":     {"color": 1, "linetype": "Continuous", "lineweight": 0.50},  # Vermelho
    "PIPE-UTILITY":     {"color": 3, "linetype": "Continuous", "lineweight": 0.35},  # Verde
    "PIPE-INSTRUMENT":  {"color": 6, "linetype": "DASHED",     "lineweight": 0.25},  # Magenta — Instrumentação (N-58)
    "EQUIP-VESSEL":     {"color": 4, "linetype": "Continuous", "lineweight": 0.70},  # Cyan — Equipamentos (N-58)
    "EQUIP-PUMP":       {"color": 4, "linetype": "Continuous", "lineweight": 0.50},  # Cyan — Equipamentos (N-58)
    "VALVE":            {"color": 6, "linetype": "Continuous", "lineweight": 0.50},  # Magenta
    "FLANGE":           {"color": 4, "linetype": "Continuous", "lineweight": 0.35},  # Cyan
    "SUPPORT":          {"color": 8, "linetype": "CENTER",     "lineweight": 0.25},  # Cinza
    "ANNOTATION":       {"color": 7, "linetype": "Continuous", "lineweight": 0.18},  # Branco
    "DIMENSION":        {"color": 7, "linetype": "Continuous", "lineweight": 0.18},  # Branco
    "ISOMETRIC":        {"color": 150,"linetype": "Continuous", "lineweight": 0.25},
}

MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY_S = 2.0

# Número máximo de tentativas de escrita na pasta de rede
BRIDGE_WRITE_RETRIES = 3
BRIDGE_WRITE_RETRY_DELAY_S = 1.0


@dataclass
class DriverResult:
    """Resultado padronizado de qualquer operação do Driver."""
    success: bool
    operation: str
    status: str = ""
    message: str = ""
    entity_handle: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "operation": self.operation,
            "status": self.status,
            "message": self.message,
            "entity_handle": self.entity_handle,
            "details": self.details,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DRIVER PRINCIPAL — HÍBRIDO (COM + PONTE)
# ═══════════════════════════════════════════════════════════════════════════════

class AutoCADDriver:
    """
    Operador híbrido do AutoCAD: COM direto OU Ponte de Rede (AutoLISP).

    Modo COM (use_bridge=False):
        Thread-safe, cada operação inicializa COM na thread atual.
        Recuperável: reconecta automaticamente se o AutoCAD cair.

    Modo Ponte (use_bridge=True):
        Acumula comandos AutoLISP em self.command_buffer.
        commit() grava o buffer como .lsp na pasta de rede (bridge_path).
        O script vigilante no PC B detecta e executa o .lsp no AutoCAD.
    """

    def __init__(self):
        # ── Estado COM (modo direto) ──
        self._acad = None
        self._doc = None
        self._model = None
        self._status = DriverStatus.DISCONNECTED
        self._engine = CADEngine.UNKNOWN
        self._lock = threading.Lock()
        self._stats = {
            "operations_total": 0,
            "operations_success": 0,
            "operations_failed": 0,
            "reconnections": 0,
            "bridge_commits": 0,
            "bridge_commands_sent": 0,
            "last_error": None,
        }

        # ── Modo Ponte (rede) ──
        self.use_bridge: bool = True
        self.bridge_path: str = os.getenv("AUTOCAD_BRIDGE_PATH", "")
        self.command_buffer: List[str] = []
        self._layers_emitted: set = set()    # Layers já emitidos no buffer atual
        self._session_layers_initialized: bool = False  # Auto-criar layers no 1º connect()

    # ─── Propriedades ────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        if self.use_bridge:
            return DriverStatus.BRIDGE.value
        return self._status.value

    @property
    def is_connected(self) -> bool:
        if self.use_bridge:
            return bool(self.bridge_path)
        return self._status == DriverStatus.CONNECTED

    @property
    def engine_name(self) -> str:
        """Retorna o nome do engine CAD detectado."""
        return self._engine.value

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "status": self.status,
            "engine": self.engine_name,
            "mode": "bridge" if self.use_bridge else "com",
            "bridge_path": self.bridge_path,
            "buffer_size": len(self.command_buffer),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO DA PONTE
    # ═══════════════════════════════════════════════════════════════════════

    def set_bridge_path(self, path: str) -> DriverResult:
        """Define o caminho da pasta de rede onde o Vigilante espera os .lsp."""
        path = path.strip()
        if not path:
            return DriverResult(
                success=False,
                operation="set_bridge_path",
                status=self.status,
                message="Caminho da ponte não pode ser vazio",
            )

        # Validação adicional na camada do driver (defesa em profundidade)
        normalized = os.path.normpath(os.path.abspath(path))
        if ".." in path or "\x00" in path:
            logger.warning("Tentativa de path traversal bloqueada: %s", path[:100])
            return DriverResult(
                success=False,
                operation="set_bridge_path",
                status=self.status,
                message="Caminho inválido — caracteres proibidos",
            )

        accessible = os.path.isdir(normalized)
        self.bridge_path = normalized

        if accessible:
            logger.info("Bridge path configurado e acessível: %s", path)
        else:
            logger.warning("Bridge path configurado mas INACESSÍVEL no momento: %s", path)

        return DriverResult(
            success=True,
            operation="set_bridge_path",
            status=self.status,
            message=f"Ponte configurada: {path}" + ("" if accessible else " (inacessível agora — será validado no commit)"),
            details={"path": path, "accessible": accessible},
        )

    def set_mode(self, use_bridge: bool) -> DriverResult:
        """Alterna entre modo COM direto e modo Ponte."""
        old_mode = "bridge" if self.use_bridge else "com"
        self.use_bridge = use_bridge
        new_mode = "bridge" if self.use_bridge else "com"
        logger.info("Modo alterado: %s → %s", old_mode, new_mode)
        return DriverResult(
            success=True,
            operation="set_mode",
            status=self.status,
            message=f"Modo alterado para: {new_mode.upper()}",
            details={"mode": new_mode, "bridge_path": self.bridge_path},
        )

    # ═══════════════════════════════════════════════════════════════════════
    # BRIDGE — Geração de AutoLISP
    # ═══════════════════════════════════════════════════════════════════════

    def _lisp_ensure_layer(self, layer_name: str) -> None:
        """Emite comandos LISP para criar/ativar um layer N-58 no buffer."""
        if layer_name in self._layers_emitted:
            return
        spec = N58_LAYER_SPEC.get(layer_name, {})
        color = spec.get("color", 7)
        # -LAYER Make cria o layer se não existir e o torna corrente
        self.command_buffer.append(
            f'(command "-LAYER" "M" "{layer_name}" "C" "{color}" "{layer_name}" "")'
        )
        lt = spec.get("linetype", "Continuous")
        if lt != "Continuous":
            # Carrega linetype e atribui ao layer
            self.command_buffer.append(
                f'(command "-LINETYPE" "L" "{lt}" "{self.linetype_file}" "" "")'
            )
            self.command_buffer.append(
                f'(command "-LAYER" "LT" "{lt}" "{layer_name}" "")'
            )
        self._layers_emitted.add(layer_name)

    @staticmethod
    def _fmt_pt(coords: List[float]) -> str:
        """Formata coordenada para string LISP: '10.0,20.0,0.0'."""
        x = float(coords[0])
        y = float(coords[1])
        z = float(coords[2]) if len(coords) >= 3 else 0.0
        return f"{x},{y},{z}"

    def _bridge_draw_line(self, start: List[float], end: List[float], layer: str) -> DriverResult:
        """Modo Ponte: empilha _LINE no buffer."""
        self._lisp_ensure_layer(layer)
        self.command_buffer.append(
            f'(command "_LINE" "{self._fmt_pt(start)}" "{self._fmt_pt(end)}" "")'
        )
        self._stats["operations_total"] += 1
        self._stats["operations_success"] += 1
        return DriverResult(
            success=True,
            operation="draw_line",
            status=DriverStatus.BRIDGE.value,
            message=f"[PONTE] Linha adicionada ao buffer ({len(self.command_buffer)} cmds)",
            details={"start": start, "end": end, "layer": layer},
        )

    def _bridge_draw_pipe(self, points: List[List[float]], diameter: float, layer: str) -> DriverResult:
        """Modo Ponte: empilha _PLINE contínua no buffer."""
        self._lisp_ensure_layer(layer)
        parts = [f'(command "_PLINE"']
        for pt in points:
            parts.append(f' "{self._fmt_pt(pt)}"')
        parts.append(' "")')
        self.command_buffer.append("".join(parts))
        # Comentário de rastreamento com diâmetro
        self.command_buffer.append(f';; Tubulação Ø{diameter}" — {len(points)} pontos — Layer: {layer}')
        self._stats["operations_total"] += 1
        self._stats["operations_success"] += 1
        return DriverResult(
            success=True,
            operation="draw_pipe",
            status=DriverStatus.BRIDGE.value,
            message=f"[PONTE] Tubulação {diameter}\" adicionada ao buffer ({len(self.command_buffer)} cmds)",
            details={"points_count": len(points), "diameter": diameter, "layer": layer},
        )

    def _bridge_insert_component(self, block_name: str, coordinate: List[float],
                                  rotation: float, scale: float, layer: str) -> DriverResult:
        """Modo Ponte: empilha _-INSERT no buffer."""
        self._lisp_ensure_layer(layer)
        pt = self._fmt_pt(coordinate)
        self.command_buffer.append(
            f'(command "_-INSERT" "{block_name}" "{pt}" {scale} {scale} {rotation})'
        )
        self._stats["operations_total"] += 1
        self._stats["operations_success"] += 1
        return DriverResult(
            success=True,
            operation="insert_component",
            status=DriverStatus.BRIDGE.value,
            message=f"[PONTE] Bloco '{block_name}' adicionado ao buffer",
            details={"block_name": block_name, "coordinate": coordinate,
                     "rotation_deg": rotation, "scale": scale, "layer": layer},
        )

    def _bridge_add_text(self, text: str, position: List[float], height: float, layer: str) -> DriverResult:
        """Modo Ponte: empilha _TEXT no buffer."""
        self._lisp_ensure_layer(layer)
        pt = self._fmt_pt(position)
        # Escapar barras invertidas e aspas no texto para AutoLISP
        safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
        self.command_buffer.append(
            f'(command "_TEXT" "{pt}" {height} 0 "{safe_text}")'
        )
        self._stats["operations_total"] += 1
        self._stats["operations_success"] += 1
        return DriverResult(
            success=True,
            operation="add_text",
            status=DriverStatus.BRIDGE.value,
            message=f"[PONTE] Texto '{text[:30]}' adicionado ao buffer",
            details={"text": text, "position": position, "height": height, "layer": layer},
        )

    def _bridge_create_layer_system(self) -> DriverResult:
        """Modo Ponte: emite todos os layers N-58 no buffer."""
        for layer_name in N58_LAYER_SPEC:
            self._lisp_ensure_layer(layer_name)
        self._stats["operations_total"] += 1
        self._stats["operations_success"] += 1
        return DriverResult(
            success=True,
            operation="create_layer_system",
            status=DriverStatus.BRIDGE.value,
            message=f"[PONTE] {len(N58_LAYER_SPEC)} layers N-58 adicionados ao buffer",
            details={"layers": list(N58_LAYER_SPEC.keys())},
        )

    def commit(self) -> DriverResult:
        """
        Grava o conteúdo do buffer AutoLISP como arquivo .lsp na pasta de rede.
        Nome único: job_<timestamp_ms>.lsp para evitar conflitos.
        Inclui retry robusto caso a rede esteja temporariamente indisponível.
        """
        with self._lock:
            if not self.bridge_path:
                return DriverResult(
                    success=False,
                    operation="commit",
                    status=DriverStatus.BRIDGE.value,
                    message="Bridge path não configurado. Use POST /api/autocad/config/bridge",
                )

            if not self.command_buffer:
                return DriverResult(
                    success=True,
                    operation="commit",
                    status=DriverStatus.BRIDGE.value,
                    message="Buffer vazio — nada para enviar",
                    details={"commands": 0},
                )

            filename = f"job_{int(time.time() * 1000)}.lsp"
            full_path = os.path.join(self.bridge_path, filename)

            # Montar conteúdo .lsp
            header = (
                f";; ═══════════════════════════════════════════════════════════\n"
                f";; Engenharia CAD — Script Gerado Automaticamente\n"
                f";; Arquivo: {filename}\n"
                f";; Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f";; Comandos: {len(self.command_buffer)}\n"
                f";; ═══════════════════════════════════════════════════════════\n\n"
            )
            body = "\n".join(self.command_buffer)
            footer = (
                "\n\n;; ── Fim do script Engenharia CAD ──\n"
                '(princ "\\n[Engenharia CAD] Script executado com sucesso.")\n'
                "(princ)\n"
            )
            content = header + body + footer

            # Tentativas de escrita com retry
            last_error = None
            for attempt in range(1, BRIDGE_WRITE_RETRIES + 1):
                try:
                    # Verificar acessibilidade da pasta
                    if not os.path.isdir(self.bridge_path):
                        raise OSError(f"Pasta de rede inacessível: {self.bridge_path}")

                    # Escrever em arquivo temporário e renomear (atômico)
                    tmp_path = full_path + ".tmp"
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    os.replace(tmp_path, full_path)

                    cmd_count = len(self.command_buffer)
                    self.command_buffer.clear()
                    self._layers_emitted.clear()
                    self._stats["bridge_commits"] += 1
                    self._stats["bridge_commands_sent"] += cmd_count

                    logger.info("Bridge commit: %s (%d cmds)", filename, cmd_count)
                    return DriverResult(
                        success=True,
                        operation="commit",
                        status=DriverStatus.BRIDGE.value,
                        message=f"Enviado para ponte: {filename} ({cmd_count} comandos)",
                        details={
                            "filename": filename,
                            "path": full_path,
                            "commands": cmd_count,
                            "size_bytes": len(content),
                        },
                    )
                except OSError as exc:
                    last_error = str(exc)
                    logger.warning(
                        "Falha ao gravar na ponte (tentativa %d/%d): %s",
                        attempt, BRIDGE_WRITE_RETRIES, exc,
                    )
                    if attempt < BRIDGE_WRITE_RETRIES:
                        time.sleep(BRIDGE_WRITE_RETRY_DELAY_S)

            # Todas as tentativas falharam — NÃO limpa o buffer (preserva os dados)
            self._stats["operations_failed"] += 1
            self._stats["last_error"] = last_error
            return DriverResult(
                success=False,
                operation="commit",
                status=DriverStatus.ERROR.value,
                message=f"Falha ao gravar na rede após {BRIDGE_WRITE_RETRIES} tentativas: {last_error}",
                details={
                    "bridge_path": self.bridge_path,
                    "buffer_preserved": True,
                    "buffer_size": len(self.command_buffer),
                },
            )

    # ─── Contexto COM thread-safe ────────────────────────────────────────

    @contextmanager
    def _com_context(self):
        """Inicializa/finaliza COM na thread atual — obrigatório para FastAPI."""
        if not _COM_AVAILABLE:
            yield
            return
        pythoncom.CoInitialize()
        try:
            yield
        finally:
            pythoncom.CoUninitialize()

    # ─── Conexão ─────────────────────────────────────────────────────────

    def connect(self) -> DriverResult:
        """Conecta ao AutoCAD ativo ou inicia uma nova instância."""
        if self.use_bridge:
            accessible = bool(self.bridge_path) and os.path.isdir(self.bridge_path)
            result = DriverResult(
                success=True,
                operation="connect",
                status=DriverStatus.BRIDGE.value,
                message=f"Modo Ponte ativo — bridge: {self.bridge_path or '(não configurado)'}",
                details={"mode": "bridge", "bridge_path": self.bridge_path, "accessible": accessible},
            )
            # Auto-criar layers N-58 no primeiro connect() da sessão
            if not self._session_layers_initialized:
                self.create_layer_system()
                self._session_layers_initialized = True
                result.details["layers_auto_created"] = True
            return result
        with self._lock:
            result = self._connect_internal()
            # Auto-criar layers N-58 no primeiro connect() COM bem-sucedido
            if result.success and not self._session_layers_initialized:
                self.create_layer_system()
                self._session_layers_initialized = True
                result.details["layers_auto_created"] = True
            return result

    def _connect_internal(self) -> DriverResult:
        if not _COM_AVAILABLE:
            self._status = DriverStatus.SIMULATION
            logger.info("Modo simulação ativo (pywin32 não disponível)")
            return DriverResult(
                success=True,
                operation="connect",
                status=DriverStatus.SIMULATION.value,
                message="Driver em modo simulação — pywin32 não instalado",
            )

        with self._com_context():
            # Tentar cada engine (AutoCAD primeiro, depois GstarCAD)
            for engine, progids in _ENGINE_PROGIDS.items():
                for progid in progids:
                    # 1) Tentar capturar instância ativa
                    try:
                        self._acad = win32com.client.GetActiveObject(progid)
                        self._acad.Visible = True
                        self._doc = self._acad.ActiveDocument
                        self._model = self._doc.ModelSpace
                        self._status = DriverStatus.CONNECTED
                        self._engine = engine
                        logger.info("Conectado a %s ativo (ProgID=%s): %s", engine.value, progid, self._doc.Name)
                        return DriverResult(
                            success=True,
                            operation="connect",
                            status=DriverStatus.CONNECTED.value,
                            message=f"Conectado a {engine.value}: {self._doc.Name}",
                            details={"engine": engine.value, "progid": progid},
                        )
                    except Exception:
                        logger.debug("GetActiveObject('%s') falhou — tentando próximo", progid)

            # 2) Nenhuma instância ativa — tentar Dispatch em ordem
            for engine, progids in _ENGINE_PROGIDS.items():
                for progid in progids:
                    try:
                        self._acad = win32com.client.Dispatch(progid)
                        self._acad.Visible = True
                        # Aguardar inicialização
                        for _ in range(30):
                            try:
                                self._doc = self._acad.ActiveDocument
                                break
                            except Exception:
                                time.sleep(1)
                        else:
                            self._doc = self._acad.Documents.Add()

                        self._model = self._doc.ModelSpace
                        self._status = DriverStatus.CONNECTED
                        self._engine = engine
                        logger.info("Nova instância %s iniciada (ProgID=%s): %s", engine.value, progid, self._doc.Name)
                        return DriverResult(
                            success=True,
                            operation="connect",
                            status=DriverStatus.CONNECTED.value,
                            message=f"Nova instância {engine.value} iniciada: {self._doc.Name}",
                            details={"engine": engine.value, "progid": progid},
                        )
                    except Exception as exc:
                        logger.debug("Dispatch('%s') falhou: %s", progid, exc)
                        continue

            # 3) Nenhum engine disponível
            self._status = DriverStatus.ERROR
            self._engine = CADEngine.UNKNOWN
            msg = "Nenhum CAD encontrado (AutoCAD / GstarCAD)"
            self._stats["last_error"] = msg
            logger.error(msg)
            return DriverResult(
                success=False,
                operation="connect",
                status=DriverStatus.ERROR.value,
                message=msg,
            )

    def disconnect(self) -> DriverResult:
        """Libera a referência COM sem fechar o CAD."""
        with self._lock:
            prev_engine = self._engine.value
            self._acad = None
            self._doc = None
            self._model = None
            self._status = DriverStatus.DISCONNECTED
            self._engine = CADEngine.UNKNOWN
            logger.info("Driver desconectado de %s", prev_engine)
            return DriverResult(
                success=True,
                operation="disconnect",
                status=DriverStatus.DISCONNECTED.value,
                message=f"Driver desconectado de {prev_engine}",
            )

    def _ensure_connection(self) -> bool:
        """Verifica conexão e reconecta se necessário. Retorna True se conectado."""
        if self._status == DriverStatus.SIMULATION:
            return True

        if self._status == DriverStatus.CONNECTED:
            # Validar que a conexão ainda está viva
            try:
                _ = self._doc.Name
                return True
            except Exception:
                logger.warning("Conexão COM perdida — tentando reconectar")
                self._status = DriverStatus.RECOVERING

        # Reconectar
        self._status = DriverStatus.RECOVERING
        self._stats["reconnections"] += 1

        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            logger.info("Tentativa de reconexão %d/%d", attempt, MAX_RECONNECT_ATTEMPTS)
            result = self._connect_internal()
            if result.success and self._status == DriverStatus.CONNECTED:
                return True
            time.sleep(RECONNECT_DELAY_S)

        self._status = DriverStatus.ERROR
        return False

    def _execute(self, operation: str, fn, *args, **kwargs) -> DriverResult:
        """Executa uma operação COM com tratamento de erro e reconexão."""
        with self._lock:
            self._stats["operations_total"] += 1

            if not self._ensure_connection():
                self._stats["operations_failed"] += 1
                return DriverResult(
                    success=False,
                    operation=operation,
                    status=self._status.value,
                    message="AutoCAD indisponível após tentativas de reconexão",
                )

            if self._status == DriverStatus.SIMULATION:
                self._stats["operations_success"] += 1
                return DriverResult(
                    success=True,
                    operation=operation,
                    status=DriverStatus.SIMULATION.value,
                    message=f"[SIMULAÇÃO] {operation} executado com sucesso",
                    details={"args": str(args), "kwargs": str(kwargs)},
                )

            with self._com_context():
                try:
                    result = fn(*args, **kwargs)
                    self._stats["operations_success"] += 1
                    return result
                except Exception as exc:
                    self._stats["operations_failed"] += 1
                    self._stats["last_error"] = str(exc)
                    logger.error("Erro em %s: %s", operation, exc, exc_info=True)

                    # Tentar recuperar conexão para próxima operação
                    self._status = DriverStatus.RECOVERING
                    return DriverResult(
                        success=False,
                        operation=operation,
                        status=DriverStatus.RECOVERING.value,
                        message=f"Falha em {operation}: {exc}",
                    )

    # ═══════════════════════════════════════════════════════════════════════
    # GEOMETRIA — Métodos de alto nível para a IA (HÍBRIDOS)
    # ═══════════════════════════════════════════════════════════════════════

    def _variant_point(self, coords: List[float]):
        """Converte [x, y, z] para VARIANT(VT_ARRAY|VT_R8) do COM."""
        if len(coords) == 2:
            coords = [coords[0], coords[1], 0.0]
        return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, coords)

    def _variant_points(self, flat_coords: List[float]):
        """Converte lista plana [x1,y1,z1, x2,y2,z2, ...] para VARIANT."""
        return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_coords)

    def draw_pipe(
        self,
        points: List[List[float]],
        diameter: float = 6.0,
        layer: str = "PIPE-PROCESS",
    ) -> DriverResult:
        """
        Desenha uma tubulação como polyline.
        Modo COM: AddLightWeightPolyline / Add3DPoly via COM.
        Modo Ponte: _PLINE contínua no buffer AutoLISP.
        """
        if len(points) < 2:
            return DriverResult(
                success=False,
                operation="draw_pipe",
                status=self.status,
                message="Mínimo de 2 pontos necessários para desenhar tubulação",
            )

        if self.use_bridge:
            return self._bridge_draw_pipe(points, diameter, layer)

        def _do_draw():
            # Garantir layer existe
            self._ensure_layer(layer)

            # Verificar se todos os pontos são 3D
            is_3d = any(len(p) >= 3 and p[2] != 0 for p in points)

            if is_3d:
                # 3D Polyline — via flat array de pontos
                flat = []
                for p in points:
                    flat.extend([float(p[0]), float(p[1]), float(p[2]) if len(p) >= 3 else 0.0])
                pts_var = self._variant_points(flat)
                entity = self._model.Add3DPoly(pts_var)
            else:
                # Lightweight 2D Polyline
                flat = []
                for p in points:
                    flat.extend([float(p[0]), float(p[1])])
                pts_var = self._variant_points(flat)
                entity = self._model.AddLightWeightPolyline(pts_var)

            entity.Layer = layer
            handle = entity.Handle

            # Adicionar XData com diâmetro (metadado rastreável)
            try:
                app_name = "ENGCAD"
                self._doc.RegisteredApplications.Add(app_name)
            except Exception:
                pass  # Já registrado

            xdata_type = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_I2, [1001, 1040]
            )
            xdata_val = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, ["ENGCAD", diameter]
            )
            entity.SetXData(xdata_type, xdata_val)

            return DriverResult(
                success=True,
                operation="draw_pipe",
                status=DriverStatus.CONNECTED.value,
                message=f"Tubulação {diameter}\" desenhada com {len(points)} pontos",
                entity_handle=handle,
                details={"points_count": len(points), "diameter": diameter, "layer": layer, "3d": is_3d},
            )

        return self._execute("draw_pipe", _do_draw)

    def draw_line(
        self,
        start: List[float],
        end: List[float],
        layer: str = "PIPE-PROCESS",
    ) -> DriverResult:
        """
        Desenha uma linha simples.
        Modo COM: AddLine via COM.
        Modo Ponte: _LINE no buffer AutoLISP.
        """
        if self.use_bridge:
            return self._bridge_draw_line(start, end, layer)

        def _do_draw():
            self._ensure_layer(layer)
            start_p = self._variant_point(start)
            end_p = self._variant_point(end)
            entity = self._model.AddLine(start_p, end_p)
            entity.Layer = layer
            return DriverResult(
                success=True,
                operation="draw_line",
                status=DriverStatus.CONNECTED.value,
                message="Linha desenhada",
                entity_handle=entity.Handle,
                details={"start": start, "end": end, "layer": layer},
            )

        return self._execute("draw_line", _do_draw)

    def insert_component(
        self,
        block_name: str,
        coordinate: List[float],
        rotation: float = 0.0,
        scale: float = 1.0,
        layer: str = "VALVE",
    ) -> DriverResult:
        """
        Insere um bloco (válvula, flange, etc.).
        Modo COM: InsertBlock via COM.
        Modo Ponte: _-INSERT no buffer AutoLISP.
        """
        if self.use_bridge:
            return self._bridge_insert_component(block_name, coordinate, rotation, scale, layer)

        def _do_insert():
            self._ensure_layer(layer)
            pos = self._variant_point(coordinate)
            rotation_rad = math.radians(rotation)

            entity = self._model.InsertBlock(
                pos, block_name, scale, scale, scale, rotation_rad
            )
            entity.Layer = layer
            return DriverResult(
                success=True,
                operation="insert_component",
                status=DriverStatus.CONNECTED.value,
                message=f"Bloco '{block_name}' inserido em {coordinate}",
                entity_handle=entity.Handle,
                details={
                    "block_name": block_name,
                    "coordinate": coordinate,
                    "rotation_deg": rotation,
                    "scale": scale,
                    "layer": layer,
                },
            )

        return self._execute("insert_component", _do_insert)

    def add_text(
        self,
        text: str,
        position: List[float],
        height: float = 2.5,
        layer: str = "ANNOTATION",
    ) -> DriverResult:
        """
        Adiciona texto de anotação.
        Modo COM: AddText via COM.
        Modo Ponte: _TEXT no buffer AutoLISP.
        """
        if self.use_bridge:
            return self._bridge_add_text(text, position, height, layer)

        def _do_text():
            self._ensure_layer(layer)
            pos = self._variant_point(position)
            entity = self._model.AddText(text, pos, height)
            entity.Layer = layer
            return DriverResult(
                success=True,
                operation="add_text",
                status=DriverStatus.CONNECTED.value,
                message=f"Texto adicionado: '{text[:30]}'",
                entity_handle=entity.Handle,
                details={"text": text, "position": position, "height": height, "layer": layer},
            )

        return self._execute("add_text", _do_text)

    # ═══════════════════════════════════════════════════════════════════════
    # NORMA N-58 — Sistema de Layers
    # ═══════════════════════════════════════════════════════════════════════

    def create_layer_system(self) -> DriverResult:
        """
        Cria todos os layers padrão N-58 Petrobras.
        Modo COM: cria diretamente via COM.
        Modo Ponte: emite comandos -LAYER no buffer AutoLISP.
        """
        if self.use_bridge:
            return self._bridge_create_layer_system()

        def _do_layers():
            layers_created = []
            for layer_name, spec in N58_LAYER_SPEC.items():
                self._ensure_layer(layer_name)
                layers_created.append(layer_name)

            return DriverResult(
                success=True,
                operation="create_layer_system",
                status=DriverStatus.CONNECTED.value,
                message=f"Sistema N-58 aplicado: {len(layers_created)} layers criados",
                details={"layers": layers_created},
            )

        return self._execute("create_layer_system", _do_layers)

    def _ensure_layer(self, layer_name: str):
        """Cria o layer se não existir, aplicando spec N-58 (modo COM)."""
        try:
            layer = self._doc.Layers.Add(layer_name)
            spec = N58_LAYER_SPEC.get(layer_name, {})
            if "color" in spec:
                layer.Color = spec["color"]
            if "lineweight" in spec:
                # AutoCAD lineweight em centésimos de mm
                lw_mm = spec["lineweight"]
                lw_code = int(lw_mm * 100)
                layer.Lineweight = lw_code
            # Linetypes precisam ser carregadas antes de atribuir
            if "linetype" in spec and spec["linetype"] != "Continuous":
                try:
                    self._doc.Linetypes.Load(spec["linetype"], self.linetype_file)
                except Exception:
                    pass  # Já carregado
                try:
                    layer.Linetype = spec["linetype"]
                except Exception:
                    pass  # Linetype não disponível, manter Continuous
        except Exception:
            pass  # Layer já existe — OK

    # ═══════════════════════════════════════════════════════════════════════
    # FINALIZAÇÃO VISUAL — O "Gran Finale" (HÍBRIDO)
    # ═══════════════════════════════════════════════════════════════════════

    def zoom_extents(self) -> DriverResult:
        """Enquadra a vista em toda a geometria do desenho."""
        if self.use_bridge:
            self.command_buffer.append('(command "_ZOOM" "E")')
            return DriverResult(
                success=True, operation="zoom_extents",
                status=DriverStatus.BRIDGE.value,
                message="[PONTE] Zoom Extents adicionado ao buffer",
            )

        def _do_zoom():
            self._acad.ZoomExtents()
            return DriverResult(
                success=True,
                operation="zoom_extents",
                status=DriverStatus.CONNECTED.value,
                message="Vista enquadrada em ZoomExtents",
            )

        return self._execute("zoom_extents", _do_zoom)

    def regen(self) -> DriverResult:
        """Força regeneração completa da tela do AutoCAD."""
        if self.use_bridge:
            self.command_buffer.append('(command "_REGEN")')
            return DriverResult(
                success=True, operation="regen",
                status=DriverStatus.BRIDGE.value,
                message="[PONTE] Regen adicionado ao buffer",
            )

        def _do_regen():
            # acRegenTypeAllViewports = 0
            self._doc.Regen(0)
            return DriverResult(
                success=True,
                operation="regen",
                status=DriverStatus.CONNECTED.value,
                message="Regeneração completa executada",
            )

        return self._execute("regen", _do_regen)

    def finalize_view(self) -> DriverResult:
        """
        O 'Gran Finale': Zoom Extents + Regen.
        Modo COM: executa diretamente + pausa dramática.
        Modo Ponte: adiciona ao buffer + chama commit() → grava .lsp.
        """
        if self.use_bridge:
            self.command_buffer.append('(command "_ZOOM" "E")')
            self.command_buffer.append('(command "_REGEN")')
            return self.commit()

        def _do_finalize():
            self._acad.ZoomExtents()
            time.sleep(0.3)
            self._doc.Regen(0)
            return DriverResult(
                success=True,
                operation="finalize_view",
                status=DriverStatus.CONNECTED.value,
                message="Projeto apresentado — Gran Finale executado",
            )

        return self._execute("finalize_view", _do_finalize)

    # ═══════════════════════════════════════════════════════════════════════
    # UTILITÁRIOS
    # ═══════════════════════════════════════════════════════════════════════

    def send_command(self, command: str) -> DriverResult:
        """Envia um comando de texto direto ao AutoCAD (ex: LISP, comandos nativos)."""
        if self.use_bridge:
            self.command_buffer.append(command)
            return DriverResult(
                success=True,
                operation="send_command",
                status=DriverStatus.BRIDGE.value,
                message=f"[PONTE] Comando adicionado ao buffer: {command[:60]}",
            )

        def _do_cmd():
            self._doc.SendCommand(command + "\n")
            return DriverResult(
                success=True,
                operation="send_command",
                status=DriverStatus.CONNECTED.value,
                message=f"Comando enviado: {command[:60]}",
            )

        return self._execute("send_command", _do_cmd)

    def save_document(self) -> DriverResult:
        """Salva o documento ativo (só funciona em modo COM)."""
        if self.use_bridge:
            self.command_buffer.append('(command "_QSAVE")')
            return DriverResult(
                success=True,
                operation="save_document",
                status=DriverStatus.BRIDGE.value,
                message="[PONTE] QSAVE adicionado ao buffer",
            )

        def _do_save():
            self._doc.Save()
            return DriverResult(
                success=True,
                operation="save_document",
                status=DriverStatus.CONNECTED.value,
                message=f"Documento salvo: {self._doc.FullName}",
            )

        return self._execute("save_document", _do_save)

    def get_const(self, name: str) -> Any:
        """Retorna o valor normalizado de uma constante CAD para o engine ativo."""
        if name in _ACAD_CONST_ALIASES:
            engine = self._engine if self._engine != CADEngine.UNKNOWN else CADEngine.AUTOCAD
            return _ACAD_CONST_ALIASES[name].get(engine, _ACAD_CONST_ALIASES[name].get(CADEngine.AUTOCAD))
        return None

    @property
    def linetype_file(self) -> str:
        """Retorna o arquivo de linetype correto para o engine ativo."""
        return self.get_const("linetypeFile") or "acad.lin"

    def health_check(self) -> dict:
        """Retorna diagnóstico completo para o ai_watchdog."""
        result = {
            "driver_status": self.status,
            "engine": self.engine_name,
            "mode": "bridge" if self.use_bridge else "com",
            "com_available": _COM_AVAILABLE,
            "stats": {**self._stats},
            "document": None,
        }

        if self.use_bridge:
            result["bridge"] = {
                "path": self.bridge_path,
                "accessible": bool(self.bridge_path) and os.path.isdir(self.bridge_path),
                "buffer_size": len(self.command_buffer),
            }
        elif self._status == DriverStatus.CONNECTED:
            try:
                with self._com_context():
                    result["document"] = {
                        "name": self._doc.Name,
                        "path": self._doc.FullName,
                        "saved": self._doc.Saved,
                    }
            except Exception as exc:
                result["driver_status"] = DriverStatus.RECOVERING.value
                result["connection_error"] = str(exc)

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# INSTÂNCIA SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

# Instância global — importar de qualquer módulo
acad_driver = AutoCADDriver()
