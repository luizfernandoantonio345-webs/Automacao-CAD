"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE RBAC (Role-Based Access Control)
  Sistema de Permissões Granular para Controle de Acesso
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Permissões granulares do sistema."""
    # Projetos
    PROJECT_VIEW = "project.view"
    PROJECT_CREATE = "project.create"
    PROJECT_EDIT = "project.edit"
    PROJECT_DELETE = "project.delete"
    PROJECT_APPROVE = "project.approve"
    PROJECT_EXPORT = "project.export"
    PROJECT_ARCHIVE = "project.archive"
    
    # Desenhos
    DRAWING_VIEW = "drawing.view"
    DRAWING_UPLOAD = "drawing.upload"
    DRAWING_ANALYZE = "drawing.analyze"
    DRAWING_MODIFY = "drawing.modify"
    DRAWING_DELETE = "drawing.delete"
    DRAWING_EXPORT = "drawing.export"
    
    # IAs
    AI_USE_BASIC = "ai.use_basic"
    AI_USE_ADVANCED = "ai.use_advanced"
    AI_CONFIGURE = "ai.configure"
    AI_TRAIN = "ai.train"
    AI_DEPLOY = "ai.deploy"
    
    # AutoCAD
    AUTOCAD_VIEW = "autocad.view"
    AUTOCAD_CONNECT = "autocad.connect"
    AUTOCAD_DRAW = "autocad.draw"
    AUTOCAD_BATCH = "autocad.batch"
    
    # Quality Gate
    QUALITY_VIEW = "quality.view"
    QUALITY_RUN = "quality.run"
    QUALITY_CONFIGURE = "quality.configure"
    QUALITY_OVERRIDE = "quality.override"
    
    # Relatórios
    REPORT_VIEW = "report.view"
    REPORT_CREATE = "report.create"
    REPORT_EXPORT = "report.export"
    REPORT_SCHEDULE = "report.schedule"
    
    # Analytics
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_EXPORT = "analytics.export"
    ANALYTICS_ADVANCED = "analytics.advanced"
    
    # Admin
    ADMIN_USERS = "admin.users"
    ADMIN_ROLES = "admin.roles"
    ADMIN_SETTINGS = "admin.settings"
    ADMIN_AUDIT = "admin.audit"
    ADMIN_BILLING = "admin.billing"
    ADMIN_INTEGRATIONS = "admin.integrations"
    ADMIN_BACKUP = "admin.backup"
    
    # Sistema
    SYSTEM_HEALTH = "system.health"
    SYSTEM_LOGS = "system.logs"
    SYSTEM_CONFIG = "system.config"


@dataclass
class Role:
    """Papel/função com conjunto de permissões."""
    id: str
    name: str
    description: str
    permissions: Set[Permission]
    is_system: bool = False  # Roles de sistema não podem ser editados
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "is_system": self.is_system,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Roles padrão do sistema
SYSTEM_ROLES = {
    "superadmin": Role(
        id="role_superadmin",
        name="Super Administrador",
        description="Acesso total a todas as funcionalidades do sistema",
        permissions=set(Permission),  # Todas as permissões
        is_system=True,
    ),
    "admin": Role(
        id="role_admin",
        name="Administrador",
        description="Gerenciamento completo exceto configurações críticas",
        permissions={
            Permission.PROJECT_VIEW, Permission.PROJECT_CREATE, Permission.PROJECT_EDIT,
            Permission.PROJECT_DELETE, Permission.PROJECT_APPROVE, Permission.PROJECT_EXPORT,
            Permission.DRAWING_VIEW, Permission.DRAWING_UPLOAD, Permission.DRAWING_ANALYZE,
            Permission.DRAWING_MODIFY, Permission.DRAWING_DELETE, Permission.DRAWING_EXPORT,
            Permission.AI_USE_BASIC, Permission.AI_USE_ADVANCED, Permission.AI_CONFIGURE,
            Permission.AUTOCAD_VIEW, Permission.AUTOCAD_CONNECT, Permission.AUTOCAD_DRAW,
            Permission.AUTOCAD_BATCH,
            Permission.QUALITY_VIEW, Permission.QUALITY_RUN, Permission.QUALITY_CONFIGURE,
            Permission.REPORT_VIEW, Permission.REPORT_CREATE, Permission.REPORT_EXPORT,
            Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT, Permission.ANALYTICS_ADVANCED,
            Permission.ADMIN_USERS, Permission.ADMIN_ROLES, Permission.ADMIN_SETTINGS,
            Permission.ADMIN_AUDIT,
            Permission.SYSTEM_HEALTH, Permission.SYSTEM_LOGS,
        },
        is_system=True,
    ),
    "manager": Role(
        id="role_manager",
        name="Gerente de Projetos",
        description="Gerenciamento de projetos e equipes",
        permissions={
            Permission.PROJECT_VIEW, Permission.PROJECT_CREATE, Permission.PROJECT_EDIT,
            Permission.PROJECT_APPROVE, Permission.PROJECT_EXPORT, Permission.PROJECT_ARCHIVE,
            Permission.DRAWING_VIEW, Permission.DRAWING_UPLOAD, Permission.DRAWING_ANALYZE,
            Permission.DRAWING_EXPORT,
            Permission.AI_USE_BASIC, Permission.AI_USE_ADVANCED,
            Permission.AUTOCAD_VIEW,
            Permission.QUALITY_VIEW, Permission.QUALITY_RUN,
            Permission.REPORT_VIEW, Permission.REPORT_CREATE, Permission.REPORT_EXPORT,
            Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
        },
        is_system=True,
    ),
    "engineer": Role(
        id="role_engineer",
        name="Engenheiro",
        description="Trabalho técnico em projetos e desenhos",
        permissions={
            Permission.PROJECT_VIEW, Permission.PROJECT_CREATE, Permission.PROJECT_EDIT,
            Permission.DRAWING_VIEW, Permission.DRAWING_UPLOAD, Permission.DRAWING_ANALYZE,
            Permission.DRAWING_MODIFY, Permission.DRAWING_EXPORT,
            Permission.AI_USE_BASIC, Permission.AI_USE_ADVANCED,
            Permission.AUTOCAD_VIEW, Permission.AUTOCAD_CONNECT, Permission.AUTOCAD_DRAW,
            Permission.QUALITY_VIEW, Permission.QUALITY_RUN,
            Permission.REPORT_VIEW, Permission.REPORT_CREATE,
            Permission.ANALYTICS_VIEW,
        },
        is_system=True,
    ),
    "designer": Role(
        id="role_designer",
        name="Projetista",
        description="Criação e modificação de desenhos CAD",
        permissions={
            Permission.PROJECT_VIEW,
            Permission.DRAWING_VIEW, Permission.DRAWING_UPLOAD, Permission.DRAWING_ANALYZE,
            Permission.DRAWING_MODIFY,
            Permission.AI_USE_BASIC,
            Permission.AUTOCAD_VIEW, Permission.AUTOCAD_CONNECT, Permission.AUTOCAD_DRAW,
            Permission.QUALITY_VIEW,
            Permission.REPORT_VIEW,
        },
        is_system=True,
    ),
    "viewer": Role(
        id="role_viewer",
        name="Visualizador",
        description="Apenas visualização de dados",
        permissions={
            Permission.PROJECT_VIEW,
            Permission.DRAWING_VIEW,
            Permission.QUALITY_VIEW,
            Permission.REPORT_VIEW,
            Permission.ANALYTICS_VIEW,
        },
        is_system=True,
    ),
    "auditor": Role(
        id="role_auditor",
        name="Auditor",
        description="Acesso para auditoria e compliance",
        permissions={
            Permission.PROJECT_VIEW, Permission.PROJECT_EXPORT,
            Permission.DRAWING_VIEW,
            Permission.QUALITY_VIEW,
            Permission.REPORT_VIEW, Permission.REPORT_EXPORT,
            Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT, Permission.ANALYTICS_ADVANCED,
            Permission.ADMIN_AUDIT,
            Permission.SYSTEM_LOGS,
        },
        is_system=True,
    ),
}


@dataclass
class UserPermissions:
    """Permissões associadas a um usuário."""
    user_id: str
    roles: Set[str]  # IDs dos roles
    direct_permissions: Set[Permission] = field(default_factory=set)  # Permissões diretas
    denied_permissions: Set[Permission] = field(default_factory=set)  # Permissões negadas
    
    def get_effective_permissions(self, rbac: 'RBACManager') -> Set[Permission]:
        """Calcula permissões efetivas considerando roles e overrides."""
        effective = set(self.direct_permissions)
        
        for role_id in self.roles:
            role = rbac.get_role(role_id)
            if role:
                effective |= role.permissions
        
        # Remover permissões negadas
        effective -= self.denied_permissions
        
        return effective


class RBACManager:
    """Gerenciador de controle de acesso baseado em roles."""
    
    _instance: Optional['RBACManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.roles: Dict[str, Role] = dict(SYSTEM_ROLES)
        self.user_permissions: Dict[str, UserPermissions] = {}
        logger.info(f"RBACManager initialized with {len(self.roles)} system roles")
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """Obtém um role pelo ID."""
        return self.roles.get(role_id)
    
    def get_all_roles(self) -> List[Role]:
        """Retorna todos os roles."""
        return list(self.roles.values())
    
    def create_role(
        self,
        name: str,
        description: str,
        permissions: Set[Permission],
    ) -> Role:
        """Cria um novo role customizado."""
        role_id = f"role_{uuid.uuid4().hex[:8]}"
        role = Role(
            id=role_id,
            name=name,
            description=description,
            permissions=permissions,
            is_system=False,
        )
        self.roles[role_id] = role
        logger.info(f"Created custom role: {name} with {len(permissions)} permissions")
        return role
    
    def update_role(
        self,
        role_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[Set[Permission]] = None,
    ) -> Optional[Role]:
        """Atualiza um role existente (não pode atualizar roles de sistema)."""
        role = self.roles.get(role_id)
        if not role:
            return None
        if role.is_system:
            raise ValueError("Cannot modify system roles")
        
        if name:
            role.name = name
        if description:
            role.description = description
        if permissions is not None:
            role.permissions = permissions
        role.updated_at = datetime.now(UTC).isoformat()
        
        return role
    
    def delete_role(self, role_id: str) -> bool:
        """Remove um role (não pode remover roles de sistema)."""
        role = self.roles.get(role_id)
        if not role:
            return False
        if role.is_system:
            raise ValueError("Cannot delete system roles")
        
        del self.roles[role_id]
        
        # Remover role de todos os usuários
        for user_perms in self.user_permissions.values():
            user_perms.roles.discard(role_id)
        
        return True
    
    def assign_role(self, user_id: str, role_id: str) -> bool:
        """Atribui um role a um usuário."""
        if role_id not in self.roles:
            return False
        
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = UserPermissions(
                user_id=user_id,
                roles=set(),
            )
        
        self.user_permissions[user_id].roles.add(role_id)
        logger.info(f"Assigned role {role_id} to user {user_id}")
        return True
    
    def revoke_role(self, user_id: str, role_id: str) -> bool:
        """Remove um role de um usuário."""
        if user_id not in self.user_permissions:
            return False
        
        self.user_permissions[user_id].roles.discard(role_id)
        return True
    
    def grant_permission(self, user_id: str, permission: Permission) -> None:
        """Concede permissão direta a um usuário."""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = UserPermissions(
                user_id=user_id,
                roles=set(),
            )
        
        self.user_permissions[user_id].direct_permissions.add(permission)
    
    def deny_permission(self, user_id: str, permission: Permission) -> None:
        """Nega explicitamente uma permissão (override de roles)."""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = UserPermissions(
                user_id=user_id,
                roles=set(),
            )
        
        self.user_permissions[user_id].denied_permissions.add(permission)
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Verifica se usuário tem determinada permissão."""
        user_perms = self.user_permissions.get(user_id)
        if not user_perms:
            return False
        
        effective = user_perms.get_effective_permissions(self)
        return permission in effective
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Retorna todas as permissões efetivas de um usuário."""
        user_perms = self.user_permissions.get(user_id)
        if not user_perms:
            return set()
        
        return user_perms.get_effective_permissions(self)
    
    def get_user_roles(self, user_id: str) -> List[Role]:
        """Retorna os roles de um usuário."""
        user_perms = self.user_permissions.get(user_id)
        if not user_perms:
            return []
        
        return [self.roles[r] for r in user_perms.roles if r in self.roles]
    
    def get_permissions_by_category(self) -> Dict[str, List[Dict[str, str]]]:
        """Agrupa permissões por categoria para UI."""
        categories: Dict[str, List[Dict[str, str]]] = {}
        
        for perm in Permission:
            category = perm.value.split(".")[0].title()
            if category not in categories:
                categories[category] = []
            
            categories[category].append({
                "value": perm.value,
                "name": perm.name.replace("_", " ").title(),
            })
        
        return categories


# Singleton instance
rbac_manager = RBACManager()
