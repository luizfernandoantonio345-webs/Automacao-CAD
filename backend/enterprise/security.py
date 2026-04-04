"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE SECURITY MANAGER
  Gerenciamento de Segurança Avançado
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import hashlib
import secrets
import re
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Tipos de eventos de segurança."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    IP_BLOCKED = "ip_blocked"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    PERMISSION_ESCALATION = "permission_escalation"
    DATA_EXPORT = "data_export"
    ADMIN_ACTION = "admin_action"


class ThreatLevel(str, Enum):
    """Níveis de ameaça."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Evento de segurança."""
    id: str
    type: SecurityEventType
    threat_level: ThreatLevel
    user_email: Optional[str]
    ip_address: str
    user_agent: Optional[str]
    details: Dict[str, Any]
    timestamp: str
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class IPReputation:
    """Reputação de um IP."""
    ip_address: str
    failed_attempts: int
    successful_logins: int
    last_attempt: str
    blocked: bool
    blocked_until: Optional[str]
    risk_score: float


@dataclass
class APIKey:
    """Chave de API."""
    id: str
    name: str
    key_hash: str  # Armazena apenas o hash
    key_prefix: str  # Primeiros 8 caracteres para identificação
    created_by: str
    created_at: str
    expires_at: Optional[str]
    last_used: Optional[str]
    scopes: Set[str]
    rate_limit: int  # Requests per hour
    active: bool


