#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
ENGENHARIA CAD — Validador de Comandos AutoCAD
═══════════════════════════════════════════════════════════════════════════════

Whitelist de comandos permitidos para prevenir command injection.
Valida e sanitiza comandos antes de enviar ao AutoCAD.
"""

import re
import logging
from typing import Set, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger("engcad.cad_command_validator")


# ═══════════════════════════════════════════════════════════════════════════════
# WHITELIST DE COMANDOS AUTOCAD PERMITIDOS
# ═══════════════════════════════════════════════════════════════════════════════

# Comandos de desenho básicos
DRAWING_COMMANDS: Set[str] = {
    "line", "pline", "polyline", "circle", "arc", "ellipse",
    "rectangle", "polygon", "spline", "xline", "ray",
    "point", "donut", "helix", "region", "boundary",
}

# Comandos de modificação
MODIFY_COMMANDS: Set[str] = {
    "move", "copy", "rotate", "scale", "mirror", "stretch",
    "trim", "extend", "break", "join", "fillet", "chamfer",
    "offset", "array", "explode", "pedit", "splinedit",
    "lengthen", "align", "erase", "undo", "redo",
}

# Comandos de visualização (seguros)
VIEW_COMMANDS: Set[str] = {
    "zoom", "pan", "orbit", "regen", "regenall", "redraw",
    "view", "vpoint", "dview", "3dorbit", "viewres",
}

# Comandos de layer e propriedades
LAYER_COMMANDS: Set[str] = {
    "layer", "-layer", "la", "layerstate", "laymch",
    "laycur", "layoff", "layon", "layiso", "layfrz", "laythw",
    "color", "linetype", "lineweight", "properties", "matchprop",
}

# Comandos de texto e anotação
ANNOTATION_COMMANDS: Set[str] = {
    "text", "mtext", "dtext", "style", "dim", "dimstyle",
    "leader", "mleader", "hatch", "bhatch", "gradient",
    "table", "tabledit", "field",
}

# Comandos de blocos
BLOCK_COMMANDS: Set[str] = {
    "block", "-block", "insert", "-insert", "wblock",
    "bedit", "bclose", "battman", "refedit", "refset",
}

# Comandos de salvamento (controlados)
SAVE_COMMANDS: Set[str] = {
    "save", "saveas", "qsave",
}

# Comandos LISP e scripts (BLOQUEADOS por segurança)
BLOCKED_COMMANDS: Set[str] = {
    # Execução de código
    "lisp", "script", "appload", "arx", "arxload", "arxunload",
    "vbaide", "vbaload", "vbaman", "vbarun", "vbaunload",
    "netload", "pyload",
    # Comandos de sistema
    "shell", "sh", "start", "startapp",
    # File system perigosos
    "open", "new", "recover", "recover", "audit",
    # Rede e comunicação
    "etransmit", "publish", "exportpdf",
    # Comandos internos perigosos
    "setenv", "getenv", "sysvdlg", "options",
}

# Todos os comandos permitidos (união de todas as categorias)
ALLOWED_COMMANDS: Set[str] = (
    DRAWING_COMMANDS |
    MODIFY_COMMANDS |
    VIEW_COMMANDS |
    LAYER_COMMANDS |
    ANNOTATION_COMMANDS |
    BLOCK_COMMANDS |
    SAVE_COMMANDS
)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE PARÂMETROS
# ═══════════════════════════════════════════════════════════════════════════════

# Regex para parâmetros válidos de comando (números, coordenadas, strings simples)
# Permite: números, coordenadas (x,y ou x,y,z), nomes de layer/block, @relativo
VALID_PARAM_PATTERN = re.compile(
    r'^('
    r'[\d\.\-\,\s\@]+|'              # Números, coordenadas, @relativo
    r'[a-zA-Z_][a-zA-Z0-9_\-]*|'     # Identificadores (nomes de layer, block)
    r'"[^"]{0,100}"|'                # Strings entre aspas (max 100 chars)
    r'#[0-9a-fA-F]{6}'               # Cores hex
    r')$'
)

# Caracteres perigosos que nunca devem aparecer em comandos
DANGEROUS_CHARS = re.compile(r'[;|&`$\(\)\{\}\[\]<>\\]')

# Tamanho máximo de comando
MAX_COMMAND_LENGTH = 500


@dataclass
class ValidationResult:
    """Resultado da validação de comando."""
    valid: bool
    command: str
    sanitized_command: str
    error: Optional[str] = None
    warning: Optional[str] = None


def extract_command_name(command: str) -> str:
    """
    Extrai o nome do comando (primeira palavra).
    
    Args:
        command: Comando completo
        
    Returns:
        Nome do comando em minúsculas
    """
    command = command.strip()
    # Comandos podem começar com - (ex: -layer)
    if command.startswith("-"):
        parts = command[1:].split()
        if parts:
            return "-" + parts[0].lower()
    
    parts = command.split()
    return parts[0].lower() if parts else ""


def validate_command(command: str) -> ValidationResult:
    """
    Valida e sanitiza um comando AutoCAD.
    
    Args:
        command: Comando a validar
        
    Returns:
        ValidationResult com status e comando sanitizado
    """
    # Sanitização básica
    command = command.strip()
    
    # Verificar tamanho
    if len(command) > MAX_COMMAND_LENGTH:
        return ValidationResult(
            valid=False,
            command=command,
            sanitized_command="",
            error=f"Comando muito longo (max {MAX_COMMAND_LENGTH} caracteres)"
        )
    
    # Verificar caracteres perigosos
    if DANGEROUS_CHARS.search(command):
        dangerous = DANGEROUS_CHARS.findall(command)
        return ValidationResult(
            valid=False,
            command=command,
            sanitized_command="",
            error=f"Caracteres não permitidos: {dangerous}"
        )
    
    # Extrair nome do comando
    cmd_name = extract_command_name(command)
    if not cmd_name:
        return ValidationResult(
            valid=False,
            command=command,
            sanitized_command="",
            error="Comando vazio"
        )
    
    # Verificar se está bloqueado
    cmd_base = cmd_name.lstrip("-")
    if cmd_base in BLOCKED_COMMANDS or cmd_name in BLOCKED_COMMANDS:
        return ValidationResult(
            valid=False,
            command=command,
            sanitized_command="",
            error=f"Comando bloqueado por segurança: {cmd_name}"
        )
    
    # Verificar se está na whitelist
    if cmd_base not in ALLOWED_COMMANDS and cmd_name not in ALLOWED_COMMANDS:
        return ValidationResult(
            valid=False,
            command=command,
            sanitized_command="",
            error=f"Comando não permitido: {cmd_name}. Use comandos da whitelist."
        )
    
    # Validar parâmetros (se houver)
    parts = command.split(maxsplit=1)
    if len(parts) > 1:
        params = parts[1]
        # Dividir por espaços e validar cada parte
        for param in params.split():
            # Pular valores especiais do AutoCAD
            if param.upper() in {"Y", "N", "YES", "NO", "ALL", "LAST", "PREVIOUS"}:
                continue
            # Pular enters (\n)
            if param == "\\n" or param == "\n":
                continue
            # Verificar se parâmetro é seguro
            if not VALID_PARAM_PATTERN.match(param):
                logger.warning(f"Parâmetro potencialmente inseguro: {param}")
    
    # Comando válido
    return ValidationResult(
        valid=True,
        command=command,
        sanitized_command=command,  # já foi sanitizado
    )


def validate_batch_commands(commands: list) -> Tuple[list, list]:
    """
    Valida múltiplos comandos.
    
    Args:
        commands: Lista de comandos
        
    Returns:
        Tupla (comandos_validos, erros)
    """
    valid_commands = []
    errors = []
    
    for i, cmd in enumerate(commands):
        result = validate_command(cmd)
        if result.valid:
            valid_commands.append(result.sanitized_command)
        else:
            errors.append(f"Comando {i+1}: {result.error}")
    
    return valid_commands, errors


def is_command_allowed(command: str) -> bool:
    """
    Verifica rapidamente se um comando é permitido.
    
    Args:
        command: Comando a verificar
        
    Returns:
        True se permitido, False caso contrário
    """
    return validate_command(command).valid


def get_allowed_commands() -> Set[str]:
    """
    Retorna conjunto de todos os comandos permitidos.
    
    Returns:
        Set com nomes de comandos permitidos
    """
    return ALLOWED_COMMANDS.copy()


def get_blocked_commands() -> Set[str]:
    """
    Retorna conjunto de comandos bloqueados.
    
    Returns:
        Set com nomes de comandos bloqueados
    """
    return BLOCKED_COMMANDS.copy()
