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
from collections import OrderedDict
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("engcad.billing")

router = APIRouter(prefix="/api/billing", tags=["billing"])

# Webhook idempotency: track last N processed event IDs
_WEBHOOK_PROCESSED: OrderedDict[str, float] = OrderedDict()
_WEBHOOK_MAX_EVENTS = 500
_WEBHOOK_LOCK = Lock()

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
        "stripe_price_id_monthly": os.getenv("STRIPE_PRICE_STARTER", "price_starter_mock"),
        "stripe_price_id_yearly": os.getenv(
            "STRIPE_PRICE_STARTER_YEARLY",
            os.getenv("STRIPE_PRICE_STARTER", "price_starter_mock"),
        ),
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
        "stripe_price_id_monthly": os.getenv("STRIPE_PRICE_PRO", "price_pro_mock"),
        "stripe_price_id_yearly": os.getenv(
            "STRIPE_PRICE_PRO_YEARLY",
            os.getenv("STRIPE_PRICE_PRO", "price_pro_mock"),
        ),
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
        "stripe_price_id_monthly": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_mock"),
        "stripe_price_id_yearly": os.getenv(
            "STRIPE_PRICE_ENTERPRISE_YEARLY",
            os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_mock"),
        ),
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
# Vercel serverless requer /tmp para arquivos temporários
_BILLING_BASE = Path("/tmp") if os.getenv("VERCEL") else Path(__file__).parent.parent / "data"  # nosec B108
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


def _normalize_billing_cycle(value: str) -> str:
    cycle = (value or "monthly").strip().lower()
    aliases = {
        "month": "monthly",
        "monthly": "monthly",
        "mensal": "monthly",
        "year": "yearly",
        "yearly": "yearly",
        "annual": "yearly",
        "annually": "yearly",
        "anual": "yearly",
    }
    normalized = aliases.get(cycle)
    if not normalized:
        raise HTTPException(status_code=400, detail="billing_cycle inválido. Use monthly ou yearly.")
    return normalized


