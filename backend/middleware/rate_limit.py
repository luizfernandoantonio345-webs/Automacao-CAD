"""
backend/middleware/rate_limit.py
---------------------------------
Redis sliding-window rate limiter middleware for FastAPI.

Limits requests per IP using a sorted set in Redis (score = timestamp in ms).
Window: 60 seconds, configurable per endpoint via decorator.

Usage (route-level):
    @router.get("/endpoint")
    @rate_limit(requests=10, window=60)
    async def endpoint(request: Request): ...

Global middleware registered in server.py:
    app.add_middleware(RateLimitMiddleware, requests=120, window=60)
"""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("engcad.rate_limit")

# ─────────────────────────────────────────────────────────────────────────────
# Redis helper
# ─────────────────────────────────────────────────────────────────────────────

async def _check_rate_limit(redis_client, key: str, max_requests: int, window_sec: int) -> tuple[bool, int]:
    """
    Sliding window algorithm using Redis sorted set.
    Returns (allowed: bool, remaining: int).
    """
    now_ms = int(time.time() * 1000)
    window_start = now_ms - window_sec * 1000

    pipe = redis_client.pipeline()
    # Remove expired entries
    pipe.zremrangebyscore(key, 0, window_start)
    # Count current window
    pipe.zcard(key)
    # Add current request
    pipe.zadd(key, {str(now_ms): now_ms})
    # Set TTL so keys expire automatically
    pipe.expire(key, window_sec + 1)
    results = await pipe.execute()

    current_count: int = results[1]
    remaining = max(0, max_requests - current_count - 1)
    allowed = current_count < max_requests
    return allowed, remaining


# ─────────────────────────────────────────────────────────────────────────────
# Global middleware
# ─────────────────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a global sliding-window rate limit to all requests."""

    def __init__(
        self,
        app: ASGIApp,
        requests: int = 120,
        window: int = 60,
        exclude_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.requests = requests
        self.window = window
        self.exclude_paths: list[str] = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        key = f"rl:global:{client_ip}"

        try:
            allowed, remaining = await _check_rate_limit(redis, key, self.requests, self.window)
        except Exception as exc:
            logger.warning("Rate limiter Redis error: %s", exc)
            return await call_next(request)

        if not allowed:
            return Response(
                content='{"detail":"Too Many Requests"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(self.window),
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(self.window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window)
        return response


# ─────────────────────────────────────────────────────────────────────────────
# Route-level decorator
# ─────────────────────────────────────────────────────────────────────────────

def rate_limit(requests: int = 30, window: int = 60):
    """
    Decorator for individual routes.

    @router.post("/login")
    @rate_limit(requests=5, window=60)
    async def login(request: Request, ...): ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is not None:
                redis = getattr(request.app.state, "redis", None)
                if redis is not None:
                    client_ip = _get_client_ip(request)
                    route = request.url.path
                    key = f"rl:route:{route}:{client_ip}"
                    try:
                        allowed, remaining = await _check_rate_limit(redis, key, requests, window)
                        if not allowed:
                            raise HTTPException(
                                status_code=429,
                                detail="Too Many Requests",
                                headers={
                                    "Retry-After": str(window),
                                    "X-RateLimit-Limit": str(requests),
                                    "X-RateLimit-Remaining": "0",
                                },
                            )
                    except HTTPException:
                        raise
                    except Exception as exc:
                        logger.warning("Route rate-limiter Redis error: %s", exc)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting trusted X-Forwarded-For from proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take only the first (client) IP; never trust the full chain blindly
        ip = forwarded_for.split(",")[0].strip()
        # Basic sanity check: IPv4/IPv6 chars only
        if all(c in "0123456789abcdefABCDEF.:[]" for c in ip):
            return ip
    return request.client.host if request.client else "unknown"
