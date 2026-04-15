"""
Engenharia CAD — Rate Limiting Robusto com Redis

Sistema de rate limiting com múltiplas estratégias:
- Redis (produção): Distribuído, preciso, escalável
- Memória (fallback): Local, para desenvolvimento

Usa algoritmo de janela deslizante (sliding window) para maior precisão.
"""
from __future__ import annotations

import os
import time
import logging
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from functools import wraps

from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException

logger = logging.getLogger("engcad.ratelimit")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RateLimitRule:
    """Regra de rate limiting."""
    requests: int  # Número máximo de requests
    window_seconds: int  # Janela de tempo em segundos
    
    @property
    def key_suffix(self) -> str:
        return f"{self.window_seconds}s"


# Limites padrão por tipo de endpoint
DEFAULT_LIMITS = {
    "default": RateLimitRule(requests=100, window_seconds=60),  # 100/min
    "auth": RateLimitRule(requests=10, window_seconds=60),  # 10/min (login, registro)
    "api": RateLimitRule(requests=60, window_seconds=60),  # 60/min
    "heavy": RateLimitRule(requests=10, window_seconds=60),  # 10/min (IA, uploads)
    "bridge": RateLimitRule(requests=120, window_seconds=60),  # 120/min (heartbeat)
}

# Limites por tier de usuário (multiplicadores)
TIER_MULTIPLIERS = {
    "demo": 0.5,  # 50% do limite
    "starter": 1.0,  # 100% do limite
    "pro": 2.0,  # 200% do limite
    "enterprise": 5.0,  # 500% do limite
}


# ═══════════════════════════════════════════════════════════════════════════════
# REDIS RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════