def _append_query_params(url: str, **params: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        query[key] = value
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/pricing")
async def get_pricing():
    """Retorna tabela de preços."""
    return {
        "tiers": PRICING_TIERS,
        "currency": "BRL",
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

    billing_cycle = _normalize_billing_cycle(req.billing_cycle)
    tier_config = PRICING_TIERS[req.tier]
    price_id_key = (
        "stripe_price_id_yearly" if billing_cycle == "yearly" else "stripe_price_id_monthly"
    )
    price_id = tier_config[price_id_key]
    stripe = get_stripe()

    if stripe and STRIPE_SECRET_KEY:
        # Modo produção com Stripe real
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=_append_query_params(
                    req.success_url, session_id="{CHECKOUT_SESSION_ID}"
                ),
                cancel_url=req.cancel_url,
                customer_email=req.email,
                metadata={
                    "tier": req.tier,
                    "email": req.email,
                    "billing_cycle": billing_cycle,
                },
                subscription_data={
                    "trial_period_days": 14,
                    "metadata": {
                        "tier": req.tier,
                        "billing_cycle": billing_cycle,
                    }
                }
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "mode": "live",
                "billing_cycle": billing_cycle,
            }
        except Exception as e:
            logger.error(f"Erro ao criar checkout Stripe: {e}")
            raise HTTPException(status_code=500, detail="Erro ao processar pagamento")
    else:
        # Modo mock — bloquear em produção
        app_env = os.getenv("APP_ENV", "development")
        if app_env == "production":
            logger.error("Checkout mock bloqueado em produção — configure STRIPE_SECRET_KEY")
            raise HTTPException(
                status_code=503,
                detail="Sistema de pagamento temporariamente indisponível. Tente novamente em breve."
            )
        # Modo mock para desenvolvimento
        mock_session_id = f"cs_mock_{secrets.token_hex(16)}"
        with _BILLING_LOCK:
            data = _load_billing_data()
            data["subscriptions"][req.email] = {
                "session_id": mock_session_id,
                "tier": req.tier,
                "billing_cycle": billing_cycle,
                "status": "trialing",
                "created_at": datetime.now(UTC).isoformat(),
                "trial_end": (datetime.now(UTC) + timedelta(days=14)).isoformat(),
                "current_period_end": (datetime.now(UTC) + timedelta(days=44)).isoformat(),
                "cancel_at_period_end": False,
            }
            _save_billing_data(data)

        return {
            "checkout_url": _append_query_params(req.success_url, session_id=mock_session_id),
            "session_id": mock_session_id,
            "mode": "mock",
            "billing_cycle": billing_cycle,
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
    event_id = event.get("id", "")
    
    # Idempotency check — skip already-processed events
    if event_id:
        with _WEBHOOK_LOCK:
            if event_id in _WEBHOOK_PROCESSED:
                logger.info(f"Stripe webhook duplicate skipped: {event_id}")
                return {"received": True, "duplicate": True}
            _WEBHOOK_PROCESSED[event_id] = time.time()
            # Evict oldest if over limit
            while len(_WEBHOOK_PROCESSED) > _WEBHOOK_MAX_EVENTS:
                _WEBHOOK_PROCESSED.popitem(last=False)
    
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


# ═══════════════════════════════════════════════════════════════════════════════
# INVOICES - Histórico de Faturas
# ═══════════════════════════════════════════════════════════════════════════════

class InvoiceResponse(BaseModel):
    id: str
    number: str
    status: str  # paid, pending, failed, refunded
    amount: int  # centavos
    currency: str
    description: str
    created_at: str
    paid_at: Optional[str]
    pdf_url: Optional[str]
    period_start: str
    period_end: str


@router.get("/invoices")
async def list_invoices(
    email: str,
    limit: int = 12,
    status: Optional[str] = None
):
    """
    Lista faturas do usuário.
    
    - **email**: Email do usuário
    - **limit**: Máximo de faturas a retornar (default 12)
    - **status**: Filtrar por status (paid, pending, failed, refunded)
    """
    with _BILLING_LOCK:
        data = _load_billing_data()
        invoices_data = data.get("invoices", {}).get(email, [])
    
    # Filtrar por status se especificado
    if status:
        invoices_data = [inv for inv in invoices_data if inv.get("status") == status]
    
    # Ordenar por data (mais recente primeiro)
    invoices_data = sorted(invoices_data, key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Limitar resultados
    invoices_data = invoices_data[:limit]
    
    # Se não houver faturas, gerar algumas de exemplo para demonstração
    if not invoices_data:
        now = datetime.now(UTC)
        sub = data.get("subscriptions", {}).get(email, {})
        tier = sub.get("tier", "starter")
        tier_config = PRICING_TIERS.get(tier, PRICING_TIERS["starter"])
        
        # Gerar faturas dos últimos 3 meses como exemplo
        demo_invoices = []
        for i in range(3):
            month_date = now - timedelta(days=30 * i)
            period_start = month_date.replace(day=1)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1) - timedelta(days=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1) - timedelta(days=1)
            
            demo_invoices.append({
                "id": f"inv_{hashlib.sha256(f'{email}{i}'.encode()).hexdigest()[:16]}",
                "number": f"INV-{month_date.strftime('%Y%m')}-{1000 + i:04d}",
                "status": "paid" if i > 0 else ("pending" if now.day < 5 else "paid"),
                "amount": tier_config["price_monthly"] * 100,  # Em centavos
                "currency": tier_config["currency"],
                "description": f"Assinatura {tier_config['name']} - {month_date.strftime('%B %Y')}",
                "created_at": period_start.isoformat(),
                "paid_at": (period_start + timedelta(days=1)).isoformat() if i > 0 else None,
                "pdf_url": f"/api/billing/invoices/inv_{hashlib.sha256(f'{email}{i}'.encode()).hexdigest()[:16]}/pdf",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            })
        invoices_data = demo_invoices
    
    return {
        "invoices": invoices_data,
        "total": len(invoices_data),
        "has_more": False,
    }


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: str, email: str):
    """
    Retorna URL para download do PDF da fatura.
    Em produção, isso geraria o PDF ou retornaria URL do Stripe.
    """
    # Em produção, buscar PDF do Stripe ou gerar dinamicamente
    # Por enquanto, retornar informações para gerar no frontend
    
    with _BILLING_LOCK:
        data = _load_billing_data()
        invoices = data.get("invoices", {}).get(email, [])
    
    invoice = next((inv for inv in invoices if inv.get("id") == invoice_id), None)
    
    # Se não encontrar, criar dados de demonstração
    if not invoice:
        invoice = {
            "id": invoice_id,
            "number": f"INV-{datetime.now(UTC).strftime('%Y%m')}-0001",
            "amount": 29700,
            "currency": "BRL",
            "status": "paid",
            "description": "Assinatura Starter - Demonstração",
            "created_at": datetime.now(UTC).isoformat(),
            "paid_at": datetime.now(UTC).isoformat(),
        }
    
    return {
        "invoice_id": invoice_id,
        "download_url": f"https://automacao-cad-backend.vercel.app/api/billing/invoices/{invoice_id}/download",
        "invoice": invoice,
        "message": "PDF será gerado em breve. Por enquanto, use os dados da fatura para exibição.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT METHODS - Métodos de Pagamento
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentMethodResponse(BaseModel):
    id: str
    type: str  # card, pix, boleto
    brand: Optional[str]  # visa, mastercard, etc
    last4: Optional[str]
    exp_month: Optional[int]
    exp_year: Optional[int]
    is_default: bool
    created_at: str


class AddPaymentMethodRequest(BaseModel):
    type: str = Field(..., description="Tipo: card, pix, boleto")
    token: Optional[str] = Field(None, description="Token do Stripe para cartão")
    set_default: bool = Field(default=True, description="Definir como método padrão")


@router.get("/payment-methods")
async def list_payment_methods(email: str):
    """Lista métodos de pagamento do usuário."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        methods = data.get("payment_methods", {}).get(email, [])
    
    # Se não houver métodos, retornar exemplo para demonstração
    if not methods:
        methods = [
            {
                "id": "pm_demo_visa",
                "type": "card",
                "brand": "visa",
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2027,
                "is_default": True,
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]
    
    return {
        "payment_methods": methods,
        "default_method": next((m["id"] for m in methods if m.get("is_default")), None),
    }


@router.post("/payment-methods")
async def add_payment_method(email: str, request: AddPaymentMethodRequest):
    """
    Adiciona um novo método de pagamento.
    
    Em produção, isso usaria o Stripe para processar o token do cartão.
    """
    new_method = {
        "id": f"pm_{secrets.token_hex(8)}",
        "type": request.type,
        "brand": "visa" if request.type == "card" else None,
        "last4": "4242" if request.type == "card" else None,
        "exp_month": 12 if request.type == "card" else None,
        "exp_year": 2027 if request.type == "card" else None,
        "is_default": request.set_default,
        "created_at": datetime.now(UTC).isoformat(),
    }
    
    with _BILLING_LOCK:
        data = _load_billing_data()
        if "payment_methods" not in data:
            data["payment_methods"] = {}
        if email not in data["payment_methods"]:
            data["payment_methods"][email] = []
        
        # Se set_default, remover default dos outros
        if request.set_default:
            for m in data["payment_methods"][email]:
                m["is_default"] = False
        
        data["payment_methods"][email].append(new_method)
        _save_billing_data(data)
    
    return {
        "success": True,
        "payment_method": new_method,
        "message": "Método de pagamento adicionado com sucesso",
    }


@router.delete("/payment-methods/{method_id}")
async def remove_payment_method(email: str, method_id: str):
    """Remove um método de pagamento."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        methods = data.get("payment_methods", {}).get(email, [])
        
        # Verificar se é o único método
        if len(methods) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Não é possível remover o único método de pagamento"
            )
        
        # Encontrar e remover
        method = next((m for m in methods if m["id"] == method_id), None)
        if not method:
            raise HTTPException(status_code=404, detail="Método de pagamento não encontrado")
        
        was_default = method.get("is_default", False)
        methods.remove(method)
        
        # Se era default, definir outro como default
        if was_default and methods:
            methods[0]["is_default"] = True
        
        data["payment_methods"][email] = methods
        _save_billing_data(data)
    
    return {"success": True, "message": "Método de pagamento removido"}


@router.put("/payment-methods/{method_id}/default")
async def set_default_payment_method(email: str, method_id: str):
    """Define um método de pagamento como padrão."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        methods = data.get("payment_methods", {}).get(email, [])
        
        found = False
        for m in methods:
            if m["id"] == method_id:
                m["is_default"] = True
                found = True
            else:
                m["is_default"] = False
        
        if not found:
            raise HTTPException(status_code=404, detail="Método de pagamento não encontrado")
        
        data["payment_methods"][email] = methods
        _save_billing_data(data)
    
    return {"success": True, "message": "Método padrão atualizado"}


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN MANAGEMENT - Gerenciamento de Plano
# ═══════════════════════════════════════════════════════════════════════════════

class ChangePlanRequest(BaseModel):
    new_tier: str = Field(..., description="Novo plano: starter, professional, enterprise")
    billing_cycle: str = Field(default="monthly", description="monthly ou yearly")
    prorate: bool = Field(default=True, description="Calcular diferença proporcional")


@router.put("/subscription/plan")
async def change_subscription_plan(email: str, request: ChangePlanRequest):
    """
    Altera o plano da assinatura.
    
    - Upgrade: Aplicado imediatamente, cobrança proporcional
    - Downgrade: Aplicado no próximo período de faturamento
    """
    if request.new_tier not in PRICING_TIERS:
        raise HTTPException(status_code=400, detail="Plano inválido")
    
    billing_cycle = _normalize_billing_cycle(request.billing_cycle)
    new_tier_config = PRICING_TIERS[request.new_tier]
    
    with _BILLING_LOCK:
        data = _load_billing_data()
        sub = data.get("subscriptions", {}).get(email)
        
        if not sub:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        current_tier = sub.get("tier", "starter")
        current_config = PRICING_TIERS.get(current_tier, PRICING_TIERS["starter"])
        
        # Determinar se é upgrade ou downgrade
        tier_order = {"starter": 1, "professional": 2, "enterprise": 3}
        is_upgrade = tier_order.get(request.new_tier, 0) > tier_order.get(current_tier, 0)
        
        # Calcular valores
        price_key = f"price_{billing_cycle}"
        new_price = new_tier_config.get(price_key, new_tier_config["price_monthly"])
        old_price = current_config.get(price_key, current_config["price_monthly"])
        
        prorate_amount = 0
        if request.prorate and is_upgrade:
            # Calcular crédito proporcional do plano atual
            days_remaining = 15  # Simplificado: assumir meio do período
            daily_rate_old = old_price / 30
            credit = daily_rate_old * days_remaining
            
            daily_rate_new = new_price / 30
            charge = daily_rate_new * days_remaining
            
            prorate_amount = round(charge - credit, 2)
        
        # Atualizar assinatura
        if is_upgrade:
            sub["tier"] = request.new_tier
            sub["billing_cycle"] = billing_cycle
            sub["updated_at"] = datetime.now(UTC).isoformat()
            effective_date = datetime.now(UTC).isoformat()
        else:
            # Downgrade: agendar para próximo período
            sub["pending_tier"] = request.new_tier
            sub["pending_billing_cycle"] = billing_cycle
            effective_date = sub.get("current_period_end", datetime.now(UTC).isoformat())
        
        data["subscriptions"][email] = sub
        _save_billing_data(data)
    
    return {
        "success": True,
        "is_upgrade": is_upgrade,
        "previous_tier": current_tier,
        "new_tier": request.new_tier,
        "effective_date": effective_date,
        "prorate_amount": prorate_amount if is_upgrade else 0,
        "message": (
            f"Plano alterado para {new_tier_config['name']}. "
            f"{'Aplicado imediatamente.' if is_upgrade else 'Será aplicado no próximo período.'}"
        ),
    }


@router.get("/subscription/plans")
async def get_available_plans(email: str):
    """Retorna planos disponíveis para o usuário com comparação ao plano atual."""
    with _BILLING_LOCK:
        data = _load_billing_data()
        sub = data.get("subscriptions", {}).get(email, {})
    
    current_tier = sub.get("tier", "starter")
    current_cycle = sub.get("billing_cycle", "monthly")
    
    plans = []
    tier_order = {"starter": 1, "professional": 2, "enterprise": 3}
    
    for tier_key, tier_config in PRICING_TIERS.items():
        is_current = tier_key == current_tier
        is_upgrade = tier_order.get(tier_key, 0) > tier_order.get(current_tier, 0)
        is_downgrade = tier_order.get(tier_key, 0) < tier_order.get(current_tier, 0)
        
        plans.append({
            "tier": tier_key,
            "name": tier_config["name"],
            "price_monthly": tier_config["price_monthly"],
            "price_yearly": tier_config["price_yearly"],
            "currency": tier_config["currency"],
            "features": tier_config["features"],
            "is_current": is_current,
            "is_upgrade": is_upgrade,
            "is_downgrade": is_downgrade,
            "savings_yearly": tier_config["price_monthly"] * 12 - tier_config["price_yearly"],
        })
    
    return {
        "current_tier": current_tier,
        "current_cycle": current_cycle,
        "plans": plans,
    }
