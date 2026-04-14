"""
Redis Session Management for FastAPI Production Deployment
Replaces in-memory sessions with persistent Redis backend
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════════
# REDIS SESSION MANAGER
# ════════════════════════════════════════════════════════════════════════════════

class RedisSessionManager:
    """
    Manages user sessions using Redis backend.
    Falls back to in-memory storage if Redis is unavailable.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.use_redis = False
        self.in_memory_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES", "1440"))
        
        # Lazy initialization of Redis client
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection (async, can be deferred)"""
        if self._initialized:
            return
        
        try:
            import redis.asyncio as redis
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Test connection
            await self.redis_client.ping()
            self.use_redis = True
            logger.info("✓ Redis session manager inicializado com sucesso")
            
        except Exception as e:
            logger.warning(f"⚠ Redis não disponível, usando sessões em memória: {e}")
            self.use_redis = False
            self.redis_client = None
        
        self._initialized = True
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data by ID"""
        await self.initialize()
        
        try:
            if self.use_redis and self.redis_client:
                session_data = await self.redis_client.get(f"session:{session_id}")
                if session_data:
                    return json.loads(session_data)
                return None
            else:
                return self.in_memory_sessions.get(session_id)
        except Exception as e:
            logger.error(f"Erro ao recuperar sessão {session_id}: {e}")
            return None
    
    async def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl_minutes: Optional[int] = None
    ) -> bool:
        """Store session data with automatic expiration"""
        await self.initialize()
        
        ttl = ttl_minutes or self.session_timeout_minutes
        
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.setex(
                    f"session:{session_id}",
                    ttl * 60,  # Convert minutes to seconds
                    json.dumps(data, default=str)
                )
                return True
            else:
                self.in_memory_sessions[session_id] = data
                return True
        except Exception as e:
            logger.error(f"Erro ao salvar sessão {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session data"""
        await self.initialize()
        
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(f"session:{session_id}")
                return True
            else:
                self.in_memory_sessions.pop(session_id, None)
                return True
        except Exception as e:
            logger.error(f"Erro ao deletar sessão {session_id}: {e}")
            return False
    
    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update specific fields in session data"""
        await self.initialize()
        
        try:
            current_data = await self.get_session(session_id)
            if current_data:
                current_data.update(updates)
                return await self.set_session(session_id, current_data)
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar sessão {session_id}: {e}")
            return False
    
    async def exists(self, session_id: str) -> bool:
        """Check if session exists"""
        await self.initialize()
        
        try:
            if self.use_redis and self.redis_client:
                exists = await self.redis_client.exists(f"session:{session_id}")
                return bool(exists)
            else:
                return session_id in self.in_memory_sessions
        except Exception as e:
            logger.error(f"Erro ao verificar sessão {session_id}: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Conexão Redis fechada")


# ════════════════════════════════════════════════════════════════════════════════
# GLOBAL SESSION MANAGER INSTANCE
# ════════════════════════════════════════════════════════════════════════════════

_session_manager: Optional[RedisSessionManager] = None

def get_session_manager() -> RedisSessionManager:
    """Get or create global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = RedisSessionManager()
    return _session_manager

async def initialize_session_manager():
    """Initialize the global session manager (call on app startup)"""
    manager = get_session_manager()
    await manager.initialize()

async def close_session_manager():
    """Close the global session manager (call on app shutdown)"""
    global _session_manager
    if _session_manager:
        await _session_manager.close()


# ════════════════════════════════════════════════════════════════════════════════
# SESSION MIDDLEWARE
# ════════════════════════════════════════════════════════════════════════════════

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import secrets

class SessionMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for Redis-backed session management.
    Automatically manages session cookies and persistence.
    """
    
    COOKIE_NAME = "session_id"
    COOKIE_MAX_AGE = int(os.getenv("SESSION_TIMEOUT_MINUTES", "1440")) * 60
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with session support"""
        
        manager = get_session_manager()
        
        # Try to get existing session
        session_id = request.cookies.get(self.COOKIE_NAME)
        
        if session_id and await manager.exists(session_id):
            request.state.session_id = session_id
            request.state.session = await manager.get_session(session_id)
        else:
            # Create new session
            session_id = secrets.token_urlsafe(32)
            request.state.session_id = session_id
            request.state.session = {
                "created_at": datetime.now().isoformat(),
                "user_id": None,
                "permissions": [],
            }
            await manager.set_session(session_id, request.state.session)
        
        response = await call_next(request)
        
        # Save updated session
        if hasattr(request.state, "session"):
            await manager.set_session(session_id, request.state.session)
        
        # Set cookie
        response.set_cookie(
            self.COOKIE_NAME,
            session_id,
            max_age=self.COOKIE_MAX_AGE,
            httponly=True,
            secure=os.getenv("ENVIRONMENT") == "production",
            samesite="Lax",
        )
        
        return response


# ════════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

async def set_user_session(user_id: str, session_id: str, user_data: Dict[str, Any]) -> bool:
    """Helper to set user data in session"""
    manager = get_session_manager()
    return await manager.update_session(session_id, {
        "user_id": user_id,
        "user_data": user_data,
        "last_activity": datetime.now().isoformat(),
    })

async def get_user_from_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Helper to retrieve user from session"""
    manager = get_session_manager()
    session = await manager.get_session(session_id)
    return session.get("user_data") if session else None

async def invalidate_session(session_id: str) -> bool:
    """Helper to invalidate (logout) a session"""
    manager = get_session_manager()
    return await manager.delete_session(session_id)
