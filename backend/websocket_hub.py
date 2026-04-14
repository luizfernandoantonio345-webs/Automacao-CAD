"""
═══════════════════════════════════════════════════════════════════════════════
  WEBSOCKET REAL-TIME HUB — Comunicação bidirecional multi-usuário
  Substitui SSE para operações que precisam de resposta em tempo real
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

logger = logging.getLogger("engcad.websocket")

router = APIRouter(tags=["websocket"])


class WSChannel(str, Enum):
    """Canais de WebSocket disponíveis."""
    SYSTEM = "system"           # Métricas de sistema
    CAD = "cad"                 # Operações CAD em tempo real
    CAM = "cam"                 # Jobs CNC e progresso
    AI = "ai"                   # Respostas de IA
    NOTIFICATIONS = "notifications"
    CHAT = "chat"               # Chat entre usuários
    TELEMETRY = "telemetry"     # Dados de telemetria
    COLLABORATION = "collaboration"  # Edição colaborativa


@dataclass
class WSClient:
    """Representa um cliente WebSocket conectado."""
    id: str
    websocket: WebSocket
    user_email: str
    channels: Set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)
    messages_sent: int = 0
    messages_received: int = 0
    tenant_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_email": self.user_email,
            "channels": list(self.channels),
            "connected_at": self.connected_at,
            "last_ping": self.last_ping,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
        }


class ConnectionManager:
    """Gerencia todas as conexões WebSocket ativas."""

    def __init__(self, max_connections_per_user: int = 5, max_total: int = 1000):
        self.max_per_user = max_connections_per_user
        self.max_total = max_total
        self._clients: Dict[str, WSClient] = {}
        self._user_clients: Dict[str, Set[str]] = defaultdict(set)
        self._channel_clients: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._message_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._stats = {
            "total_connections": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "peak_connections": 0,
            "total_errors": 0,
        }

    async def connect(
        self,
        websocket: WebSocket,
        user_email: str,
        channels: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> WSClient:
        """Aceita e registra uma nova conexão WebSocket."""
        async with self._lock:
            # Verificar limites
            if len(self._clients) >= self.max_total:
                await websocket.close(code=1013, reason="Servidor lotado")
                raise ConnectionError("Limite total de conexões atingido")

            user_conns = self._user_clients.get(user_email, set())
            if len(user_conns) >= self.max_per_user:
                # Desconectar a mais antiga
                oldest_id = min(
                    user_conns,
                    key=lambda cid: self._clients[cid].connected_at
                    if cid in self._clients else float("inf"),
                )
                if oldest_id in self._clients:
                    await self._disconnect_client(oldest_id, reason="Nova conexão aberta")

            await websocket.accept()

            client_id = str(uuid.uuid4())
            client = WSClient(
                id=client_id,
                websocket=websocket,
                user_email=user_email,
                channels=set(channels or [WSChannel.SYSTEM.value]),
                tenant_id=tenant_id,
            )

            self._clients[client_id] = client
            self._user_clients[user_email].add(client_id)
            for ch in client.channels:
                self._channel_clients[ch].add(client_id)

            self._stats["total_connections"] += 1
            current = len(self._clients)
            if current > self._stats["peak_connections"]:
                self._stats["peak_connections"] = current

            logger.info(
                "WS conectado: %s (user=%s, channels=%s)",
                client_id[:8], user_email, client.channels,
            )
            return client

    async def disconnect(self, client_id: str) -> None:
        """Desconecta um cliente."""
        async with self._lock:
            await self._disconnect_client(client_id)

    async def _disconnect_client(self, client_id: str, reason: str = "") -> None:
        client = self._clients.pop(client_id, None)
        if not client:
            return
        self._user_clients[client.user_email].discard(client_id)
        if not self._user_clients[client.user_email]:
            del self._user_clients[client.user_email]
        for ch in client.channels:
            self._channel_clients[ch].discard(client_id)
        try:
            if client.websocket.client_state == WebSocketState.CONNECTED:
                await client.websocket.close(code=1000, reason=reason)
        except Exception:
            pass
        logger.info("WS desconectado: %s (user=%s)", client_id[:8], client.user_email)

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Envia mensagem para um cliente específico."""
        client = self._clients.get(client_id)
        if not client:
            return False
        try:
            await client.websocket.send_json(message)
            client.messages_sent += 1
            self._stats["total_messages_sent"] += 1
            return True
        except Exception as e:
            self._stats["total_errors"] += 1
            logger.warning("Erro ao enviar WS para %s: %s", client_id[:8], e)
            await self.disconnect(client_id)
            return False

    async def send_to_user(self, user_email: str, message: Dict[str, Any]) -> int:
        """Envia mensagem para todas as conexões de um usuário."""
        client_ids = list(self._user_clients.get(user_email, set()))
        sent = 0
        for cid in client_ids:
            if await self.send_to_client(cid, message):
                sent += 1
        return sent

    async def broadcast_to_channel(
        self,
        channel: str,
        message: Dict[str, Any],
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """Envia mensagem para todos os clientes em um canal."""
        client_ids = list(self._channel_clients.get(channel, set()))
        exclude = exclude or set()
        sent = 0
        tasks = []
        for cid in client_ids:
            if cid not in exclude:
                tasks.append(self.send_to_client(cid, message))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        sent = sum(1 for r in results if r is True)
        return sent

    async def broadcast_all(self, message: Dict[str, Any]) -> int:
        """Envia mensagem para todos os clientes conectados."""
        tasks = [
            self.send_to_client(cid, message)
            for cid in list(self._clients.keys())
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if r is True)

    def on_message(self, message_type: str):
        """Decorator para registrar handlers de mensagens."""
        def decorator(func: Callable):
            self._message_handlers[message_type].append(func)
            return func
        return decorator

    async def handle_message(self, client_id: str, data: Dict[str, Any]) -> None:
        """Processa uma mensagem recebida de um cliente."""
        client = self._clients.get(client_id)
        if not client:
            return
        client.messages_received += 1
        self._stats["total_messages_received"] += 1

        msg_type = data.get("type", "unknown")
        handlers = self._message_handlers.get(msg_type, [])

        if msg_type == "ping":
            client.last_ping = time.time()
            await self.send_to_client(client_id, {
                "type": "pong",
                "ts": datetime.now(UTC).isoformat(),
            })
            return

        if msg_type == "subscribe":
            channels = data.get("channels", [])
            async with self._lock:
                for ch in channels:
                    client.channels.add(ch)
                    self._channel_clients[ch].add(client_id)
            await self.send_to_client(client_id, {
                "type": "subscribed",
                "channels": list(client.channels),
            })
            return

        if msg_type == "unsubscribe":
            channels = data.get("channels", [])
            async with self._lock:
                for ch in channels:
                    client.channels.discard(ch)
                    self._channel_clients[ch].discard(client_id)
            return

        for handler in handlers:
            try:
                await handler(client, data)
            except Exception as e:
                logger.error("Erro no handler WS '%s': %s", msg_type, e)
                await self.send_to_client(client_id, {
                    "type": "error",
                    "message": f"Erro ao processar '{msg_type}'",
                })

    async def cleanup_stale(self, timeout: float = 120.0) -> int:
        """Remove conexões inativas (sem ping recente)."""
        now = time.time()
        stale = [
            cid for cid, client in self._clients.items()
            if now - client.last_ping > timeout
        ]
        for cid in stale:
            await self.disconnect(cid)
        if stale:
            logger.info("Removidas %d conexões inativas", len(stale))
        return len(stale)

    @property
    def active_connections(self) -> int:
        return len(self._clients)

    @property
    def active_users(self) -> int:
        return len(self._user_clients)

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "active_connections": self.active_connections,
            "active_users": self.active_users,
            "channels": {
                ch: len(clients)
                for ch, clients in self._channel_clients.items()
                if clients
            },
        }

    def get_user_connections(self, user_email: str) -> List[Dict[str, Any]]:
        client_ids = self._user_clients.get(user_email, set())
        return [
            self._clients[cid].to_dict()
            for cid in client_ids
            if cid in self._clients
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

ws_manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP TASK
# ═══════════════════════════════════════════════════════════════════════════════

_cleanup_task: Optional[asyncio.Task] = None


async def _periodic_cleanup():
    while True:
        try:
            await asyncio.sleep(60)
            await ws_manager.cleanup_stale()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Erro no cleanup WS: %s", e)


def start_ws_cleanup():
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_periodic_cleanup())


