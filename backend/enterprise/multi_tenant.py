"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE MULTI-TENANT MANAGER
  Gerenciamento de Múltiplos Clientes/Organizações
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


class TenantPlan(str, Enum):
    """Planos disponíveis."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


class TenantStatus(str, Enum):
    """Status do tenant."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"


@dataclass
class TenantLimits:
    """Limites por plano."""
    max_users: int
    max_projects: int
    max_drawings_per_month: int
    max_ai_calls_per_month: int
    max_storage_gb: int
    integrations_enabled: bool
    workflows_enabled: bool
    api_access: bool
    priority_support: bool
    custom_branding: bool


PLAN_LIMITS = {
    TenantPlan.FREE: TenantLimits(
        max_users=2,
        max_projects=5,
        max_drawings_per_month=20,
        max_ai_calls_per_month=100,
        max_storage_gb=1,
        integrations_enabled=False,
        workflows_enabled=False,
        api_access=False,
        priority_support=False,
        custom_branding=False,
    ),
    TenantPlan.STARTER: TenantLimits(
        max_users=5,
        max_projects=25,
        max_drawings_per_month=100,
        max_ai_calls_per_month=500,
        max_storage_gb=10,
        integrations_enabled=False,
        workflows_enabled=True,
        api_access=True,
        priority_support=False,
        custom_branding=False,
    ),
    TenantPlan.PROFESSIONAL: TenantLimits(
        max_users=25,
        max_projects=100,
        max_drawings_per_month=500,
        max_ai_calls_per_month=2000,
        max_storage_gb=50,
        integrations_enabled=True,
        workflows_enabled=True,
        api_access=True,
        priority_support=True,
        custom_branding=True,
    ),
    TenantPlan.ENTERPRISE: TenantLimits(
        max_users=100,
        max_projects=500,
        max_drawings_per_month=5000,
        max_ai_calls_per_month=20000,
        max_storage_gb=500,
        integrations_enabled=True,
        workflows_enabled=True,
        api_access=True,
        priority_support=True,
        custom_branding=True,
    ),
    TenantPlan.UNLIMITED: TenantLimits(
        max_users=-1,
        max_projects=-1,
        max_drawings_per_month=-1,
        max_ai_calls_per_month=-1,
        max_storage_gb=-1,
        integrations_enabled=True,
        workflows_enabled=True,
        api_access=True,
        priority_support=True,
        custom_branding=True,
    ),
}


@dataclass
class TenantBranding:
    """Configuração de branding customizado."""
    logo_url: Optional[str] = None
    primary_color: str = "#2b6cb0"
    secondary_color: str = "#1a365d"
    company_name: Optional[str] = None
    favicon_url: Optional[str] = None
    custom_css: Optional[str] = None