class RedisRateLimiter:
    """
    Rate limiter distribuído usando Redis.
    
    Implementa sliding window log algorithm para maior precisão.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self._client = None
        self._available = False
        self._connect()
    
    def _connect(self):
        """Tenta conectar ao Redis."""
        if not self.redis_url:
            logger.info("Redis URL não configurada, rate limiting em memória")
            return
        
        try:
            import redis
            self._client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self._client.ping()
            self._available = True
            logger.info("Rate limiter Redis conectado")
        except Exception as e:
            logger.warning(f"Redis não disponível para rate limiting: {e}")
            self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available and self._client is not None
    
    def check_rate_limit(
        self,
        key: str,
        rule: RateLimitRule,
        tier: str = "starter"
    ) -> Tuple[bool, int, int]:
        """
        Verifica rate limit usando sliding window.
        
        Returns:
            Tuple[allowed, remaining, reset_in_seconds]
        """
        if not self.is_available:
            # Fallback: sempre permite
            return True, rule.requests, rule.window_seconds
        
        try:
            # Calcular limite baseado no tier
            multiplier = TIER_MULTIPLIERS.get(tier, 1.0)
            limit = int(rule.requests * multiplier)
            
            now = time.time()
            window_start = now - rule.window_seconds
            redis_key = f"ratelimit:{key}:{rule.key_suffix}"
            
            # Pipeline para operações atômicas
            pipe = self._client.pipeline()
            
            # Remover entradas antigas
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Contar requests na janela
            pipe.zcount(redis_key, window_start, now)
            
            # Adicionar novo request
            pipe.zadd(redis_key, {str(now): now})
            
            # Definir TTL
            pipe.expire(redis_key, rule.window_seconds)
            
            # Executar
            results = pipe.execute()
            current_count = results[1]
            
            remaining = max(0, limit - current_count - 1)
            allowed = current_count < limit
            
            # Calcular reset
            oldest = self._client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                reset_in = int(oldest[0][1] + rule.window_seconds - now)
            else:
                reset_in = rule.window_seconds
            
            if not allowed:
                logger.warning(f"Rate limit exceeded: {key} ({current_count}/{limit})")
            
            return allowed, remaining, max(0, reset_in)
            
        except Exception as e:
            logger.error(f"Erro no rate limiting Redis: {e}")
            # Em caso de erro, permite a requisição
            return True, rule.requests, rule.window_seconds
    
    def reset(self, key: str):
        """Reseta rate limit para uma chave."""
        if not self.is_available:
            return
        
        try:
            for rule in DEFAULT_LIMITS.values():
                redis_key = f"ratelimit:{key}:{rule.key_suffix}"
                self._client.delete(redis_key)
        except Exception as e:
            logger.error(f"Erro ao resetar rate limit: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY RATE LIMITER (FALLBACK)
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryRateLimiter:
    """
    Rate limiter em memória para fallback.
    
    Nota: Não funciona em ambiente distribuído (múltiplas instâncias).
    """
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Limpar a cada minuto
    
    def _cleanup(self):
        """Remove entradas antigas."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        cutoff = now - 3600  # Manter última hora
        
        keys_to_delete = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if not self._requests[key]:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._requests[key]
    
    def check_rate_limit(
        self,
        key: str,
        rule: RateLimitRule,
        tier: str = "starter"
    ) -> Tuple[bool, int, int]:
        """Verifica rate limit em memória."""
        self._cleanup()
        
        multiplier = TIER_MULTIPLIERS.get(tier, 1.0)
        limit = int(rule.requests * multiplier)
        
        now = time.time()
        window_start = now - rule.window_seconds
        full_key = f"{key}:{rule.key_suffix}"
        
        if full_key not in self._requests:
            self._requests[full_key] = []
        
        # Filtrar requests na janela
        self._requests[full_key] = [
            t for t in self._requests[full_key]
            if t > window_start
        ]
        
        current_count = len(self._requests[full_key])
        
        if current_count < limit:
            self._requests[full_key].append(now)
            remaining = limit - current_count - 1
            return True, remaining, rule.window_seconds
        else:
            oldest = min(self._requests[full_key]) if self._requests[full_key] else now
            reset_in = int(oldest + rule.window_seconds - now)
            return False, 0, max(0, reset_in)
    
    def reset(self, key: str):
        """Reseta rate limit."""
        for rule in DEFAULT_LIMITS.values():
            full_key = f"{key}:{rule.key_suffix}"
            if full_key in self._requests:
                del self._requests[full_key]


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """
    Rate limiter com fallback automático.
    
    Usa Redis quando disponível, fallback para memória.
    """
    
    _instance: Optional["RateLimiter"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._redis_limiter = RedisRateLimiter()
        self._memory_limiter = MemoryRateLimiter()
        self._initialized = True
        
        backend = "Redis" if self._redis_limiter.is_available else "Memory"
        logger.info(f"Rate limiter inicializado (backend: {backend})")
    
    @property
    def _active_limiter(self):
        if self._redis_limiter.is_available:
            return self._redis_limiter
        return self._memory_limiter
    
    @property
    def backend(self) -> str:
        return "redis" if self._redis_limiter.is_available else "memory"
    
    def get_client_key(self, request: Request) -> str:
        """Extrai identificador do cliente."""
        # Tentar header X-Forwarded-For (proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
        else:
            ip = "unknown"
        
        # Hash para privacidade
        return hashlib.sha256(ip.encode()).hexdigest()[:16]
    
    def get_user_tier(self, request: Request) -> str:
        """Obtém tier do usuário do request."""
        # Tentar extrair do state (set pelo middleware de auth)
        if hasattr(request.state, "user_tier"):
            return request.state.user_tier
        
        # Default
        return "starter"
    
    def check(
        self,
        request: Request,
        endpoint_type: str = "default"
    ) -> Tuple[bool, int, int]:
        """
        Verifica rate limit para um request.
        
        Args:
            request: Starlette Request
            endpoint_type: Tipo de endpoint (default, auth, api, heavy, bridge)
            
        Returns:
            Tuple[allowed, remaining, reset_in_seconds]
        """
        key = self.get_client_key(request)
        tier = self.get_user_tier(request)
        rule = DEFAULT_LIMITS.get(endpoint_type, DEFAULT_LIMITS["default"])
        
        return self._active_limiter.check_rate_limit(key, rule, tier)
    
    def reset(self, request: Request):
        """Reseta rate limit para o cliente."""
        key = self.get_client_key(request)
        self._active_limiter.reset(key)


# Singleton global
rate_limiter = RateLimiter()


# ═══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

def get_endpoint_type(path: str) -> str:
    """Determina tipo de endpoint pelo path."""
    path_lower = path.lower()
    
    # Autenticação
    if any(p in path_lower for p in ["/login", "/register", "/auth", "/password"]):
        return "auth"
    
    # Bridge (heartbeat do agente)
    if "/api/bridge" in path_lower:
        return "bridge"
    
    # Operações pesadas
    if any(p in path_lower for p in ["/ai/", "/upload", "/export", "/generate"]):
        return "heavy"
    
    # API geral
    if path_lower.startswith("/api/"):
        return "api"
    
    return "default"


class RateLimitMiddleware:
    """
    Middleware de rate limiting para FastAPI/Starlette.
    
    Uso:
        app.add_middleware(RateLimitMiddleware)
    """
    
    def __init__(self, app):
        self.app = app
        self.limiter = rate_limiter
        self._exclude_paths = {
            "/health",
            "/healthz",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        path = request.url.path
        
        # Excluir paths específicos
        if path in self._exclude_paths or path.startswith("/static"):
            await self.app(scope, receive, send)
            return
        
        # Verificar rate limit
        endpoint_type = get_endpoint_type(path)
        allowed, remaining, reset_in = self.limiter.check(request, endpoint_type)
        
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Muitas requisições. Tente novamente mais tarde.",
                    "retry_after": reset_in,
                },
                headers={
                    "Retry-After": str(reset_in),
                    "X-RateLimit-Limit": str(DEFAULT_LIMITS[endpoint_type].requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                }
            )
            await response(scope, receive, send)
            return
        
        # Adicionar headers de rate limit à resposta
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"X-RateLimit-Remaining", str(remaining).encode()),
                    (b"X-RateLimit-Reset", str(reset_in).encode()),
                ])
                message["headers"] = headers
            await send(message)
        
        await self.app(scope, receive, send_with_headers)


