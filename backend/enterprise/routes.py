"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE API ROUTES
  Rotas da API para funcionalidades Enterprise
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from .audit import audit_logger, AuditAction
from .rbac import rbac_manager, Permission, Role
from .integrations import integration_hub, IntegrationType, SyncDirection
from .workflows import workflow_engine, ApprovalDecision
from .export import export_manager, ExportType, ExportFormat
from .multi_tenant import tenant_manager, TenantPlan
from .sla import sla_monitor
from .security import security_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/enterprise", tags=["Enterprise"])


# ════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════════════════

class RoleCreateRequest(BaseModel):
    name: str
    description: str
    permissions: List[str]


class IntegrationCreateRequest(BaseModel):
    name: str
    type: str
    direction: str
    credentials: Dict[str, str]
    settings: Dict[str, Any]
    mappings: Dict[str, str]
    sync_interval_minutes: int = 60


class ExportRequest(BaseModel):
    type: str
    format: str
    data: Dict[str, Any]
    options: Dict[str, Any] = {}


class WorkflowStartRequest(BaseModel):
    workflow_id: str
    context: Dict[str, Any]


class ApprovalRequest(BaseModel):
    decision: str
    comments: Optional[str] = None


class TenantCreateRequest(BaseModel):
    name: str
    slug: str
    owner_email: str
    plan: str = "free"


# ════════════════════════════════════════════════════════════════════════════
# ENTERPRISE OVERVIEW
# ════════════════════════════════════════════════════════════════════════════

