#!/usr/bin/env python3
"""
Engenharia CAD — Hardware Identity (HWID) Module
Gera um fingerprint único da máquina combinando Serial da Placa-Mãe + CPU ID.
Usado tanto no Agente Local quanto no Servidor Central para licenciamento.

Segurança:
    - O hash é SHA-256 one-way (não reversível)
    - Não transmite dados brutos de hardware, apenas o hash derivado
    - Salt fixo por aplicação para evitar rainbow tables
"""

from __future__ import annotations

import hashlib
import logging
import platform
import subprocess
from typing import Optional

logger = logging.getLogger("engcad.hwid")

# Salt único do Engenharia CAD — evita que o mesmo hardware gere o mesmo hash
# em aplicações diferentes (proteção contra rainbow tables)
_APP_SALT = "EngenhariaCAD-V1-HWID-2026"


def _run_wmic(query: str) -> str:
    """Executa uma consulta WMIC e retorna a saída limpa."""
    try:
        result = subprocess.run(
            ["wmic"] + query.split(),
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )
        lines = [
            line.strip()
            for line in result.stdout.strip().splitlines()
            if line.strip() and line.strip().lower() not in ("serialnumber", "processorid")
        ]
        return lines[0] if lines else ""
    except Exception as exc:
        logger.warning("WMIC query falhou (%s): %s", query, exc)
        return ""


def _get_motherboard_serial() -> str:
    """Obtém o serial da placa-mãe via WMIC."""
    return _run_wmic("baseboard get serialnumber")


def _get_cpu_id() -> str:
    """Obtém o ProcessorId via WMIC."""
    return _run_wmic("cpu get processorid")


def generate_hwid() -> str:
    """
    Gera um HWID único combinando placa-mãe + CPU.
    Retorna hash SHA-256 hex (64 caracteres).

    Se não conseguir obter dados de hardware (ex: Linux, VM),
    gera um fallback baseado no hostname + platform.
    """
    mb_serial = _get_motherboard_serial()
    cpu_id = _get_cpu_id()

    # Fallback para ambientes sem WMIC (Linux, containers, VMs)
    if not mb_serial and not cpu_id:
        logger.warning("WMIC indisponível — usando fallback (hostname + platform)")
        mb_serial = platform.node()
        cpu_id = platform.processor() or platform.machine()

    raw = f"{_APP_SALT}|{mb_serial}|{cpu_id}"
    hwid = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    logger.info("HWID gerado: %s...%s", hwid[:8], hwid[-8:])
    return hwid


def validate_hwid(stored_hwid: str, incoming_hwid: str) -> bool:
    """Compara HWIDs usando comparação de tempo constante (anti-timing attack)."""
    import hmac
    return hmac.compare_digest(stored_hwid, incoming_hwid)
