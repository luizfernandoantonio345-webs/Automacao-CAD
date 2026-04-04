# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY MIDDLEWARE - ENGCAD AUTOMAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
"""
Middleware de segurança para adicionar headers HTTP de proteção.

Headers implementados:
- Content-Security-Policy (CSP) - Previne XSS
- X-Content-Type-Options - Previne MIME sniffing
- X-Frame-Options - Previne clickjacking
- X-XSS-Protection - Proteção XSS legada
- Strict-Transport-Security (HSTS) - Força HTTPS
- Referrer-Policy - Controla vazamento de referrer
- Permissions-Policy - Restringe APIs do browser

Uso:
    from backend.security import SecurityHeadersMiddleware, add_security_headers
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Ou para rotas específicas
    add_security_headers(app)
"""
from __future__ import annotations

import os
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from functools import wraps

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

logger = logging.getLogger("engcad.security")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SecurityConfig:
    """Configuração dos headers de segurança."""
    
    # HSTS - Strict Transport Security
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 ano
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False
    
    # CSP - Content Security Policy
    csp_enabled: bool = True
    csp_default_src: List[str] = field(default_factory=lambda: ["'self'"])
    csp_script_src: List[str] = field(default_factory=lambda: ["'self'", "'unsafe-inline'"])
    csp_style_src: List[str] = field(default_factory=lambda: ["'self'", "'unsafe-inline'"])
    csp_img_src: List[str] = field(default_factory=lambda: ["'self'", "data:", "https:"])
    csp_connect_src: List[str] = field(default_factory=lambda: ["'self'", "https:"])
    csp_font_src: List[str] = field(default_factory=lambda: ["'self'", "https:", "data:"])
    csp_frame_ancestors: List[str] = field(default_factory=lambda: ["'none'"])
    csp_report_uri: Optional[str] = None
    
    # X-Frame-Options
    frame_options: str = "DENY"  # DENY, SAMEORIGIN, ALLOW-FROM uri
    
    # X-Content-Type-Options
    content_type_options: str = "nosniff"
    
    # X-XSS-Protection
    xss_protection: str = "1; mode=block"
    
    # Referrer-Policy
    referrer_policy: str = "strict-origin-when-cross-origin"
    
    # Permissions-Policy (feature policy)
    permissions_policy: Dict[str, List[str]] = field(default_factory=lambda: {
        "geolocation": [],
        "microphone": [],
        "camera": [],
        "payment": [],
        "usb": [],
    })
    
    # Paths a excluir (ex: docs, health check)
    exclude_paths: Set[str] = field(default_factory=lambda: {
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/health",
        "/api/health"
    })
    
    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Carrega configuração do ambiente."""
        config = cls()
        
        # HSTS
        if os.getenv("SECURITY_HSTS_DISABLED", "").lower() in ("1", "true"):
            config.hsts_enabled = False
        if hsts_age := os.getenv("SECURITY_HSTS_MAX_AGE"):
            config.hsts_max_age = int(hsts_age)
            
        # CSP
        if os.getenv("SECURITY_CSP_DISABLED", "").lower() in ("1", "true"):
            config.csp_enabled = False
        if report_uri := os.getenv("SECURITY_CSP_REPORT_URI"):
            config.csp_report_uri = report_uri
            
        # Frame Options
        if frame_opt := os.getenv("SECURITY_FRAME_OPTIONS"):
            config.frame_options = frame_opt
            
        return config


# Configuração padrão
DEFAULT_CONFIG = SecurityConfig()


# ═══════════════════════════════════════════════════════════════════════════════
# BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_csp_header(config: SecurityConfig) -> str:
    """Constrói header Content-Security-Policy."""
    directives = []
    
    if config.csp_default_src:
        directives.append(f"default-src {' '.join(config.csp_default_src)}")
    if config.csp_script_src:
        directives.append(f"script-src {' '.join(config.csp_script_src)}")
    if config.csp_style_src:
        directives.append(f"style-src {' '.join(config.csp_style_src)}")
    if config.csp_img_src:
        directives.append(f"img-src {' '.join(config.csp_img_src)}")
    if config.csp_connect_src:
        directives.append(f"connect-src {' '.join(config.csp_connect_src)}")
    if config.csp_font_src:
        directives.append(f"font-src {' '.join(config.csp_font_src)}")
    if config.csp_frame_ancestors:
        directives.append(f"frame-ancestors {' '.join(config.csp_frame_ancestors)}")
    if config.csp_report_uri:
        directives.append(f"report-uri {config.csp_report_uri}")
    
    return "; ".join(directives)


def build_hsts_header(config: SecurityConfig) -> str:
    """Constrói header Strict-Transport-Security."""
    parts = [f"max-age={config.hsts_max_age}"]
    
    if config.hsts_include_subdomains:
        parts.append("includeSubDomains")
    if config.hsts_preload:
        parts.append("preload")
    
    return "; ".join(parts)


def build_permissions_policy(config: SecurityConfig) -> str:
    """Constrói header Permissions-Policy."""
    policies = []
    
    for feature, allowlist in config.permissions_policy.items():
        if not allowlist:
            policies.append(f"{feature}=()")
        else:
            policies.append(f"{feature}=({' '.join(allowlist)})")
    
    return ", ".join(policies)


# ═══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona headers de segurança a todas as respostas.
    
    Exemplo:
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        # Ou com configuração customizada
        config = SecurityConfig(hsts_max_age=86400)
        app.add_middleware(SecurityHeadersMiddleware, config=config)
    """
    
    def __init__(self, app, config: Optional[SecurityConfig] = None):
        super().__init__(app)
        self.config = config or DEFAULT_CONFIG
        
        # Pre-computar headers estáticos
        self._static_headers: Dict[str, str] = {
            "X-Content-Type-Options": self.config.content_type_options,
            "X-XSS-Protection": self.config.xss_protection,
            "X-Frame-Options": self.config.frame_options,
            "Referrer-Policy": self.config.referrer_policy,
        }
        
        if self.config.hsts_enabled:
            self._static_headers["Strict-Transport-Security"] = build_hsts_header(self.config)
        
        if self.config.csp_enabled:
            self._static_headers["Content-Security-Policy"] = build_csp_header(self.config)
        
        if self.config.permissions_policy:
            self._static_headers["Permissions-Policy"] = build_permissions_policy(self.config)
        
        logger.info("SecurityHeadersMiddleware configurado com %d headers", len(self._static_headers))
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processa request e adiciona headers de segurança."""
        response = await call_next(request)
        
        # Verificar se path está excluído
        path = request.url.path
        if path in self.config.exclude_paths or any(path.startswith(p) for p in self.config.exclude_paths):
            return response
        
        # Adicionar headers
        for header, value in self._static_headers.items():
            response.headers[header] = value
        
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def add_security_headers(app: FastAPI, config: Optional[SecurityConfig] = None):
    """
    Adiciona middleware de segurança ao app FastAPI.
    
    Args:
        app: Instância FastAPI
        config: Configuração customizada (opcional)
    """
    app.add_middleware(SecurityHeadersMiddleware, config=config or DEFAULT_CONFIG)
    logger.info("Security headers middleware adicionado")


def secure_response(response: Response, config: Optional[SecurityConfig] = None) -> Response:
    """
    Adiciona headers de segurança a uma response específica.
    
    Útil para rotas que precisam de headers customizados.
    """
    cfg = config or DEFAULT_CONFIG
    
    response.headers["X-Content-Type-Options"] = cfg.content_type_options
    response.headers["X-XSS-Protection"] = cfg.xss_protection
    response.headers["X-Frame-Options"] = cfg.frame_options
    response.headers["Referrer-Policy"] = cfg.referrer_policy
    
    if cfg.hsts_enabled:
        response.headers["Strict-Transport-Security"] = build_hsts_header(cfg)
    
    if cfg.csp_enabled:
        response.headers["Content-Security-Policy"] = build_csp_header(cfg)
    
    return response


def with_security_headers(config: Optional[SecurityConfig] = None):
    """
    Decorator para adicionar headers de segurança a uma rota específica.
    
    Exemplo:
        @app.get("/secure-data")
        @with_security_headers()
        async def secure_data():
            return {"data": "secret"}
    """
    cfg = config or DEFAULT_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Se já é uma Response, adicionar headers
            if isinstance(result, Response):
                return secure_response(result, cfg)
            
            return result
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RateLimitConfig:
    """Configuração de rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    enabled: bool = True