class SecurityManager:
    """Gerenciador de segurança Enterprise."""
    
    _instance: Optional['SecurityManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.events: List[SecurityEvent] = []
        self.ip_reputations: Dict[str, IPReputation] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.blocked_ips: Set[str] = set()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Configurações
        self.max_failed_attempts = 5
        self.block_duration_minutes = 30
        self.session_timeout_minutes = 60
        
        # Padrões suspeitos
        self.suspicious_patterns = [
            r"[<>'\";]",  # SQL/XSS injection
            r"\.\./",     # Path traversal
            r"(?i)(union|select|drop|delete|insert|update)\s",  # SQL keywords
        ]
        
        self._seed_demo_data()
        logger.info("SecurityManager initialized")
    
    def _seed_demo_data(self):
        """Adiciona dados de demonstração."""
        import uuid
        
        # Algumas chaves de API
        self.api_keys["key_demo"] = APIKey(
            id="key_demo",
            name="Demo Integration Key",
            key_hash=hashlib.sha256("demo_key_123".encode()).hexdigest(),
            key_prefix="demo_key",
            created_by="admin@demo.com",
            created_at=datetime.now(UTC).isoformat(),
            expires_at=None,
            last_used=datetime.now(UTC).isoformat(),
            scopes={"read", "write"},
            rate_limit=1000,
            active=True,
        )
        
        # Eventos de demonstração
        for i in range(10):
            self.events.append(SecurityEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                type=SecurityEventType.LOGIN_SUCCESS,
                threat_level=ThreatLevel.LOW,
                user_email="user@demo.com",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                details={},
                timestamp=(datetime.now(UTC) - timedelta(hours=i)).isoformat(),
            ))
    
    def record_event(
        self,
        event_type: SecurityEventType,
        ip_address: str,
        user_email: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityEvent:
        """Registra um evento de segurança."""
        import uuid
        
        threat_level = self._determine_threat_level(event_type, ip_address)
        
        event = SecurityEvent(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            type=event_type,
            threat_level=threat_level,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            timestamp=datetime.now(UTC).isoformat(),
        )
        
        self.events.append(event)
        
        # Manter apenas últimos 10000 eventos
        if len(self.events) > 10000:
            self.events = self.events[-10000:]
        
        # Atualizar reputação do IP
        self._update_ip_reputation(event)
        
        # Log eventos de alto risco
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            logger.warning(f"Security event: {event_type.value} from {ip_address} - {threat_level.value}")
        
        return event
    
    def _determine_threat_level(self, event_type: SecurityEventType, ip_address: str) -> ThreatLevel:
        """Determina o nível de ameaça do evento."""
        if event_type in [SecurityEventType.BRUTE_FORCE_ATTEMPT, SecurityEventType.PERMISSION_ESCALATION]:
            return ThreatLevel.CRITICAL
        elif event_type in [SecurityEventType.SUSPICIOUS_ACTIVITY, SecurityEventType.IP_BLOCKED]:
            return ThreatLevel.HIGH
        elif event_type in [SecurityEventType.LOGIN_FAILED, SecurityEventType.MFA_DISABLED]:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
    
    def _update_ip_reputation(self, event: SecurityEvent) -> None:
        """Atualiza reputação de um IP baseado no evento."""
        ip = event.ip_address
        
        if ip not in self.ip_reputations:
            self.ip_reputations[ip] = IPReputation(
                ip_address=ip,
                failed_attempts=0,
                successful_logins=0,
                last_attempt=event.timestamp,
                blocked=False,
                blocked_until=None,
                risk_score=0.0,
            )
        
        reputation = self.ip_reputations[ip]
        reputation.last_attempt = event.timestamp
        
        if event.type == SecurityEventType.LOGIN_FAILED:
            reputation.failed_attempts += 1
            reputation.risk_score = min(100, reputation.risk_score + 10)
            
            # Verificar se deve bloquear
            if reputation.failed_attempts >= self.max_failed_attempts:
                self._block_ip(ip)
        
        elif event.type == SecurityEventType.LOGIN_SUCCESS:
            reputation.successful_logins += 1
            reputation.failed_attempts = 0  # Reset
            reputation.risk_score = max(0, reputation.risk_score - 5)
    
    def _block_ip(self, ip_address: str) -> None:
        """Bloqueia um IP."""
        if ip_address in self.ip_reputations:
            reputation = self.ip_reputations[ip_address]
            reputation.blocked = True
            reputation.blocked_until = (
                datetime.now(UTC) + timedelta(minutes=self.block_duration_minutes)
            ).isoformat()
        
        self.blocked_ips.add(ip_address)
        
        self.record_event(
            SecurityEventType.IP_BLOCKED,
            ip_address,
            details={"reason": "Too many failed attempts"},
        )
        
        logger.warning(f"IP blocked: {ip_address}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Verifica se um IP está bloqueado."""
        if ip_address not in self.blocked_ips:
            return False
        
        reputation = self.ip_reputations.get(ip_address)
        if reputation and reputation.blocked_until:
            blocked_until = datetime.fromisoformat(reputation.blocked_until)
            if datetime.now(UTC) > blocked_until.replace(tzinfo=UTC):
                # Desbloquear
                self.blocked_ips.discard(ip_address)
                reputation.blocked = False
                reputation.blocked_until = None
                return False
        
        return True
    
    def check_input_safety(self, input_value: str) -> Dict[str, Any]:
        """Verifica se um input é seguro."""
        threats_found = []
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, input_value):
                threats_found.append({
                    "pattern": pattern,
                    "type": "injection_attempt",
                })
        
        return {
            "safe": len(threats_found) == 0,
            "threats": threats_found,
            "sanitized": re.sub(r"[<>'\";]", "", input_value),
        }
    
    def create_api_key(
        self,
        name: str,
        created_by: str,
        scopes: Set[str],
        rate_limit: int = 1000,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, str]:
        """Cria uma nova API key."""
        import uuid
        
        key_id = f"key_{uuid.uuid4().hex[:8]}"
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        now = datetime.now(UTC)
        expires_at = None
        if expires_in_days:
            expires_at = (now + timedelta(days=expires_in_days)).isoformat()
        
        api_key = APIKey(
            id=key_id,
            name=name,
            key_hash=key_hash,
            key_prefix=raw_key[:8],
            created_by=created_by,
            created_at=now.isoformat(),
            expires_at=expires_at,
            last_used=None,
            scopes=scopes,
            rate_limit=rate_limit,
            active=True,
        )
        
        self.api_keys[key_id] = api_key
        
        self.record_event(
            SecurityEventType.API_KEY_CREATED,
            "system",
            user_email=created_by,
            details={"key_id": key_id, "name": name},
        )
        
        # Retorna a chave completa apenas uma vez
        return {
            "key_id": key_id,
            "api_key": raw_key,  # IMPORTANTE: Só é mostrado uma vez!
            "prefix": raw_key[:8],
            "expires_at": expires_at,
        }
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Valida uma API key."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        for api_key in self.api_keys.values():
            if api_key.key_hash == key_hash:
                if not api_key.active:
                    return None
                
                if api_key.expires_at:
                    expires = datetime.fromisoformat(api_key.expires_at)
                    if datetime.now(UTC) > expires.replace(tzinfo=UTC):
                        api_key.active = False
                        return None
                
                api_key.last_used = datetime.now(UTC).isoformat()
                return api_key
        
        return None
    
    def revoke_api_key(self, key_id: str, revoked_by: str) -> bool:
        """Revoga uma API key."""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False
        
        api_key.active = False
        
        self.record_event(
            SecurityEventType.API_KEY_REVOKED,
            "system",
            user_email=revoked_by,
            details={"key_id": key_id},
        )
        
        return True
    
    def create_session(self, user_email: str, ip_address: str, user_agent: str) -> str:
        """Cria uma nova sessão."""
        session_id = secrets.token_urlsafe(32)
        
        self.active_sessions[session_id] = {
            "user_email": user_email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now(UTC).isoformat(),
            "last_activity": datetime.now(UTC).isoformat(),
        }
        
        self.record_event(
            SecurityEventType.SESSION_CREATED,
            ip_address,
            user_email=user_email,
            user_agent=user_agent,
        )
        
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Valida uma sessão."""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        last_activity = datetime.fromisoformat(session["last_activity"])
        if datetime.now(UTC) - last_activity.replace(tzinfo=UTC) > timedelta(minutes=self.session_timeout_minutes):
            self.invalidate_session(session_id)
            return None
        
        session["last_activity"] = datetime.now(UTC).isoformat()
        return session
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalida uma sessão."""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            self.record_event(
                SecurityEventType.SESSION_EXPIRED,
                session.get("ip_address", "unknown"),
                user_email=session.get("user_email"),
            )
            return True
        return False
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Retorna dados para dashboard de segurança."""
        now = datetime.now(UTC)
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        events_24h = [e for e in self.events if datetime.fromisoformat(e.timestamp).replace(tzinfo=UTC) >= last_24h]
        events_7d = [e for e in self.events if datetime.fromisoformat(e.timestamp).replace(tzinfo=UTC) >= last_7d]
        
        # Contar por tipo
        by_type = defaultdict(int)
        by_threat = defaultdict(int)
        for event in events_24h:
            by_type[event.type.value] += 1
            by_threat[event.threat_level.value] += 1
        
        return {
            "events_24h": len(events_24h),
            "events_7d": len(events_7d),
            "blocked_ips": len(self.blocked_ips),
            "active_sessions": len(self.active_sessions),
            "active_api_keys": sum(1 for k in self.api_keys.values() if k.active),
            "by_event_type": dict(by_type),
            "by_threat_level": dict(by_threat),
            "high_risk_ips": [
                {"ip": ip, "risk_score": rep.risk_score, "failed_attempts": rep.failed_attempts}
                for ip, rep in self.ip_reputations.items()
                if rep.risk_score >= 50
            ],
            "recent_events": [
                {
                    "type": e.type.value,
                    "threat_level": e.threat_level.value,
                    "user": e.user_email,
                    "ip": e.ip_address,
                    "timestamp": e.timestamp,
                }
                for e in self.events[-10:]
            ],
        }


# Singleton instance
security_manager = SecurityManager()
