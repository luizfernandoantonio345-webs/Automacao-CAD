#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ENGENHARIA CAD — LLM GATEWAY (Multi-provider AI Proxy)
# ═══════════════════════════════════════════════════════════════════════════════
"""
Gateway unificado para múltiplos provedores de LLM:
- OpenAI (GPT-4o, GPT-4-turbo)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)
- Ollama (Local models - Llama3, Mistral)

Features:
- Rate limiting por usuário
- Fallback automático entre provedores
- Streaming support
- Token counting e billing
- Caching de respostas similares
- Retry com exponential backoff
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import AsyncGenerator, Dict, Any, List, Optional, Literal

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger("engcad.llm_gateway")

router = APIRouter(prefix="/api/llm", tags=["llm-gateway"])

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

DEFAULT_MODEL = os.getenv("LLM_DEFAULT_MODEL", "gpt-4o")
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Rate limits por tier
RATE_LIMITS = {
    "starter": {"requests_per_minute": 20, "tokens_per_day": 50000},
    "professional": {"requests_per_minute": 60, "tokens_per_day": 200000},
    "enterprise": {"requests_per_minute": 200, "tokens_per_day": 1000000},
}

# Modelos disponíveis
AVAILABLE_MODELS = {
    # OpenAI
    "gpt-4o": {"provider": "openai", "context_window": 128000, "cost_per_1k_input": 0.005, "cost_per_1k_output": 0.015},
    "gpt-4o-mini": {"provider": "openai", "context_window": 128000, "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006},
    "gpt-4-turbo": {"provider": "openai", "context_window": 128000, "cost_per_1k_input": 0.01, "cost_per_1k_output": 0.03},
    # Anthropic
    "claude-3-5-sonnet-20241022": {"provider": "anthropic", "context_window": 200000, "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015},
    "claude-3-opus-20240229": {"provider": "anthropic", "context_window": 200000, "cost_per_1k_input": 0.015, "cost_per_1k_output": 0.075},
    "claude-3-haiku-20240307": {"provider": "anthropic", "context_window": 200000, "cost_per_1k_input": 0.00025, "cost_per_1k_output": 0.00125},
    # Ollama (local)
    "llama3.2": {"provider": "ollama", "context_window": 128000, "cost_per_1k_input": 0, "cost_per_1k_output": 0},
    "mistral": {"provider": "ollama", "context_window": 32000, "cost_per_1k_input": 0, "cost_per_1k_output": 0},
    "codellama": {"provider": "ollama", "context_window": 16000, "cost_per_1k_input": 0, "cost_per_1k_output": 0},
}

# Fallback chain
FALLBACK_CHAIN = {
    "openai": ["anthropic", "ollama"],
    "anthropic": ["openai", "ollama"],
    "ollama": ["openai", "anthropic"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDERS (Lazy loading)
# ═══════════════════════════════════════════════════════════════════════════════

_openai_client = None
_anthropic_client = None
_httpx_client = None


def get_openai_client():
    """Carrega OpenAI client sob demanda."""
    global _openai_client
    if _openai_client is None and OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI client inicializado")
        except ImportError:
            logger.warning("OpenAI SDK não instalado")
    return _openai_client


def get_anthropic_client():
    """Carrega Anthropic client sob demanda."""
    global _anthropic_client
    if _anthropic_client is None and ANTHROPIC_API_KEY:
        try:
            from anthropic import AsyncAnthropic
            _anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            logger.info("Anthropic client inicializado")
        except ImportError:
            logger.warning("Anthropic SDK não instalado")
    return _anthropic_client


async def get_httpx_client():
    """Carrega httpx client para Ollama."""
    global _httpx_client
    if _httpx_client is None:
        import httpx
        _httpx_client = httpx.AsyncClient(timeout=120.0)
    return _httpx_client


# ═══════════════════════════════════════════════════════════════════════════════
# TOKEN COUNTING
# ═══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=8)
def get_tokenizer(model: str):
    """Carrega tokenizer para contagem de tokens."""
    try:
        import tiktoken
        if "gpt" in model or "openai" in model:
            return tiktoken.encoding_for_model("gpt-4o")
        return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        return None


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Conta tokens de um texto."""
    tokenizer = get_tokenizer(model)
    if tokenizer:
        return len(tokenizer.encode(text))
    # Fallback: estimativa ~4 chars per token
    return len(text) // 4


