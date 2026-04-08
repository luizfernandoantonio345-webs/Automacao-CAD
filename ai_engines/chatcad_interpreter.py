"""
═══════════════════════════════════════════════════════════════════════════════
  ChatCAD — Interpretador de Linguagem Natural para Comandos CAD
═══════════════════════════════════════════════════════════════════════════════

Transforma comandos em português natural em planos de execução estruturados
que são executados pelo sistema AutoCAD Driver existente.

Fluxo:
  Usuário → Chat → interpretarPrompt() → Planner → Executor → AutoCAD

Reutiliza 100% das funções existentes do backend/routes_autocad.py
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import re
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("engcad.chatcad")


# ─── Tipos de comando ────────────────────────────────────────────────────────

class ComandoTipo:
    SIMPLES = "comando_simples"
    COMPOSTO = "comando_composto"
    PROJETO = "projeto_completo"
    PERGUNTA = "pergunta"
    DESCONHECIDO = "desconhecido"


@dataclass
class InterpretacaoResult:
    tipo: str
    dados: Dict[str, Any]
    confianca: float = 0.0
    sugestoes: List[str] = field(default_factory=list)
    texto_original: str = ""
    correcao: str = ""

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "dados": self.dados,
            "confianca": self.confianca,
            "sugestoes": self.sugestoes,
            "texto_original": self.texto_original,
            "correcao": self.correcao,
        }


@dataclass
class PlanoAcao:
    plano: List[Dict[str, Any]]
    descricao: str = ""
    estimativa_operacoes: int = 0

    def to_dict(self) -> dict:
        return {
            "plano": self.plano,
            "descricao": self.descricao,
            "estimativa_operacoes": self.estimativa_operacoes,
        }


# ─── Padrões de Reconhecimento ───────────────────────────────────────────────

# Mapeamento de diâmetros nominais comuns (polegadas)
DIAMETROS_NOMINAIS = {
    "meia": 0.5, "1/2": 0.5,
    "3/4": 0.75, "tres quartos": 0.75,
    "1": 1, "uma": 1, "uma polegada": 1,
    "1.5": 1.5, "1 1/2": 1.5, "uma e meia": 1.5,
    "2": 2, "duas": 2, "duas polegadas": 2,
    "3": 3, "tres": 3, "três": 3,
    "4": 4, "quatro": 4,
    "6": 6, "seis": 6,
    "8": 8, "oito": 8,
    "10": 10, "dez": 10,
    "12": 12, "doze": 12,
    "14": 14, "quatorze": 14, "catorze": 14,
    "16": 16, "dezesseis": 16,
    "20": 20, "vinte": 20,
    "24": 24, "vinte e quatro": 24,
}

# Mapeamento de blocos de válvulas
VALVE_KEYWORDS = {
    "gaveta": "VALVE-GATE",
    "gate": "VALVE-GATE",
    "globo": "VALVE-GLOBE",
    "globe": "VALVE-GLOBE",
    "retencao": "VALVE-CHECK",
    "retenção": "VALVE-CHECK",
    "check": "VALVE-CHECK",
    "esfera": "VALVE-BALL",
    "ball": "VALVE-BALL",
    "borboleta": "VALVE-BUTTERFLY",
    "butterfly": "VALVE-BUTTERFLY",
    "agulha": "VALVE-NEEDLE",
    "needle": "VALVE-NEEDLE",
    "alivio": "VALVE-RELIEF",
    "alívio": "VALVE-RELIEF",
    "relief": "VALVE-RELIEF",
    "controle": "VALVE-CONTROL",
    "control": "VALVE-CONTROL",
    "plug": "VALVE-PLUG",
    "macho": "VALVE-PLUG",
}

COMPONENT_KEYWORDS = {
    "flange wn": "FLANGE-WN",
    "flange welding neck": "FLANGE-WN",
    "flange so": "FLANGE-SO",
    "flange slip on": "FLANGE-SO",
    "flange cega": "FLANGE-BL",
    "flange bl": "FLANGE-BL",
    "flange blind": "FLANGE-BL",
    "redutor concentrico": "REDUCER-CON",
    "redutor concêntrico": "REDUCER-CON",
    "redutor excentrico": "REDUCER-ECC",
    "redutor excêntrico": "REDUCER-ECC",
    "te igual": "TEE-EQUAL",
    "te reduzido": "TEE-REDUCING",
    "tê igual": "TEE-EQUAL",
    "tê reduzido": "TEE-REDUCING",
    "cotovelo 90": "ELBOW-90",
    "curva 90": "ELBOW-90",
    "cotovelo 45": "ELBOW-45",
    "curva 45": "ELBOW-45",
}

# Padrões de eixo
EIXO_MAP = {
    "x": ([1, 0, 0], "eixo X"),
    "y": ([0, 1, 0], "eixo Y"),
    "z": ([0, 0, 1], "eixo Z"),
    "horizontal": ([1, 0, 0], "horizontal (X)"),
    "vertical": ([0, 1, 0], "vertical (Y)"),
    "altura": ([0, 0, 1], "altitude (Z)"),
}

# ─── Correção de Texto ───────────────────────────────────────────────────────

CORRECOES = {
    "tudo": "tubo",
    "tubu": "tubo",
    "poegadas": "polegadas",
    "poelgadas": "polegadas",
    "valvla": "válvula",
    "valvula": "válvula",
    "vavula": "válvula",
    "compriment": "comprimento",
    "compriemnto": "comprimento",
    "dimetro": "diâmetro",
    "diamentro": "diâmetro",
    "diamtro": "diâmetro",
    "flaneg": "flange",
    "flangi": "flange",
    "lihna": "linha",
    "linh": "linha",
    "criar": "criar",
    "cria": "criar",
    "faca": "faça",
    "fase": "faça",
    "inseri": "inserir",
    "insira": "inserir",
    "desnehar": "desenhar",
    "desehar": "desenhar",
    "desneho": "desenho",
}


def corrigir_texto(texto: str) -> str:
    """Aplica correções ortográficas comuns."""
    resultado = texto.lower().strip()
    for errado, correto in CORRECOES.items():
        resultado = re.sub(r'\b' + re.escape(errado) + r'\b', correto, resultado)
    return resultado


# ─── Extração de Parâmetros ───────────────────────────────────────────────────

def extrair_diametro(texto: str) -> Optional[float]:
    """Extrai diâmetro do texto em polegadas."""
    # Padrão: "6 polegadas", "6\"", "Ø6", "DN150"
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:polegad|pol|"|\u2033)',
        r'[øØ]\s*(\d+(?:\.\d+)?)',
        r'(?:diâmetro|diametro|diam)\s*(?:de\s*)?(\d+(?:\.\d+)?)',
        r'dn\s*(\d+)',
    ]
    for pat in patterns:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            # Se valor > 50, provavelmente é DN (mm), converter para polegadas
            if val > 50 and 'dn' in texto.lower():
                return round(val / 25.4, 1)
            return val

    # Tentar por nome
    for nome, val in DIAMETROS_NOMINAIS.items():
        if nome in texto:
            return val
    return None


def extrair_comprimento(texto: str) -> Optional[float]:
    """Extrai comprimento em mm."""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:mm|milímetr|milimetr)',
        r'(\d+(?:\.\d+)?)\s*(?:m\b|metr)',
        r'(\d+(?:\.\d+)?)\s*(?:cm|centímetr|centimetr)',
        r'comprimento\s*(?:de\s*)?(\d+(?:\.\d+)?)',
    ]
    for pat in patterns:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 'cm' in texto.lower() or 'centímetr' in texto.lower():
                return val * 10
            if re.search(r'\d+\s*m\b|\d+\s*metr', texto, re.IGNORECASE) and val < 100:
                return val * 1000
            return val
    # Número solto com "mm" implícito
    m = re.search(r'(\d{3,5})\s*(?:de\s*)?(?:compri|longo|extensão)', texto, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def extrair_eixo(texto: str) -> Optional[Tuple[List[int], str]]:
    """Extrai direção do eixo."""
    for key, val in EIXO_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', texto, re.IGNORECASE):
            return val
    return None


def extrair_coordenadas(texto: str) -> Optional[List[float]]:
    """Extrai coordenadas explícitas (x, y, z)."""
    m = re.search(r'(?:em|no ponto|posição|coordenada)\s*\(?(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*(?:,\s*(\d+(?:\.\d+)?))?\)?', texto, re.IGNORECASE)
    if m:
        x = float(m.group(1))
        y = float(m.group(2))
        z = float(m.group(3)) if m.group(3) else 0.0
        return [x, y, z]
    return None


def extrair_valvula(texto: str) -> Optional[str]:
    """Identifica tipo de válvula."""
    t = texto.lower()
    for keyword, block in VALVE_KEYWORDS.items():
        if keyword in t:
            return block
    # Genérico
    if re.search(r'\bv[aá]lvula\b', t):
        return "VALVE-GATE"
    return None


def extrair_componente(texto: str) -> Optional[str]:
    """Identifica tipo de componente (flanges, tees, etc.)."""
    t = texto.lower()
    for keyword, block in COMPONENT_KEYWORDS.items():
        if keyword in t:
            return block
    if 'flange' in t:
        return "FLANGE-WN"
    return None


def extrair_texto_anotacao(texto: str) -> Optional[str]:
    """Extrai texto para anotação."""
    m = re.search(r'(?:texto|anota[çc][aã]o|tag|etiqueta|label)\s*[:\-]?\s*["\'](.+?)["\']', texto, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'(?:escrever?|digitar?|anotar?|adicionar texto)\s+["\'](.+?)["\']', texto, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


# ─── INTERPRETADOR PRINCIPAL ─────────────────────────────────────────────────

def interpretar_prompt(texto: str) -> InterpretacaoResult:
    """
    Interpreta um comando em linguagem natural e retorna tipo + dados estruturados.
    
    Retorno:
        InterpretacaoResult com tipo (simples/composto/projeto/pergunta) e dados.
    """
    texto_original = texto
    texto_corrigido = corrigir_texto(texto)
    correcao = texto_corrigido if texto_corrigido != texto.lower().strip() else ""

    t = texto_corrigido.lower()

    # ─── Detectar perguntas ──────────────────────────────────────────────
    if _is_pergunta(t):
        return InterpretacaoResult(
            tipo=ComandoTipo.PERGUNTA,
            dados={"mensagem": texto_original},
            confianca=0.9,
            texto_original=texto_original,
            correcao=correcao,
        )

    # ─── Detectar projeto completo ───────────────────────────────────────
    if _is_projeto(t):
        plano = _planejar_projeto(t)
        return InterpretacaoResult(
            tipo=ComandoTipo.PROJETO,
            dados=plano.to_dict(),
            confianca=0.75,
            sugestoes=["Confira o plano antes de executar"],
            texto_original=texto_original,
            correcao=correcao,
        )

    # ─── Detectar comando composto ───────────────────────────────────────
    acoes = _detectar_multiplas_acoes(t)
    if len(acoes) > 1:
        plano = PlanoAcao(
            plano=acoes,
            descricao=f"Comando composto com {len(acoes)} ações",
            estimativa_operacoes=len(acoes),
        )
        return InterpretacaoResult(
            tipo=ComandoTipo.COMPOSTO,
            dados=plano.to_dict(),
            confianca=0.8,
            texto_original=texto_original,
            correcao=correcao,
        )

    # ─── Detectar comando simples ────────────────────────────────────────
    acao = _detectar_acao_simples(t)
    if acao:
        return InterpretacaoResult(
            tipo=ComandoTipo.SIMPLES,
            dados={"plano": [acao], "descricao": acao.get("descricao", ""), "estimativa_operacoes": 1},
            confianca=0.85,
            texto_original=texto_original,
            correcao=correcao,
        )

    # ─── Desconhecido — sugerir ──────────────────────────────────────────
    return InterpretacaoResult(
        tipo=ComandoTipo.DESCONHECIDO,
        dados={"mensagem": texto_original},
        confianca=0.0,
        sugestoes=[
            'Tente: "tubo 6 polegadas 1000mm eixo x"',
            'Tente: "inserir válvula gaveta em 500,0,0"',
            'Tente: "criar linha de 0,0 até 1000,500"',
            'Tente: "criar planta com tubulação principal e derivações"',
        ],
        texto_original=texto_original,
        correcao=correcao,
    )


# ─── Detecção interna ────────────────────────────────────────────────────────

def _is_pergunta(t: str) -> bool:
    """Checa se é uma pergunta ou mensagem conversacional (não-ação)."""
    indicators = [
        r'^(?:o que|como|qual|quando|onde|por que|porque|quem)',
        r'\?$',
        r'^(?:me )?(?:explica|diga|fala|conta)',
        r'^(?:ajuda|help)',
        r'^(?:oi|olá|ola|bom dia|boa tarde|boa noite|hello|hi|hey|e aí|eai)',
        r'^(?:obrigad|valeu|thanks|vlw|beleza)',
        r'^(?:sim|não|nao|ok|certo|entendi)',
        r'^(?:quero|preciso|gostaria|pode)',
        r'(?:funciona|significa|serve|diferença|vantagem|desvantagem)',
        r'(?:recomend|sugest|conselho|opinião|melhor)',
    ]
    return any(re.search(p, t) for p in indicators)


def _is_projeto(t: str) -> bool:
    """Checa se é um pedido de projeto completo."""
    indicators = [
        r'(?:criar?|gerar?|fazer?|desenhar?|montar?)\s+(?:planta|projeto|layout|isométrico|isometrico)',
        r'(?:tubulação|tubulacao)\s+(?:principal|completa)',
        r'(?:planta|layout)\s+(?:com|de)',
        r'(?:projeto\s+completo|planta\s+completa)',
        r'(?:sistema\s+de\s+tubulação|sistema\s+de\s+tubulacao)',
    ]
    return any(re.search(p, t) for p in indicators)


def _detectar_acao_simples(t: str) -> Optional[Dict[str, Any]]:
    """Detecta um único comando."""
    # ── Tubo / Tubulação ──
    if re.search(r'\b(?:tubo|tubula[çc][aã]o|pipe|cano)\b', t):
        return _criar_acao_tubo(t)

    # ── Válvula ──
    valvula = extrair_valvula(t)
    if valvula:
        return _criar_acao_valvula(t, valvula)

    # ── Componente (flange, tee, cotovelo) ──
    comp = extrair_componente(t)
    if comp:
        return _criar_acao_componente(t, comp)

    # ── Linha simples ──
    if re.search(r'\b(?:linha|line|reta|segmento)\b', t):
        return _criar_acao_linha(t)

    # ── Texto/Anotação ──
    if re.search(r'\b(?:texto|anota[çc][aã]o|tag|etiqueta|escrever)\b', t):
        return _criar_acao_texto(t)

    # ── Layers ──
    if re.search(r'\b(?:layer|camada|n-?58)\b', t):
        return {"acao": "criar_layers", "params": {}, "descricao": "Criar sistema de layers N-58"}

    # ── Finalizar / Zoom ──
    if re.search(r'\b(?:finalizar|zoom|regen|visualizar)\b', t):
        return {"acao": "finalizar", "params": {}, "descricao": "Finalizar visualização (ZoomExtents + Regen)"}

    # ── Salvar ──
    if re.search(r'\b(?:salvar|save|gravar)\b', t):
        return {"acao": "salvar", "params": {}, "descricao": "Salvar documento"}

    # ── Commit ──
    if re.search(r'\b(?:commit|enviar buffer|publicar)\b', t):
        return {"acao": "commit", "params": {}, "descricao": "Commit do buffer para .lsp"}

    # ── Conectar ──
    if re.search(r'\b(?:conectar|connect|ligar)\b', t):
        return {"acao": "conectar", "params": {}, "descricao": "Conectar ao AutoCAD"}

    return None


def _detectar_multiplas_acoes(t: str) -> List[Dict[str, Any]]:
    """Detecta múltiplos comandos em uma frase."""
    # Dividir por "e", "depois", "em seguida", "então"
    partes = re.split(r'\s+(?:e\s+(?:depois\s+)?|depois\s+|em seguida\s+|então\s+|,\s*(?:e\s+)?)', t)
    acoes = []
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        acao = _detectar_acao_simples(parte)
        if acao:
            acoes.append(acao)
    return acoes


# ─── Criadores de ação ────────────────────────────────────────────────────────

def _criar_acao_tubo(t: str) -> Dict[str, Any]:
    """Cria ação de tubo a partir do texto."""
    diametro = extrair_diametro(t) or 6.0
    comprimento = extrair_comprimento(t) or 1000.0
    eixo_info = extrair_eixo(t)
    coord_inicio = extrair_coordenadas(t)

    if eixo_info:
        direcao, nome_eixo = eixo_info
    else:
        direcao, nome_eixo = [1, 0, 0], "eixo X (padrão)"

    if coord_inicio:
        ponto_a = coord_inicio
    else:
        ponto_a = [0, 0, 0]

    ponto_b = [
        ponto_a[0] + direcao[0] * comprimento,
        ponto_a[1] + direcao[1] * comprimento,
        ponto_a[2] + direcao[2] * comprimento,
    ]

    return {
        "acao": "criar_tubo",
        "params": {
            "points": [ponto_a, ponto_b],
            "diameter": diametro,
            "layer": "PIPE-PROCESS",
        },
        "descricao": f'Tubo Ø{diametro}" • {comprimento}mm • {nome_eixo}',
    }


def _criar_acao_valvula(t: str, bloco: str) -> Dict[str, Any]:
    """Cria ação de inserção de válvula."""
    coord = extrair_coordenadas(t) or [500, 0, 0]
    rotacao = 0.0
    m_rot = re.search(r'(\d+)\s*(?:°|graus?|degree)', t)
    if m_rot:
        rotacao = float(m_rot.group(1))
    
    return {
        "acao": "inserir_componente",
        "params": {
            "block_name": bloco,
            "coordinate": coord,
            "rotation": rotacao,
            "scale": 1.0,
            "layer": "VALVE",
        },
        "descricao": f"Válvula {bloco} em ({coord[0]},{coord[1]},{coord[2]})",
    }


def _criar_acao_componente(t: str, bloco: str) -> Dict[str, Any]:
    """Cria ação de inserção de componente genérico."""
    coord = extrair_coordenadas(t) or [0, 0, 0]
    return {
        "acao": "inserir_componente",
        "params": {
            "block_name": bloco,
            "coordinate": coord,
            "rotation": 0.0,
            "scale": 1.0,
            "layer": "VALVE",
        },
        "descricao": f"Componente {bloco} em ({coord[0]},{coord[1]},{coord[2]})",
    }


def _criar_acao_linha(t: str) -> Dict[str, Any]:
    """Cria ação de linha simples."""
    # Tentar extrair "de X1,Y1 até X2,Y2"
    m = re.search(r'(?:de|desde)\s*\(?(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\)?\s*(?:até|ate|a|para)\s*\(?(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\)?', t)
    if m:
        start = [float(m.group(1)), float(m.group(2)), 0]
        end = [float(m.group(3)), float(m.group(4)), 0]
    else:
        comprimento = extrair_comprimento(t) or 1000.0
        eixo_info = extrair_eixo(t)
        direcao = eixo_info[0] if eixo_info else [1, 0, 0]
        start = [0, 0, 0]
        end = [direcao[0] * comprimento, direcao[1] * comprimento, 0]

    return {
        "acao": "criar_linha",
        "params": {
            "start": start,
            "end": end,
            "layer": "PIPE-UTILITY",
        },
        "descricao": f"Linha de ({start[0]},{start[1]}) até ({end[0]},{end[1]})",
    }


def _criar_acao_texto(t: str) -> Dict[str, Any]:
    """Cria ação de texto/anotação."""
    conteudo = extrair_texto_anotacao(t) or "TAG-001"
    coord = extrair_coordenadas(t) or [0, 0, 0]
    return {
        "acao": "adicionar_texto",
        "params": {
            "text": conteudo,
            "position": coord,
            "height": 2.5,
            "layer": "ANNOTATION",
        },
        "descricao": f'Texto "{conteudo}" em ({coord[0]},{coord[1]},{coord[2]})',
    }


# ─── PLANNER (Projeto Completo) ──────────────────────────────────────────────

def _planejar_projeto(t: str) -> PlanoAcao:
    """Gera plano estruturado para projeto completo."""
    acoes: List[Dict[str, Any]] = []

    # 1. Sempre iniciar com layers
    acoes.append({"acao": "criar_layers", "params": {}, "descricao": "Inicializar layers N-58 Petrobras"})

    # 2. Tubulação principal
    comprimento_principal = extrair_comprimento(t) or 5000.0
    diametro_principal = extrair_diametro(t) or 6.0

    acoes.append({
        "acao": "criar_tubo",
        "params": {
            "points": [[0, 0, 0], [comprimento_principal, 0, 0]],
            "diameter": diametro_principal,
            "layer": "PIPE-PROCESS",
        },
        "descricao": f'Tubulação principal Ø{diametro_principal}" • {comprimento_principal}mm',
    })

    # 3. Se menciona derivações
    if re.search(r'(?:derivaç|ramifica|branch|lateral|secundári)', t, re.IGNORECASE):
        # Derivação no meio
        meio = comprimento_principal / 2
        acoes.append({
            "acao": "inserir_componente",
            "params": {
                "block_name": "TEE-EQUAL",
                "coordinate": [meio, 0, 0],
                "rotation": 0, "scale": 1, "layer": "VALVE",
            },
            "descricao": f"Tê de derivação em x={meio}",
        })
        acoes.append({
            "acao": "criar_tubo",
            "params": {
                "points": [[meio, 0, 0], [meio, 2000, 0]],
                "diameter": max(2, diametro_principal - 2),
                "layer": "PIPE-UTILITY",
            },
            "descricao": "Derivação vertical (2000mm)",
        })

    # 4. Se menciona válvulas
    if re.search(r'(?:v[aá]lvula|valve|bloqueio|isolamento)', t, re.IGNORECASE):
        valve_type = extrair_valvula(t) or "VALVE-GATE"
        acoes.append({
            "acao": "inserir_componente",
            "params": {
                "block_name": valve_type,
                "coordinate": [comprimento_principal * 0.25, 0, 0],
                "rotation": 0, "scale": 1, "layer": "VALVE",
            },
            "descricao": f"Válvula {valve_type} a 25% do comprimento",
        })

    # 5. Se menciona flanges / conexões
    if re.search(r'(?:flange|conex[aã]o|junta|acoplamento)', t, re.IGNORECASE):
        acoes.append({
            "acao": "inserir_componente",
            "params": {
                "block_name": "FLANGE-WN",
                "coordinate": [0, 0, 0],
                "rotation": 0, "scale": 1, "layer": "FLANGE",
            },
            "descricao": "Flange WN na origem",
        })
        acoes.append({
            "acao": "inserir_componente",
            "params": {
                "block_name": "FLANGE-WN",
                "coordinate": [comprimento_principal, 0, 0],
                "rotation": 180, "scale": 1, "layer": "FLANGE",
            },
            "descricao": "Flange WN na extremidade",
        })

    # 6. Anotações automáticas
    acoes.append({
        "acao": "adicionar_texto",
        "params": {
            "text": f'LINHA PROCESSO Ø{diametro_principal}"',
            "position": [comprimento_principal / 2, -50, 0],
            "height": 5.0,
            "layer": "ANNOTATION",
        },
        "descricao": "Anotação da linha de processo",
    })

    # 7. Finalizar
    acoes.append({"acao": "finalizar", "params": {}, "descricao": "ZoomExtents + Regen"})
    acoes.append({"acao": "commit", "params": {}, "descricao": "Commit para AutoCAD"})

    return PlanoAcao(
        plano=acoes,
        descricao=f"Projeto completo: {len(acoes)} operações planejadas",
        estimativa_operacoes=len(acoes),
    )


# ─── EXECUTOR ─────────────────────────────────────────────────────────────────

# Mapeamento de ação → endpoint REST existente
ACAO_ENDPOINT_MAP = {
    "criar_tubo": {"method": "POST", "path": "/api/autocad/draw-pipe"},
    "criar_linha": {"method": "POST", "path": "/api/autocad/draw-line"},
    "inserir_componente": {"method": "POST", "path": "/api/autocad/insert-component"},
    "adicionar_texto": {"method": "POST", "path": "/api/autocad/add-text"},
    "criar_layers": {"method": "POST", "path": "/api/autocad/create-layers"},
    "finalizar": {"method": "POST", "path": "/api/autocad/finalize"},
    "salvar": {"method": "POST", "path": "/api/autocad/save"},
    "commit": {"method": "POST", "path": "/api/autocad/commit"},
    "conectar": {"method": "POST", "path": "/api/autocad/connect"},
}


async def executar_plano(plano: List[Dict[str, Any]], driver=None) -> Dict[str, Any]:
    """
    Executa um plano de ações chamando as funções existentes do AutoCAD Driver.
    
    Reutiliza 100% do backend/autocad_driver.py existente.
    """
    if driver is None:
        try:
            from backend.autocad_driver import acad_driver
            driver = acad_driver
        except ImportError:
            pass

    # Fallback to mock driver when real AutoCAD is unavailable
    if driver is None:
        try:
            from backend.mock_autocad_driver import MockAutoCADDriver
            driver = MockAutoCADDriver()
            logger.info("ChatCAD executando com driver mock (AutoCAD não disponível)")
        except ImportError:
            return {
                "success": False,
                "executadas": 0,
                "total": len(plano),
                "resultados": [],
                "erro": "AutoCAD Driver não disponível",
            }

    resultados = []
    executadas = 0
    falhas = 0

    for i, acao in enumerate(plano):
        nome_acao = acao.get("acao", "")
        params = acao.get("params", {})
        descricao = acao.get("descricao", nome_acao)

        try:
            result = _executar_acao(driver, nome_acao, params)
            resultados.append({
                "index": i,
                "acao": nome_acao,
                "descricao": descricao,
                "success": result.success if hasattr(result, 'success') else True,
                "message": result.message if hasattr(result, 'message') else "OK",
            })
            executadas += 1
        except Exception as e:
            logger.error(f"Erro ao executar ação {nome_acao}: {e}")
            resultados.append({
                "index": i,
                "acao": nome_acao,
                "descricao": descricao,
                "success": False,
                "message": str(e),
            })
            falhas += 1

    return {
        "success": falhas == 0,
        "executadas": executadas,
        "falhas": falhas,
        "total": len(plano),
        "resultados": resultados,
    }


def _executar_acao(driver, nome: str, params: Dict[str, Any]):
    """Chama a função correspondente no driver existente."""
    if nome == "criar_tubo":
        return driver.draw_pipe(**params)
    elif nome == "criar_linha":
        return driver.draw_line(**params)
    elif nome == "inserir_componente":
        return driver.insert_component(**params)
    elif nome == "adicionar_texto":
        return driver.add_text(**params)
    elif nome == "criar_layers":
        return driver.create_layer_system()
    elif nome == "finalizar":
        return driver.finalize_view()
    elif nome == "salvar":
        return driver.save_document()
    elif nome == "commit":
        return driver.commit()
    elif nome == "conectar":
        return driver.connect()
    else:
        raise ValueError(f"Ação desconhecida: {nome}")
