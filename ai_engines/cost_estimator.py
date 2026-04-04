"""
═══════════════════════════════════════════════════════════════════════════════
  COST ESTIMATOR AI - Estimativa Inteligente de Custos e MTO
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Geração de Material Take-Off (MTO)
  - Estimativa de custos de projeto
  - Análise de variações de preço
  - Comparação de alternativas de materiais
  - Projeções de orçamento

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


class CostEstimatorAI(BaseAI):
    """
    IA especializada em estimativa de custos.
    
    Capacidades:
    - Geração de MTO completo
    - Estimativa de custos por categoria
    - Análise de custo-benefício
    - Comparação de materiais alternativos
    - Projeção de custos com margens
    """
    
    # Base de preços (R$) - em produção viria de banco de dados
    PRICE_DATABASE = {
        "pipe": {
            "steel": {"base_price": 180, "unit": "m", "schedule_factor": {"40": 1.0, "80": 1.4, "160": 2.0}},
            "stainless_304": {"base_price": 720, "unit": "m", "schedule_factor": {"40": 1.0, "80": 1.5}},
            "stainless_316": {"base_price": 950, "unit": "m", "schedule_factor": {"40": 1.0, "80": 1.5}},
            "pvc": {"base_price": 35, "unit": "m", "schedule_factor": {"40": 1.0, "80": 1.3}},
            "cpvc": {"base_price": 85, "unit": "m", "schedule_factor": {"40": 1.0}},
            "hdpe": {"base_price": 45, "unit": "m", "schedule_factor": {"SDR11": 1.0, "SDR17": 0.8}},
        },
        "valve": {
            "gate": {"base_price": 450, "unit": "un", "diameter_factor": 0.8},
            "globe": {"base_price": 680, "unit": "un", "diameter_factor": 0.9},
            "ball": {"base_price": 320, "unit": "un", "diameter_factor": 0.7},
            "butterfly": {"base_price": 280, "unit": "un", "diameter_factor": 0.5},
            "check": {"base_price": 380, "unit": "un", "diameter_factor": 0.75},
            "control": {"base_price": 2500, "unit": "un", "diameter_factor": 1.2},
            "safety": {"base_price": 1800, "unit": "un", "diameter_factor": 1.0},
        },
        "fitting": {
            "elbow_90": {"base_price": 85, "unit": "un", "diameter_factor": 0.6},
            "elbow_45": {"base_price": 70, "unit": "un", "diameter_factor": 0.55},
            "tee": {"base_price": 120, "unit": "un", "diameter_factor": 0.7},
            "reducer": {"base_price": 95, "unit": "un", "diameter_factor": 0.65},
            "flange": {"base_price": 180, "unit": "un", "diameter_factor": 0.8},
            "cap": {"base_price": 45, "unit": "un", "diameter_factor": 0.5},
            "coupling": {"base_price": 55, "unit": "un", "diameter_factor": 0.5},
        },
        "support": {
            "pipe_shoe": {"base_price": 85, "unit": "un"},
            "pipe_hanger": {"base_price": 120, "unit": "un"},
            "spring_hanger": {"base_price": 850, "unit": "un"},
            "guide": {"base_price": 95, "unit": "un"},
            "anchor": {"base_price": 280, "unit": "un"},
        },
        "insulation": {
            "mineral_wool": {"base_price": 45, "unit": "m2"},
            "calcium_silicate": {"base_price": 85, "unit": "m2"},
            "cellular_glass": {"base_price": 120, "unit": "m2"},
            "elastomeric": {"base_price": 65, "unit": "m2"},
        },
    }
    
    # Fatores de mão de obra por tipo
    LABOR_FACTORS = {
        "pipe": 0.45,      # 45% do custo de material
        "valve": 0.25,     # 25% do custo de material  
        "fitting": 0.35,   # 35% do custo de material
        "support": 0.50,   # 50% do custo de material
        "insulation": 0.60,  # 60% do custo de material
    }
    
    # Fatores de contingência
    CONTINGENCY_FACTORS = {
        "low": 0.05,        # 5% - projeto bem definido
        "medium": 0.15,     # 15% - projeto típico
        "high": 0.25,       # 25% - projeto com incertezas
        "preliminary": 0.35,  # 35% - estimativa preliminar
    }
    
    def __init__(self):
        super().__init__(name="CostEstimator", version="1.0.0")
        self.confidence_threshold = 0.7
    
    def get_capabilities(self) -> List[str]:
        return [
            "mto_generation",
            "cost_estimation",
            "material_comparison",
            "labor_calculation",
            "contingency_analysis",
            "budget_projection",
            "alternative_analysis",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Processa dados para estimativa de custos.
        
        Input esperado:
        {
            "items": [...],           # Lista de itens do projeto
            "operation": str,         # "mto", "estimate", "compare"
            "contingency_level": str, # "low", "medium", "high", "preliminary"
            "include_labor": bool,    # Incluir mão de obra
            "alternatives": [...],    # Materiais alternativos para comparar
        }
        """
        operation = input_data.get("operation", "estimate")
        items = input_data.get("items", [])
        contingency_level = input_data.get("contingency_level", "medium")
        include_labor = input_data.get("include_labor", True)
        
        results = {
            "operation": operation,
            "mto": {},
            "cost_breakdown": {},
            "summary": {},
            "alternatives": [],
            "recommendations": [],
        }
        
        try:
            # Gerar MTO
            mto = self._generate_mto(items)
            results["mto"] = mto
            
            # Calcular custos
            cost_breakdown = self._calculate_costs(mto, include_labor)
            results["cost_breakdown"] = cost_breakdown
            
            # Aplicar contingência
            contingency_factor = self.CONTINGENCY_FACTORS.get(contingency_level, 0.15)
            
            material_cost = sum(c["total"] for c in cost_breakdown.get("materials", []))
            labor_cost = sum(c["total"] for c in cost_breakdown.get("labor", []))
            subtotal = material_cost + labor_cost
            contingency = subtotal * contingency_factor
            
            results["summary"] = {
                "material_cost": round(material_cost, 2),
                "labor_cost": round(labor_cost, 2),
                "subtotal": round(subtotal, 2),
                "contingency_percent": contingency_factor * 100,
                "contingency_value": round(contingency, 2),
                "total_estimated": round(subtotal + contingency, 2),
                "currency": "BRL",
            }
            
            # Comparar alternativas se solicitado
            if input_data.get("alternatives"):
                results["alternatives"] = self._compare_alternatives(
                    mto,
                    input_data["alternatives"]
                )
            
            # Gerar recomendações
            results["recommendations"] = self._generate_recommendations(
                results["cost_breakdown"],
                results["summary"]
            )
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation=operation,
                data=results,
                confidence=0.85,
                metadata={
                    "items_processed": len(items),
                    "contingency_level": contingency_level,
                    "include_labor": include_labor,
                }
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro na estimativa")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation=operation,
                data={},
                errors=[str(e)],
            )
    
    def _generate_mto(self, items: List[Dict]) -> Dict[str, Any]:
        """Gera Material Take-Off organizado."""
        mto = {
            "pipes": [],
            "valves": [],
            "fittings": [],
            "supports": [],
            "insulation": [],
            "others": [],
            "totals": {},
        }
        
        for item in items:
            item_type = item.get("type", "other")
            category = self._get_category(item_type)
            
            mto_item = {
                "id": item.get("id", ""),
                "type": item_type,
                "description": item.get("description", ""),
                "material": item.get("material", ""),
                "diameter": item.get("diameter", 0),
                "schedule": item.get("schedule", "40"),
                "quantity": item.get("quantity", 1),
                "unit": item.get("unit", "un"),
                "specifications": item.get("specifications", {}),
            }
            
            mto[category].append(mto_item)
        
        # Calcular totais
        for category in ["pipes", "valves", "fittings", "supports", "insulation", "others"]:
            mto["totals"][category] = len(mto[category])
        
        return mto
    
    def _get_category(self, item_type: str) -> str:
        """Mapeia tipo de item para categoria."""
        type_map = {
            "pipe": "pipes",
            "valve": "valves",
            "gate_valve": "valves",
            "ball_valve": "valves",
            "check_valve": "valves",
            "control_valve": "valves",
            "elbow": "fittings",
            "tee": "fittings",
            "reducer": "fittings",
            "flange": "fittings",
            "support": "supports",
            "hanger": "supports",
            "insulation": "insulation",
        }
        return type_map.get(item_type.lower(), "others")
    
    def _calculate_costs(
        self,
        mto: Dict[str, Any],
        include_labor: bool
    ) -> Dict[str, Any]:
        """Calcula custos baseado no MTO."""
        breakdown = {
            "materials": [],
            "labor": [],
        }
        
        # Processar cada categoria
        for category in ["pipes", "valves", "fittings", "supports", "insulation"]:
            items = mto.get(category, [])
            
            for item in items:
                cost = self._calculate_item_cost(item, category)
                
                if cost > 0:
                    breakdown["materials"].append({
                        "item": item.get("description") or f"{item.get('type')} {item.get('diameter', '')}",
                        "quantity": item.get("quantity", 1),
                        "unit": item.get("unit", "un"),
                        "unit_price": round(cost / item.get("quantity", 1), 2),
                        "total": round(cost, 2),
                        "category": category,
                    })
                    
                    if include_labor:
                        labor_factor = self.LABOR_FACTORS.get(category.rstrip("s"), 0.3)
                        labor_cost = cost * labor_factor
                        
                        breakdown["labor"].append({
                            "item": f"Instalação - {item.get('description') or item.get('type')}",
                            "total": round(labor_cost, 2),
                            "category": category,
                        })
        
        return breakdown
    
    def _calculate_item_cost(self, item: Dict, category: str) -> float:
        """Calcula custo de um item individual."""
        item_type = item.get("type", "").lower()
        material = item.get("material", "steel").lower()
        diameter = item.get("diameter", 100)
        quantity = item.get("quantity", 1)
        schedule = item.get("schedule", "40")
        
        # Buscar preço base
        category_key = category.rstrip("s")  # pipes -> pipe
        
        if category_key in self.PRICE_DATABASE:
            type_prices = self.PRICE_DATABASE[category_key]
            
            # Tentar encontrar preço específico
            if item_type in type_prices:
                price_info = type_prices[item_type]
            elif material in type_prices:
                price_info = type_prices[material]
            else:
                # Usar primeiro disponível
                price_info = next(iter(type_prices.values()), {"base_price": 100})
            
            base_price = price_info.get("base_price", 100)
            
            # Aplicar fator de diâmetro se existir
            if "diameter_factor" in price_info:
                base_price = base_price * (diameter / 100) ** price_info["diameter_factor"]
            
            # Aplicar fator de schedule se existir
            if "schedule_factor" in price_info:
                schedule_factor = price_info["schedule_factor"].get(str(schedule), 1.0)
                base_price = base_price * schedule_factor
            
            return base_price * quantity
        
        return 100 * quantity  # Preço default
    
    def _compare_alternatives(
        self,
        mto: Dict[str, Any],
        alternatives: List[Dict]
    ) -> List[Dict]:
        """Compara custos com materiais alternativos."""
        comparisons = []
        
        for alt in alternatives:
            alt_mto = self._apply_alternative(mto, alt)
            alt_costs = self._calculate_costs(alt_mto, include_labor=True)
            
            alt_total = (
                sum(c["total"] for c in alt_costs.get("materials", [])) +
                sum(c["total"] for c in alt_costs.get("labor", []))
            )
            
            comparisons.append({
                "alternative": alt.get("name", "Alternativa"),
                "description": alt.get("description", ""),
                "total_cost": round(alt_total, 2),
                "changes": alt.get("changes", []),
            })
        
        return comparisons
    
    def _apply_alternative(self, mto: Dict, alternative: Dict) -> Dict:
        """Aplica mudanças de alternativa ao MTO."""
        new_mto = {k: list(v) if isinstance(v, list) else v for k, v in mto.items()}
        
        for change in alternative.get("changes", []):
            category = change.get("category", "pipes")
            from_material = change.get("from", "")
            to_material = change.get("to", "")
            
            if category in new_mto:
                for item in new_mto[category]:
                    if item.get("material", "").lower() == from_material.lower():
                        item["material"] = to_material
        
        return new_mto
    
    def _generate_recommendations(
        self,
        cost_breakdown: Dict,
        summary: Dict
    ) -> List[Dict]:
        """Gera recomendações de otimização de custos."""
        recommendations = []
        
        total = summary.get("total_estimated", 0)
        material_cost = summary.get("material_cost", 0)
        labor_cost = summary.get("labor_cost", 0)
        
        # Analisar proporção de custos
        if material_cost > 0:
            labor_ratio = labor_cost / material_cost
            
            if labor_ratio > 0.6:
                recommendations.append({
                    "priority": "medium",
                    "category": "labor",
                    "issue": f"Custo de mão de obra alto ({labor_ratio*100:.0f}% do material)",
                    "suggestion": "Considere pré-fabricação em shop para reduzir instalação em campo",
                    "potential_savings": f"R$ {labor_cost * 0.15:.2f} (estimativa 15%)",
                })
        
        # Verificar itens de alto custo
        materials = cost_breakdown.get("materials", [])
        if materials:
            sorted_materials = sorted(materials, key=lambda x: x["total"], reverse=True)
            top_items = sorted_materials[:3]
            
            if top_items:
                top_cost = sum(i["total"] for i in top_items)
                if top_cost > total * 0.5:
                    recommendations.append({
                        "priority": "high",
                        "category": "materials",
                        "issue": f"3 itens representam {top_cost/total*100:.0f}% do custo total",
                        "suggestion": "Avaliar alternativas de material ou especificação para itens principais",
                        "items": [i["item"] for i in top_items],
                    })
        
        # Contingência alta
        if summary.get("contingency_percent", 0) > 20:
            recommendations.append({
                "priority": "medium",
                "category": "planning",
                "issue": f"Contingência alta ({summary['contingency_percent']:.0f}%)",
                "suggestion": "Refinar escopo e especificações para reduzir incertezas",
            })
        
        return recommendations


# Registrar IA
ai_registry.register(CostEstimatorAI())
