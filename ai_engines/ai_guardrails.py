"""
═══════════════════════════════════════════════════════════════════════════════
  AI GUARDRAILS - Sistema de Contexto e Limites para IAs
═══════════════════════════════════════════════════════════════════════════════

Este módulo implementa guardrails para garantir que as IAs:
  - Respondam apenas sobre tópicos do sistema (CAD, engenharia, cálculos)
  - Redirecionem gentilmente quando detectar perguntas irrelevantes
  - Mantenham foco no contexto de automação industrial

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT - Contexto obrigatório para todas as IAs
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Você é o Assistente Técnico do ForgeCad, um sistema especializado em automação industrial para engenharia CAD.

ESCOPO DE ATUAÇÃO (APENAS responda sobre estes tópicos):
- Desenho técnico e CAD (AutoCAD, comandos, layers, blocos)
- Normas técnicas industriais (ASME, API, ISO, ABNT, NR)
- Materiais de engenharia (tubulação, aços, polímeros)
- Cálculos de engenharia (espessura, pressão, vazão, Reynolds)
- Processos industriais (soldagem, caldeiraria, inspeção)
- Automação de corte CNC (plasma, laser, oxicorte)
- Nesting e otimização de chapas
- G-code e pós-processamento
- Tubulação industrial e P&ID
- Custos e orçamentos de projetos industriais
- Funcionamento do sistema ForgeCad

REGRAS OBRIGATÓRIAS:
1. NUNCA responda sobre política, religião, ideologia ou temas polêmicos
2. NUNCA faça piadas, receitas culinárias, poemas ou entretenimento
3. NUNCA dê opiniões pessoais ou conselhos de vida
4. NUNCA ajude com tarefas não relacionadas à engenharia/indústria
5. Se a pergunta estiver fora do escopo, redirecione educadamente

FORMATO DE RESPOSTA:
- Seja direto, técnico e objetivo
- Use unidades do SI (metros, kg, Pa)
- Referencie normas quando aplicável
- Ofereça sugestões relevantes ao final

SOBRE O SISTEMA ForgeCad:
- Software de automação CAD industrial
- Integração com AutoCAD via Bridge ou COM
- Geração de G-code para corte CNC
- Otimização de nesting para chapas
- Análise de desenhos com IA
- Estimativa de custos automatizada
"""


# ═══════════════════════════════════════════════════════════════════════════════
# OFF-TOPIC DETECTION - Padrões de perguntas fora do escopo
# ═══════════════════════════════════════════════════════════════════════════════

OFF_TOPIC_PATTERNS = {
    # Política e ideologia
    "politica": [
        r"\b(politik|governo|presidente|deputad|senad|eleição|vot[ao]|partido|esquerd|direit|comunis|capitalis|social-democra)\b",
        r"\b(bolsonaro|lula|trump|biden|doria|ciro|marina)\b",
        r"\b(pt|psdb|mdb|psl|podemos|psol)\b",
    ],
    
    # Religião
    "religiao": [
        r"\b(deus|jesus|alá|buda|religião|igreja|evangélico|católico|espírita|umbanda|candomblé)\b",
        r"\b(bíblia|corão|torá|oração|pecado|céu|inferno)\b",
    ],
    
    # Entretenimento
    "entretenimento": [
        r"\b(filme|série|netflix|novela|big brother|bbb|futebol|times? de|flamengo|corinthians)\b",
        r"\b(música|cantor|banda|show|letra de|playlist)\b",
        r"\b(jogo|game|playstation|xbox|videogame)\b",
    ],
    
    # Receitas e culinária
    "culinaria": [
        r"\b(receita|ingrediente|cozinhar|assar|fritar|tempero|massa|bolo|pizza|hamburguer)\b",
        r"\b(café da manhã|almoço|jantar|lanche|comida|prato)\b",
    ],
    
    # Relacionamentos pessoais
    "pessoal": [
        r"\b(namorad|casamento|divorc|relacionamento|amor|paixão|crush|ficante)\b",
        r"\b(ansiedade|depressão|terapia|psicólog|psiquiatra)\b",
    ],
    
    # Piadas e humor
    "humor": [
        r"\b(piada|anedota|meme|engraçad|humor|comédia|stand.?up)\b",
        r"\b(conta uma|me faz rir|animador)\b",
    ],
    
    # Poesia e literatura não-técnica
    "literatura": [
        r"\b(poema|poesi|verso|rima|soneto|haiku|romance)\b",
        r"\b(escreva um|componha|crie uma história)\b",
    ],
    
    # Conselhos de vida
    "conselhos": [
        r"\b(sentido da vida|dica de vida|conselho pessoal|motivação|autoajuda)\b",
        r"\b(como ser feliz|como ter sucesso|dica para)\b",
    ],
}


