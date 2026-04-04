"""
Enterprise Notifications System - ForgeCad
Sistema completo de notificações em tempo real.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import asyncio

# ── Enums ──
class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    WEBHOOK = "webhook"

# ── Data Classes ──
@dataclass
class Notification:
    id: str
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.MEDIUM
    user_id: Optional[str] = None
    channel: NotificationChannel = NotificationChannel.IN_APP
    created_at: datetime = field(default_factory=datetime.now)
    read: bool = False
    read_at: Optional[datetime] = None
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type.value,
            "priority": self.priority.value,
            "user_id": self.user_id,
            "channel": self.channel.value,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "action_url": self.action_url,
            "metadata": self.metadata
        }

@dataclass
class NotificationPreference:
    user_id: str
    email_enabled: bool = True
    push_enabled: bool = True
    sms_enabled: bool = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"
    types_enabled: List[str] = field(default_factory=lambda: ["info", "success", "warning", "error", "alert"])
    
    def to_dict(self) -> Dict:
        return asdict(self)

# ── Notification Engine ──
class NotificationEngine:
    """Motor principal de notificações."""
    
    def __init__(self):
        self.notifications: Dict[str, List[Notification]] = {}  # por user_id
        self.global_notifications: List[Notification] = []
        self.preferences: Dict[str, NotificationPreference] = {}
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}  # SSE subscribers
        self._notification_counter = 0
    
    def _generate_id(self) -> str:
        self._notification_counter += 1
        return f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._notification_counter:04d}"
    
    async def send(
        self,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        user_id: Optional[str] = None,
        channels: List[NotificationChannel] = None,
        action_url: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Notification:
        """Envia uma notificação."""
        channels = channels or [NotificationChannel.IN_APP]
        
        notification = Notification(
            id=self._generate_id(),
            title=title,
            message=message,
            type=type,
            priority=priority,
            user_id=user_id,
            channel=channels[0],
            action_url=action_url,
            metadata=metadata or {}
        )
        
        # Armazenar notificação
        if user_id:
            if user_id not in self.notifications:
                self.notifications[user_id] = []
            self.notifications[user_id].append(notification)
            
            # Manter apenas últimas 500 por usuário
            if len(self.notifications[user_id]) > 500:
                self.notifications[user_id] = self.notifications[user_id][-500:]
        else:
            self.global_notifications.append(notification)
            if len(self.global_notifications) > 1000:
                self.global_notifications = self.global_notifications[-1000:]
        
        # Notificar subscribers SSE
        await self._notify_subscribers(notification)
        
        # Processar outros canais
        for channel in channels:
            if channel == NotificationChannel.EMAIL:
                await self._send_email(notification)
            elif channel == NotificationChannel.PUSH:
                await self._send_push(notification)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook(notification)
        
        return notification
    
    async def _notify_subscribers(self, notification: Notification):
        """Notifica subscribers SSE."""
        user_id = notification.user_id or "global"
        if user_id in self.subscribers:
            for queue in self.subscribers[user_id]:
                try:
                    await queue.put(notification.to_dict())
                except:
                    pass
    
    async def _send_email(self, notification: Notification):
        """Envia notificação por email (placeholder)."""
        # Em produção: integrar com SendGrid, AWS SES, etc.
        pass
    
    async def _send_push(self, notification: Notification):
        """Envia push notification (placeholder)."""
        # Em produção: integrar com Firebase, OneSignal, etc.
        pass
    
    async def _send_webhook(self, notification: Notification):
        """Envia para webhook (placeholder)."""
        # Em produção: fazer HTTP POST para URL configurada
        pass
    
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """Retorna notificações de um usuário."""
        notifications = self.notifications.get(user_id, [])
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        return [n.to_dict() for n in notifications[-limit:]]
    
    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Marca notificação como lida."""
        if user_id in self.notifications:
            for notif in self.notifications[user_id]:
                if notif.id == notification_id:
                    notif.read = True
                    notif.read_at = datetime.now()
                    return True
        return False
    
    def mark_all_as_read(self, user_id: str) -> int:
        """Marca todas notificações como lidas."""
        count = 0
        if user_id in self.notifications:
            for notif in self.notifications[user_id]:
                if not notif.read:
                    notif.read = True
                    notif.read_at = datetime.now()
                    count += 1
        return count
    
    def get_unread_count(self, user_id: str) -> int:
        """Retorna contagem de não lidas."""
        if user_id in self.notifications:
            return sum(1 for n in self.notifications[user_id] if not n.read)
        return 0
    
    def subscribe(self, user_id: str, queue: asyncio.Queue):
        """Adiciona subscriber SSE."""
        if user_id not in self.subscribers:
            self.subscribers[user_id] = []
        self.subscribers[user_id].append(queue)
    
    def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        """Remove subscriber SSE."""
        if user_id in self.subscribers:
            self.subscribers[user_id] = [q for q in self.subscribers[user_id] if q != queue]