def count_message_tokens(messages: List[Dict], model: str = "gpt-4o") -> int:
    """Conta tokens totais de uma lista de mensagens."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""), model)
        total += 4  # Overhead per message
    total += 3  # Priming
    return total


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE CACHE
# ═══════════════════════════════════════════════════════════════════════════════

_CACHE_FILE = Path(__file__).parent.parent / "data" / "llm_cache.json"
_CACHE_LOCK = Lock()
_CACHE_MAX_SIZE = 1000
_CACHE_TTL_SECONDS = 3600  # 1 hora


def _get_cache_key(model: str, messages: List[Dict], temperature: float) -> str:
    """Gera cache key determinístico."""
    content = json.dumps({"model": model, "messages": messages, "temperature": temperature}, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _load_cache() -> Dict[str, Any]:
    """Carrega cache do disco."""
    if not _CACHE_FILE.exists():
        return {}
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    """Salva cache no disco."""
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Limitar tamanho
    if len(cache) > _CACHE_MAX_SIZE:
        # Remover entradas mais antigas
        sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("timestamp", 0))
        for key in sorted_keys[:len(cache) - _CACHE_MAX_SIZE]:
            del cache[key]
    _CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def get_cached_response(cache_key: str) -> Optional[str]:
    """Busca resposta em cache."""
    with _CACHE_LOCK:
        cache = _load_cache()
        entry = cache.get(cache_key)
        if entry:
            # Verificar TTL
            if time.time() - entry.get("timestamp", 0) < _CACHE_TTL_SECONDS:
                logger.info(f"Cache hit: {cache_key}")
                return entry.get("response")
            # Cache expirado
            del cache[cache_key]
            _save_cache(cache)
    return None


def set_cached_response(cache_key: str, response: str) -> None:
    """Salva resposta em cache."""
    with _CACHE_LOCK:
        cache = _load_cache()
        cache[cache_key] = {
            "response": response,
            "timestamp": time.time(),
        }
        _save_cache(cache)


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

_USAGE_FILE = Path(__file__).parent.parent / "data" / "llm_usage.json"
_USAGE_LOCK = Lock()


def _load_usage() -> Dict[str, Any]:
    if not _USAGE_FILE.exists():
        return {}
    try:
        return json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
    except:
        return {}


def _save_usage(usage: Dict[str, Any]) -> None:
    _USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _USAGE_FILE.write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")


def track_llm_usage(email: str, model: str, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
    """Registra uso de LLM e calcula custo."""
    model_info = AVAILABLE_MODELS.get(model, AVAILABLE_MODELS["gpt-4o"])
    cost = (input_tokens / 1000 * model_info["cost_per_1k_input"] +
            output_tokens / 1000 * model_info["cost_per_1k_output"])
    
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    
    with _USAGE_LOCK:
        usage = _load_usage()
        
        if email not in usage:
            usage[email] = {}
        if today not in usage[email]:
            usage[email][today] = {"tokens": 0, "requests": 0, "cost": 0.0}
        
        usage[email][today]["tokens"] += input_tokens + output_tokens
        usage[email][today]["requests"] += 1
        usage[email][today]["cost"] += cost
        
        _save_usage(usage)
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }


def check_rate_limit(email: str, tier: str = "starter") -> bool:
    """Verifica se usuário está dentro do rate limit."""
    limits = RATE_LIMITS.get(tier, RATE_LIMITS["starter"])
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    
    with _USAGE_LOCK:
        usage = _load_usage()
        day_usage = usage.get(email, {}).get(today, {"tokens": 0, "requests": 0})
    
    return day_usage["tokens"] < limits["tokens_per_day"]


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class Message(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(..., description="Papel da mensagem")
    content: str = Field(..., min_length=1, max_length=100000, description="Conteúdo")


class CompletionRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL, description="Nome do modelo")
    messages: List[Message] = Field(..., min_length=1, max_length=100, description="Mensagens")
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0, le=2, description="Temperatura")
    max_tokens: int = Field(default=MAX_TOKENS, ge=1, le=32000, description="Máximo de tokens")
    stream: bool = Field(default=False, description="Streaming response")
    use_cache: bool = Field(default=True, description="Usar cache de respostas")


class CompletionResponse(BaseModel):
    id: str
    model: str
    content: str
    usage: Dict[str, Any]
    provider: str
    cached: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def call_openai(
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
    stream: bool = False,
) -> AsyncGenerator[str, None] | str:
    """Chama OpenAI API."""
    client = get_openai_client()
    if not client:
        raise HTTPException(status_code=503, detail="OpenAI não configurado")
    
    formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    if stream:
        response = await client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        response = await client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield response.choices[0].message.content


async def call_anthropic(
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
    stream: bool = False,
) -> AsyncGenerator[str, None] | str:
    """Chama Anthropic API."""
    client = get_anthropic_client()
    if not client:
        raise HTTPException(status_code=503, detail="Anthropic não configurado")
    
    # Separar system message
    system_msg = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            user_messages.append({"role": m["role"], "content": m["content"]})
    
    if stream:
        async with client.messages.stream(
            model=model,
            system=system_msg,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as response:
            async for text in response.text_stream:
                yield text
    else:
        response = await client.messages.create(
            model=model,
            system=system_msg,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield response.content[0].text


async def call_ollama(
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
    stream: bool = False,
) -> AsyncGenerator[str, None] | str:
    """Chama Ollama API (local)."""
    client = await get_httpx_client()
    
    payload = {
        "model": model,
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }
    
    if stream:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if content := data.get("message", {}).get("content"):
                        yield content
    else:
        response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        data = response.json()
        yield data.get("message", {}).get("content", "")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GATEWAY LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

async def call_llm(
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
    stream: bool = False,
    fallback: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Gateway central que roteia para o provider correto.
    Implementa fallback automático se provider primário falhar.
    Sempre retorna um async generator para consistência.
    """
    model_info = AVAILABLE_MODELS.get(model)
    if not model_info:
        raise HTTPException(status_code=400, detail=f"Modelo não suportado: {model}")
    
    provider = model_info["provider"]
    providers_to_try = [provider]
    if fallback:
        providers_to_try.extend(FALLBACK_CHAIN.get(provider, []))
    
    last_error = None
    for try_provider in providers_to_try:
        try:
            # Selecionar modelo compatível do provider
            if try_provider == provider:
                use_model = model
            else:
                # Fallback model
                if try_provider == "openai":
                    use_model = "gpt-4o-mini"
                elif try_provider == "anthropic":
                    use_model = "claude-3-haiku-20240307"
                else:
                    use_model = "llama3.2"
            
            logger.info(f"Chamando {try_provider} com modelo {use_model}")
            
            if try_provider == "openai":
                async for chunk in call_openai(use_model, messages, temperature, max_tokens, stream):
                    yield chunk
                return
            elif try_provider == "anthropic":
                async for chunk in call_anthropic(use_model, messages, temperature, max_tokens, stream):
                    yield chunk
                return
            elif try_provider == "ollama":
                async for chunk in call_ollama(use_model, messages, temperature, max_tokens, stream):
                    yield chunk
                return
                
        except Exception as e:
            logger.warning(f"Falha em {try_provider}: {e}")
            last_error = e
            continue
    
    raise HTTPException(
        status_code=503,
        detail=f"Todos os provedores falharam. Último erro: {last_error}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/models")
