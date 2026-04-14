"""
Enterprise Audit Trail System - ForgeCad
Sistema completo de auditoria e compliance.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import hashlib

# ── Enums ──
class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"
    SHARE = "share"
    DOWNLOAD = "download"
    UPLOAD = "upload"

class AuditCategory(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIG = "system_config"
    AI_OPERATION = "ai_operation"
    EXPORT = "export"
    INTEGRATION = "integration"
    SECURITY = "security"

class AuditSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ── Data Classes ──
@dataclass
class AuditEntry:
    id: str
    timestamp: datetime
    user_id: str
    user_email: str
    action: AuditAction
    category: AuditCategory
    severity: AuditSeverity
    resource_type: str
    resource_id: str
    description: str
    ip_address: str
    user_agent: str
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    duration_ms: float = 0
    hash: str = ""  # Hash para integridade
    
    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Computa hash para integridade do registro."""
        data = f"{self.id}{self.timestamp}{self.user_id}{self.action}{self.resource_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_email": self.user_email,
            "action": self.action.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "metadata": self.metadata,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "hash": self.hash
        }

# ── Audit Engine ──
class AuditEngine:
    """Motor principal de auditoria."""
    
    def __init__(self):
        self.entries: List[AuditEntry] = []
        self._entry_counter = 0
    
    def _generate_id(self) -> str:
        self._entry_counter += 1
        return f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._entry_counter:06d}"
    
    def log(
        self,
        user_id: str,
        user_email: str,
        action: AuditAction,
        category: AuditCategory,
        resource_type: str,
        resource_id: str,
        description: str,
        ip_address: str = "unknown",  # nosec B104 - default para log, não bind
        user_agent: str = "unknown",
        severity: AuditSeverity = AuditSeverity.LOW,
        request_data: Dict = None,
        response_data: Dict = None,
        metadata: Dict = None,
        success: bool = True,
        error_message: str = None,
        duration_ms: float = 0
    ) -> AuditEntry:
        """Registra uma entrada de auditoria."""
        entry = AuditEntry(
            id=self._generate_id(),
            timestamp=datetime.now(),
            user_id=user_id,
            user_email=user_email,
            action=action,
            category=category,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data or {},
            response_data=response_data or {},
            metadata=metadata or {},
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        self.entries.append(entry)
        
        # Manter apenas últimos 100000 registros em memória
        if len(self.entries) > 100000:
            self.entries = self.entries[-100000:]
        
        return entry
    
    def search(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        category: Optional[AuditCategory] = None,
        severity: Optional[AuditSeverity] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success_only: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """Pesquisa registros de auditoria."""
        results = self.entries
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if category:
            results = [e for e in results if e.category == category]
        if severity:
            results = [e for e in results if e.severity == severity]
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        if end_date:
            results = [e for e in results if e.timestamp <= end_date]
        if success_only is not None:
            results = [e for e in results if e.success == success_only]
        
        total = len(results)
        results = results[offset:offset + limit]
        
        return {
            "entries": [e.to_dict() for e in results],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def get_summary(self, period_hours: int = 24) -> Dict:
        """Retorna resumo de auditoria."""
        cutoff = datetime.now() - timedelta(hours=period_hours)
        recent = [e for e in self.entries if e.timestamp >= cutoff]
        
        # Contagens por categoria
        by_category = {}
        for entry in recent:
            cat = entry.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        
        # Contagens por ação
        by_action = {}
        for entry in recent:
            act = entry.action.value
            by_action[act] = by_action.get(act, 0) + 1
        
        # Contagens por severidade
        by_severity = {}
        for entry in recent:
            sev = entry.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        # Falhas
        failures = [e for e in recent if not e.success]
        
        # Top usuários
        user_counts = {}
        for entry in recent:
            user_counts[entry.user_email] = user_counts.get(entry.user_email, 0) + 1
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "period_hours": period_hours,
            "total_entries": len(recent),
            "by_category": by_category,
            "by_action": by_action,
            "by_severity": by_severity,
            "failure_count": len(failures),
            "success_rate": round((len(recent) - len(failures)) / max(len(recent), 1) * 100, 2),
            "top_users": [{"email": u, "count": c} for u, c in top_users],
            "recent_failures": [e.to_dict() for e in failures[-10:]]
        }
    
    def get_user_activity(self, user_id: str, days: int = 30) -> Dict:
        """Retorna atividade de um usuário."""
        cutoff = datetime.now() - timedelta(days=days)
        user_entries = [e for e in self.entries if e.user_id == user_id and e.timestamp >= cutoff]
        
        # Agrupar por dia
        by_day = {}
        for entry in user_entries:
            day = entry.timestamp.strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + 1
        
        # Ações mais comuns
        actions = {}
        for entry in user_entries:
            actions[entry.action.value] = actions.get(entry.action.value, 0) + 1
        
        return {
            "user_id": user_id,
            "total_actions": len(user_entries),
            "days_active": len(by_day),
            "activity_by_day": by_day,
            "top_actions": sorted(actions.items(), key=lambda x: x[1], reverse=True)[:10],
            "recent_entries": [e.to_dict() for e in user_entries[-20:]]
        }
    
    def get_security_report(self) -> Dict:
        """Retorna relatório de segurança."""
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        security_entries = [e for e in self.entries if e.category == AuditCategory.SECURITY]
        auth_entries = [e for e in self.entries if e.category == AuditCategory.AUTHENTICATION]
        
        # Falhas de login
        login_failures = [e for e in auth_entries if e.action == AuditAction.LOGIN and not e.success]
        
        # Ações críticas recentes
        critical_entries = [e for e in self.entries if e.severity == AuditSeverity.CRITICAL and e.timestamp >= day_ago]
        
        # IPs suspeitos (múltiplas falhas)
        failed_ips = {}
        for entry in login_failures:
            if entry.timestamp >= week_ago:
                failed_ips[entry.ip_address] = failed_ips.get(entry.ip_address, 0) + 1
        suspicious_ips = {ip: count for ip, count in failed_ips.items() if count >= 5}
        
        return {
            "generated_at": now.isoformat(),
            "security_events_24h": len([e for e in security_entries if e.timestamp >= day_ago]),
            "login_failures_24h": len([e for e in login_failures if e.timestamp >= day_ago]),
            "login_failures_7d": len([e for e in login_failures if e.timestamp >= week_ago]),
            "critical_events_24h": len(critical_entries),
            "critical_events": [e.to_dict() for e in critical_entries[:20]],
            "suspicious_ips": suspicious_ips,
            "recent_security_events": [e.to_dict() for e in security_entries[-20:]],
            "recommendations": self._get_security_recommendations(len(critical_entries), len(suspicious_ips))
        }
    
    def _get_security_recommendations(self, critical_count: int, suspicious_ip_count: int) -> List[str]:
        """Gera recomendações de segurança."""
        recommendations = []
        
        if critical_count > 5:
            recommendations.append("Alto número de eventos críticos - investigar imediatamente")
        if suspicious_ip_count > 0:
            recommendations.append(f"Bloquear {suspicious_ip_count} IP(s) suspeito(s) com múltiplas falhas de login")
        if critical_count == 0 and suspicious_ip_count == 0:
            recommendations.append("Sistema em estado saudável - continuar monitoramento")
        
        return recommendations
    
    def export_logs(
        self,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Exporta logs de auditoria."""
        entries = self.entries
        
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]
        
        if format == "json":
            return {
                "format": "json",
                "entries": [e.to_dict() for e in entries],
                "exported_at": datetime.now().isoformat(),
                "total": len(entries)
            }
        else:
            return {"error": "Formato não suportado"}


# ── Singleton ──
_audit_engine: Optional[AuditEngine] = None

def get_audit_engine() -> AuditEngine:
    global _audit_engine
    if _audit_engine is None:
        _audit_engine = AuditEngine()
    return _audit_engine


# ── Decorators ──
def audit_action(
    action: AuditAction,
    category: AuditCategory,
    resource_type: str,
    severity: AuditSeverity = AuditSeverity.LOW
):
    """Decorator para auditar automaticamente uma função."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            engine = get_audit_engine()
            start_time = datetime.now()
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Registrar sucesso
                engine.log(
                    user_id=kwargs.get("user_id", "system"),
                    user_email=kwargs.get("user_email", "system@forgecad.com"),
                    action=action,
                    category=category,
                    resource_type=resource_type,
                    resource_id=str(kwargs.get("resource_id", "unknown")),
                    description=f"{func.__name__} executado com sucesso",
                    severity=severity,
                    duration_ms=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Registrar falha
                engine.log(
                    user_id=kwargs.get("user_id", "system"),
                    user_email=kwargs.get("user_email", "system@forgecad.com"),
                    action=action,
                    category=category,
                    resource_type=resource_type,
                    resource_id=str(kwargs.get("resource_id", "unknown")),
                    description=f"{func.__name__} falhou",
                    severity=AuditSeverity.HIGH,
                    duration_ms=duration,
                    success=False,
                    error_message=str(e)
                )
                
                raise
        
        return wrapper
    return decorator


# ── FastAPI Routes ──
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])

class AuditLogInput(BaseModel):
    user_id: str
    user_email: str
    action: str
    category: str
    resource_type: str
    resource_id: str
    description: str
    ip_address: str = "unknown"  # nosec B104 - default para log
    severity: str = "low"
    success: bool = True
    error_message: Optional[str] = None

@router.get("/logs")
async def get_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0
):
    """Retorna logs de auditoria com filtros."""
    engine = get_audit_engine()
    return engine.search(
        user_id=user_id,
        action=AuditAction(action) if action else None,
        category=AuditCategory(category) if category else None,
        severity=AuditSeverity(severity) if severity else None,
        resource_type=resource_type,
        limit=limit,
        offset=offset
    )

@router.post("/logs")
async def create_log(entry: AuditLogInput):
    """Cria um novo registro de auditoria."""
    engine = get_audit_engine()
    audit_entry = engine.log(
        user_id=entry.user_id,
        user_email=entry.user_email,
        action=AuditAction(entry.action),
        category=AuditCategory(entry.category),
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        description=entry.description,
        ip_address=entry.ip_address,
        severity=AuditSeverity(entry.severity),
        success=entry.success,
        error_message=entry.error_message
    )
    return audit_entry.to_dict()

@router.get("/summary")
async def get_summary(period_hours: int = 24):
    """Retorna resumo de auditoria."""
    engine = get_audit_engine()
    return engine.get_summary(period_hours)

@router.get("/user/{user_id}")
async def get_user_activity(user_id: str, days: int = 30):
    """Retorna atividade de um usuário."""
    engine = get_audit_engine()
    return engine.get_user_activity(user_id, days)

@router.get("/security-report")
async def get_security_report():
    """Retorna relatório de segurança."""
    engine = get_audit_engine()
    return engine.get_security_report()

@router.get("/export")
async def export_logs(
    format: str = "json",
    days_back: int = 7
):
    """Exporta logs de auditoria."""
    engine = get_audit_engine()
    start_date = datetime.now() - timedelta(days=days_back)
    return engine.export_logs(format=format, start_date=start_date)
