"""
═══════════════════════════════════════════════════════════════════════════════
  NOTIFICATIONS ENGINE - Sistema de Notificações Enterprise
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


# ════════════════════════════════════════════════════════════════════════════
# ENUMS & MODELS
# ════════════════════════════════════════════════════════════════════════════

class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationCategory(str, Enum):
    SYSTEM = "system"
    PROJECT = "project"
    AI = "ai"
    QUALITY = "quality"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    BILLING = "billing"


@dataclass
class Notification:
    id: str
    title: str
    message: str
    type: NotificationType
    priority: NotificationPriority
    category: NotificationCategory
    created_at: str
    read: bool = False
    dismissed: bool = False
    user_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS STORE
# ════════════════════════════════════════════════════════════════════════════

class NotificationsStore:
    """Gerencia notificações do sistema."""
    
    def __init__(self):
        self.notifications: Dict[str, Notification] = {}
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self._seed_demo_notifications()
    
    def _seed_demo_notifications(self):
        """Adiciona notificações de demonstração."""
        demo_notifications = [
            {
                "title": "Sistema atualizado para v2.0",
                "message": "Nova versão do ForgeCad com 8 IAs especializadas disponível.",
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.NORMAL,
                "category": NotificationCategory.SYSTEM,
            },
            {
                "title": "Análise de conflitos concluída",
                "message": "Projeto PRJ-2024-001: 3 conflitos detectados e resolvidos automaticamente.",
                "type": NotificationType.INFO,
                "priority": NotificationPriority.NORMAL,
                "category": NotificationCategory.AI,
            },
            {
                "title": "Novo projeto aguardando aprovação",
                "message": "Projeto REGAP-TOWER-12 passou pelo Quality Gate e aguarda aprovação final.",
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.HIGH,
                "category": NotificationCategory.PROJECT,
            },
            {
                "title": "Manutenção preventiva recomendada",
                "message": "IA detectou componentes com vida útil < 20%. Revisar relatório de manutenção.",
                "type": NotificationType.ALERT,
                "priority": NotificationPriority.HIGH,
                "category": NotificationCategory.MAINTENANCE,
            },
            {
                "title": "Backup diário concluído",
                "message": "Todos os projetos foram salvos com sucesso às 03:00.",
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.LOW,
                "category": NotificationCategory.SYSTEM,
            },
        ]
        
        for i, notif in enumerate(demo_notifications):
            self.create_notification(
                title=notif["title"],
                message=notif["message"],
                type=notif["type"],
                priority=notif["priority"],
                category=notif["category"],
            )
    
    def create_notification(
        self,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        category: NotificationCategory = NotificationCategory.SYSTEM,
        user_id: Optional[str] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Notification:
        """Cria uma nova notificação."""
        notif = Notification(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            type=type,
            priority=priority,
            category=category,
            created_at=datetime.now(UTC).isoformat(),
            user_id=user_id,
            action_url=action_url,
            metadata=metadata or {},
        )
        self.notifications[notif.id] = notif
        
        # Notificar subscribers (só se tiver event loop rodando)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._notify_subscribers(notif))
        except RuntimeError:
            # Sem event loop (ex: durante init) - notificação foi criada mas não broadcast
            pass
        
        # Manter apenas últimas 1000 notificações
        if len(self.notifications) > 1000:
            oldest = sorted(self.notifications.values(), key=lambda x: x.created_at)[:200]
            for n in oldest:
                del self.notifications[n.id]
        
        return notif
    
    async def _notify_subscribers(self, notif: Notification):
        """Envia notificação para todos os subscribers."""
        for queue in self._subscribers.values():
            try:
                await queue.put(notif)
            except Exception:
                pass
    
    def subscribe(self, subscriber_id: str) -> asyncio.Queue:
        """Cria uma subscription para receber notificações."""
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[subscriber_id] = queue
        return queue
    
    def unsubscribe(self, subscriber_id: str):
        """Remove subscription."""
        self._subscribers.pop(subscriber_id, None)
    
    def get_all(
        self,
        unread_only: bool = False,
        category: Optional[NotificationCategory] = None,
        limit: int = 50,
    ) -> List[Notification]:
        """Retorna lista de notificações."""
        notifications = list(self.notifications.values())
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        if category:
            notifications = [n for n in notifications if n.category == category]
        
        # Ordenar por prioridade e data
        priority_order = {
            NotificationPriority.URGENT: 0,
            NotificationPriority.HIGH: 1,
            NotificationPriority.NORMAL: 2,
            NotificationPriority.LOW: 3,
        }
        notifications.sort(
            key=lambda x: (priority_order.get(x.priority, 2), x.created_at),
            reverse=True
        )
        
        return notifications[:limit]
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Marca notificação como lida."""
        if notification_id in self.notifications:
            self.notifications[notification_id].read = True
            return True
        return False
    
    def mark_all_as_read(self) -> int:
        """Marca todas as notificações como lidas."""
        count = 0
        for notif in self.notifications.values():
            if not notif.read:
                notif.read = True
                count += 1
        return count
    
    def dismiss(self, notification_id: str) -> bool:
        """Descarta uma notificação."""
        if notification_id in self.notifications:
            self.notifications[notification_id].dismissed = True
            return True
        return False
    
    def get_unread_count(self) -> int:
        """Retorna contagem de não lidas."""
        return sum(1 for n in self.notifications.values() if not n.read and not n.dismissed)
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo das notificações."""
        all_notifs = [n for n in self.notifications.values() if not n.dismissed]
        
        by_type = {}
        by_category = {}
        by_priority = {}
        
        for n in all_notifs:
            by_type[n.type.value] = by_type.get(n.type.value, 0) + 1
            by_category[n.category.value] = by_category.get(n.category.value, 0) + 1
            by_priority[n.priority.value] = by_priority.get(n.priority.value, 0) + 1
        
        return {
            "total": len(all_notifs),
            "unread": self.get_unread_count(),
            "by_type": by_type,
            "by_category": by_category,
            "by_priority": by_priority,
        }


# Singleton
notifications_store = NotificationsStore()


# ════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ════════════════════════════════════════════════════════════════════════════

class CreateNotificationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: NotificationCategory = NotificationCategory.SYSTEM
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    type: str
    priority: str
    category: str
    created_at: str
    read: bool
    action_url: Optional[str]


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("")
async def get_notifications(
    unread_only: bool = Query(False),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Lista todas as notificações."""
    cat = NotificationCategory(category) if category else None
    notifications = notifications_store.get_all(
        unread_only=unread_only,
        category=cat,
        limit=limit,
    )
    
    return {
        "success": True,
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type.value,
                "priority": n.priority.value,
                "category": n.category.value,
                "created_at": n.created_at,
                "read": n.read,
                "action_url": n.action_url,
                "metadata": n.metadata,
            }
            for n in notifications if not n.dismissed
        ],
        "unread_count": notifications_store.get_unread_count(),
    }


