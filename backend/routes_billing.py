#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ENGENHARIA CAD — BILLING & MONETIZAÇÃO (Stripe Integration)
# ═══════════════════════════════════════════════════════════════════════════════
"""
Sistema de billing completo com Stripe:
- Checkout Sessions para onboarding
- Webhooks para eventos de pagamento
- Gerenciamento de assinaturas
- API Keys com quotas

Pricing Tiers:
- STARTER: $99/mês - 500 jobs CAM, 1 usuário
- PROFESSIONAL: $299/mês - 2500 jobs CAM, 5 usuários
- ENTERPRISE: $999/mês - Unlimited, 25 usuários, SLA 99.9%
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
import hashlib
from datetime import datetime, timedelta, UTC
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("engcad.billing")

router = APIRouter(prefix="/api/billing", tags=["billing"])

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO STRIPE
# ═══════════════════════════════════════════════════════════════════════════════

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

# Preços (IDs do Stripe ou mock)
PRICING_TIERS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 297,
        "price_yearly": 2970,
        "currency": "BRL",
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", "price_starter_mock"),
        "features": {
            "cam_jobs_per_month": 500,
            "max_users": 1,
            "max_machines": 1,
            "max_projects": 5,
            "ai_queries_per_month": 100,
            "support": "email",
            "sla": "99%",
            "api_access": False,
        }
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 697,
        "price_yearly": 6970,
        "currency": "BRL",
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_pro_mock"),
        "features": {
            "cam_jobs_per_month": 2500,
            "max_users": 5,
            "max_machines": 2,
            "max_projects": 20,
            "ai_queries_per_month": 500,
            "support": "priority",
            "sla": "99.5%",
            "api_access": True,
        }
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 1497,
        "price_yearly": 14970,
        "currency": "BRL",
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_mock"),
        "features": {
            "cam_jobs_per_month": -1,  # Unlimited
            "max_users": 25,
            "max_machines": -1,  # Unlimited
            "max_projects": -1,
            "ai_queries_per_month": -1,
            "support": "dedicated",
            "sla": "99.9%",
            "api_access": True,
            "custom_integrations": True,
            "onboarding": True,
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# STRIPE CLIENT (Lazy loading)
# ═══════════════════════════════════════════════════════════════════════════════

_stripe = None

def get_stripe():
    """Carrega Stripe SDK sob demanda."""
    global _stripe
    if _stripe is None:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            _stripe = stripe
            logger.info("Stripe SDK carregado com sucesso")
        except ImportError:
            logger.warning("Stripe SDK não instalado - usando modo mock")
            _stripe = None
    return _stripe


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STORE (JSON File - Produção usaria PostgreSQL)
# ═══════════════════════════════════════════════════════════════════════════════

_BILLING_BASE = Path("/tmp") if os.getenv("VERCEL") else Path(__file__).parent.parent / "data"
_BILLING_FILE = _BILLING_BASE / "billing.json"
_BILLING_LOCK = Lock()


def _load_billing_data() -> Dict[str, Any]:
    """Carrega dados de billing do disco."""
    if not _BILLING_FILE.exists():
        return {"subscriptions": {}, "api_keys": {}, "usage": {}}
    try:
        return json.loads(_BILLING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"subscriptions": {}, "api_keys": {}, "usage": {}}


def _save_billing_data(data: Dict[str, Any]) -> None:
    """Salva dados de billing no disco."""
    _BILLING_FILE.parent.mkdir(parents=True, exist_ok=True)
    _BILLING_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateCheckoutRequest(BaseModel):
    email: str = Field(..., description="Email do cliente")
    tier: str = Field(..., description="Tier: starter, professional, enterprise")
    billing_cycle: str = Field(default="monthly", description="monthly ou yearly")
    success_url: str = Field(default="https://app.engenharia-cad.com/billing/success")
    cancel_url: str = Field(default="https://app.engenharia-cad.com/billing/cancel")


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="Nome da API key")
    expires_days: int = Field(default=365, ge=1, le=3650, description="Dias até expiração")


class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    key_prefix: str
    created_at: str
    expires_at: str
    last_used: Optional[str]
    requests_today: int
    requests_month: int


class SubscriptionResponse(BaseModel):
    status: str
    tier: str
    current_period_end: str
    cancel_at_period_end: bool
    usage: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/pricing")
async def get_pricing():
    """Retorna tabela de preços."""
    return {
        "tiers": PRICING_TIERS,
        "currency": "USD",
        "trial_days": 14,
        "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKOUT SESSION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/checkout")
async def create_checkout_session(req: CreateCheckoutRequest):
    """Cria sessão de checkout Stripe."""
    if req.tier not in PRICING_TIERS:
        raise HTTPException(status_code=400, detail=f"Tier inválido: {req.tier}")
    
    tier_config = PRICING_TIERS[req.tier]
    stripe = get_stripe()
    
    if stripe and STRIPE_SECRET_KEY:
        # Modo produção com Stripe real
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price": tier_config["stripe_price_id"],
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=req.success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=req.cancel_url,
                customer_email=req.email,
                metadata={
                    "tier": req.tier,
                    "email": req.email,
                },
                subscription_data={
                    "trial_period_days": 14,
                    "metadata": {
                        "tier": req.tier,
                    }
                }
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "mode": "live",
            }
        except Exception as e:
            logger.error(f"Erro ao criar checkout Stripe: {e}")
            raise HTTPException(status_code=500, detail="Erro ao processar pagamento")
    else:
        # Modo mock para desenvolvimento
        mock_session_id = f"cs_mock_{secrets.token_hex(16)}"
        with _BILLING_LOCK:
            data = _load_billing_data()
            data["subscriptions"][req.email] = {
                "session_id": mock_session_id,
                "tier": req.tier,
                "status": "trialing",
                "created_at": datetime.now(UTC).isoformat(),
                "trial_end": (datetime.now(UTC) + timedelta(days=14)).isoformat(),
                "current_period_end": (datetime.now(UTC) + timedelta(days=44)).isoformat(),
                "cancel_at_period_end": False,
            }
            _save_billing_data(data)
        
        return {
            "checkout_url": f"{req.success_url}?session_id={mock_session_id}",
            "session_id": mock_session_id,
            "mode": "mock",
            "message": "Modo desenvolvimento - Stripe não configurado",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STRIPE WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Webhook para eventos Stripe:
    - checkout.session.completed
    - invoice.paid
    - invoice.payment_failed
    - customer.subscription.updated
    - customer.subscription.deleted
    """
    payload = await request.body()
    stripe = get_stripe()
    
    if stripe and STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Mock mode
        try:
            event = json.loads(payload)
            event["type"] = event.get("type", "mock.event")
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    
    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})
    
    logger.info(f"Stripe webhook: {event_type}")
    
    with _BILLING_LOCK:
        data = _load_billing_data()
        
        if event_type == "checkout.session.completed":
            email = event_data.get("customer_email") or event_data.get("metadata", {}).get("email")
            tier = event_data.get("metadata", {}).get("tier", "starter")
            
            if email:
                data["subscriptions"][email] = {
                    "stripe_customer_id": event_data.get("customer"),
                    "stripe_subscription_id": event_data.get("subscription"),
                    "tier": tier,
                    "status": "active",
                    "created_at": datetime.now(UTC).isoformat(),
                    "current_period_end": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                }
                logger.info(f"Assinatura criada: {email} -> {tier}")
        
        elif event_type == "invoice.paid":
            customer_id = event_data.get("customer")
            # Atualizar período
            for email, sub in data["subscriptions"].items():
                if sub.get("stripe_customer_id") == customer_id:
                    sub["status"] = "active"
                    sub["current_period_end"] = (datetime.now(UTC) + timedelta(days=30)).isoformat()
                    logger.info(f"Invoice paga: {email}")
                    break
        
        elif event_type == "invoice.payment_failed":
            customer_id = event_data.get("customer")
            for email, sub in data["subscriptions"].items():
                if sub.get("stripe_customer_id") == customer_id:
                    sub["status"] = "past_due"
                    logger.warning(f"Pagamento falhou: {email}")
                    break
        
        elif event_type == "customer.subscription.deleted":
            subscription_id = event_data.get("id")
            for email, sub in data["subscriptions"].items():
                if sub.get("stripe_subscription_id") == subscription_id:
                    sub["status"] = "canceled"
                    logger.info(f"Assinatura cancelada: {email}")
                    break
        
        _save_billing_data(data)
    
    return {"received": True}


