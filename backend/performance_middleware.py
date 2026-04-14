"""
═══════════════════════════════════════════════════════════════════════════════
  PERFORMANCE PROFILER MIDDLEWARE — Mede latência e identifica gargalos
  Integra com SystemMonitor para visibilidade total
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("engcad.profiler")


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware que mede latência de cada request e registra métricas."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.monotonic()

        # Injetar request_id no state
        request.state.request_id = request_id

        response: Optional[Response] = None
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._record(request, 500, elapsed_ms, request_id)
            raise

        elapsed_ms = (time.monotonic() - start) * 1000
        status_code = response.status_code if response else 500

        # Headers de performance
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"

        self._record(request, status_code, elapsed_ms, request_id)

        # Log slow requests
        if elapsed_ms > 3000:
            logger.warning(
                "SLOW REQUEST [%s]: %s %s → %d em %.0fms",
                request_id[:8], request.method, request.url.path,
                status_code, elapsed_ms,
            )

        return response

    def _record(self, request: Request, status_code: int, elapsed_ms: float, request_id: str) -> None:
        """Registra métricas no SystemMonitor."""
        try:
            from backend.system_monitor import get_monitor
            monitor = get_monitor()
            path = request.url.path.rstrip("/") or "/"
            # Normalizar caminhos com IDs para evitar cardinality explosion
            parts = path.split("/")
            normalized = []
            for part in parts:
                if part.isdigit() or (len(part) > 20 and "-" in part):
                    normalized.append(":id")
                else:
                    normalized.append(part)
            normalized_path = "/".join(normalized)
            monitor.record_request(normalized_path, request.method, status_code, elapsed_ms)
        except Exception:
            pass  # Monitor não pode quebrar o request