# Padrões de tópicos PERMITIDOS (whitelist)
ON_TOPIC_PATTERNS = [
    # CAD e desenho técnico
    r"\b(cad|autocad|dwg|dxf|desenho técnico|layer|block|plot|layout|scale|coordenada)\b",
    r"\b(linha|círculo|arco|polilinha|spline|hatch|dimension|cota|texto)\b",
    
    # Engenharia e normas
    r"\b(norma|asme|api|iso|abnt|nr|astm|aws|din)\b",
    r"\b(engenharia|projeto|cálculo|dimensionament|especificaç)\b",
    
    # Materiais e processos
    r"\b(aço|inox|carbono|alumínio|cobre|pvc|polímero|material|liga)\b",
    r"\b(soldagem|corte|dobra|calandragem|usinagem|torneament|fresament)\b",
    
    # Tubulação
    r"\b(tubo|tubulação|pipe|fitting|flange|válvula|bomba|compressor)\b",
    r"\b(pid|p&id|isométrico|spool|suporte)\b",
    
    # CNC e fabricação
    r"\b(cnc|gcode|g-code|plasma|laser|oxicorte|máquina|nesting)\b",
    r"\b(chapa|placa|corte|otimização|arranjo|encaixe)\b",
    
    # Cálculos técnicos
    r"\b(espessura|pressão|temperatura|vazão|reynolds|velocidade|diâmetro)\b",
    r"\b(sch|schedule|nominal|mm|polegada|bar|psi|mpa)\b",
    
    # Sistema ForgeCad
    r"\b(forgecad|forge.?cad|sistema|software|licença|hwid|login|plano|funcionalidade)\b",
    
    # Custos industriais
    r"\b(custo|orçamento|mto|lista material|estimativa|preço|valor)\b",
]


# ═══════════════════════════════════════════════════════════════════════════════
# REDIRECIONAMENTO - Mensagens para perguntas fora do escopo
# ═══════════════════════════════════════════════════════════════════════════════

REDIRECT_MESSAGES = {
    "politica": """Desculpe, não posso ajudar com tópicos políticos ou ideológicos.

🔧 **Posso ajudar você com:**
- Normas técnicas (ASME, API, ISO)
- Cálculos de engenharia
- Comandos AutoCAD
- Otimização de corte CNC
- Custos de projetos industriais

Como posso ajudar no seu projeto de engenharia?""",

    "religiao": """Desculpe, assuntos religiosos estão fora do meu escopo de atuação.

🔧 **Minha especialidade é engenharia industrial:**
- Análise de desenhos CAD
- Materiais e especificações técnicas
- Automação de processos
- Geração de G-code

Tem alguma dúvida técnica sobre seu projeto?""",

    "entretenimento": """Sou um assistente técnico especializado em engenharia!

🔧 **Posso ajudar melhor com:**
- Desenho técnico e AutoCAD
- Normas e especificações
- Cálculos industriais
- Otimização de nesting

Qual é o desafio técnico que você está enfrentando?""",

    "culinaria": """Como assistente técnico de CAD, infelizmente não tenho receitas!

🔧 **Mas posso te ajudar com:**
- Tubulação industrial (não é macarronada! 😄)
- Cálculos de engenharia
- Comandos CAD
- Processos de fabricação

Tem algum projeto industrial para discutirmos?""",

    "pessoal": """Entendo sua situação, mas sou especializado em engenharia técnica.

🔧 **Meu foco é ajudar com:**
- Projetos CAD
- Automação industrial
- Normas técnicas
- Cálculos e dimensionamentos

Se precisar de apoio pessoal, recomendo buscar um profissional especializado. Posso ajudar com algum projeto técnico?""",

    "humor": """Minha especialidade é engenharia, não comédia!

🔧 **Mas posso tornar seu trabalho mais fácil com:**
- Automação de tarefas repetitivas
- Cálculos rápidos e precisos
- Otimização de cortes
- Geração de documentação

Vamos resolver algum desafio técnico?""",

    "literatura": """Sou especializado em documentação técnica, não literatura criativa!

🔧 **Posso gerar automaticamente:**
- Relatórios técnicos
- Listas de materiais (MTO)
- Especificações de soldagem
- Documentação de projeto

Precisa de algum documento técnico?""",

    "conselhos": """Agradeço a confiança! Mas minha especialidade é engenharia industrial.

🔧 **Posso dar dicas técnicas sobre:**
- Melhores práticas em CAD
- Escolha de materiais
- Otimização de processos
- Redução de custos industriais

Como posso ajudar no seu projeto?""",

    "default": """Essa pergunta parece estar fora do meu escopo de atuação.

🔧 **Sou especializado em:**
- Desenho técnico e CAD
- Normas industriais (ASME, API, ISO)
- Cálculos de engenharia
- Automação de corte CNC
- Otimização de materiais

Posso ajudar com algum desses tópicos?"""
}


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def is_on_topic(message: str) -> Tuple[bool, float]:
    """
    Verifica se a mensagem é sobre um tópico relevante.
    
    Returns:
        Tuple[bool, float]: (é_relevante, confidence)
    """
    message_lower = message.lower()
    
    # Verificar whitelist primeiro
    for pattern in ON_TOPIC_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True, 0.95
    
    # Verificar se é pergunta muito curta (saudações OK)
    if len(message.split()) <= 3:
        if re.search(r"\b(oi|olá|bom dia|boa tarde|boa noite|obrigad|valeu|até)\b", message_lower):
            return True, 0.9  # Saudações são OK
    
    return True, 0.6  # Default: deixar passar com confiança baixa


