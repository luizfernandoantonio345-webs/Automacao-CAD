"""
═══════════════════════════════════════════════════════════════════════════════
  ChatCAD — API Routes (NLP → AutoCAD)
═══════════════════════════════════════════════════════════════════════════════

Endpoints REST para o ChatCAD:
  POST /api/chatcad/interpret   — Interpreta prompt natural
  POST /api/chatcad/execute     — Executa plano de ações
  POST /api/chatcad/chat        — Interpreta + executa em um só passo
  GET  /api/chatcad/examples    — Exemplos de comandos
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ai_engines.chatcad_interpreter import (
    interpretar_prompt,
    executar_plano,
    ComandoTipo,
    ACAO_ENDPOINT_MAP,
)

logger = logging.getLogger("engcad.chatcad.routes")

router = APIRouter(prefix="/api/chatcad", tags=["ChatCAD - NLP"])

# ── LLM disponível? ──
_LLM_AVAILABLE = bool(os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", ""))


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChatCadPromptRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=2000, description="Comando em linguagem natural")
    contexto: Dict[str, Any] = Field(default_factory=dict)


class ChatCadExecuteRequest(BaseModel):
    plano: List[Dict[str, Any]] = Field(..., min_length=1, description="Plano de ações a executar")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/interpret")
async def interpret_prompt(req: ChatCadPromptRequest):
    """Interpreta um prompt em linguagem natural e retorna o plano estruturado."""
    result = interpretar_prompt(req.texto)
    return {
        "success": True,
        **result.to_dict(),
    }


@router.post("/execute")
async def execute_plan(req: ChatCadExecuteRequest):
    """Executa um plano de ações previamente interpretado."""
    result = await executar_plano(req.plano)
    return result


@router.post("/chat")
async def chat_and_execute(req: ChatCadPromptRequest):
    """
    Fluxo completo: Interpreta → Planeja → Executa.
    
    Se for pergunta, redireciona para o chatbot assistente existente.
    Se for comando, interpreta e executa automaticamente.
    """
    interpretacao = interpretar_prompt(req.texto)

    # Se for pergunta, usar o assistente existente
    if interpretacao.tipo == ComandoTipo.PERGUNTA:
        try:
            # Tentar LLM primeiro (OpenAI/Anthropic) para resposta interativa estilo ChatGPT
            if _LLM_AVAILABLE:
                try:
                    from ai_engines.llm_gateway import call_llm, OPENAI_API_KEY, ANTHROPIC_API_KEY
                    from ai_engines.ai_guardrails import inject_system_prompt
                    
                    model = "gpt-4o-mini" if OPENAI_API_KEY else "claude-3-haiku-20240307"
                    messages = inject_system_prompt([
                        {"role": "user", "content": req.texto}
                    ])
                    
                    full_response = ""
                    async for chunk in call_llm(model, messages, 0.7, 2048, stream=False):
                        full_response += chunk
                    
                    if full_response.strip():
                        return {
                            "success": True,
                            "tipo": "pergunta",
                            "interpretacao": interpretacao.to_dict(),
                            "resposta": {"response": full_response.strip()},
                            "executado": False,
                            "llm": True,
                        }
                except Exception as llm_err:
                    logger.warning(f"LLM falhou, usando chatbot padrão: {llm_err}")
            
            # Fallback: chatbot baseado em padrões
            from ai_engines.router import ai_router as engine_router
            chat_result = await engine_router.chat(req.texto, req.contexto)
            return {
                "success": True,
                "tipo": "pergunta",
                "interpretacao": interpretacao.to_dict(),
                "resposta": chat_result,
                "executado": False,
            }
        except Exception as e:
            logger.warning(f"Chatbot indisponível: {e}")
            return {
                "success": True,
                "tipo": "pergunta",
                "interpretacao": interpretacao.to_dict(),
                "resposta": {"response": "Assistente temporariamente indisponível. Tente um comando como: 'tubo 6 polegadas 1000mm eixo x'"},
                "executado": False,
            }

    # Se desconhecido, tentar LLM ou retornar sugestões
    if interpretacao.tipo == ComandoTipo.DESCONHECIDO:
        # Tentar LLM para resposta inteligente
        if _LLM_AVAILABLE:
            try:
                from ai_engines.llm_gateway import call_llm, OPENAI_API_KEY, ANTHROPIC_API_KEY
                from ai_engines.ai_guardrails import inject_system_prompt
                
                model = "gpt-4o-mini" if OPENAI_API_KEY else "claude-3-haiku-20240307"
                messages = inject_system_prompt([
                    {"role": "user", "content": req.texto}
                ])
                
                full_response = ""
                async for chunk in call_llm(model, messages, 0.7, 2048, stream=False):
                    full_response += chunk
                
                if full_response.strip():
                    return {
                        "success": True,
                        "tipo": "pergunta",
                        "interpretacao": interpretacao.to_dict(),
                        "resposta": {"response": full_response.strip()},
                        "executado": False,
                        "llm": True,
                    }
            except Exception as llm_err:
                logger.warning(f"LLM falhou no desconhecido: {llm_err}")
        
        # Fallback: tentar chatbot padrão
        try:
            from ai_engines.router import ai_router as engine_router
            chat_result = await engine_router.chat(req.texto, req.contexto)
            resp_text = chat_result.get("response", "") if isinstance(chat_result, dict) else str(chat_result)
            if resp_text and "Desculpe" not in resp_text and len(resp_text) > 30:
                return {
                    "success": True,
                    "tipo": "pergunta",
                    "interpretacao": interpretacao.to_dict(),
                    "resposta": {"response": resp_text},
                    "executado": False,
                }
        except Exception:
            pass
        
        return {
            "success": True,
            "tipo": "desconhecido",
            "interpretacao": interpretacao.to_dict(),
            "resposta": {
                "response": "Não entendi esse comando. Veja as sugestões abaixo.",
            },
            "executado": False,
        }

    # Comando reconhecido → executar
    plano = interpretacao.dados.get("plano", [])
    if not plano:
        return {
            "success": True,
            "tipo": interpretacao.tipo,
            "interpretacao": interpretacao.to_dict(),
            "resposta": {"response": "Plano vazio — nada a executar."},
            "executado": False,
        }

    execucao = await executar_plano(plano)
    
    return {
        "success": True,
        "tipo": interpretacao.tipo,
        "interpretacao": interpretacao.to_dict(),
        "execucao": execucao,
        "executado": True,
        "resposta": {
            "response": _gerar_resumo(interpretacao, execucao),
        },
    }


def _gerar_resumo(interpretacao, execucao: Dict) -> str:
    """Gera um resumo legível da execução."""
    total = execucao.get("total", 0)
    ok = execucao.get("executadas", 0)
    falhas = execucao.get("falhas", 0)

    if falhas == 0:
        return f"✅ Executado com sucesso! {ok}/{total} operações concluídas."
    elif ok > 0:
        return f"⚠️ Parcialmente executado: {ok}/{total} OK, {falhas} falhas."
    else:
        return f"❌ Falha na execução: {falhas}/{total} operações falharam."


@router.get("/examples")
async def get_examples():
    """Retorna exemplos de comandos aceitos."""
    return {
        "simples": [
            {"comando": "tubo 6 polegadas 1000mm eixo x", "descricao": "Cria tubo Ø6\" de 1000mm no eixo X"},
            {"comando": "válvula gaveta em 500,0,0", "descricao": "Insere válvula gaveta na posição (500,0,0)"},
            {"comando": "linha de 0,0 até 1000,500", "descricao": "Desenha linha entre dois pontos"},
            {"comando": 'texto "TAG-001" em 100,200,0', "descricao": "Adiciona anotação de texto"},
            {"comando": "criar layers n-58", "descricao": "Cria sistema de layers Petrobras"},
            {"comando": "salvar", "descricao": "Salva o documento atual"},
        ],
        "compostos": [
            {"comando": "criar linha e adicionar válvula no meio", "descricao": "Cria linha + insere válvula no ponto médio"},
            {"comando": "tubo 8 polegadas 2000mm e depois commit", "descricao": "Cria tubo e envia para AutoCAD"},
        ],
        "projetos": [
            {"comando": "criar planta com tubulação principal e derivações", "descricao": "Gera projeto completo com headers e branches"},
            {"comando": "criar planta com tubulação 6 polegadas, válvulas e flanges", "descricao": "Projeto com tubulação, válvulas e flanges"},
        ],
        "perguntas": [
            {"comando": "o que é a norma ASME B31.3?", "descricao": "Pergunta técnica sobre normas"},
            {"comando": "como calcular espessura de parede?", "descricao": "Pergunta sobre cálculos"},
        ],
    }


@router.get("/actions")
async def get_supported_actions():
    """Lista todas as ações suportadas e seus endpoints."""
    return {
        "actions": [
            {"acao": k, "endpoint": v["path"], "method": v["method"]}
            for k, v in ACAO_ENDPOINT_MAP.items()
        ]
    }
