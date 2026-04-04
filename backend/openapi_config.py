# ═══════════════════════════════════════════════════════════════════════════════
# OPENAPI CONFIGURATION - ENGCAD AUTOMAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
"""
Configuração OpenAPI para documentação automática da API.

Este módulo define:
- Metadados da API (título, versão, descrição)
- Tags para agrupamento de endpoints
- Exemplos de requisições/respostas
- Schemas customizados

Uso:
    from backend.openapi_config import configure_openapi
    
    app = FastAPI()
    configure_openapi(app)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


# ═══════════════════════════════════════════════════════════════════════════════
# METADADOS
# ═══════════════════════════════════════════════════════════════════════════════

API_TITLE = "ENGCAD Automação API"
API_VERSION = "2.5.0"
API_DESCRIPTION = """
# ENGCAD Automação - API de Integração CAD/CAM

Sistema de automação para engenharia CAD com integração AutoCAD, 
suporte a manufatura CNC (Plasma, Laser, Router) e inteligência artificial.

## 🚀 Features

- **AutoCAD Integration**: Sincronização em tempo real com AutoCAD
- **CAM/CNC**: Geração de G-code para máquinas Plasma e Laser
- **AI Engines**: Análise inteligente de desenhos e otimização
- **Enterprise**: Licenciamento, auditoria e multi-tenant

## 🔐 Autenticação

A API usa JWT Bearer tokens. Para obter um token:

```
POST /api/auth/login
{
  "username": "user@email.com",
  "password": "senha123"
}
```

Depois use o token em todas as requisições:
```
Authorization: Bearer <seu_token>
```

## 📦 Rate Limiting

- 60 requisições por minuto
- 1000 requisições por hora
- Burst de até 10 requisições simultâneas

## 🔗 Links Úteis

- [Documentação Completa](/docs)
- [ReDoc](/redoc)
- [Health Check](/api/health)
"""

CONTACT_INFO = {
    "name": "ENGCAD Support",
    "url": "https://engcad.com/support",
    "email": "suporte@engcad.com"
}

LICENSE_INFO = {
    "name": "Proprietary",
    "url": "https://engcad.com/license"
}


# ═══════════════════════════════════════════════════════════════════════════════
# TAGS
# ═══════════════════════════════════════════════════════════════════════════════

TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Endpoints de verificação de saúde e status do sistema."
    },
    {
        "name": "Auth",
        "description": "Autenticação e autorização. Login, registro, tokens JWT."
    },
    {
        "name": "AutoCAD",
        "description": """
Operações de integração com AutoCAD.

Inclui:
- Sincronização de desenhos
- Comandos remotos
- Criação de entidades (linhas, arcos, textos)
- Gerenciamento de layers
        """
    },
    {
        "name": "CAM",
        "description": """
Módulo CAM (Computer-Aided Manufacturing).

Funcionalidades:
- Geração de G-code para CNC
- Suporte Plasma, Laser e Router
- Nesting de peças
- Otimização de corte
        """
    },
    {
        "name": "AI Engines",
        "description": """
Motores de Inteligência Artificial.

- **Drawing Analyzer**: Análise de desenhos técnicos
- **Pipe Optimizer**: Otimização de rotas de tubulação
- **Cost Estimator**: Estimativa de custos
- **Quality Inspector**: Inspeção de qualidade
- **Conflict Detector**: Detecção de conflitos
        """
    },
    {
        "name": "Enterprise",
        "description": """
Funcionalidades Enterprise.