def detect_off_topic(message: str) -> Tuple[bool, str, float]:
    """
    Detecta se a mensagem é sobre um tópico proibido.
    
    Returns:
        Tuple[bool, str, float]: (é_off_topic, categoria, confidence)
    """
    message_lower = message.lower()
    
    # Primeiro verificar se é explicitamente on-topic
    is_valid, confidence = is_on_topic(message)
    if is_valid and confidence > 0.8:
        return False, "", 0.0
    
    # Verificar padrões off-topic
    for category, patterns in OFF_TOPIC_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                # Verificar se não é falso positivo
                # Ex: "jogos de tubos" não é sobre games
                if category == "entretenimento":
                    if re.search(r"\b(tubo|pipe|máquina|cnc|industrial)\b", message_lower):
                        continue
                
                logger.info(f"[Guardrails] Off-topic detectado: {category}")
                return True, category, 0.85
    
    return False, "", 0.0


def get_redirect_message(category: str) -> str:
    """Retorna mensagem de redirecionamento para a categoria."""
    return REDIRECT_MESSAGES.get(category, REDIRECT_MESSAGES["default"])


def apply_guardrails(message: str) -> Dict[str, Any]:
    """
    Aplica guardrails completos à mensagem.
    
    Returns:
        Dict com:
        - allowed: bool - se a mensagem deve ser processada
        - redirect: str - mensagem de redirecionamento (se bloqueada)
        - category: str - categoria off-topic (se aplicável)
        - confidence: float - confiança na detecção
        - system_prompt: str - prompt de sistema para usar
    """
    # Detectar off-topic
    is_off, category, confidence = detect_off_topic(message)
    
    if is_off and confidence > 0.7:
        return {
            "allowed": False,
            "redirect": get_redirect_message(category),
            "category": category,
            "confidence": confidence,
            "system_prompt": SYSTEM_PROMPT,
        }
    
    return {
        "allowed": True,
        "redirect": None,
        "category": None,
        "confidence": confidence,
        "system_prompt": SYSTEM_PROMPT,
    }


def inject_system_prompt(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Injeta o system prompt nas mensagens para o LLM.
    
    Garante que o contexto do sistema está sempre presente.
    """
    # Verificar se já tem system prompt
    has_system = any(m.get("role") == "system" for m in messages)
    
    if has_system:
        # Atualizar o system existente
        for msg in messages:
            if msg.get("role") == "system":
                # Adicionar nosso contexto ao início
                original = msg.get("content", "")
                msg["content"] = f"{SYSTEM_PROMPT}\n\n{original}"
                break
    else:
        # Inserir no início
        messages.insert(0, {
            "role": "system",
            "content": SYSTEM_PROMPT
        })
    
    return messages


def validate_response(response: str) -> Tuple[bool, str]:
    """
    Valida se a resposta da IA está dentro do escopo.
    
    Útil para second-pass validation após resposta do LLM.
    """
    # Verificar se inclui conteúdo proibido
    off_topic_in_response = [
        r"não posso opinar sobre política",
        r"minha opinião pessoal",
        r"vou te contar uma piada",
        r"aqui está uma receita",
    ]
    
    response_lower = response.lower()
    for pattern in off_topic_in_response:
        if re.search(pattern, response_lower):
            logger.warning(f"[Guardrails] Resposta da IA contém conteúdo off-topic")
            return False, "A resposta foi filtrada por questões de escopo."
    
    return True, response


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "SYSTEM_PROMPT",
    "apply_guardrails",
    "inject_system_prompt",
    "detect_off_topic",
    "is_on_topic",
    "get_redirect_message",
    "validate_response",
]