class SimpleRateLimiter:
    """
    Rate limiter simples baseado em memória.
    
    Para produção, considere usar Redis ou similar.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Verifica se cliente pode fazer requisição."""
        if not self.config.enabled:
            return True
        
        import time
        now = time.time()
        
        if client_id not in self._requests:
            self._requests[client_id] = []
        
        # Limpar requests antigas (> 1 hora)
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if now - t < 3600
        ]
        
        # Verificar limites
        recent = self._requests[client_id]
        
        # Requests no último minuto
        last_minute = sum(1 for t in recent if now - t < 60)
        if last_minute >= self.config.requests_per_minute:
            return False
        
        # Requests na última hora
        if len(recent) >= self.config.requests_per_hour:
            return False
        
        # Registrar request
        self._requests[client_id].append(now)
        return True
    
    def get_client_id(self, request: Request) -> str:
        """Extrai ID do cliente (IP ou token)."""
        # Primeiro tenta header X-Forwarded-For (proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Fallback para client host
        if request.client:
            return request.client.host
        
        return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# CORS SEGURO
# ═══════════════════════════════════════════════════════════════════════════════

def get_secure_cors_config() -> Dict[str, Any]:
    """
    Retorna configuração segura de CORS.
    
    Uso:
        from fastapi.middleware.cors import CORSMiddleware
        
        app.add_middleware(CORSMiddleware, **get_secure_cors_config())
    """
    # Origens permitidas do ambiente
    allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
    
    # Se não definido, usar origens padrão
    if not allowed_origins:
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",  # Vite
            "https://automacao-cad-backend.vercel.app",
        ]
    
    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "X-CSRF-Token",
            "X-Request-ID",
        ],
        "expose_headers": ["X-Request-ID", "X-RateLimit-Remaining"],
        "max_age": 600,  # Cache preflight por 10 minutos
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRO INTEGRADO
# ═══════════════════════════════════════════════════════════════════════════════