@dataclass
class TenantUsage:
    """Uso atual do tenant."""
    current_users: int = 0
    current_projects: int = 0
    drawings_this_month: int = 0
    ai_calls_this_month: int = 0
    storage_used_gb: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class Tenant:
    """Representação de um tenant/organização."""
    id: str
    name: str
    slug: str  # URL-friendly identifier
    plan: TenantPlan
    status: TenantStatus
    owner_email: str
    admin_emails: List[str]
    branding: TenantBranding
    usage: TenantUsage
    settings: Dict[str, Any]
    created_at: str
    updated_at: str
    trial_ends_at: Optional[str]
    suspended_reason: Optional[str]
    
    def to_dict(self, include_usage: bool = True) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan.value,
            "status": self.status.value,
            "owner_email": self.owner_email,
            "admin_emails": self.admin_emails,
            "branding": {
                "logo_url": self.branding.logo_url,
                "primary_color": self.branding.primary_color,
                "secondary_color": self.branding.secondary_color,
                "company_name": self.branding.company_name,
            },
            "settings": self.settings,
            "created_at": self.created_at,
            "trial_ends_at": self.trial_ends_at,
        }
        if include_usage:
            result["usage"] = {
                "current_users": self.usage.current_users,
                "current_projects": self.usage.current_projects,
                "drawings_this_month": self.usage.drawings_this_month,
                "ai_calls_this_month": self.usage.ai_calls_this_month,
                "storage_used_gb": self.usage.storage_used_gb,
            }
            result["limits"] = self.get_limits_dict()
        return result
    
    def get_limits(self) -> TenantLimits:
        """Retorna os limites do plano atual."""
        return PLAN_LIMITS.get(self.plan, PLAN_LIMITS[TenantPlan.FREE])
    
    def get_limits_dict(self) -> Dict[str, Any]:
        """Retorna limites como dicionário."""
        limits = self.get_limits()
        return {
            "max_users": limits.max_users,
            "max_projects": limits.max_projects,
            "max_drawings_per_month": limits.max_drawings_per_month,
            "max_ai_calls_per_month": limits.max_ai_calls_per_month,
            "max_storage_gb": limits.max_storage_gb,
            "integrations_enabled": limits.integrations_enabled,
            "workflows_enabled": limits.workflows_enabled,
            "api_access": limits.api_access,
            "priority_support": limits.priority_support,
            "custom_branding": limits.custom_branding,
        }
    
    def check_limit(self, limit_type: str) -> bool:
        """Verifica se ainda está dentro do limite."""
        limits = self.get_limits()
        
        if limit_type == "users":
            return limits.max_users == -1 or self.usage.current_users < limits.max_users
        elif limit_type == "projects":
            return limits.max_projects == -1 or self.usage.current_projects < limits.max_projects
        elif limit_type == "drawings":
            return limits.max_drawings_per_month == -1 or self.usage.drawings_this_month < limits.max_drawings_per_month
        elif limit_type == "ai_calls":
            return limits.max_ai_calls_per_month == -1 or self.usage.ai_calls_this_month < limits.max_ai_calls_per_month
        elif limit_type == "storage":
            return limits.max_storage_gb == -1 or self.usage.storage_used_gb < limits.max_storage_gb
        
        return True


