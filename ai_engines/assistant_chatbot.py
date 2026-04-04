"""
═══════════════════════════════════════════════════════════════════════════════
  ASSISTANT CHATBOT AI - Assistente Técnico Inteligente
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Responder perguntas técnicas sobre CAD
  - Auxiliar na resolução de problemas
  - Fornecer orientações de projeto
  - Explicar normas e especificações
  - Sugerir melhores práticas

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


class AssistantChatbotAI(BaseAI):
    """
    IA assistente para interação com usuários.
    
    Capacidades:
    - Responder perguntas técnicas
    - Auxiliar em cálculos
    - Explicar conceitos
    - Sugerir soluções
    - Guiar usuário no sistema
    """
    
    # Base de conhecimento
    KNOWLEDGE_BASE = {
        "normas": {
            "ASME B31.3": "Norma para tubulação de processo industrial. Define requisitos de projeto, materiais, fabricação, montagem, teste e inspeção.",
            "ASME B31.1": "Norma para tubulação de energia (vapor, água quente). Aplicável a usinas e caldeiras.",
            "API 650": "Norma para tanques de armazenamento atmosféricos soldados.",
            "ASME VIII": "Norma para vasos de pressão. Define requisitos de projeto e construção.",
            "ISO 10628": "Norma para diagramas de processo e instrumentação (P&ID).",
        },
        "materiais": {
            "carbon_steel": {
                "name": "Aço Carbono",
                "grades": ["A106 Gr.B", "A53 Gr.B", "A333 Gr.6"],
                "temp_range": "-29°C a 427°C",
                "applications": "Tubulação de processo geral, vapor, água, óleo",
            },
            "stainless_304": {
                "name": "Aço Inox 304",
                "temp_range": "-196°C a 816°C",
                "applications": "Ambientes corrosivos, alimentos, químicos",
            },
            "stainless_316": {
                "name": "Aço Inox 316",
                "temp_range": "-196°C a 816°C",
                "applications": "Ambientes marinhos, químicos agressivos, farmacêutica",
            },
        },
        "formulas": {
            "wall_thickness": "t = (P × D) / (2 × S × E + 2 × Y × P) + C",
            "pressure_drop": "ΔP = f × (L/D) × (ρ × v²) / 2",
            "flow_velocity": "v = Q / A = 4 × Q / (π × D²)",
            "reynolds": "Re = (ρ × v × D) / μ",
        },
        "commands_cad": {
            "layer": "Controla a camada de trabalho atual",
            "line": "Desenha uma linha reta entre dois pontos",
            "circle": "Desenha um círculo dado centro e raio",
            "block": "Cria um bloco a partir de objetos selecionados",
            "insert": "Insere um bloco existente no desenho",
            "trim": "Corta objetos nos limites de outros objetos",
            "extend": "Estende objetos até encontrar outros",
            "offset": "Cria cópia paralela de objetos",
            "mirror": "Cria cópia espelhada de objetos",
            "array": "Cria múltiplas cópias em padrão",
        },
    }
    
    # Patterns de intenção
    INTENT_PATTERNS = {
        "greeting": [r"oi", r"olá", r"bom dia", r"boa tarde", r"boa noite", r"hello", r"hi"],
        "help": [r"ajuda", r"help", r"como", r"onde", r"o que", r"explica"],
        "calculate": [r"calcul", r"quanto", r"qual o valor", r"compute"],
        "norm": [r"norma", r"asme", r"api", r"iso", r"abnt", r"padrão"],
        "material": [r"material", r"aço", r"inox", r"carbono", r"pvc", r"tubo"],
        "command": [r"comando", r"command", r"autocad", r"cad", r"desenho"],
        "error": [r"erro", r"error", r"problema", r"não funciona", r"bug"],
        "status": [r"status", r"estado", r"situação", r"andamento"],
    }
    
    def __init__(self):
        super().__init__(name="AssistantChatbot", version="1.0.0")
        self.confidence_threshold = 0.6
        self._conversation_history: List[Dict] = []
    
    def get_capabilities(self) -> List[str]:
        return [
            "question_answering",
            "technical_guidance",
            "calculation_assistance",
            "norm_explanation",
            "troubleshooting",
            "system_navigation",
            "best_practices",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Processa mensagem do usuário.
        
        Input esperado:
        {
            "message": str,           # Mensagem do usuário
            "context": {...},         # Contexto opcional
            "conversation_id": str,   # ID da conversa
        }
        """
        message = input_data.get("message", "").strip()
        context = input_data.get("context", {})
        
        if not message:
            return AIResult(
                success=True,
                ai_name=self.name,
                operation="chat",
                data={
                    "response": "Por favor, digite sua pergunta ou dúvida.",
                    "suggestions": self._get_suggestions(),
                },
                confidence=1.0,
            )
        
        try:
            # Detectar intenção
            intent, intent_confidence = self._detect_intent(message)
            
            # Gerar resposta baseada na intenção
            response, response_data = self._generate_response(message, intent, context)
            
            # Adicionar sugestões relevantes
            suggestions = self._get_contextual_suggestions(intent, message)
            
            # Adicionar à história
            self._conversation_history.append({
                "role": "user",
                "message": message,
                "intent": intent,
            })
            self._conversation_history.append({
                "role": "assistant",
                "message": response,
            })
            
            # Limitar história
            if len(self._conversation_history) > 20:
                self._conversation_history = self._conversation_history[-20:]
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation="chat",
                data={
                    "response": response,
                    "intent": intent,
                    "suggestions": suggestions,
                    "additional_data": response_data,
                },
                confidence=intent_confidence,
                metadata={
                    "message_length": len(message),
                    "intent_detected": intent,
                }
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro no processamento")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation="chat",
                data={
                    "response": "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
                },
                errors=[str(e)],
            )
    
    def _detect_intent(self, message: str) -> Tuple[str, float]:
        """Detecta a intenção do usuário."""
        message_lower = message.lower()
        
        best_intent = "help"
        best_score = 0.0
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    # Score baseado na posição do match
                    match = re.search(pattern, message_lower)
                    if match:
                        # Matches no início têm mais peso
                        position_score = 1.0 - (match.start() / len(message_lower))
                        score = 0.7 + (0.3 * position_score)
                        
                        if score > best_score:
                            best_score = score
                            best_intent = intent
        
        return best_intent, max(0.5, best_score)
    
    def _generate_response(
        self,
        message: str,
        intent: str,
        context: Dict
    ) -> Tuple[str, Dict]:
        """Gera resposta baseada na intenção."""
        response_data = {}
        
        if intent == "greeting":
            response = self._handle_greeting()
            
        elif intent == "norm":
            response, response_data = self._handle_norm_query(message)
            
        elif intent == "material":
            response, response_data = self._handle_material_query(message)
            
        elif intent == "command":
            response, response_data = self._handle_command_query(message)
            
        elif intent == "calculate":
            response, response_data = self._handle_calculation(message)
            
        elif intent == "error":
            response = self._handle_error_troubleshooting(message, context)
            
        elif intent == "status":
            response = self._handle_status_query(context)
            
        else:
            response = self._handle_general_help(message)
        
        return response, response_data
    
    def _handle_greeting(self) -> str:
        """Responde a saudações."""
        return """Olá! 👋 Sou o assistente técnico do ForgeCad.

Posso ajudar você com:
- **Normas técnicas** (ASME, API, ISO)
- **Materiais** (especificações, compatibilidade)
- **Comandos CAD** (AutoCAD, desenho técnico)
- **Cálculos** (espessura, pressão, vazão)
- **Problemas técnicos** (troubleshooting)

Como posso ajudar você hoje?"""
    
    def _handle_norm_query(self, message: str) -> Tuple[str, Dict]:
        """Responde perguntas sobre normas."""
        message_lower = message.lower()
        
        found_norms = []
        for norm_id, description in self.KNOWLEDGE_BASE["normas"].items():
            if norm_id.lower() in message_lower or any(
                part.lower() in message_lower 
                for part in norm_id.replace(".", " ").split()
            ):
                found_norms.append((norm_id, description))
        
        if found_norms:
            response = "📚 **Informações sobre normas:**\n\n"
            for norm_id, description in found_norms:
                response += f"**{norm_id}:**\n{description}\n\n"
            return response, {"norms_found": [n[0] for n in found_norms]}
        
        # Listar normas disponíveis
        response = """📚 **Normas disponíveis no sistema:**

"""
        for norm_id, description in self.KNOWLEDGE_BASE["normas"].items():
            response += f"- **{norm_id}**: {description[:60]}...\n"
        
        response += "\nPara mais detalhes, pergunte sobre uma norma específica."
        return response, {}
    
    def _handle_material_query(self, message: str) -> Tuple[str, Dict]:
        """Responde perguntas sobre materiais."""
        message_lower = message.lower()
        
        found_materials = []
        for mat_id, mat_info in self.KNOWLEDGE_BASE["materiais"].items():
            if mat_id.replace("_", " ") in message_lower or mat_info["name"].lower() in message_lower:
                found_materials.append((mat_id, mat_info))
        
        if found_materials:
            response = "🔧 **Informações sobre materiais:**\n\n"
            for mat_id, mat_info in found_materials:
                response += f"**{mat_info['name']}**\n"
                response += f"- Faixa de temperatura: {mat_info.get('temp_range', 'N/A')}\n"
                response += f"- Aplicações: {mat_info.get('applications', 'N/A')}\n"
                if 'grades' in mat_info:
                    response += f"- Grades comuns: {', '.join(mat_info['grades'])}\n"
                response += "\n"
            return response, {"materials_found": [m[0] for m in found_materials]}
        
        # Informações gerais de materiais
        response = """🔧 **Materiais de tubulação comuns:**

**Aço Carbono (Carbon Steel)**
- Mais comum em processos industriais
- Econômico, boa resistência mecânica
- Limitado em ambientes corrosivos

**Aço Inox 304/316**
- Excelente resistência à corrosão
- 316 superior para ambientes marinhos/químicos
- Custo mais elevado

**PVC/CPVC**
- Baixo custo, leve
- Resistente a químicos
- Limitado em temperatura e pressão

Para detalhes específicos, pergunte sobre um material."""
        return response, {}
    
    def _handle_command_query(self, message: str) -> Tuple[str, Dict]:
        """Responde perguntas sobre comandos CAD."""
        message_lower = message.lower()
        
        found_commands = []
        for cmd, description in self.KNOWLEDGE_BASE["commands_cad"].items():
            if cmd in message_lower:
                found_commands.append((cmd, description))
        
        if found_commands:
            response = "🖥️ **Comandos CAD:**\n\n"
            for cmd, description in found_commands:
                response += f"**{cmd.upper()}**: {description}\n\n"
            return response, {"commands_found": [c[0] for c in found_commands]}
        
        # Listar comandos comuns
        response = """🖥️ **Comandos CAD mais usados:**

**Desenho:**
- `LINE` - Desenha linhas retas
- `CIRCLE` - Desenha círculos
- `ARC` - Desenha arcos

**Modificação:**
- `TRIM` - Corta objetos
- `EXTEND` - Estende objetos
- `OFFSET` - Cria cópias paralelas
- `MIRROR` - Espelha objetos

**Organização:**
- `LAYER` - Gerencia camadas
- `BLOCK` - Cria blocos
- `INSERT` - Insere blocos

Pergunte sobre um comando específico para mais detalhes."""
        return response, {}
    
    def _handle_calculation(self, message: str) -> Tuple[str, Dict]:
        """Auxilia com cálculos técnicos."""
        message_lower = message.lower()
        
        if "espessura" in message_lower or "parede" in message_lower:
            response = """📐 **Cálculo de Espessura de Parede (ASME B31.3):**

**Fórmula:**
```
t = (P × D) / (2 × S × E + 2 × Y × P) + C
```

**Onde:**
- t = espessura de parede (mm)
- P = pressão de projeto (MPa)
- D = diâmetro externo (mm)
- S = tensão admissível do material (MPa)
- E = fator de eficiência de junta (0.8-1.0)
- Y = coeficiente de temperatura
- C = tolerância de corrosão (mm)

**Exemplo para tubo DN100 SCH40:**
- D = 114.3mm, P = 1.0MPa, S = 137.9MPa
- t = (1.0 × 114.3) / (2 × 137.9 × 1.0) = 0.41mm
- Com tolerância: usar mínimo 3.05mm (SCH40)"""
            return response, {"calculation_type": "wall_thickness"}
        
        if "velocidade" in message_lower or "vazão" in message_lower:
            response = """📐 **Cálculo de Velocidade de Fluxo:**

**Fórmula:**
```
v = Q / A = 4 × Q / (π × D²)
```

**Onde:**
- v = velocidade (m/s)
- Q = vazão volumétrica (m³/s)
- D = diâmetro interno (m)

**Velocidades recomendadas:**
- Líquidos: 1-3 m/s
- Gases: 15-30 m/s
- Vapor: 25-40 m/s

**Exemplo:**
- Q = 0.1 m³/s, D = 150mm (0.15m)
- v = 4 × 0.1 / (3.14159 × 0.15²) = 5.66 m/s"""
            return response, {"calculation_type": "flow_velocity"}
        
        # Fórmulas disponíveis
        response = """📐 **Fórmulas disponíveis:**

- **Espessura de parede** - Pergunte "como calcular espessura"
- **Velocidade de fluxo** - Pergunte "como calcular velocidade"
- **Perda de carga** - Em desenvolvimento
- **Reynolds** - Em desenvolvimento

Para qual cálculo você precisa de ajuda?"""
        return response, {}
    
    def _handle_error_troubleshooting(self, message: str, context: Dict) -> str:
        """Auxilia na resolução de problemas."""
        message_lower = message.lower()
        
        if "conexão" in message_lower or "conectar" in message_lower:
            return """🔧 **Problemas de Conexão:**

**Verificações:**
1. ✅ Sincronizador está rodando? (tray icon verde)
2. ✅ AutoCAD está aberto?
3. ✅ Firewall liberado? (portas 8000, 3000)

**Solução rápida:**
1. Reinicie o sincronizador
2. Verifique se a URL está correta
3. Execute como administrador

Se persistir, verifique os logs em:
`%APPDATA%\\ForgeCad\\logs\\`"""
        
        if "lento" in message_lower or "travando" in message_lower:
            return """🔧 **Problemas de Performance:**

**Possíveis causas:**
1. Desenho muito grande (muitas entidades)
2. Muitos blocos não-purgados
3. Memória insuficiente

**Soluções:**
1. Execute `PURGE` no AutoCAD
2. Use `AUDIT` para verificar erros
3. Reduza resolução de hatches
4. Congele layers não utilizados"""
        
        return """🔧 **Suporte Técnico:**

Descreva seu problema com mais detalhes:
- Qual operação estava realizando?
- Qual mensagem de erro apareceu?
- O problema é recorrente?

**Recursos úteis:**
- Logs do sistema: Menu > Logs
- Status do sistema: Menu > Status
- Documentação: /docs"""
    
    def _handle_status_query(self, context: Dict) -> str:
        """Responde sobre status do sistema."""
        # Em produção, buscaria status real
        return """📊 **Status do Sistema:**

**Backend (API):** ✅ Online
**Frontend (Dashboard):** ✅ Online
**AutoCAD Bridge:** ⏳ Aguardando conexão

**IAs Disponíveis:**
- 🧠 DrawingAnalyzer: ✅ Ativo
- 🧠 PipeOptimizer: ✅ Ativo
- 🧠 ConflictDetector: ✅ Ativo
- 🧠 CostEstimator: ✅ Ativo
- 🧠 QualityInspector: ✅ Ativo

Use o menu "AI Dashboard" para acessar as IAs."""
    
    def _handle_general_help(self, message: str) -> str:
        """Resposta genérica de ajuda."""
        return f"""Entendi sua pergunta: "{message}"

Posso ajudar com:

📚 **Normas** - "Qual norma usar para vapor?"
🔧 **Materiais** - "Qual material para ambiente corrosivo?"
🖥️ **Comandos** - "Como usar o comando OFFSET?"
📐 **Cálculos** - "Como calcular espessura de parede?"
🔧 **Problemas** - "Não consigo conectar ao AutoCAD"

Digite sua pergunta de forma específica para eu ajudar melhor!"""
    
    def _get_suggestions(self) -> List[str]:
        """Retorna sugestões padrão."""
        return [
            "Quais normas estão disponíveis?",
            "Como calcular espessura de parede?",
            "Qual material usar para vapor?",
            "Comandos CAD mais usados",
        ]
    
    def _get_contextual_suggestions(self, intent: str, message: str) -> List[str]:
        """Retorna sugestões baseadas no contexto."""
        suggestions_map = {
            "norm": [
                "Diferença entre ASME B31.1 e B31.3",
                "Quando usar API 650?",
                "Requisitos de inspeção por norma",
            ],
            "material": [
                "Comparação aço carbono vs inox",
                "Material para alta temperatura",
                "Tabela de compatibilidade de materiais",
            ],
            "command": [
                "Atalhos de teclado CAD",
                "Como criar blocos dinâmicos?",
                "Configurar layers para tubulação",
            ],
            "calculate": [
                "Calcular perda de carga",
                "Determinar schedule de tubo",
                "Velocidade máxima recomendada",
            ],
        }
        
        return suggestions_map.get(intent, self._get_suggestions())


# Registrar IA
ai_registry.register(AssistantChatbotAI())