def stop_ws_cleanup():
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    channels: Optional[str] = Query(None),
):
    """Endpoint principal de WebSocket."""
    import jwt as pyjwt

    # Autenticar via token na query string
    user_email = "anonymous"
    if token:
        try:
            secret = os.environ.get("JARVIS_SECRET", "")
            if secret:
                payload = pyjwt.decode(token, secret, algorithms=["HS256"])
                user_email = payload.get("user", "anonymous")
        except Exception:
            await websocket.close(code=4001, reason="Token inválido")
            return

    channel_list = channels.split(",") if channels else [WSChannel.SYSTEM.value]

    try:
        client = await ws_manager.connect(
            websocket=websocket,
            user_email=user_email,
            channels=channel_list,
        )
    except ConnectionError as e:
        logger.warning("Conexão WS recusada: %s", e)
        return

    # Enviar mensagem de boas-vindas
    await ws_manager.send_to_client(client.id, {
        "type": "connected",
        "client_id": client.id,
        "channels": list(client.channels),
        "server_time": datetime.now(UTC).isoformat(),
    })

    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(client.id, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(client.id)
    except Exception as e:
        logger.error("Erro WS para %s: %s", client.id[:8], e)
        await ws_manager.disconnect(client.id)


@router.get("/ws/stats")
async def ws_stats():
    """Estatísticas das conexões WebSocket."""
    return ws_manager.get_stats()


import os  # noqa: E402 — necessário para JARVIS_SECRET no websocket_endpoint