# ═══════════════════════════════════════════════════════════════════════════════
# SUBSCRIPTION STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/subscription/{email}")
async def get_subscription(email: str):
    """Retorna status da assinatura."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        sub = data["subscriptions"].get(email)
    
    if not sub:
        return {
            "status": "none",
            "tier": None,
            "message": "Nenhuma assinatura encontrada",
        }
    
    tier = sub.get("tier", "starter")
    tier_config = PRICING_TIERS.get(tier, PRICING_TIERS["starter"])
    
    # Calcular uso
    usage_key = f"{email}:{datetime.now(UTC).strftime('%Y-%m')}"
    usage = data.get("usage", {}).get(usage_key, {"cam_jobs": 0, "api_calls": 0})
    
    return {
        "status": sub.get("status", "unknown"),
        "tier": tier,
        "tier_name": tier_config["name"],
        "current_period_end": sub.get("current_period_end"),
        "cancel_at_period_end": sub.get("cancel_at_period_end", False),
        "features": tier_config["features"],
        "usage": {
            "cam_jobs_used": usage.get("cam_jobs", 0),
            "cam_jobs_limit": tier_config["features"]["cam_jobs_per_month"],
            "api_calls_used": usage.get("api_calls", 0),
        }
    }


@router.post("/subscription/{email}/cancel")
async def cancel_subscription(email: str):
    """Cancela assinatura no fim do período."""
    stripe = get_stripe()
    
    with _BILLING_LOCK:
        data = _load_billing_data()
        sub = data["subscriptions"].get(email)
        
        if not sub:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        if stripe and sub.get("stripe_subscription_id"):
            try:
                stripe.Subscription.modify(
                    sub["stripe_subscription_id"],
                    cancel_at_period_end=True
                )
            except Exception as e:
                logger.error(f"Erro ao cancelar no Stripe: {e}")
        
        sub["cancel_at_period_end"] = True
        _save_billing_data(data)
    
    return {
        "message": "Assinatura será cancelada no fim do período",
        "current_period_end": sub.get("current_period_end"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_api_key() -> tuple[str, str]:
    """Gera API key e retorna (full_key, hashed_key)."""
    key = f"engcad_{secrets.token_hex(32)}"
    hashed = hashlib.sha256(key.encode()).hexdigest()
    return key, hashed


@router.post("/api-keys")
async def create_api_key(req: CreateAPIKeyRequest, email: str = Header(..., alias="X-User-Email")):
    """Cria nova API key para o usuário."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        sub = data["subscriptions"].get(email)
        
        # Verificar se tem assinatura com API access
        if not sub:
            raise HTTPException(status_code=403, detail="Assinatura necessária")
        
        tier = sub.get("tier", "starter")
        if not PRICING_TIERS[tier]["features"].get("api_access"):
            raise HTTPException(
                status_code=403, 
                detail="Seu plano não inclui acesso à API. Faça upgrade para Professional ou Enterprise."
            )
        
        # Gerar key
        full_key, hashed_key = _generate_api_key()
        key_id = f"key_{secrets.token_hex(8)}"
        
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=req.expires_days)
        
        if "api_keys" not in data:
            data["api_keys"] = {}
        
        data["api_keys"][key_id] = {
            "hashed_key": hashed_key,
            "name": req.name,
            "owner_email": email,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used": None,
            "requests_today": 0,
            "requests_month": 0,
            "is_active": True,
        }
        
        _save_billing_data(data)
    
    # Retorna a key completa apenas uma vez
    return {
        "key_id": key_id,
        "api_key": full_key,  # Mostrar apenas na criação!
        "name": req.name,
        "expires_at": expires_at.isoformat(),
        "warning": "Guarde esta API key em local seguro. Ela não será mostrada novamente.",
    }


