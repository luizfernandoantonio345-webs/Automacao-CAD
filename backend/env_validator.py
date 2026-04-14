#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
ENGENHARIA CAD — Validador de Variáveis de Ambiente
═══════════════════════════════════════════════════════════════════════════════

Valida variáveis obrigatórias antes do startup para evitar falhas silenciosas.
"""

import os
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger("engcad.env_validator")


@dataclass
class EnvVar:
    """Definição de uma variável de ambiente."""
    name: str
    required_in_production: bool = True
    required_always: bool = False
    pattern: Optional[str] = None  # Regex para validar formato
    min_length: int = 0
    description: str = ""
    sensitive: bool = False  # Se True, não mostra valor em logs


# Variáveis de ambiente que o sistema usa
ENV_VARS: List[EnvVar] = [
    # === CRÍTICOS (obrigatórios em produção) ===
    EnvVar(
        name="JARVIS_SECRET",
        required_in_production=True,
        min_length=32,
        sensitive=True,
        description="Secret para JWT (mínimo 32 bytes para HS256)"
    ),
    EnvVar(
        name="DATABASE_URL",
        required_in_production=True,
        pattern=r"^postgres(ql)?://",
        description="URL do PostgreSQL (obrigatório em produção)"
    ),
    
    # === PAGAMENTOS (obrigatórios se billing habilitado) ===
    EnvVar(
        name="STRIPE_SECRET_KEY",
        required_in_production=True,
        pattern=r"^sk_(test|live)_",
        sensitive=True,
        description="Stripe Secret Key (começa com sk_)"
    ),
    EnvVar(
        name="STRIPE_WEBHOOK_SECRET",
        required_in_production=True,
        pattern=r"^whsec_",
        sensitive=True,
        description="Stripe Webhook Secret (começa com whsec_)"
    ),
    EnvVar(
        name="STRIPE_PUBLISHABLE_KEY",
        required_in_production=True,
        pattern=r"^pk_(test|live)_",
        description="Stripe Publishable Key (começa com pk_)"
    ),
    
    # === AI/LLM (opcionais, mas validados se presentes) ===
    EnvVar(
        name="OPENAI_API_KEY",
        required_in_production=False,
        pattern=r"^sk-",
        sensitive=True,
        description="OpenAI API Key (começa com sk-)"
    ),
    EnvVar(
        name="ANTHROPIC_API_KEY",
        required_in_production=False,
        pattern=r"^sk-ant-",
        sensitive=True,
        description="Anthropic API Key (começa com sk-ant-)"
    ),
    
    # === REDIS (recomendado em produção) ===
    EnvVar(
        name="REDIS_URL",
        required_in_production=False,
        pattern=r"^redis(s)?://",
        description="URL do Redis para cache/rate limiting"
    ),
]


class EnvValidationError(Exception):
    """Erro de validação de ambiente."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Erros de validação de ambiente: {'; '.join(errors)}")


def validate_environment(
    strict: bool = False,
    raise_on_error: bool = True
) -> Dict[str, Any]:
    """
    Valida todas as variáveis de ambiente definidas.
    
    Args:
        strict: Se True, valida também variáveis opcionais se estiverem definidas
        raise_on_error: Se True, levanta exceção em caso de erro
        
    Returns:
        Dict com resultado da validação
        
    Raises:
        EnvValidationError: Se houver erros e raise_on_error=True
    """
    app_env = os.getenv("APP_ENV", "development").lower()
    vercel_env = os.getenv("VERCEL_ENV", "").lower()
    is_production = app_env == "production" or vercel_env == "production"
    
    errors: List[str] = []
    warnings: List[str] = []
    validated: List[str] = []
    
    for var in ENV_VARS:
        value = os.getenv(var.name, "")
        
        # Verificar se é obrigatório
        if var.required_always or (var.required_in_production and is_production):
            if not value:
                errors.append(f"{var.name} é obrigatório ({var.description})")
                continue
        
        # Se não tem valor e não é obrigatório, pular
        if not value:
            continue
        
        # Validar tamanho mínimo
        if var.min_length > 0 and len(value.encode("utf-8")) < var.min_length:
            if var.required_in_production and is_production:
                errors.append(
                    f"{var.name} deve ter no mínimo {var.min_length} bytes "
                    f"(atual: {len(value.encode('utf-8'))} bytes)"
                )
            else:
                warnings.append(
                    f"{var.name} recomendado ter {var.min_length}+ bytes"
                )
            continue
        
        # Validar padrão (regex)
        if var.pattern:
            if not re.match(var.pattern, value):
                msg = f"{var.name} tem formato inválido (esperado: {var.pattern})"
                if var.required_in_production and is_production:
                    errors.append(msg)
                elif strict:
                    warnings.append(msg)
                continue
        
        # Variável válida
        validated.append(var.name)
        if var.sensitive:
            logger.debug(f"✓ {var.name} validado: {value[:8]}...***")
        else:
            logger.debug(f"✓ {var.name} validado")
    
    # Log de resultado
    if errors:
        logger.error(f"Validação de ambiente FALHOU: {len(errors)} erros")
        for err in errors:
            logger.error(f"  ✗ {err}")
    
    if warnings:
        for warn in warnings:
            logger.warning(f"  ⚠ {warn}")
    
    if validated:
        logger.info(f"Variáveis de ambiente validadas: {len(validated)}/{len(ENV_VARS)}")
    
    result = {
        "valid": len(errors) == 0,
        "is_production": is_production,
        "errors": errors,
        "warnings": warnings,
        "validated": validated,
    }
    
    if errors and raise_on_error:
        raise EnvValidationError(errors)
    
    return result


def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """
    Mascara valor sensível para exibição em logs.
    
    Args:
        value: Valor a mascarar
        visible_chars: Quantos caracteres iniciais mostrar
        
    Returns:
        Valor mascarado (ex: "sk-ab...***")
    """
    if not value:
        return "(vazio)"
    if len(value) <= visible_chars + 3:
        return "***"
    return f"{value[:visible_chars]}...***"


def get_env_summary() -> Dict[str, Any]:
    """
    Retorna resumo do ambiente para debug (sem valores sensíveis).
    """
    summary = {}
    for var in ENV_VARS:
        value = os.getenv(var.name, "")
        if var.sensitive:
            summary[var.name] = mask_sensitive_value(value) if value else "(não definido)"
        else:
            summary[var.name] = value if value else "(não definido)"
    return summary


# Auto-validar em import se estiver em produção
def _auto_validate_on_import():
    """Validação automática quando módulo é importado em produção."""
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env == "production":
        try:
            validate_environment(strict=True, raise_on_error=True)
        except EnvValidationError as e:
            logger.critical(f"FATAL: {e}")
            raise SystemExit(f"FATAL: Validação de ambiente falhou: {e}") from e


# Descomente abaixo para auto-validar em produção
# _auto_validate_on_import()