# ═══════════════════════════════════════════════════════════════════════════════
# DECORADOR
# ═══════════════════════════════════════════════════════════════════════════════

def rate_limit(endpoint_type: str = "default"):
    """
    Decorador para aplicar rate limiting em rotas específicas.
    
    Exemplo:
        @app.post("/api/ai/chat")
        @rate_limit("heavy")
        async def ai_chat(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            allowed, remaining, reset_in = rate_limiter.check(request, endpoint_type)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": "Muitas requisições. Tente novamente mais tarde.",
                        "retry_after": reset_in,
                    },
                    headers={
                        "Retry-After": str(reset_in),
                        "X-RateLimit-Remaining": "0",
                    }
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════════════

def setup_rate_limiting(app):
    """
    Configura rate limiting no app FastAPI.
    
    Uso:
        from backend.rate_limiter import setup_rate_limiting
        setup_rate_limiting(app)
    """
    from starlette.middleware import Middleware
    
    app.add_middleware(RateLimitMiddleware)
    
    # Endpoint de status
    @app.get("/api/rate-limit/status", tags=["Rate Limit"])
    async def rate_limit_status(request: Request):
        """Retorna status do rate limiting para o cliente atual."""
        key = rate_limiter.get_client_key(request)
        tier = rate_limiter.get_user_tier(request)
        
        limits = {}
        for name, rule in DEFAULT_LIMITS.items():
            allowed, remaining, reset_in = rate_limiter._active_limiter.check_rate_limit(
                key, rule, tier
            )
            multiplier = TIER_MULTIPLIERS.get(tier, 1.0)
            limits[name] = {
                "limit": int(rule.requests * multiplier),
                "remaining": remaining,
                "reset_in": reset_in,
                "window_seconds": rule.window_seconds,
            }
        
        return {
            "backend": rate_limiter.backend,
            "tier": tier,
            "limits": limits,
        }
    
    logger.info(f"Rate limiting configurado (backend: {rate_limiter.backend})")