@router.get("/api-keys")
async def list_api_keys(email: str = Header(..., alias="X-User-Email")):
    """Lista API keys do usuário (sem mostrar as keys)."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        keys = data.get("api_keys", {})
    
    user_keys = []
    for key_id, key_data in keys.items():
        if key_data.get("owner_email") == email:
            user_keys.append({
                "key_id": key_id,
                "name": key_data["name"],
                "key_prefix": "engcad_****",  # Não mostrar key real
                "created_at": key_data["created_at"],
                "expires_at": key_data["expires_at"],
                "last_used": key_data.get("last_used"),
                "requests_today": key_data.get("requests_today", 0),
                "requests_month": key_data.get("requests_month", 0),
                "is_active": key_data.get("is_active", True),
            })
    
    return {"api_keys": user_keys}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, email: str = Header(..., alias="X-User-Email")):
    """Revoga uma API key."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        
        if key_id not in data.get("api_keys", {}):
            raise HTTPException(status_code=404, detail="API key não encontrada")
        
        key_data = data["api_keys"][key_id]
        if key_data.get("owner_email") != email:
            raise HTTPException(status_code=403, detail="Sem permissão")
        
        key_data["is_active"] = False
        key_data["revoked_at"] = datetime.now(UTC).isoformat()
        _save_billing_data(data)
    
    return {"message": "API key revogada com sucesso"}