@router.get("/summary")
async def get_notifications_summary():
    """Retorna resumo das notificações."""
    return {
        "success": True,
        **notifications_store.get_summary(),
    }


@router.post("")
async def create_notification(request: CreateNotificationRequest):
    """Cria uma nova notificação."""
    notif = notifications_store.create_notification(
        title=request.title,
        message=request.message,
        type=request.type,
        priority=request.priority,
        category=request.category,
        action_url=request.action_url,
        metadata=request.metadata,
    )
    
    return {
        "success": True,
        "notification": {
            "id": notif.id,
            "title": notif.title,
            "created_at": notif.created_at,
        },
    }


@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: str):
    """Marca notificação como lida."""
    if notifications_store.mark_as_read(notification_id):
        return {"success": True, "message": "Marked as read"}
    raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/read-all")
async def mark_all_as_read():
    """Marca todas as notificações como lidas."""
    count = notifications_store.mark_all_as_read()
    return {"success": True, "count": count}


@router.delete("/{notification_id}")
async def dismiss_notification(notification_id: str):
    """Descarta uma notificação."""
    if notifications_store.dismiss(notification_id):
        return {"success": True, "message": "Dismissed"}
    raise HTTPException(status_code=404, detail="Notification not found")


@router.get("/unread-count")
async def get_unread_count():
    """Retorna contagem de não lidas."""
    return {
        "success": True,
        "count": notifications_store.get_unread_count(),
    }


# ════════════════════════════════════════════════════════════════════════════
# NOTIFICATION TRIGGERS (para outros módulos)
# ════════════════════════════════════════════════════════════════════════════

def notify_project_created(project_name: str, company: str):
    """Trigger de notificação para novo projeto."""
    notifications_store.create_notification(
        title=f"Novo projeto criado",
        message=f"Projeto '{project_name}' da {company} foi criado com sucesso.",
        type=NotificationType.SUCCESS,
        priority=NotificationPriority.NORMAL,
        category=NotificationCategory.PROJECT,
        action_url=f"/project/{project_name}",
    )


def notify_ai_result(ai_name: str, result: str, project_id: str = None):
    """Trigger de notificação para resultado de IA."""
    notifications_store.create_notification(
        title=f"{ai_name} concluiu análise",
        message=result,
        type=NotificationType.INFO,
        priority=NotificationPriority.NORMAL,
        category=NotificationCategory.AI,
    )


def notify_quality_issue(project_name: str, issue_count: int, severity: str):
    """Trigger de notificação para problema de qualidade."""
    priority = NotificationPriority.URGENT if severity == "critical" else NotificationPriority.HIGH
    notifications_store.create_notification(
        title=f"Problemas de qualidade detectados",
        message=f"Projeto '{project_name}': {issue_count} problemas ({severity}) requerem atenção.",
        type=NotificationType.WARNING,
        priority=priority,
        category=NotificationCategory.QUALITY,
        action_url=f"/quality?project={project_name}",
    )


def notify_maintenance_required(component: str, health_percent: float):
    """Trigger de notificação para manutenção."""
    priority = NotificationPriority.URGENT if health_percent < 10 else NotificationPriority.HIGH
    notifications_store.create_notification(
        title=f"Manutenção preventiva recomendada",
        message=f"Componente '{component}' com {health_percent}% de vida útil. Revisar plano de manutenção.",
        type=NotificationType.ALERT,
        priority=priority,
        category=NotificationCategory.MAINTENANCE,
    )


def notify_system_alert(title: str, message: str, is_error: bool = False):
    """Trigger de notificação para alerta de sistema."""
    notifications_store.create_notification(
        title=title,
        message=message,
        type=NotificationType.ERROR if is_error else NotificationType.WARNING,
        priority=NotificationPriority.HIGH if is_error else NotificationPriority.NORMAL,
        category=NotificationCategory.SYSTEM,
    )