def setup_security(app: FastAPI, security_config: Optional[SecurityConfig] = None):
    """
    Configura todas as medidas de segurança de uma vez.
    
    Args:
        app: Instância FastAPI
        security_config: Configuração de segurança
        
    Exemplo:
        app = FastAPI()
        setup_security(app)
    """
    from fastapi.middleware.cors import CORSMiddleware
    
    # CORS seguro
    cors_config = get_secure_cors_config()
    app.add_middleware(CORSMiddleware, **cors_config)
    
    # Headers de segurança
    add_security_headers(app, security_config)
    
    # Endpoint de verificação de segurança
    @app.get("/api/security/check", tags=["Security"])
    async def security_check():
        """Verifica configuração de segurança."""
        return {
            "cors_origins": cors_config["allow_origins"],
            "hsts_enabled": (security_config or DEFAULT_CONFIG).hsts_enabled,
            "csp_enabled": (security_config or DEFAULT_CONFIG).csp_enabled,
            "headers_active": True
        }
    
    logger.info("Segurança configurada: CORS + Headers + Check endpoint")


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Demonstração dos headers gerados
    config = SecurityConfig()
    
    print("=== Headers de Segurança ===\n")
    
    print(f"HSTS: {build_hsts_header(config)}")
    print(f"\nCSP: {build_csp_header(config)}")
    print(f"\nPermissions-Policy: {build_permissions_policy(config)}")
    print(f"\nX-Frame-Options: {config.frame_options}")
    print(f"X-Content-Type-Options: {config.content_type_options}")
    print(f"X-XSS-Protection: {config.xss_protection}")
    print(f"Referrer-Policy: {config.referrer_policy}")
    
    print("\n=== CORS Config ===\n")
    cors = get_secure_cors_config()
    for key, value in cors.items():
        print(f"{key}: {value}")