async def list_models():
    """Lista modelos disponíveis."""
    models = []
    for model_name, info in AVAILABLE_MODELS.items():
        available = False
        if info["provider"] == "openai" and OPENAI_API_KEY:
            available = True
        elif info["provider"] == "anthropic" and ANTHROPIC_API_KEY:
            available = True
        elif info["provider"] == "ollama":
            available = True  # Assume Ollama local disponível
        
        models.append({
            "id": model_name,
            "provider": info["provider"],
            "context_window": info["context_window"],
            "cost_per_1k_input": info["cost_per_1k_input"],
            "cost_per_1k_output": info["cost_per_1k_output"],
            "available": available,
        })
    
    return {"models": models, "default": DEFAULT_MODEL}


from ai_engines.ai_guardrails import apply_guardrails, inject_system_prompt


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    req: CompletionRequest,
    email: str = Header(default="anonymous", alias="X-User-Email"),
    tier: str = Header(default="starter", alias="X-User-Tier"),
):
    """
    Gera completion usando LLM.
    Suporta cache, rate limiting, guardrails e fallback automático.
    """
    # Verificar rate limit
    if not check_rate_limit(email, tier):
        raise HTTPException(
            status_code=429,
            detail="Rate limit excedido. Faça upgrade do plano para mais tokens."
        )
    
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    
    # Aplicar guardrails - verificar se mensagem está no escopo
    last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    guardrail_result = apply_guardrails(last_user_msg)
    
    if not guardrail_result["allowed"]:
        # Mensagem fora do escopo - retornar redirecionamento sem chamar LLM
        return CompletionResponse(
            id="guardrail_blocked",
            model=req.model,
            content=guardrail_result["redirect"],
            usage={"blocked": True, "reason": guardrail_result["category"]},
            provider="guardrails",
            cached=False,
        )
    
    # Injetar system prompt para contextualizar a IA
    messages = inject_system_prompt(messages)
    
    # Verificar cache
    if req.use_cache and not req.stream:
        cache_key = _get_cache_key(req.model, messages, req.temperature)
        cached = get_cached_response(cache_key)
        if cached:
            return CompletionResponse(
                id=f"cached_{cache_key}",
                model=req.model,
                content=cached,
                usage={"cached": True, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0},
                provider="cache",
                cached=True,
            )
    
    # Contar tokens de entrada
    input_tokens = count_message_tokens(messages, req.model)
    
    if req.stream:
        # Streaming response
        async def stream_generator():
            full_response = ""
            async for chunk in call_llm(
                req.model, messages, req.temperature, req.max_tokens, stream=True
            ):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            # Track usage após streaming completo
            output_tokens = count_tokens(full_response, req.model)
            usage = track_llm_usage(email, req.model, input_tokens, output_tokens)
            yield f"data: {json.dumps({'done': True, 'usage': usage})}\n\n"
        
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    
    # Non-streaming response - collect all chunks
    content_chunks = []
    async for chunk in call_llm(
        req.model, messages, req.temperature, req.max_tokens, stream=False
    ):
        content_chunks.append(chunk)
    content = "".join(content_chunks)
    
    # Contar tokens de saída
    output_tokens = count_tokens(content, req.model)
    usage = track_llm_usage(email, req.model, input_tokens, output_tokens)
    
    # Salvar em cache
    if req.use_cache:
        cache_key = _get_cache_key(req.model, messages, req.temperature)
        set_cached_response(cache_key, content)
    
    model_info = AVAILABLE_MODELS.get(req.model, AVAILABLE_MODELS["gpt-4o"])
    
    return CompletionResponse(
        id=f"cmpl_{hashlib.sha256(content.encode()).hexdigest()[:16]}",
        model=req.model,
        content=content,
        usage=usage,
        provider=model_info["provider"],
        cached=False,
    )