class TenantManager:
    """Gerenciador de multi-tenancy."""
    
    _instance: Optional['TenantManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tenants: Dict[str, Tenant] = {}
        self.user_tenant_map: Dict[str, str] = {}  # email -> tenant_id
        self._seed_demo_tenants()
        logger.info("TenantManager initialized")
    
    def _seed_demo_tenants(self):
        """Adiciona tenants de demonstração."""
        demo_tenants = [
            Tenant(
                id="tenant_demo",
                name="Empresa Demonstração",
                slug="demo",
                plan=TenantPlan.PROFESSIONAL,
                status=TenantStatus.ACTIVE,
                owner_email="admin@demo.com",
                admin_emails=["admin@demo.com"],
                branding=TenantBranding(),
                usage=TenantUsage(
                    current_users=5,
                    current_projects=12,
                    drawings_this_month=45,
                    ai_calls_this_month=230,
                    storage_used_gb=2.5,
                ),
                settings={"timezone": "America/Sao_Paulo", "language": "pt-BR"},
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                trial_ends_at=None,
                suspended_reason=None,
            ),
            Tenant(
                id="tenant_enterprise",
                name="Petrobras Engenharia",
                slug="petrobras",
                plan=TenantPlan.ENTERPRISE,
                status=TenantStatus.ACTIVE,
                owner_email="engenharia@petrobras.com.br",
                admin_emails=["engenharia@petrobras.com.br", "ti@petrobras.com.br"],
                branding=TenantBranding(
                    primary_color="#00A859",
                    secondary_color="#006341",
                    company_name="Petrobras",
                ),
                usage=TenantUsage(
                    current_users=45,
                    current_projects=156,
                    drawings_this_month=1250,
                    ai_calls_this_month=8500,
                    storage_used_gb=125.8,
                ),
                settings={"timezone": "America/Sao_Paulo", "language": "pt-BR"},
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                trial_ends_at=None,
                suspended_reason=None,
            ),
            Tenant(
                id="tenant_vale",
                name="Vale Mineração",
                slug="vale",
                plan=TenantPlan.ENTERPRISE,
                status=TenantStatus.ACTIVE,
                owner_email="engenharia@vale.com",
                admin_emails=["engenharia@vale.com"],
                branding=TenantBranding(
                    primary_color="#007E7A",
                    secondary_color="#005955",
                    company_name="Vale",
                ),
                usage=TenantUsage(
                    current_users=38,
                    current_projects=98,
                    drawings_this_month=890,
                    ai_calls_this_month=5600,
                    storage_used_gb=89.2,
                ),
                settings={"timezone": "America/Sao_Paulo", "language": "pt-BR"},
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                trial_ends_at=None,
                suspended_reason=None,
            ),
        ]
        
        for tenant in demo_tenants:
            self.tenants[tenant.id] = tenant
            self.user_tenant_map[tenant.owner_email] = tenant.id
            for admin in tenant.admin_emails:
                self.user_tenant_map[admin] = tenant.id
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Obtém um tenant pelo ID."""
        return self.tenants.get(tenant_id)
    
    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Obtém um tenant pelo slug."""
        for tenant in self.tenants.values():
            if tenant.slug == slug:
                return tenant
        return None
    
    def get_tenant_for_user(self, user_email: str) -> Optional[Tenant]:
        """Obtém o tenant de um usuário."""
        tenant_id = self.user_tenant_map.get(user_email)
        if tenant_id:
            return self.tenants.get(tenant_id)
        return None
    
    def get_all_tenants(self) -> List[Tenant]:
        """Retorna todos os tenants."""
        return list(self.tenants.values())
    
    def create_tenant(
        self,
        name: str,
        slug: str,
        owner_email: str,
        plan: TenantPlan = TenantPlan.TRIAL if hasattr(TenantPlan, 'TRIAL') else TenantPlan.FREE,
    ) -> Tenant:
        """Cria um novo tenant."""
        tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        
        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=slug,
            plan=plan,
            status=TenantStatus.TRIAL,
            owner_email=owner_email,
            admin_emails=[owner_email],
            branding=TenantBranding(),
            usage=TenantUsage(),
            settings={"timezone": "America/Sao_Paulo", "language": "pt-BR"},
            created_at=now,
            updated_at=now,
            trial_ends_at=None,
            suspended_reason=None,
        )
        
        self.tenants[tenant_id] = tenant
        self.user_tenant_map[owner_email] = tenant_id
        
        logger.info(f"Created tenant: {name} ({tenant_id})")
        return tenant
    
    def update_tenant(
        self,
        tenant_id: str,
        **updates
    ) -> Optional[Tenant]:
        """Atualiza um tenant."""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.now(UTC).isoformat()
        return tenant
    
    def add_user_to_tenant(self, tenant_id: str, user_email: str) -> bool:
        """Adiciona usuário a um tenant."""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False
        
        if not tenant.check_limit("users"):
            raise ValueError("User limit reached for this tenant")
        
        self.user_tenant_map[user_email] = tenant_id
        tenant.usage.current_users += 1
        return True
    
    def remove_user_from_tenant(self, tenant_id: str, user_email: str) -> bool:
        """Remove usuário de um tenant."""
        if self.user_tenant_map.get(user_email) == tenant_id:
            del self.user_tenant_map[user_email]
            tenant = self.tenants.get(tenant_id)
            if tenant:
                tenant.usage.current_users = max(0, tenant.usage.current_users - 1)
            return True
        return False
    
    def increment_usage(self, tenant_id: str, usage_type: str, amount: int = 1) -> bool:
        """Incrementa contadores de uso."""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False
        
        if usage_type == "drawings":
            tenant.usage.drawings_this_month += amount
        elif usage_type == "ai_calls":
            tenant.usage.ai_calls_this_month += amount
        elif usage_type == "projects":
            tenant.usage.current_projects += amount
        
        tenant.usage.last_updated = datetime.now(UTC).isoformat()
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas globais."""
        active = sum(1 for t in self.tenants.values() if t.status == TenantStatus.ACTIVE)
        by_plan = {}
        total_users = 0
        total_projects = 0
        
        for tenant in self.tenants.values():
            plan = tenant.plan.value
            by_plan[plan] = by_plan.get(plan, 0) + 1
            total_users += tenant.usage.current_users
            total_projects += tenant.usage.current_projects
        
        return {
            "total_tenants": len(self.tenants),
            "active_tenants": active,
            "by_plan": by_plan,
            "total_users": total_users,
            "total_projects": total_projects,
        }


# Singleton instance
tenant_manager = TenantManager()