# ═══════════════════════════════════════════════════════════════════════════════
# API KEY VALIDATION (para uso interno)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Valida API key e retorna dados do owner.
    Usado pelos outros routers para autenticar requests com API key.
    """
    if not api_key or not api_key.startswith("engcad_"):
        return None
    
    hashed = hashlib.sha256(api_key.encode()).hexdigest()
    
    with _BILLING_LOCK:
        data = _load_billing_data()
        
        for key_id, key_data in data.get("api_keys", {}).items():
            if key_data.get("hashed_key") == hashed:
                # Verificar se está ativa
                if not key_data.get("is_active", True):
                    return None
                
                # Verificar expiração
                expires_at = datetime.fromisoformat(key_data["expires_at"].replace("Z", "+00:00"))
                if datetime.now(UTC) > expires_at:
                    return None
                
                # Atualizar estatísticas
                key_data["last_used"] = datetime.now(UTC).isoformat()
                key_data["requests_today"] = key_data.get("requests_today", 0) + 1
                key_data["requests_month"] = key_data.get("requests_month", 0) + 1
                _save_billing_data(data)
                
                # Retornar dados do owner
                email = key_data["owner_email"]
                sub = data["subscriptions"].get(email, {})
                
                return {
                    "email": email,
                    "key_id": key_id,
                    "tier": sub.get("tier", "starter"),
                    "features": PRICING_TIERS.get(sub.get("tier", "starter"), {}).get("features", {}),
                }
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

def track_usage(email: str, usage_type: str, amount: int = 1) -> bool:
    """
    Registra uso e verifica se está dentro do limite.
    
    Args:
        email: Email do usuário
        usage_type: "cam_jobs" ou "api_calls"
        amount: Quantidade a adicionar
    
    Returns:
        True se dentro do limite, False se excedeu
    """
    with _BILLING_LOCK:
        data = _load_billing_data()
        sub = data["subscriptions"].get(email)
        
        if not sub:
            # Sem assinatura - usar limite free tier
            limit = 10
        else:
            tier = sub.get("tier", "starter")
            tier_config = PRICING_TIERS.get(tier, PRICING_TIERS["starter"])
            
            if usage_type == "cam_jobs":
                limit = tier_config["features"]["cam_jobs_per_month"]
            else:
                limit = -1  # API calls ilimitados por enquanto
        
        # Key de uso mensal
        usage_key = f"{email}:{datetime.now(UTC).strftime('%Y-%m')}"
        
        if "usage" not in data:
            data["usage"] = {}
        
        if usage_key not in data["usage"]:
            data["usage"][usage_key] = {"cam_jobs": 0, "api_calls": 0}
        
        current = data["usage"][usage_key].get(usage_type, 0)
        
        # -1 significa ilimitado
        if limit != -1 and current + amount > limit:
            return False
        
        data["usage"][usage_key][usage_type] = current + amount
        _save_billing_data(data)
    
    return True


@router.get("/usage/{email}")
async def get_usage(email: str):
    """Retorna uso atual do mês."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        sub = data["subscriptions"].get(email, {})
        
        usage_key = f"{email}:{datetime.now(UTC).strftime('%Y-%m')}"
        usage = data.get("usage", {}).get(usage_key, {"cam_jobs": 0, "api_calls": 0})
    
    tier = sub.get("tier", "starter")
    tier_config = PRICING_TIERS.get(tier, PRICING_TIERS["starter"])
    
    return {
        "period": datetime.now(UTC).strftime("%Y-%m"),
        "cam_jobs": {
            "used": usage.get("cam_jobs", 0),
            "limit": tier_config["features"]["cam_jobs_per_month"],
            "remaining": max(0, tier_config["features"]["cam_jobs_per_month"] - usage.get("cam_jobs", 0))
                if tier_config["features"]["cam_jobs_per_month"] != -1 else "unlimited",
        },
        "api_calls": {
            "used": usage.get("api_calls", 0),
            "limit": "unlimited",
        }
    }
