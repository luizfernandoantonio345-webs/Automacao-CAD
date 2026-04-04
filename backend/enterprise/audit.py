"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE AUDIT LOGGER
  Sistema de Auditoria Completo para Compliance e Rastreabilidade
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Ações que podem ser auditadas."""
    # Autenticação
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGE = "auth.password_change"
    MFA_ENABLED = "auth.mfa_enabled"
    
    # Projetos
    PROJECT_CREATE = "project.create"
    PROJECT_UPDATE = "project.update"
    PROJECT_DELETE = "project.delete"
    PROJECT_EXPORT = "project.export"
    PROJECT_APPROVE = "project.approve"
    PROJECT_REJECT = "project.reject"
    
    # Desenhos
    DRAWING_UPLOAD = "drawing.upload"
    DRAWING_ANALYZE = "drawing.analyze"
    DRAWING_MODIFY = "drawing.modify"
    DRAWING_EXPORT = "drawing.export"
    
    # IAs
    AI_EXECUTE = "ai.execute"
    AI_CONFIG_CHANGE = "ai.config_change"
    AI_TRAIN = "ai.train"
    
    # Admin
    USER_CREATE = "admin.user_create"
    USER_UPDATE = "admin.user_update"
    USER_DELETE = "admin.user_delete"
    ROLE_ASSIGN = "admin.role_assign"
    PERMISSION_CHANGE = "admin.permission_change"
    SETTINGS_CHANGE = "admin.settings_change"
    
    # Sistema
    BACKUP_CREATE = "system.backup_create"
    BACKUP_RESTORE = "system.backup_restore"
    CONFIG_CHANGE = "system.config_change"
    INTEGRATION_CONNECT = "system.integration_connect"
    
    # Dados
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    DATA_DELETE = "data.delete"
    REPORT_GENERATE = "data.report_generate"


class AuditSeverity(str, Enum):
    """Níveis de severidade para auditoria."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Evento de auditoria."""
    id: str
    timestamp: str
    action: AuditAction
    severity: AuditSeverity
    user_id: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str]
    duration_ms: Optional[float]
    tenant_id: Optional[str]
    checksum: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Sistema de auditoria Enterprise."""
    
    _instance: Optional['AuditLogger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.events: List[AuditEvent] = []
        self.max_events = 100000
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Inicializa storage de auditoria."""
        logger.info("AuditLogger initialized with in-memory storage")
    
    def _generate_checksum(self, data: Dict[str, Any]) -> str:
        """Gera checksum para integridade do evento."""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def log(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
    ) -> AuditEvent:
        """Registra um evento de auditoria."""
        
        # Auto-determinar severidade se não especificada
        if severity is None:
            severity = self._determine_severity(action, success)
        
        # Criar dados base para checksum
        base_data = {
            "action": action.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            action=action,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            checksum=self._generate_checksum(base_data),
        )
        
        self.events.append(event)
        
        # Rotação de eventos
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Log também via logger padrão
        log_level = logging.WARNING if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL] else logging.INFO
        logger.log(
            log_level,
            f"AUDIT: {action.value} | user={user_email} | resource={resource_type}/{resource_id} | success={success}"
        )
        
        return event
    
    def _determine_severity(self, action: AuditAction, success: bool) -> AuditSeverity:
        """Determina severidade baseada na ação."""
        critical_actions = {
            AuditAction.USER_DELETE, AuditAction.ROLE_ASSIGN,
            AuditAction.BACKUP_RESTORE, AuditAction.DATA_DELETE,
            AuditAction.PERMISSION_CHANGE,
        }
        high_actions = {
            AuditAction.USER_CREATE, AuditAction.PROJECT_DELETE,
            AuditAction.SETTINGS_CHANGE, AuditAction.CONFIG_CHANGE,
            AuditAction.LOGIN_FAILED,
        }
        
        if not success:
            return AuditSeverity.HIGH
        if action in critical_actions:
            return AuditSeverity.CRITICAL
        if action in high_actions:
            return AuditSeverity.HIGH
        return AuditSeverity.MEDIUM
    
    def query(
        self,
        action: Optional[AuditAction] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """Consulta eventos de auditoria."""
        results = self.events.copy()
        
        if action:
            results = [e for e in results if e.action == action]
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]
        if severity:
            results = [e for e in results if e.severity == severity]
        if start_date:
            results = [e for e in results if datetime.fromisoformat(e.timestamp) >= start_date]
        if end_date:
            results = [e for e in results if datetime.fromisoformat(e.timestamp) <= end_date]
        
        # Ordenar por timestamp desc
        results.sort(key=lambda x: x.timestamp, reverse=True)
        
        return results[offset:offset + limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de auditoria."""
        from collections import Counter
        
        action_counts = Counter(e.action.value for e in self.events)
        severity_counts = Counter(e.severity.value for e in self.events)
        user_counts = Counter(e.user_email for e in self.events if e.user_email)
        success_rate = sum(1 for e in self.events if e.success) / max(len(self.events), 1) * 100
        
        return {
            "total_events": len(self.events),
            "by_action": dict(action_counts.most_common(20)),
            "by_severity": dict(severity_counts),
            "by_user": dict(user_counts.most_common(10)),
            "success_rate": round(success_rate, 2),
            "critical_events": sum(1 for e in self.events if e.severity == AuditSeverity.CRITICAL),
            "failed_events": sum(1 for e in self.events if not e.success),
        }
    
    def export_csv(self, events: List[AuditEvent]) -> str:
        """Exporta eventos para CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        if not events:
            return ""
        
        fieldnames = list(events[0].to_dict().keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in events:
            row = event.to_dict()
            row["details"] = json.dumps(row["details"])
            writer.writerow(row)
        
        return output.getvalue()


# Singleton instance
audit_logger = AuditLogger()
