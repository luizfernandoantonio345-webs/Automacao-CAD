"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE INTEGRATION HUB
  Integrações com SAP, Oracle, ERPs e Sistemas Externos
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
import asyncio

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    """Tipos de integração suportados."""
    SAP = "sap"
    ORACLE = "oracle"
    TOTVS = "totvs"
    DYNAMICS = "dynamics"
    SALESFORCE = "salesforce"
    JIRA = "jira"
    SHAREPOINT = "sharepoint"
    TEAMS = "teams"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    REST_API = "rest_api"
    SOAP = "soap"
    DATABASE = "database"
    FTP = "ftp"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"


class IntegrationStatus(str, Enum):
    """Status da integração."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONFIGURING = "configuring"
    TESTING = "testing"


class SyncDirection(str, Enum):
    """Direção da sincronização."""
    INBOUND = "inbound"      # Externos -> ForgeCad
    OUTBOUND = "outbound"    # ForgeCad -> Externos
    BIDIRECTIONAL = "bidirectional"


@dataclass
class IntegrationConfig:
    """Configuração de uma integração."""
    id: str
    name: str
    type: IntegrationType
    status: IntegrationStatus
    direction: SyncDirection
    enabled: bool
    credentials: Dict[str, str]  # Encrypted in production
    settings: Dict[str, Any]
    mappings: Dict[str, str]  # Campo ForgeCad -> Campo Externo
    sync_interval_minutes: int
    last_sync: Optional[str]
    last_error: Optional[str]
    created_at: str
    updated_at: str
    created_by: str
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "status": self.status.value,
            "direction": self.direction.value,
            "enabled": self.enabled,
            "settings": self.settings,
            "mappings": self.mappings,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync": self.last_sync,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_secrets:
            result["credentials"] = self.credentials
        return result


@dataclass
class SyncResult:
    """Resultado de uma sincronização."""
    id: str
    integration_id: str
    started_at: str
    finished_at: Optional[str]
    status: str
    direction: SyncDirection
    records_processed: int
    records_created: int
    records_updated: int
    records_deleted: int
    records_failed: int
    errors: List[Dict[str, str]]
    duration_seconds: Optional[float]


class IntegrationHub:
    """Hub central de integrações Enterprise."""
    
    _instance: Optional['IntegrationHub'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.integrations: Dict[str, IntegrationConfig] = {}
        self.sync_history: List[SyncResult] = []
        self.handlers: Dict[IntegrationType, Callable] = {}
        self._setup_default_handlers()
        self._seed_demo_integrations()
        logger.info("IntegrationHub initialized")
    
    def _setup_default_handlers(self):
        """Configura handlers padrão para integrações."""
        self.handlers[IntegrationType.WEBHOOK] = self._handle_webhook
        self.handlers[IntegrationType.REST_API] = self._handle_rest_api
        self.handlers[IntegrationType.EMAIL] = self._handle_email
        self.handlers[IntegrationType.SAP] = self._handle_sap
        self.handlers[IntegrationType.ORACLE] = self._handle_oracle
        self.handlers[IntegrationType.TOTVS] = self._handle_totvs
    
    def _seed_demo_integrations(self):
        """Adiciona integrações de demonstração."""
        demo_integrations = [
            IntegrationConfig(
                id="int_sap_001",
                name="SAP S/4HANA Production",
                type=IntegrationType.SAP,
                status=IntegrationStatus.CONNECTED,
                direction=SyncDirection.BIDIRECTIONAL,
                enabled=True,
                credentials={"client_id": "***", "client_secret": "***"},
                settings={
                    "endpoint": "https://sap.empresa.com/api",
                    "company_code": "1000",
                    "plant": "BR01",
                },
                mappings={
                    "project.id": "AUFNR",
                    "project.name": "KTEXT",
                    "project.cost": "NETWR",
                    "material.code": "MATNR",
                    "material.quantity": "MENGE",
                },
                sync_interval_minutes=15,
                last_sync=datetime.now(UTC).isoformat(),
                last_error=None,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                created_by="admin@empresa.com",
            ),
            IntegrationConfig(
                id="int_oracle_001",
                name="Oracle ERP Cloud",
                type=IntegrationType.ORACLE,
                status=IntegrationStatus.CONNECTED,
                direction=SyncDirection.OUTBOUND,
                enabled=True,
                credentials={"api_key": "***"},
                settings={
                    "endpoint": "https://oracle.empresa.com/erpcloud",
                    "business_unit": "BU_ENGENHARIA",
                },
                mappings={
                    "project.id": "PROJECT_ID",
                    "project.budget": "BUDGET_AMOUNT",
                    "mto.total": "MATERIAL_COST",
                },
                sync_interval_minutes=30,
                last_sync=datetime.now(UTC).isoformat(),
                last_error=None,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                created_by="admin@empresa.com",
            ),
            IntegrationConfig(
                id="int_teams_001",
                name="Microsoft Teams Notifications",
                type=IntegrationType.TEAMS,
                status=IntegrationStatus.CONNECTED,
                direction=SyncDirection.OUTBOUND,
                enabled=True,
                credentials={"webhook_url": "***"},
                settings={
                    "channel": "Engenharia-CAD",
                    "notify_on": ["project.created", "quality.failed", "ai.completed"],
                },
                mappings={},
                sync_interval_minutes=0,
                last_sync=datetime.now(UTC).isoformat(),
                last_error=None,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                created_by="admin@empresa.com",
            ),
            IntegrationConfig(
                id="int_sharepoint_001",
                name="SharePoint Document Library",
                type=IntegrationType.SHAREPOINT,
                status=IntegrationStatus.CONNECTED,
                direction=SyncDirection.BIDIRECTIONAL,
                enabled=True,
                credentials={"tenant_id": "***", "client_id": "***"},
                settings={
                    "site_url": "https://empresa.sharepoint.com/sites/engenharia",
                    "library": "Documentos",
                    "folder": "Projetos CAD",
                },
                mappings={
                    "document.name": "FileLeafRef",
                    "document.path": "FileRef",
                },
                sync_interval_minutes=60,
                last_sync=datetime.now(UTC).isoformat(),
                last_error=None,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                created_by="admin@empresa.com",
            ),
        ]
        
        for integration in demo_integrations:
            self.integrations[integration.id] = integration
    
    async def _handle_webhook(self, config: IntegrationConfig, data: Dict) -> bool:
        """Handler para webhooks genéricos."""
        # Simula envio de webhook
        logger.info(f"Sending webhook to {config.settings.get('endpoint')}")
        return True
    
    async def _handle_rest_api(self, config: IntegrationConfig, data: Dict) -> bool:
        """Handler para REST APIs genéricas."""
        logger.info(f"Calling REST API: {config.settings.get('endpoint')}")
        return True
    
    async def _handle_email(self, config: IntegrationConfig, data: Dict) -> bool:
        """Handler para notificações por email."""
        logger.info(f"Sending email notification")
        return True
    
    async def _handle_sap(self, config: IntegrationConfig, data: Dict) -> bool:
        """Handler para integração SAP."""
        logger.info(f"SAP Integration: syncing {len(data)} records")
        # Em produção: usar SAP RFC/REST API
        return True
    
    async def _handle_oracle(self, config: IntegrationConfig, data: Dict) -> bool:
        """Handler para integração Oracle."""
        logger.info(f"Oracle ERP Integration: syncing {len(data)} records")
        return True
    
    async def _handle_totvs(self, config: IntegrationConfig, data: Dict) -> bool:
        """Handler para integração TOTVS."""
        logger.info(f"TOTVS Integration: syncing {len(data)} records")
        return True
    
    def get_all_integrations(self) -> List[IntegrationConfig]:
        """Retorna todas as integrações."""
        return list(self.integrations.values())
    
    def get_integration(self, integration_id: str) -> Optional[IntegrationConfig]:
        """Obtém uma integração pelo ID."""
        return self.integrations.get(integration_id)
    
    def create_integration(
        self,
        name: str,
        type: IntegrationType,
        direction: SyncDirection,
        credentials: Dict[str, str],
        settings: Dict[str, Any],
        mappings: Dict[str, str],
        sync_interval_minutes: int,
        created_by: str,
    ) -> IntegrationConfig:
        """Cria uma nova integração."""
        integration_id = f"int_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        
        config = IntegrationConfig(
            id=integration_id,
            name=name,
            type=type,
            status=IntegrationStatus.CONFIGURING,
            direction=direction,
            enabled=False,
            credentials=credentials,
            settings=settings,
            mappings=mappings,
            sync_interval_minutes=sync_interval_minutes,
            last_sync=None,
            last_error=None,
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )
        
        self.integrations[integration_id] = config
        logger.info(f"Created integration: {name} ({type.value})")
        return config
    
    def update_integration(
        self,
        integration_id: str,
        **updates
    ) -> Optional[IntegrationConfig]:
        """Atualiza uma integração existente."""
        config = self.integrations.get(integration_id)
        if not config:
            return None
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.now(UTC).isoformat()
        return config
    
    def delete_integration(self, integration_id: str) -> bool:
        """Remove uma integração."""
        if integration_id in self.integrations:
            del self.integrations[integration_id]
            return True
        return False
    
    async def test_connection(self, integration_id: str) -> Dict[str, Any]:
        """Testa a conexão de uma integração."""
        config = self.integrations.get(integration_id)
        if not config:
            return {"success": False, "error": "Integration not found"}
        
        config.status = IntegrationStatus.TESTING
        
        try:
            # Simula teste de conexão
            await asyncio.sleep(0.5)
            config.status = IntegrationStatus.CONNECTED
            return {
                "success": True,
                "message": f"Connected to {config.name}",
                "latency_ms": 150,
            }
        except Exception as e:
            config.status = IntegrationStatus.ERROR
            config.last_error = str(e)
            return {"success": False, "error": str(e)}
    
    async def sync(self, integration_id: str, data: Dict[str, Any] = None) -> SyncResult:
        """Executa sincronização de uma integração."""
        config = self.integrations.get(integration_id)
        if not config:
            raise ValueError("Integration not found")
        
        sync_id = f"sync_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(UTC)
        
        result = SyncResult(
            id=sync_id,
            integration_id=integration_id,
            started_at=started_at.isoformat(),
            finished_at=None,
            status="running",
            direction=config.direction,
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_deleted=0,
            records_failed=0,
            errors=[],
            duration_seconds=None,
        )
        
        try:
            handler = self.handlers.get(config.type)
            if handler:
                success = await handler(config, data or {})
                result.status = "completed" if success else "failed"
                result.records_processed = len(data) if data else 0
                result.records_created = result.records_processed
            else:
                result.status = "failed"
                result.errors.append({"message": f"No handler for {config.type}"})
            
        except Exception as e:
            result.status = "error"
            result.errors.append({"message": str(e)})
            config.last_error = str(e)
        
        finished_at = datetime.now(UTC)
        result.finished_at = finished_at.isoformat()
        result.duration_seconds = (finished_at - started_at).total_seconds()
        
        config.last_sync = finished_at.isoformat()
        if result.status == "completed":
            config.last_error = None
        
        self.sync_history.append(result)
        if len(self.sync_history) > 1000:
            self.sync_history = self.sync_history[-1000:]
        
        return result
    
    def get_sync_history(
        self,
        integration_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SyncResult]:
        """Retorna histórico de sincronizações."""
        results = self.sync_history
        if integration_id:
            results = [r for r in results if r.integration_id == integration_id]
        return sorted(results, key=lambda x: x.started_at, reverse=True)[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do hub de integrações."""
        connected = sum(1 for i in self.integrations.values() if i.status == IntegrationStatus.CONNECTED)
        enabled = sum(1 for i in self.integrations.values() if i.enabled)
        
        by_type = {}
        for integration in self.integrations.values():
            t = integration.type.value
            by_type[t] = by_type.get(t, 0) + 1
        
        recent_syncs = self.sync_history[-100:] if self.sync_history else []
        successful_syncs = sum(1 for s in recent_syncs if s.status == "completed")
        
        return {
            "total_integrations": len(self.integrations),
            "connected": connected,
            "enabled": enabled,
            "by_type": by_type,
            "total_syncs": len(self.sync_history),
            "recent_success_rate": (successful_syncs / max(len(recent_syncs), 1)) * 100,
            "records_synced_total": sum(s.records_processed for s in self.sync_history),
        }


# Singleton instance
integration_hub = IntegrationHub()
