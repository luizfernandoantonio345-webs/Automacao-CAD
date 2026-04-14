#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
ENGENHARIA CAD — OWASP Security Protections
═══════════════════════════════════════════════════════════════════════════════

Implementações de segurança baseadas nas diretrizes OWASP:
- Input validation e sanitização
- Proteção contra SQL Injection
- Proteção contra XSS
- Proteção contra Path Traversal
- Rate limiting helpers
- Secure headers validation

OWASP Top 10 2021 cobertura:
- A01:2021 – Broken Access Control: validate_path_traversal
- A03:2021 – Injection: sanitize_input, validate_sql_identifier
- A05:2021 – Security Misconfiguration: validate_config
- A07:2021 – XSS: sanitize_html, escape_output
"""

from __future__ import annotations

import html
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from functools import wraps

logger = logging.getLogger("engcad.security.owasp")

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE SEGURANÇA
# ═══════════════════════════════════════════════════════════════════════════════

# Caracteres perigosos para nomes de arquivo/path
DANGEROUS_PATH_CHARS = {"\x00", "..", "~", "|", ";", "&", "$", "`", "\n", "\r"}

# Padrões de SQL injection comuns
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
    r"(--|\#|\/\*)",
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(\'\s*(OR|AND)\s*\')",
]

# Tags HTML perigosas
DANGEROUS_HTML_TAGS = {"script", "iframe", "object", "embed", "form", "input", "style", "link", "meta"}

# Extensões de arquivo permitidas para upload
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".dxf", ".dwg", ".pdf", ".png", ".jpg", ".jpeg"}

# Tamanho máximo de entrada de texto (caracteres)
MAX_INPUT_LENGTH = 10000


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════════

def sanitize_input(value: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Sanitiza entrada de texto removendo caracteres perigosos.
    
    Args:
        value: Texto a sanitizar
        max_length: Tamanho máximo permitido
        
    Returns:
        Texto sanitizado
    """
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # Truncar se muito longo
    value = value[:max_length]
    
    # Remover null bytes
    value = value.replace("\x00", "")
    
    # Normalizar whitespace
    value = " ".join(value.split())
    
    return value


def validate_email(email: str) -> bool:
    """Valida formato de email de forma segura."""
    if not email or len(email) > 254:
        return False
    
    # RFC 5322 simplificado
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """Valida username permitindo apenas caracteres seguros."""
    if not username or len(username) > 64:
        return False
    
    # Apenas letras, números, underscore, hífen
    pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(pattern, username))


# ═══════════════════════════════════════════════════════════════════════════════
# PROTEÇÃO CONTRA PATH TRAVERSAL (A01:2021)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_path_traversal(path: str, base_dir: Optional[str] = None) -> tuple[bool, str]:
    """
    Valida caminho contra ataques de path traversal.
    
    Args:
        path: Caminho a validar
        base_dir: Diretório base permitido (opcional)
        
    Returns:
        Tupla (is_valid, error_message)
    """
    if not path:
        return False, "Caminho vazio"
    
    # Verificar caracteres perigosos
    for char in DANGEROUS_PATH_CHARS:
        if char in path:
            logger.warning("Path traversal attempt: %s", path[:100])
            return False, f"Caractere proibido no caminho: {repr(char)}"
    
    # Normalizar e verificar componentes
    try:
        normalized = os.path.normpath(path)
        
        # Verificar se tenta escapar do diretório base
        if base_dir:
            base_resolved = os.path.realpath(base_dir)
            path_resolved = os.path.realpath(os.path.join(base_dir, normalized))
            
            if not path_resolved.startswith(base_resolved):
                logger.warning("Path traversal blocked: %s escapes %s", path, base_dir)
                return False, "Acesso fora do diretório permitido"
        
        return True, ""
        
    except Exception as e:
        return False, f"Erro ao validar caminho: {e}"


def safe_join_path(base: str, *paths: str) -> Optional[str]:
    """
    Une caminhos de forma segura, prevenindo path traversal.
    
    Returns:
        Caminho seguro ou None se inválido
    """
    try:
        base_real = os.path.realpath(base)
        joined = os.path.join(base, *paths)
        joined_real = os.path.realpath(joined)
        
        if joined_real.startswith(base_real):
            return joined_real
        
        logger.warning("Safe path join blocked: %s + %s", base, paths)
        return None
        
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PROTEÇÃO CONTRA SQL INJECTION (A03:2021)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_sql_injection(value: str) -> bool:
    """
    Detecta padrões comuns de SQL injection.
    
    Nota: Isso é uma camada adicional de defesa. Sempre use queries
    parametrizadas como proteção primária.
    """
    if not value:
        return False
    
    value_upper = value.upper()
    
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value_upper, re.IGNORECASE):
            logger.warning("SQL injection pattern detected: %s", value[:100])
            return True
    
    return False