# ── Singleton ──
_notification_engine: Optional[NotificationEngine] = None

def get_notification_engine() -> NotificationEngine:
    global _notification_engine
    if _notification_engine is None:
        _notification_engine = NotificationEngine()
    return _notification_engine


# ── Helper Functions ──
async def notify_success(title: str, message: str, user_id: str = None, **kwargs):
    engine = get_notification_engine()
    return await engine.send(title, message, NotificationType.SUCCESS, user_id=user_id, **kwargs)

async def notify_error(title: str, message: str, user_id: str = None, **kwargs):
    engine = get_notification_engine()
    return await engine.send(title, message, NotificationType.ERROR, 
                            priority=NotificationPriority.HIGH, user_id=user_id, **kwargs)

async def notify_warning(title: str, message: str, user_id: str = None, **kwargs):
    engine = get_notification_engine()
    return await engine.send(title, message, NotificationType.WARNING, user_id=user_id, **kwargs)

async def notify_alert(title: str, message: str, user_id: str = None, **kwargs):
    engine = get_notification_engine()
    return await engine.send(title, message, NotificationType.ALERT, 
                            priority=NotificationPriority.URGENT, user_id=user_id, **kwargs)


# ── FastAPI Routes ──
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

class NotificationInput(BaseModel):
    title: str
    message: str
    type: str = "info"
    priority: str = "medium"
    user_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = {}

class PreferenceInput(BaseModel):
    email_enabled: bool = True
    push_enabled: bool = True
    sms_enabled: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None

@router.get("")
async def get_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = Query(default=50, le=200)
):
    """Retorna notificações do usuário."""
    engine = get_notification_engine()
    notifications = engine.get_user_notifications(user_id, unread_only, limit)
    unread_count = engine.get_unread_count(user_id)
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total": len(notifications)
    }

@router.post("")
async def create_notification(notification: NotificationInput):
    """Cria uma nova notificação."""
    engine = get_notification_engine()
    notif = await engine.send(
        title=notification.title,
        message=notification.message,
        type=NotificationType(notification.type),
        priority=NotificationPriority(notification.priority),
        user_id=notification.user_id,
        action_url=notification.action_url,
        metadata=notification.metadata
    )
    return notif.to_dict()

@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, user_id: str):
    """Marca notificação como lida."""
    engine = get_notification_engine()
    success = engine.mark_as_read(notification_id, user_id)
    if success:
        return {"status": "marked_as_read"}
    raise HTTPException(status_code=404, detail="Notification not found")

@router.post("/read-all")
async def mark_all_read(user_id: str):
    """Marca todas notificações como lidas."""
    engine = get_notification_engine()
    count = engine.mark_all_as_read(user_id)
    return {"status": "success", "marked_count": count}

@router.get("/count")
async def get_unread_count(user_id: str):
    """Retorna contagem de não lidas."""
    engine = get_notification_engine()
    return {"unread_count": engine.get_unread_count(user_id)}

@router.get("/stream")
async def notification_stream(user_id: str):
    """Stream SSE de notificações em tempo real."""
    engine = get_notification_engine()
    queue = asyncio.Queue()
    engine.subscribe(user_id, queue)
    
    async def event_generator():
        try:
            while True:
                notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(notification)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except:
            pass
        finally:
            engine.unsubscribe(user_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@router.get("/preferences")
async def get_preferences(user_id: str):
    """Retorna preferências de notificação."""
    engine = get_notification_engine()
    prefs = engine.preferences.get(user_id, NotificationPreference(user_id=user_id))
    return prefs.to_dict()

@router.put("/preferences")
async def update_preferences(user_id: str, prefs: PreferenceInput):
    """Atualiza preferências de notificação."""
    engine = get_notification_engine()
    engine.preferences[user_id] = NotificationPreference(
        user_id=user_id,
        email_enabled=prefs.email_enabled,
        push_enabled=prefs.push_enabled,
        sms_enabled=prefs.sms_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end
    )
    return {"status": "updated"}
