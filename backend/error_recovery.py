"""
═══════════════════════════════════════════════════════════════════════════════
  ERROR RECOVERY — Sistema centralizado de recuperação de erros
  Integra Circuit Breaker, retry patterns e graceful degradation
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime, UTC
from typing import Any, Callable, Dict, Optional, Type

logger = logging.getLogger("engcad.recovery")


class ErrorTracker:
    """Rastreia erros por módulo/serviço para detectar padrões de falha."""

    def __init__(self, window_seconds: int = 300, max_entries: int = 500):
        self._window = window_seconds
        self._errors: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_entries))
        self._counts: Dict[str, int] = defaultdict(int)

    def record(self, service: str, error: Exception, context: str = "") -> None:
        now = time.monotonic()
        self._errors[service].append({
            "time": now,
            "type": type(error).__name__,
            "message": str(error)[:200],
            "context": context,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        self._counts[service] += 1
        self._cleanup(service)

    def _cleanup(self, service: str) -> None:
        cutoff = time.monotonic() - self._window
        q = self._errors[service]
        while q and q[0]["time"] < cutoff:
            q.popleft()

    def error_rate(self, service: str) -> int:
        """Erros nos últimos N segundos."""
        self._cleanup(service)
        return len(self._errors[service])

    def is_degraded(self, service: str, threshold: int = 10) -> bool:
        return self.error_rate(service) >= threshold

    def get_summary(self) -> Dict[str, Any]:
        return {
            svc: {
                "recent_errors": len(errs),
                "total_errors": self._counts[svc],
                "last_error": errs[-1]["timestamp"] if errs else None,
                "degraded": self.is_degraded(svc),
            }
            for svc, errs in self._errors.items()
        }


# Singleton
_tracker = ErrorTracker()


def get_error_tracker() -> ErrorTracker:
    return _tracker


def retry_async(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    exponential: bool = True,
    retryable_exceptions: tuple = (Exception,),
    service_name: str = "",
):
    """Decorator para retry automático com backoff exponencial em funções async."""

    def decorator(func: Callable):
        svc = service_name or func.__qualname__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    _tracker.record(svc, e, f"attempt {attempt}/{max_retries}")
                    if attempt == max_retries:
                        logger.error(
                            "Falha definitiva em %s após %d tentativas: %s",
                            svc, max_retries, e,
                        )
                        raise
                    delay = base_delay * (2 ** (attempt - 1)) if exponential else base_delay
                    delay = min(delay, max_delay)
                    jitter = random.uniform(0, delay * 0.3)
                    logger.warning(
                        "Retry %d/%d para %s em %.1fs: %s",
                        attempt, max_retries, svc, delay + jitter, e,
                    )
                    await asyncio.sleep(delay + jitter)
            raise last_exception  # unreachable, but type-safe

        return wrapper

    return decorator


def retry_sync(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    service_name: str = "",
):
    """Decorator para retry automático em funções síncronas."""

    def decorator(func: Callable):
        svc = service_name or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    _tracker.record(svc, e, f"attempt {attempt}/{max_retries}")
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    delay = min(delay, max_delay)
                    jitter = random.uniform(0, delay * 0.3)
                    time.sleep(delay + jitter)
            raise last_exception

        return wrapper

    return decorator


def graceful_fallback(fallback_value: Any = None, service_name: str = ""):
    """Decorator que retorna fallback em vez de propagar exceção.
    
    Útil para serviços não-críticos (cache, métricas, notificações).
    """

    def decorator(func: Callable):
        svc = service_name or func.__qualname__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                _tracker.record(svc, e, "graceful_fallback")
                logger.warning("Fallback ativo para %s: %s", svc, e)
                return fallback_value() if callable(fallback_value) else fallback_value

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _tracker.record(svc, e, "graceful_fallback")
                logger.warning("Fallback ativo para %s: %s", svc, e)
                return fallback_value() if callable(fallback_value) else fallback_value

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