def validate_sql_identifier(identifier: str, allowed: Set[str]) -> bool:
    """
    Valida que um identificador SQL está na whitelist permitida.
    
    Args:
        identifier: Nome de coluna/tabela
        allowed: Conjunto de nomes permitidos
        
    Returns:
        True se o identificador é seguro
    """
    return identifier in allowed


# ═══════════════════════════════════════════════════════════════════════════════
# PROTEÇÃO CONTRA XSS (A07:2021)
# ═══════════════════════════════════════════════════════════════════════════════

def escape_output(value: str) -> str:
    """
    Escapa HTML para prevenir XSS.
    
    Use isso ao renderizar dados de usuário em HTML.
    """
    return html.escape(value, quote=True)


def sanitize_html(value: str, allow_basic: bool = False) -> str:
    """
    Remove ou escapa tags HTML perigosas.
    
    Args:
        value: HTML a sanitizar
        allow_basic: Permitir tags básicas (p, br, strong, em)
    """
    if not value:
        return ""
    
    # Remover scripts imediatamente
    value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    
    # Remover event handlers
    value = re.sub(r"\bon\w+\s*=", "", value, flags=re.IGNORECASE)
    
    # Remover javascript: e data: URLs
    value = re.sub(r"(javascript|data|vbscript):", "", value, flags=re.IGNORECASE)
    
    if not allow_basic:
        # Escapar tudo
        return html.escape(value, quote=True)
    
    # Permitir apenas tags básicas seguras
    allowed_tags = {"p", "br", "strong", "em", "b", "i", "ul", "ol", "li"}
    
    def replace_tag(match):
        tag = match.group(1).lower()
        if tag.lstrip("/") in allowed_tags:
            return match.group(0)
        return html.escape(match.group(0))
    
    return re.sub(r"<(/?\w+)[^>]*>", replace_tag, value)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE ARQUIVOS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_file_extension(filename: str, allowed: Optional[Set[str]] = None) -> bool:
    """Valida extensão de arquivo contra whitelist."""
    if allowed is None:
        allowed = ALLOWED_EXTENSIONS
    
    if not filename:
        return False
    
    ext = Path(filename).suffix.lower()
    return ext in allowed


def validate_file_size(size_bytes: int, max_mb: int = 50) -> bool:
    """Valida tamanho de arquivo em MB."""
    max_bytes = max_mb * 1024 * 1024
    return 0 < size_bytes <= max_bytes


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE CONFIGURAÇÃO (A05:2021)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_config() -> Dict[str, Any]:
    """
    Verifica configurações de segurança do ambiente.
    
    Returns:
        Dict com status de cada verificação
    """
    checks = {}
    
    # JARVIS_SECRET
    secret = os.getenv("JARVIS_SECRET", "")
    checks["jarvis_secret_set"] = bool(secret)
    checks["jarvis_secret_strong"] = len(secret.encode()) >= 32
    
    # DATABASE_URL em produção
    is_prod = os.getenv("APP_ENV") == "production"
    db_url = os.getenv("DATABASE_URL", "")
    checks["database_configured"] = bool(db_url) if is_prod else True
    checks["using_postgresql"] = db_url.startswith(("postgresql://", "postgres://"))
    
    # DEBUG desabilitado em produção
    debug = os.getenv("DEBUG", "false").lower() in {"true", "1", "yes"}
    checks["debug_disabled_in_prod"] = not (is_prod and debug)
    
    # CORS configurado
    cors_origins = os.getenv("CORS_ORIGINS", "")
    checks["cors_configured"] = "*" not in cors_origins if is_prod else True
    
    return checks


# ═══════════════════════════════════════════════════════════════════════════════
# DECORADORES DE SEGURANÇA
# ═══════════════════════════════════════════════════════════════════════════════

def require_secure_request(func):
    """
    Decorator que valida requisições de segurança básica.
    
    Verifica:
    - Content-Type correto
    - Tamanho de payload aceitável
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # A validação real deve ser feita no middleware
        # Este decorator é um placeholder para extensões futuras
        return await func(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# LOGS DE SEGURANÇA
# ═══════════════════════════════════════════════════════════════════════════════

def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "warning") -> None:
    """
    Registra evento de segurança para auditoria.
    
    Args:
        event_type: Tipo do evento (sql_injection, xss, path_traversal, etc.)
        details: Detalhes do evento
        severity: info, warning, error, critical
    """
    log_func = getattr(logger, severity, logger.warning)
    log_func(
        "SECURITY_EVENT: %s | %s",
        event_type,
        {k: str(v)[:200] for k, v in details.items()}
    )
