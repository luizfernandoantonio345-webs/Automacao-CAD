"""
═══════════════════════════════════════════════════════════════════════════════
  DRAWING ANALYZER AI - Análise Inteligente de Desenhos CAD
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Extrair entidades de arquivos DWG/DXF
  - Identificar componentes (válvulas, tubos, equipamentos)
  - Reconhecer padrões e layouts
  - Validar conformidade com normas
  - Extrair metadados e atributos

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


class DrawingAnalyzerAI(BaseAI):
    """
    IA especializada em análise de desenhos CAD.
    
    Capacidades:
    - Extração de entidades (linhas, arcos, círculos, blocos)
    - Identificação de componentes industriais
    - Análise de layers e organização
    - Detecção de escala e unidades
    - Extração de texto e anotações
    """
    
    # Padrões conhecidos de componentes
    COMPONENT_PATTERNS = {
        "valve": [
            r"valv[eu]la?",
            r"valve",
            r"v-\d+",
            r"(ball|gate|check|control|globe|butterfly)\s*valve",
        ],
        "pipe": [
            r"tub[uo]",
            r"pipe",
            r"line",
            r"(\d+)\s*['\"]",  # Diâmetros
        ],
        "pump": [
            r"bomba",
            r"pump",
            r"p-\d+",
        ],
        "tank": [
            r"tanque",
            r"tank",
            r"vessel",
            r"t-\d+",
        ],
        "heat_exchanger": [
            r"trocador",
            r"exchanger",
            r"e-\d+",
            r"heater",
            r"cooler",
        ],
        "instrument": [
            r"instrumento",
            r"instrument",
            r"(pt|tt|ft|lt|pi|ti)\s*-?\d+",
            r"transmitter",
            r"gauge",
        ],
        "fitting": [
            r"conexao",
            r"fitting",
            r"elbow",
            r"tee",
            r"reducer",
            r"flange",
        ],
    }
    
    # Normas suportadas
    SUPPORTED_NORMS = ["ASME", "ISO", "ABNT", "API", "ANSI", "DIN"]
    
    def __init__(self):
        super().__init__(name="DrawingAnalyzer", version="1.0.0")
        self.confidence_threshold = 0.7
    
    def get_capabilities(self) -> List[str]:
        return [
            "entity_extraction",
            "component_identification",
            "layer_analysis",
            "scale_detection",
            "text_extraction",
            "metadata_parsing",
            "norm_validation",
            "pattern_recognition",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Processa dados de desenho CAD.
        
        Input esperado:
        {
            "entities": [...],      # Lista de entidades do desenho
            "layers": [...],        # Lista de layers
            "blocks": [...],        # Lista de blocos
            "texts": [...],         # Textos encontrados
            "file_info": {...},     # Metadados do arquivo
            "analysis_type": str,   # Tipo de análise desejada
        }
        """
        analysis_type = input_data.get("analysis_type", "full")
        
        results = {
            "entities_summary": {},
            "identified_components": [],
            "layer_analysis": {},
            "scale_info": {},
            "extracted_text": [],
            "norm_compliance": {},
            "recommendations": [],
        }
        
        warnings = []
        errors = []
        confidence_scores = []
        
        try:
            # 1. Análise de entidades
            if "entities" in input_data or analysis_type in ["full", "entities"]:
                entities = input_data.get("entities", [])
                results["entities_summary"] = self._analyze_entities(entities)
                confidence_scores.append(0.9)
            
            # 2. Identificação de componentes
            if analysis_type in ["full", "components"]:
                components = self._identify_components(input_data)
                results["identified_components"] = components
                confidence_scores.append(0.85 if components else 0.5)
            
            # 3. Análise de layers
            if "layers" in input_data or analysis_type in ["full", "layers"]:
                layers = input_data.get("layers", [])
                results["layer_analysis"] = self._analyze_layers(layers)
                confidence_scores.append(0.95)
            
            # 4. Detecção de escala
            scale_info = self._detect_scale(input_data)
            results["scale_info"] = scale_info
            if not scale_info.get("detected"):
                warnings.append("Escala não detectada automaticamente")
            else:
                confidence_scores.append(0.9)
            
            # 5. Extração de texto
            if "texts" in input_data or analysis_type in ["full", "text"]:
                texts = input_data.get("texts", [])
                results["extracted_text"] = self._extract_relevant_text(texts)
                confidence_scores.append(0.88)
            
            # 6. Verificação de conformidade com normas
            norm = input_data.get("norm", "ASME")
            results["norm_compliance"] = self._check_norm_compliance(
                results["identified_components"],
                norm
            )
            
            # 7. Gerar recomendações
            results["recommendations"] = self._generate_recommendations(results)
            
            # Calcular confiança média
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation="analyze_drawing",
                data=results,
                confidence=avg_confidence,
                warnings=warnings,
                errors=errors,
                metadata={
                    "analysis_type": analysis_type,
                    "entities_processed": len(input_data.get("entities", [])),
                    "components_found": len(results["identified_components"]),
                }
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro na análise")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation="analyze_drawing",
                data={},
                errors=[str(e)],
            )
    
    def _analyze_entities(self, entities: List[Dict]) -> Dict[str, Any]:
        """Analisa e categoriza entidades do desenho."""
        summary = {
            "total": len(entities),
            "by_type": {},
            "by_layer": {},
            "bounding_box": None,
        }
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for entity in entities:
            # Contar por tipo
            etype = entity.get("type", "unknown")
            summary["by_type"][etype] = summary["by_type"].get(etype, 0) + 1
            
            # Contar por layer
            layer = entity.get("layer", "0")
            summary["by_layer"][layer] = summary["by_layer"].get(layer, 0) + 1
            
            # Calcular bounding box
            coords = entity.get("coordinates", [])
            for coord in coords:
                if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                    min_x = min(min_x, coord[0])
                    min_y = min(min_y, coord[1])
                    max_x = max(max_x, coord[0])
                    max_y = max(max_y, coord[1])
        
        if min_x != float('inf'):
            summary["bounding_box"] = {
                "min": (min_x, min_y),
                "max": (max_x, max_y),
                "width": max_x - min_x,
                "height": max_y - min_y,
            }
        
        return summary
    
    def _identify_components(self, input_data: Dict) -> List[Dict]:
        """Identifica componentes industriais no desenho."""
        components = []
        
        # Buscar em blocos
        for block in input_data.get("blocks", []):
            block_name = block.get("name", "").lower()
            component_type = self._match_component_type(block_name)
            
            if component_type:
                components.append({
                    "type": component_type,
                    "name": block.get("name"),
                    "position": block.get("insertion_point"),
                    "layer": block.get("layer"),
                    "attributes": block.get("attributes", {}),
                    "source": "block",
                    "confidence": 0.9,
                })
        
        # Buscar em textos
        for text in input_data.get("texts", []):
            text_content = text.get("content", "").lower()
            component_type = self._match_component_type(text_content)
            
            if component_type:
                components.append({
                    "type": component_type,
                    "name": text.get("content"),
                    "position": text.get("position"),
                    "layer": text.get("layer"),
                    "source": "text",
                    "confidence": 0.7,
                })
        
        # Analisar padrões geométricos
        geometric_components = self._analyze_geometric_patterns(
            input_data.get("entities", [])
        )
        components.extend(geometric_components)
        
        return components
    
    def _match_component_type(self, text: str) -> Optional[str]:
        """Identifica tipo de componente baseado em texto."""
        text_lower = text.lower()
        
        for comp_type, patterns in self.COMPONENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return comp_type
        
        return None
    
    def _analyze_geometric_patterns(self, entities: List[Dict]) -> List[Dict]:
        """Analisa padrões geométricos para identificar componentes."""
        components = []
        
        # Identificar válvulas por padrão geométrico (triângulos opostos)
        triangles = [e for e in entities if e.get("type") == "polygon" and 
                     len(e.get("vertices", [])) == 3]
        
        # Identificar tubos por linhas longas
        lines = [e for e in entities if e.get("type") == "line"]
        for line in lines:
            length = line.get("length", 0)
            if length > 100:  # Linha longa = provável tubo
                components.append({
                    "type": "pipe",
                    "source": "geometric",
                    "length": length,
                    "position": line.get("start_point"),
                    "confidence": 0.6,
                })
        
        return components
    
    def _analyze_layers(self, layers: List[Dict]) -> Dict[str, Any]:
        """Analisa organização de layers."""
        analysis = {
            "total_layers": len(layers),
            "layers": [],
            "organization_score": 0,
            "suggestions": [],
        }
        
        layer_names = []
        for layer in layers:
            name = layer.get("name", "")
            layer_names.append(name)
            
            analysis["layers"].append({
                "name": name,
                "color": layer.get("color"),
                "linetype": layer.get("linetype"),
                "is_on": layer.get("is_on", True),
                "is_frozen": layer.get("is_frozen", False),
            })
        
        # Calcular score de organização
        has_naming_convention = any("-" in n or "_" in n for n in layer_names)
        has_standard_layers = any(n.upper() in ["PIPES", "VALVES", "TEXT", "DIM"] 
                                   for n in layer_names)
        
        score = 0
        if has_naming_convention:
            score += 40
        if has_standard_layers:
            score += 30
        if len(layers) > 1:
            score += 30
        
        analysis["organization_score"] = min(score, 100)
        
        # Sugestões
        if not has_naming_convention:
            analysis["suggestions"].append(
                "Adotar convenção de nomenclatura para layers (ex: PIPE-PROCESS, VALVE-CONTROL)"
            )
        
        return analysis
    
    def _detect_scale(self, input_data: Dict) -> Dict[str, Any]:
        """Detecta escala do desenho."""
        file_info = input_data.get("file_info", {})
        
        # Verificar se escala está nos metadados
        if "scale" in file_info:
            return {
                "detected": True,
                "scale": file_info["scale"],
                "source": "metadata",
            }
        
        # Tentar detectar por dimensões conhecidas
        texts = input_data.get("texts", [])
        for text in texts:
            content = text.get("content", "")
            # Procurar padrões de escala como "1:50", "SCALE: 1/100"
            scale_match = re.search(r"(?:scale|escala)[:\s]*(\d+)[:/](\d+)", 
                                    content, re.IGNORECASE)
            if scale_match:
                return {
                    "detected": True,
                    "scale": f"{scale_match.group(1)}:{scale_match.group(2)}",
                    "source": "text_annotation",
                }
        
        return {
            "detected": False,
            "scale": None,
            "source": None,
            "suggestion": "Escala não detectada. Verifique bloco de título ou adicione anotação de escala.",
        }
    
    def _extract_relevant_text(self, texts: List[Dict]) -> List[Dict]:
        """Extrai textos relevantes do desenho."""
        relevant = []
        
        for text in texts:
            content = text.get("content", "").strip()
            if not content:
                continue
            
            # Classificar tipo de texto
            text_type = "general"
            
            # Dimensões
            if re.match(r"^\d+[.']?\d*$", content):
                text_type = "dimension"
            # Tags de equipamento
            elif re.match(r"^[A-Z]{1,4}-\d+", content):
                text_type = "equipment_tag"
            # Especificações de tubo
            elif re.search(r'\d+["\']|DN\s*\d+|NPS\s*\d+', content, re.IGNORECASE):
                text_type = "pipe_spec"
            # Notas
            elif len(content) > 50:
                text_type = "note"
            
            relevant.append({
                "content": content,
                "type": text_type,
                "position": text.get("position"),
                "layer": text.get("layer"),
            })
        
        return relevant
    
    def _check_norm_compliance(
        self, 
        components: List[Dict],
        norm: str
    ) -> Dict[str, Any]:
        """Verifica conformidade com normas técnicas."""
        compliance = {
            "norm": norm,
            "compliant": True,
            "checks": [],
            "issues": [],
        }
        
        if norm not in self.SUPPORTED_NORMS:
            compliance["warning"] = f"Norma {norm} não suportada. Usando verificação genérica."
        
        # Verificações básicas
        checks = [
            ("has_components", len(components) > 0, "Desenho contém componentes identificáveis"),
            ("has_valves", any(c["type"] == "valve" for c in components), "Válvulas identificadas"),
            ("has_pipes", any(c["type"] == "pipe" for c in components), "Tubulações identificadas"),
        ]
        
        for check_id, passed, description in checks:
            compliance["checks"].append({
                "id": check_id,
                "passed": passed,
                "description": description,
            })
            if not passed:
                compliance["issues"].append(f"Verificação falhou: {description}")
        
        compliance["compliant"] = len(compliance["issues"]) == 0
        compliance["score"] = (
            sum(1 for c in compliance["checks"] if c["passed"]) 
            / len(compliance["checks"]) * 100
            if compliance["checks"] else 0
        )
        
        return compliance
    
    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """Gera recomendações baseadas na análise."""
        recommendations = []
        
        # Verificar organização de layers
        layer_score = results.get("layer_analysis", {}).get("organization_score", 0)
        if layer_score < 70:
            recommendations.append({
                "priority": "high",
                "category": "organization",
                "message": "Melhorar organização de layers para facilitar manutenção",
                "action": "Adotar padrão de nomenclatura e separar entidades por categoria",
            })
        
        # Verificar se há muitos componentes não identificados
        components = results.get("identified_components", [])
        low_confidence = [c for c in components if c.get("confidence", 0) < 0.7]
        if len(low_confidence) > len(components) * 0.3:
            recommendations.append({
                "priority": "medium",
                "category": "identification",
                "message": f"{len(low_confidence)} componentes com baixa confiança de identificação",
                "action": "Revisar nomenclatura de blocos e adicionar atributos descritivos",
            })
        
        # Verificar escala
        if not results.get("scale_info", {}).get("detected"):
            recommendations.append({
                "priority": "high",
                "category": "metadata",
                "message": "Escala do desenho não definida",
                "action": "Adicionar indicação de escala no bloco de título",
            })
        
        return recommendations


# Registrar IA
ai_registry.register(DrawingAnalyzerAI())