@router.get("/overview")
async def get_enterprise_overview():
    """Retorna visão geral do sistema Enterprise."""
    return {
        "version": "2.0.0",
        "enterprise": True,
        "modules": {
            "audit": {"enabled": True, "events": len(audit_logger.events)},
            "rbac": {"enabled": True, "roles": len(rbac_manager.roles)},
            "integrations": {"enabled": True, "count": len(integration_hub.integrations)},
            "workflows": {"enabled": True, "definitions": len(workflow_engine.definitions)},
            "export": {"enabled": True},
            "multi_tenant": {"enabled": True, "tenants": len(tenant_manager.tenants)},
            "sla": {"enabled": True},
            "security": {"enabled": True},
        },
        "statistics": {
            "tenants": tenant_manager.get_statistics(),
            "workflows": workflow_engine.get_statistics(),
            "integrations": integration_hub.get_statistics(),
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# AUDIT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/audit/events")
async def get_audit_events(
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    """Lista eventos de auditoria."""
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except:
            pass
    
    events = audit_logger.query(
        action=action_enum,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    
    return {
        "events": [e.to_dict() for e in events],
        "total": len(audit_logger.events),
    }


@router.get("/audit/statistics")
async def get_audit_statistics():
    """Retorna estatísticas de auditoria."""
    return audit_logger.get_statistics()


# ════════════════════════════════════════════════════════════════════════════
# RBAC ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/rbac/roles")
async def get_roles():
    """Lista todos os roles."""
    roles = rbac_manager.get_all_roles()
    return {"roles": [r.to_dict() for r in roles]}


@router.post("/rbac/roles")
async def create_role(request: RoleCreateRequest):
    """Cria um novo role customizado."""
    permissions = set()
    for p in request.permissions:
        try:
            permissions.add(Permission(p))
        except:
            pass
    
    role = rbac_manager.create_role(
        name=request.name,
        description=request.description,
        permissions=permissions,
    )
    
    return {"role": role.to_dict()}


@router.get("/rbac/permissions")
async def get_permissions():
    """Lista todas as permissões disponíveis."""
    return rbac_manager.get_permissions_by_category()


@router.post("/rbac/users/{user_id}/roles/{role_id}")
async def assign_role_to_user(user_id: str, role_id: str):
    """Atribui um role a um usuário."""
    success = rbac_manager.assign_role(user_id, role_id)
    if not success:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"success": True}


@router.get("/rbac/users/{user_id}/permissions")
async def get_user_permissions(user_id: str):
    """Retorna permissões efetivas de um usuário."""
    permissions = rbac_manager.get_user_permissions(user_id)
    roles = rbac_manager.get_user_roles(user_id)
    
    return {
        "user_id": user_id,
        "roles": [r.to_dict() for r in roles],
        "permissions": [p.value for p in permissions],
    }


# ════════════════════════════════════════════════════════════════════════════
# INTEGRATIONS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/integrations")
async def get_integrations():
    """Lista todas as integrações."""
    integrations = integration_hub.get_all_integrations()
    return {"integrations": [i.to_dict() for i in integrations]}


@router.post("/integrations")
async def create_integration(request: IntegrationCreateRequest):
    """Cria uma nova integração."""
    try:
        integration_type = IntegrationType(request.type)
        direction = SyncDirection(request.direction)
    except:
        raise HTTPException(status_code=400, detail="Invalid integration type or direction")
    
    integration = integration_hub.create_integration(
        name=request.name,
        type=integration_type,
        direction=direction,
        credentials=request.credentials,
        settings=request.settings,
        mappings=request.mappings,
        sync_interval_minutes=request.sync_interval_minutes,
        created_by="api_user",
    )
    
    return {"integration": integration.to_dict()}


@router.post("/integrations/{integration_id}/test")
async def test_integration(integration_id: str):
    """Testa conexão de uma integração."""
    result = await integration_hub.test_connection(integration_id)
    return result


@router.post("/integrations/{integration_id}/sync")
async def sync_integration(integration_id: str, data: Dict[str, Any] = Body(default={})):
    """Executa sincronização de uma integração."""
    try:
        result = await integration_hub.sync(integration_id, data)
        return {
            "sync_id": result.id,
            "status": result.status,
            "records_processed": result.records_processed,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/integrations/statistics")
async def get_integration_statistics():
    """Retorna estatísticas das integrações."""
    return integration_hub.get_statistics()


# ════════════════════════════════════════════════════════════════════════════
# WORKFLOWS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/workflows")
async def get_workflows():
    """Lista definições de workflows."""
    definitions = workflow_engine.get_all_definitions()
    return {"workflows": [d.to_dict() for d in definitions]}


@router.post("/workflows/start")
async def start_workflow(request: WorkflowStartRequest):
    """Inicia uma instância de workflow."""
    try:
        instance = await workflow_engine.start_workflow(
            workflow_id=request.workflow_id,
            context=request.context,
            started_by="api_user",
        )
        return {"instance": instance.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workflows/instances/{instance_id}")
async def get_workflow_instance(instance_id: str):
    """Obtém detalhes de uma instância de workflow."""
    instance = workflow_engine.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return {"instance": instance.to_dict()}


@router.post("/workflows/instances/{instance_id}/approve")
async def approve_workflow_step(instance_id: str, request: ApprovalRequest):
    """Aprova ou rejeita um passo de workflow."""
    try:
        decision = ApprovalDecision(request.decision)
    except:
        raise HTTPException(status_code=400, detail="Invalid decision")
    
    success = await workflow_engine.submit_approval(
        instance_id=instance_id,
        decision=decision,
        approved_by="api_user",
        comments=request.comments,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Could not process approval")
    
    return {"success": True}


@router.get("/workflows/pending-approvals")
async def get_pending_approvals(user_email: str = Query(...)):
    """Lista aprovações pendentes para um usuário."""
    pending = workflow_engine.get_pending_approvals(user_email)
    return {"pending_approvals": pending}


@router.get("/workflows/statistics")
async def get_workflow_statistics():
    """Retorna estatísticas de workflows."""
    return workflow_engine.get_statistics()


# ════════════════════════════════════════════════════════════════════════════
# EXPORT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/export")
async def create_export(request: ExportRequest):
    """Cria uma exportação."""
    try:
        export_type = ExportType(request.type)
        export_format = ExportFormat(request.format)
    except:
        raise HTTPException(status_code=400, detail="Invalid export type or format")
    
    result = await export_manager.export(
        export_type=export_type,
        export_format=export_format,
        data=request.data,
        options=request.options,
        requested_by="api_user",
    )
    
    return {
        "export_id": result.id,
        "status": result.status,
        "url": result.result_url,
        "error": result.error,
    }


@router.get("/export/{export_id}")
async def get_export(export_id: str):
    """Obtém status de uma exportação."""
    export = export_manager.get_export(export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    
    return {
        "id": export.id,
        "type": export.type.value,
        "format": export.format.value,
        "status": export.status,
        "url": export.result_url,
        "error": export.error,
        "requested_at": export.requested_at,
    }


@router.get("/export/formats")
async def get_export_formats():
    """Lista formatos de exportação disponíveis."""
    return {
        "types": [t.value for t in ExportType],
        "formats": [f.value for f in ExportFormat],
    }


# ════════════════════════════════════════════════════════════════════════════
# MULTI-TENANT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/tenants")
async def get_tenants():
    """Lista todos os tenants."""
    tenants = tenant_manager.get_all_tenants()
    return {"tenants": [t.to_dict() for t in tenants]}


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Obtém detalhes de um tenant."""
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"tenant": tenant.to_dict()}


@router.post("/tenants")
async def create_tenant(request: TenantCreateRequest):
    """Cria um novo tenant."""
    try:
        plan = TenantPlan(request.plan)
    except:
        plan = TenantPlan.FREE
    
    tenant = tenant_manager.create_tenant(
        name=request.name,
        slug=request.slug,
        owner_email=request.owner_email,
        plan=plan,
    )
    
    return {"tenant": tenant.to_dict()}


@router.get("/tenants/statistics")
async def get_tenant_statistics():
    """Retorna estatísticas de tenants."""
    return tenant_manager.get_statistics()


@router.get("/tenants/plans")
async def get_available_plans():
    """Lista planos disponíveis."""
    from .multi_tenant import PLAN_LIMITS
    
    plans = []
    for plan, limits in PLAN_LIMITS.items():
        plans.append({
            "id": plan.value,
            "name": plan.name.replace("_", " ").title(),
            "limits": {
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
            },
        })
    
    return {"plans": plans}


# ════════════════════════════════════════════════════════════════════════════
# SLA ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/sla/dashboard")
async def get_sla_dashboard():
    """Retorna dashboard de SLAs."""
    return sla_monitor.get_dashboard_data()


@router.get("/sla/status")
async def get_sla_status():
    """Retorna status atual de todos os SLAs."""
    return {k.value: v for k, v in sla_monitor.get_current_status().items()}


@router.get("/sla/metrics/{metric}/history")
async def get_sla_metric_history(metric: str, hours: int = Query(24, le=168)):
    """Retorna histórico de uma métrica de SLA."""
    from .sla import SLAMetric
    
    try:
        metric_enum = SLAMetric(metric)
    except:
        raise HTTPException(status_code=400, detail="Invalid metric")
    
    history = sla_monitor.get_metric_history(metric_enum, hours)
    return {"metric": metric, "history": history}


@router.get("/sla/report")
async def get_sla_report(days: int = Query(30, le=90)):
    """Gera relatório de SLA."""
    from datetime import timedelta
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    
    report = sla_monitor.generate_report(start, end)
    
    return {
        "period_start": report.period_start,
        "period_end": report.period_end,
        "overall_compliance": report.overall_compliance,
        "summaries": {k.value: v for k, v in report.summaries.items()},
        "violations_count": len(report.violations),
        "violations": report.violations[:20],
    }


# ════════════════════════════════════════════════════════════════════════════
# SECURITY ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/security/dashboard")
async def get_security_dashboard():
    """Retorna dashboard de segurança."""
    return security_manager.get_security_dashboard()


@router.get("/security/api-keys")
async def get_api_keys():
    """Lista API keys (sem revelar as chaves)."""
    keys = []
    for key in security_manager.api_keys.values():
        keys.append({
            "id": key.id,
            "name": key.name,
            "prefix": key.key_prefix,
            "created_by": key.created_by,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "last_used": key.last_used,
            "active": key.active,
            "scopes": list(key.scopes),
        })
    return {"api_keys": keys}


@router.post("/security/api-keys")
async def create_api_key(
    name: str = Body(...),
    scopes: List[str] = Body(default=["read"]),
    rate_limit: int = Body(default=1000),
    expires_in_days: Optional[int] = Body(default=None),
):
    """Cria uma nova API key."""
    result = security_manager.create_api_key(
        name=name,
        created_by="api_user",
        scopes=set(scopes),
        rate_limit=rate_limit,
        expires_in_days=expires_in_days,
    )
    
    return {
        "key_id": result["key_id"],
        "api_key": result["api_key"],
        "prefix": result["prefix"],
        "expires_at": result["expires_at"],
        "message": "IMPORTANTE: Salve esta chave! Ela não será mostrada novamente.",
    }


@router.delete("/security/api-keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoga uma API key."""
    success = security_manager.revoke_api_key(key_id, "api_user")
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True}


@router.get("/security/blocked-ips")
async def get_blocked_ips():
    """Lista IPs bloqueados."""
    blocked = []
    for ip, rep in security_manager.ip_reputations.items():
        if rep.blocked:
            blocked.append({
                "ip": ip,
                "blocked_until": rep.blocked_until,
                "failed_attempts": rep.failed_attempts,
                "risk_score": rep.risk_score,
            })
    return {"blocked_ips": blocked}


@router.post("/security/unblock-ip/{ip_address}")
async def unblock_ip(ip_address: str):
    """Desbloqueia um IP."""
    if ip_address in security_manager.blocked_ips:
        security_manager.blocked_ips.discard(ip_address)
        if ip_address in security_manager.ip_reputations:
            security_manager.ip_reputations[ip_address].blocked = False
            security_manager.ip_reputations[ip_address].blocked_until = None
        return {"success": True}
    return {"success": False, "message": "IP not blocked"}


@router.post("/security/check-input")
async def check_input_safety(input_value: str = Body(..., embed=True)):
    """Verifica se um input é seguro."""
    result = security_manager.check_input_safety(input_value)
    return result
