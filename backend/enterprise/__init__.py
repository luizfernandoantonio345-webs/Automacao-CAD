"""
═══════════════════════════════════════════════════════════════════════════════
  FORGECAD ENTERPRISE MODULE
  Sistema Enterprise-Grade para Automação CAD Industrial
═══════════════════════════════════════════════════════════════════════════════
"""

__version__ = "2.0.0"
__enterprise__ = True

from .audit import AuditLogger, AuditEvent
from .rbac import RBACManager, Role, Permission
from .integrations import IntegrationHub
from .workflows import WorkflowEngine
from .export import ExportManager
from .multi_tenant import TenantManager
from .sla import SLAMonitor
from .security import SecurityManager

__all__ = [
    "AuditLogger",
    "AuditEvent", 
    "RBACManager",
    "Role",
    "Permission",
    "IntegrationHub",
    "WorkflowEngine",
    "ExportManager",
    "TenantManager",
    "SLAMonitor",
    "SecurityManager",
]