- Licenciamento e ativação
- Auditoria e compliance
- Multi-tenant
- Analytics avançado
        """
    },
    {
        "name": "Projects",
        "description": "Gerenciamento de projetos e arquivos."
    },
    {
        "name": "License",
        "description": "Sistema de licenciamento e ativação de produtos."
    },
    {
        "name": "Analytics",
        "description": "Métricas, dashboards e relatórios de uso."
    },
    {
        "name": "Notifications",
        "description": "Sistema de notificações e webhooks."
    },
    {
        "name": "Security",
        "description": "Verificações de segurança e configurações."
    },
    {
        "name": "Cache",
        "description": "Gerenciamento de cache (admin only)."
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLOS
# ═══════════════════════════════════════════════════════════════════════════════

EXAMPLE_RESPONSES = {
    "health": {
        "summary": "Sistema saudável",
        "value": {
            "status": "healthy",
            "version": "2.5.0",
            "timestamp": "2025-01-29T12:00:00Z",
            "services": {
                "database": "connected",
                "cache": "connected",
                "autocad": "mock"
            }
        }
    },
    "login_success": {
        "summary": "Login bem-sucedido",
        "value": {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "usr_123",
                "email": "user@email.com",
                "name": "João Silva"
            }
        }
    },
    "login_error": {
        "summary": "Credenciais inválidas",
        "value": {
            "detail": "Incorrect username or password"
        }
    },
    "gcode_generated": {
        "summary": "G-code gerado",
        "value": {
            "success": True,
            "gcode": "G21\nG90\nG0 X0 Y0\nG1 X100 Y0 F1000\n...",
            "stats": {
                "lines": 150,
                "estimated_time": "5m 30s",
                "cut_length": 2500.5
            }
        }
    },
    "nesting_result": {
        "summary": "Nesting calculado",
        "value": {
            "success": True,
            "sheets": 2,
            "efficiency": 87.5,
            "pieces_placed": 24,
            "waste_area": 125000
        }
    },
    "ai_analysis": {
        "summary": "Análise AI",
        "value": {
            "drawing_type": "P&ID",
            "entities_found": 156,
            "pipes": 48,
            "valves": 12,
            "instruments": 8,
            "confidence": 0.94,
            "issues": [
                {"type": "missing_tag", "location": [100, 200]}
            ]
        }
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS CUSTOMIZADOS
# ═══════════════════════════════════════════════════════════════════════════════

def custom_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Gera schema OpenAPI customizado."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
        tags=TAGS_METADATA,
    )
    
    # Adicionar informações de contato e licença
    openapi_schema["info"]["contact"] = CONTACT_INFO
    openapi_schema["info"]["license"] = LICENSE_INFO
    
    # Adicionar servidores
    openapi_schema["servers"] = [
        {
            "url": "https://automacao-cad-backend.vercel.app",
            "description": "Produção"
        },
        {
            "url": "http://localhost:8000",
            "description": "Desenvolvimento local"
        }
    ]
    
    # Adicionar security schemes
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtido via /api/auth/login"
        },
        "apiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key para integração (Enterprise)"
        }
    }
    
    # Security global
    openapi_schema["security"] = [
        {"bearerAuth": []},
        {"apiKey": []}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def configure_openapi(app: FastAPI):
    """
    Configura OpenAPI com documentação completa.
    
    Args:
        app: Instância FastAPI
    """
    # Usar schema customizado
    app.openapi = lambda: custom_openapi_schema(app)
    
    # Configurar docs
    app.title = API_TITLE
    app.version = API_VERSION
    app.description = API_DESCRIPTION
    app.openapi_tags = TAGS_METADATA
    
    return app


def get_api_metadata() -> Dict[str, Any]:
    """Retorna metadados da API para uso em outros módulos."""
    return {
        "title": API_TITLE,
        "version": API_VERSION,
        "contact": CONTACT_INFO,
        "license": LICENSE_INFO,
        "tags": [t["name"] for t in TAGS_METADATA]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS DE DOCUMENTAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class HealthResponse(BaseModel):
    """Resposta do health check."""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Status geral do sistema"
    )
    version: str = Field(..., description="Versão da API")
    timestamp: datetime = Field(..., description="Timestamp da verificação")
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Status dos serviços dependentes"
    )
    
    class Config:
        json_schema_extra = {
            "example": EXAMPLE_RESPONSES["health"]["value"]
        }


class LoginRequest(BaseModel):
    """Requisição de login."""
    username: str = Field(..., description="Email ou nome de usuário")
    password: str = Field(..., description="Senha do usuário")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "user@email.com",
                "password": "senha123"
            }
        }


class TokenResponse(BaseModel):
    """Resposta com token JWT."""
    access_token: str = Field(..., description="Token JWT")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")
    
    class Config:
        json_schema_extra = {
            "example": EXAMPLE_RESPONSES["login_success"]["value"]
        }


class GCodeRequest(BaseModel):
    """Requisição para geração de G-code."""
    dxf_content: Optional[str] = Field(None, description="Conteúdo DXF em base64")
    dxf_url: Optional[str] = Field(None, description="URL do arquivo DXF")
    machine_type: Literal["plasma", "laser", "router"] = Field(
        default="plasma", description="Tipo de máquina CNC"
    )
    material: str = Field(default="steel", description="Material a ser cortado")
    thickness: float = Field(default=6.0, description="Espessura em mm")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dxf_url": "https://example.com/part.dxf",
                "machine_type": "plasma",
                "material": "steel",
                "thickness": 6.0
            }
        }


class NestingRequest(BaseModel):
    """Requisição para nesting de peças."""
    pieces: List[Dict[str, Any]] = Field(..., description="Lista de peças")
    sheet_width: float = Field(default=1500, description="Largura da chapa (mm)")
    sheet_height: float = Field(default=3000, description="Altura da chapa (mm)")
    spacing: float = Field(default=5, description="Espaçamento entre peças (mm)")
    allow_rotation: bool = Field(default=True, description="Permitir rotação")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pieces": [
                    {"id": "p1", "width": 200, "height": 300, "qty": 10},
                    {"id": "p2", "width": 150, "height": 150, "qty": 20}
                ],
                "sheet_width": 1500,
                "sheet_height": 3000
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from fastapi import FastAPI
    import json
    
    app = FastAPI()
    configure_openapi(app)
    
    @app.get("/test")
    def test():
        return {"ok": True}
    
    schema = app.openapi()
    print(json.dumps(schema, indent=2, default=str))