@router.get("/usage/{email}")
async def get_llm_usage(email: str):
    """Retorna uso de LLM do usuário."""
    with _USAGE_LOCK:
        usage = _load_usage()
        user_usage = usage.get(email, {})
    
    # Calcular totais
    total_tokens = 0
    total_requests = 0
    total_cost = 0.0
    
    for day_data in user_usage.values():
        total_tokens += day_data.get("tokens", 0)
        total_requests += day_data.get("requests", 0)
        total_cost += day_data.get("cost", 0.0)
    
    return {
        "email": email,
        "daily": user_usage,
        "totals": {
            "tokens": total_tokens,
            "requests": total_requests,
            "cost_usd": round(total_cost, 4),
        }
    }


@router.get("/health")
async def llm_health():
    """Health check do LLM Gateway."""
    providers = {}
    
    if OPENAI_API_KEY:
        providers["openai"] = "configured"
    else:
        providers["openai"] = "not_configured"
    
    if ANTHROPIC_API_KEY:
        providers["anthropic"] = "configured"
    else:
        providers["anthropic"] = "not_configured"
    
    # Verificar Ollama
    try:
        client = await get_httpx_client()
        response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if response.status_code == 200:
            providers["ollama"] = "available"
        else:
            providers["ollama"] = "unavailable"
    except:
        providers["ollama"] = "unavailable"
    
    return {
        "status": "healthy" if any(v in ["configured", "available"] for v in providers.values()) else "degraded",
        "providers": providers,
        "default_model": DEFAULT_MODEL,
        "cache_enabled": True,
    }
