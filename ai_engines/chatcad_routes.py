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

# ── Engineering validator (lazy import — optional dependency) ────────────────
try:
    from backend.engineering_validator import EngineeringValidator
    _ENG_VALIDATOR_AVAILABLE = True
except ImportError:
    _ENG_VALIDATOR_AVAILABLE = False

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


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE ENGENHARIA — ASME B31.3 / B16.5 / AWS D1.1 / ISO 128
# ═══════════════════════════════════════════════════════════════════════════════

class PipeValidationRequest(BaseModel):
    diameter_mm: float = Field(..., gt=0, le=2000, description="Diâmetro externo do tubo (mm)")
    thickness_mm: float = Field(..., gt=0, le=500, description="Espessura de parede (mm)")
    pressure_bar: float = Field(..., ge=0, le=5000, description="Pressão de operação (bar)")
    fluid: str = Field(default="unknown", max_length=50)
    material_yield_mpa: float = Field(default=250.0, gt=0, le=3000)
    temperature_c: float = Field(default=25.0, ge=-50, le=1000)

    @property
    def safe_fluid(self) -> str:
        """Retorna fluido sanitizado — apenas letras, números e underscores."""
        import re as _re
        return _re.sub(r"[^a-z0-9_]", "", self.fluid.lower().strip())[:50]


class FlangeValidationRequest(BaseModel):
    size_inches: float = Field(..., gt=0, le=100, description="Diâmetro nominal (polegadas)")
    rating_class: int = Field(..., description="Classe do flange: 150, 300, 600, 900, 1500, 2500")
    pressure_bar: float = Field(..., ge=0, le=5000, description="Pressão de operação (bar)")
    temperature_c: float = Field(default=38.0, ge=-50, le=1000)
    facing: str = Field(default="RF", max_length=10)

    @property
    def safe_facing(self) -> str:
        """Apenas valores conhecidos de face."""
        allowed = {"RF", "FF", "RTJ", "MFM", "TG"}
        val = self.facing.upper().strip()
        return val if val in allowed else "RF"


class WeldValidationRequest(BaseModel):
    throat_mm: float = Field(..., gt=0, le=500, description="Garganta efetiva (mm)")
    base_material_thickness_mm: float = Field(..., gt=0, le=500, description="Espessura do metal base (mm)")
    load_kn: float = Field(default=0.0, ge=0, le=100000, description="Carga aplicada (kN)")
    electrode: str = Field(default="E7018", max_length=20)
    weld_length_mm: float = Field(default=100.0, gt=0, le=50000)

    @property
    def safe_electrode(self) -> str:
        """Apenas identificadores de eletrodo válidos (letras, números, hífen)."""
        import re as _re
        return _re.sub(r"[^A-Z0-9\-]", "", self.electrode.upper().strip())[:20]


@router.post("/validate/pipe-asme-b31-3",
             summary="Validação de tubulação ASME B31.3",
             tags=["Engineering Validation"])
async def validate_pipe(req: PipeValidationRequest):
    """
    Valida espessura de parede de tubulação conforme ASME B31.3.

    Retorna: valid, warnings, errors, recommendations e cálculos de espessura mínima.
    """
    if not _ENG_VALIDATOR_AVAILABLE:
        return {"success": False, "error": "Módulo de validação indisponível."}

    result = EngineeringValidator.validate_pipe_asme_b31_3(
        diameter_mm=req.diameter_mm,
        thickness_mm=req.thickness_mm,
        pressure_bar=req.pressure_bar,
        fluid=req.safe_fluid,
        material_yield_mpa=req.material_yield_mpa,
        temperature_c=req.temperature_c,
    )
    return {"success": True, **result}


@router.post("/validate/flange-asme-b16-5",
             summary="Validação de flange ASME B16.5",
             tags=["Engineering Validation"])
async def validate_flange(req: FlangeValidationRequest):
    """
    Valida flange conforme ASME B16.5 Pipe Flanges and Flanged Fittings.

    Retorna: valid, warnings, errors, pressão máxima admissível e recomendação de upgrade.
    """
    if not _ENG_VALIDATOR_AVAILABLE:
        return {"success": False, "error": "Módulo de validação indisponível."}

    result = EngineeringValidator.validate_flange_asme_b16_5(
        size_inches=req.size_inches,
        rating_class=req.rating_class,
        pressure_bar=req.pressure_bar,
        temperature_c=req.temperature_c,
        facing=req.safe_facing,
    )
    return {"success": True, **result}


@router.post("/validate/weld-aws-d1-1",
             summary="Validação de soldagem AWS D1.1",
             tags=["Engineering Validation"])
async def validate_weld(req: WeldValidationRequest):
    """
    Valida solda de filete conforme AWS D1.1 Structural Welding Code — Steel.

    Retorna: valid, warnings, errors, capacidade da solda e utilização.
    """
    if not _ENG_VALIDATOR_AVAILABLE:
        return {"success": False, "error": "Módulo de validação indisponível."}

    result = EngineeringValidator.validate_weld_aws_d1_1(
        throat_mm=req.throat_mm,
        base_material_thickness_mm=req.base_material_thickness_mm,
        load_kn=req.load_kn,
        electrode=req.safe_electrode,
        weld_length_mm=req.weld_length_mm,
    )
    return {"success": True, **result}


@router.get("/validate/schedule-suggestion",
            summary="Sugestão de schedule de tubo ASME B31.3",
            tags=["Engineering Validation"])
async def suggest_schedule(
    diameter_mm: float,
    pressure_bar: float,
    material_yield_mpa: float = 250.0,
):
    """
    Sugere schedule de tubo baseado em diâmetro e pressão de operação (ASME B31.3).
    """
    if not _ENG_VALIDATOR_AVAILABLE:
        return {"success": False, "error": "Módulo de validação indisponível."}

    result = EngineeringValidator.suggest_pipe_schedule(
        diameter_mm=diameter_mm,
        pressure_bar=pressure_bar,
        material_yield_mpa=material_yield_mpa,
    )
    return {"success": True, **result}
