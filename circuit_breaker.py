#!/usr/bin/env python3
# ====================================================================
# circuit_breaker.py - FASE 3: Circuit Breaker Implementation
# ====================================================================

import os
import redis
import time
import logging
from enum import Enum
from typing import Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """FASE 3: Circuit Breaker para isolamento de falhas.
    Falls back to in-memory state when Redis is unavailable."""
    
    def __init__(self, 
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: Exception = Exception,
                 redis_url: str = None):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self._use_redis = False
        
        # In-memory fallback state
        self._mem_state = CircuitState.CLOSED
        self._mem_failures = 0
        self._mem_last_failure = 0.0
        
        # Tentar conectar ao Redis; se falhar, usar memória local
        effective_url = redis_url or os.getenv("CIRCUIT_BREAKER_REDIS_URL", "redis://localhost:6380/0")
        try:
            self.redis = redis.from_url(effective_url, decode_responses=True, socket_connect_timeout=2)
            self.redis.ping()
            self._use_redis = True
        except Exception:
            self.redis = None
            logger.warning("Circuit breaker '%s': Redis indisponível — usando fallback em memória", name)
        
        # Keys Redis
        self.state_key = f"circuit:{name}:state"
        self.failures_key = f"circuit:{name}:failures"
        self.last_failure_key = f"circuit:{name}:last_failure"
        
        # Estado inicial
        if self._use_redis:
            try:
                if not self.redis.exists(self.state_key):
                    self.redis.set(self.state_key, CircuitState.CLOSED.value)
            except Exception:
                self._use_redis = False
                logger.warning("Circuit breaker '%s': Redis falhou na inicialização — fallback ativo", name)
    
    def _get_state(self) -> CircuitState:
        """Get current state from Redis or memory."""
        if not self._use_redis:
            return self._mem_state
        try:
            state_str = self.redis.get(self.state_key)
            return CircuitState(state_str) if state_str else CircuitState.CLOSED
        except Exception:
            return self._mem_state
    
    def _set_state(self, state: CircuitState):
        """Set state in Redis or memory."""
        self._mem_state = state
        if self._use_redis:
            try:
                self.redis.set(self.state_key, state.value)
            except Exception:
                pass
        logger.info(f"Circuit {self.name}: {state.value}")
    
    def _record_failure(self):
        """Record a failure."""
        self._mem_failures += 1
        self._mem_last_failure = time.time()
        if self._use_redis:
            try:
                pipe = self.redis.pipeline()
                pipe.incr(self.failures_key)
                pipe.set(self.last_failure_key, time.time())
                pipe.execute()
            except Exception:
                pass
    
    def _record_success(self):
        """Record a success."""
        self._mem_failures = 0
        if self._use_redis:
            try:
                self.redis.set(self.failures_key, 0)
            except Exception:
                pass
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset."""
        if not self._use_redis:
            return time.time() - self._mem_last_failure >= self.recovery_timeout
        try:
            last_failure = self.redis.get(self.last_failure_key)
            if not last_failure:
                return True
            return time.time() - float(last_failure) >= self.recovery_timeout
        except Exception:
            return time.time() - self._mem_last_failure >= self.recovery_timeout
    
    def _get_failure_count(self) -> int:
        """Get current failure count."""
        if not self._use_redis:
            return self._mem_failures
        try:
            count = self.redis.get(self.failures_key)
            return int(count) if count else 0
        except Exception:
            return self._mem_failures
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        state = self._get_state()
        
        if state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._set_state(CircuitState.HALF_OPEN)
                state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            if state == CircuitState.HALF_OPEN:
                self._set_state(CircuitState.CLOSED)
            return result
            
        except self.expected_exception as e:
            self._record_failure()
            failure_count = self._get_failure_count()
            
            if failure_count >= self.failure_threshold:
                self._set_state(CircuitState.OPEN)
            
            raise e

class CircuitBreakerOpen(Exception):
    """Exception raised when circuit is open."""
    pass

# ✓ Circuit Breakers globais
circuit_breakers = {}

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker."""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name, **kwargs)
    return circuit_breakers[name]

# ✓ Decorator para usar circuit breaker
def circuit_breaker(name: str, **kwargs):
    """Decorator to apply circuit breaker to functions."""
    def decorator(func):
        cb = get_circuit_breaker(name, **kwargs)
        
        @wraps(func)
        def wrapper(*args, **kwargs_inner):
            return cb.call(func, *args, **kwargs_inner)
        return wrapper
    return decorator