"""
═══════════════════════════════════════════════════════════════════════════════
  MAINTENANCE PREDICTOR AI - Predição Inteligente de Manutenção
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Análise preditiva de falhas
  - Cálculo de vida útil de componentes
  - Planejamento de manutenção preventiva
  - Análise de histórico de manutenções
  - Recomendações de substituição

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


@dataclass
class MaintenancePrediction:
    """Predição de manutenção para um componente."""
    component_id: str
    component_type: str
    current_health: float  # 0-100%
    estimated_remaining_life: int  # dias
    recommended_action: str
    priority: str  # "critical", "high", "medium", "low"
    next_maintenance_date: str
    confidence: float


class MaintenancePredictorAI(BaseAI):
    """
    IA especializada em predição de manutenção.
    
    Capacidades:
    - Análise de vida útil baseada em condições operacionais
    - Predição de falhas
    - Planejamento de manutenção preventiva
    - Análise de degradação
    - Otimização de intervalos de manutenção
    """
    
    # Vida útil base por tipo de componente (anos)
    BASE_LIFETIME = {
        "pipe": {"steel": 30, "stainless": 40, "pvc": 20, "hdpe": 25},
        "valve": {"gate": 20, "globe": 15, "ball": 15, "butterfly": 12, "control": 10},
        "pump": {"centrifugal": 15, "positive_displacement": 12},
        "heat_exchanger": {"shell_tube": 20, "plate": 15},
        "instrument": {"transmitter": 10, "gauge": 8},
        "gasket": {"rubber": 3, "ptfe": 5, "graphite": 7},
    }
    
    # Fatores de degradação
    DEGRADATION_FACTORS = {
        "temperature": {  # °C acima do nominal
            0: 1.0, 10: 0.95, 20: 0.85, 50: 0.7, 100: 0.5,
        },
        "pressure": {  # % acima do nominal
            0: 1.0, 10: 0.95, 20: 0.9, 50: 0.75,
        },
        "corrosion": {  # nível de corrosividade
            "none": 1.0, "low": 0.9, "medium": 0.75, "high": 0.5, "severe": 0.3,
        },
        "cycles": {  # ciclos por dia
            0: 1.0, 10: 0.95, 50: 0.85, 100: 0.7, 500: 0.5,
        },
    }
    
    # Intervalos de manutenção recomendados (meses)
    MAINTENANCE_INTERVALS = {
        "pipe": {"inspection": 12, "cleaning": 24, "replacement": 360},
        "valve": {"inspection": 6, "lubrication": 3, "overhaul": 60, "replacement": 180},
        "pump": {"inspection": 3, "lubrication": 1, "overhaul": 24, "replacement": 120},
        "instrument": {"calibration": 6, "replacement": 96},
        "gasket": {"inspection": 12, "replacement": 36},
    }
    
    def __init__(self):
        super().__init__(name="MaintenancePredictor", version="1.0.0")
        self.confidence_threshold = 0.7
    
    def get_capabilities(self) -> List[str]:
        return [
            "lifetime_estimation",
            "failure_prediction",
            "maintenance_planning",
            "degradation_analysis",
            "health_assessment",
            "replacement_recommendation",
            "cost_optimization",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Processa dados para predição de manutenção.
        
        Input esperado:
        {
            "components": [...],      # Lista de componentes
            "operation": str,         # "predict", "analyze", "plan"
            "planning_horizon": int,  # Horizonte de planejamento (dias)
            "history": [...],         # Histórico de manutenção
        }
        """
        components = input_data.get("components", [])
        operation = input_data.get("operation", "predict")
        planning_horizon = input_data.get("planning_horizon", 365)
        history = input_data.get("history", [])
        
        predictions: List[MaintenancePrediction] = []
        
        try:
            for component in components:
                prediction = self._predict_component(component, history)
                predictions.append(prediction)
            
            # Gerar plano de manutenção
            maintenance_plan = self._generate_maintenance_plan(
                predictions,
                planning_horizon
            )
            
            # Análise de criticidade
            criticality_analysis = self._analyze_criticality(predictions)
            
            # Recomendações de otimização
            optimization_recs = self._generate_optimization_recommendations(
                predictions,
                history
            )
            
            # Resumo
            summary = {
                "total_components": len(components),
                "critical_count": sum(1 for p in predictions if p.priority == "critical"),
                "high_priority_count": sum(1 for p in predictions if p.priority == "high"),
                "average_health": (
                    sum(p.current_health for p in predictions) / len(predictions)
                    if predictions else 0
                ),
                "maintenance_actions_30d": sum(
                    1 for p in predictions 
                    if p.estimated_remaining_life <= 30
                ),
            }
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation=operation,
                data={
                    "summary": summary,
                    "predictions": [self._prediction_to_dict(p) for p in predictions],
                    "maintenance_plan": maintenance_plan,
                    "criticality_analysis": criticality_analysis,
                    "optimization_recommendations": optimization_recs,
                },
                confidence=0.85,
                metadata={
                    "planning_horizon_days": planning_horizon,
                    "components_analyzed": len(components),
                }
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro na predição")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation=operation,
                data={},
                errors=[str(e)],
            )
    
    def _prediction_to_dict(self, pred: MaintenancePrediction) -> Dict:
        """Converte MaintenancePrediction para dict."""
        return {
            "component_id": pred.component_id,
            "component_type": pred.component_type,
            "current_health": pred.current_health,
            "estimated_remaining_life_days": pred.estimated_remaining_life,
            "recommended_action": pred.recommended_action,
            "priority": pred.priority,
            "next_maintenance_date": pred.next_maintenance_date,
            "confidence": pred.confidence,
        }
    
    def _predict_component(
        self,
        component: Dict,
        history: List[Dict]
    ) -> MaintenancePrediction:
        """Gera predição para um componente individual."""
        comp_id = component.get("id", "unknown")
        comp_type = component.get("type", "pipe")
        comp_subtype = component.get("subtype", "steel")
        
        # Calcular idade
        install_date = component.get("install_date")
        if install_date:
            try:
                install_dt = datetime.fromisoformat(install_date)
                age_days = (datetime.now() - install_dt).days
            except:
                age_days = component.get("age_days", 0)
        else:
            age_days = component.get("age_days", 0)
        
        # Obter vida útil base
        base_life_years = self.BASE_LIFETIME.get(comp_type, {}).get(comp_subtype, 20)
        base_life_days = base_life_years * 365
        
        # Aplicar fatores de degradação
        degradation_factor = self._calculate_degradation_factor(component)
        adjusted_life_days = base_life_days * degradation_factor
        
        # Calcular vida restante
        remaining_life = max(0, adjusted_life_days - age_days)
        
        # Calcular saúde atual (%)
        health = min(100, max(0, (remaining_life / adjusted_life_days) * 100))
        
        # Considerar histórico de manutenção
        comp_history = [h for h in history if h.get("component_id") == comp_id]
        if comp_history:
            # Ajustar baseado em manutenções realizadas
            last_maintenance = max(comp_history, key=lambda x: x.get("date", ""))
            last_maint_type = last_maintenance.get("type", "")
            
            if last_maint_type == "overhaul":
                health = min(health + 20, 100)
                remaining_life = int(remaining_life * 1.3)
        
        # Determinar ação recomendada
        if health < 20:
            action = "Substituição urgente"
            priority = "critical"
        elif health < 40:
            action = "Programar substituição"
            priority = "high"
        elif health < 60:
            action = "Manutenção preventiva"
            priority = "medium"
        elif health < 80:
            action = "Inspeção recomendada"
            priority = "low"
        else:
            action = "Operação normal"
            priority = "low"
        
        # Próxima manutenção
        maintenance_interval = self.MAINTENANCE_INTERVALS.get(comp_type, {}).get("inspection", 12)
        next_maintenance = (datetime.now() + timedelta(days=maintenance_interval * 30)).isoformat()
        
        # Se saúde baixa, antecipar
        if health < 50:
            next_maintenance = (datetime.now() + timedelta(days=int(remaining_life * 0.5))).isoformat()
        
        return MaintenancePrediction(
            component_id=comp_id,
            component_type=comp_type,
            current_health=round(health, 1),
            estimated_remaining_life=int(remaining_life),
            recommended_action=action,
            priority=priority,
            next_maintenance_date=next_maintenance,
            confidence=0.8 if comp_history else 0.65,
        )
    
    def _calculate_degradation_factor(self, component: Dict) -> float:
        """Calcula fator de degradação baseado em condições operacionais."""
        factor = 1.0
        
        # Temperatura
        temp_excess = component.get("temperature_excess", 0)
        for threshold, mult in sorted(self.DEGRADATION_FACTORS["temperature"].items(), reverse=True):
            if temp_excess >= threshold:
                factor *= mult
                break
        
        # Pressão
        pressure_excess = component.get("pressure_excess_percent", 0)
        for threshold, mult in sorted(self.DEGRADATION_FACTORS["pressure"].items(), reverse=True):
            if pressure_excess >= threshold:
                factor *= mult
                break
        
        # Corrosão
        corrosion = component.get("corrosion_level", "none")
        factor *= self.DEGRADATION_FACTORS["corrosion"].get(corrosion, 1.0)
        
        # Ciclos
        cycles_per_day = component.get("cycles_per_day", 0)
        for threshold, mult in sorted(self.DEGRADATION_FACTORS["cycles"].items(), reverse=True):
            if cycles_per_day >= threshold:
                factor *= mult
                break
        
        return factor
    
    def _generate_maintenance_plan(
        self,
        predictions: List[MaintenancePrediction],
        horizon_days: int
    ) -> Dict[str, Any]:
        """Gera plano de manutenção."""
        plan = {
            "horizon_days": horizon_days,
            "activities": [],
            "schedule_by_month": {},
            "resource_requirements": {},
        }
        
        now = datetime.now()
        
        for pred in predictions:
            if pred.estimated_remaining_life <= horizon_days:
                activity_date = now + timedelta(days=int(pred.estimated_remaining_life * 0.8))
                month_key = activity_date.strftime("%Y-%m")
                
                activity = {
                    "component_id": pred.component_id,
                    "component_type": pred.component_type,
                    "action": pred.recommended_action,
                    "priority": pred.priority,
                    "scheduled_date": activity_date.isoformat(),
                    "estimated_duration_hours": self._estimate_duration(pred.component_type, pred.recommended_action),
                }
                
                plan["activities"].append(activity)
                
                if month_key not in plan["schedule_by_month"]:
                    plan["schedule_by_month"][month_key] = []
                plan["schedule_by_month"][month_key].append(activity)
        
        # Ordenar por data
        plan["activities"].sort(key=lambda x: x["scheduled_date"])
        
        # Calcular recursos necessários
        plan["resource_requirements"] = {
            "total_activities": len(plan["activities"]),
            "estimated_hours": sum(a["estimated_duration_hours"] for a in plan["activities"]),
            "critical_activities": sum(1 for a in plan["activities"] if a["priority"] == "critical"),
        }
        
        return plan
    
    def _estimate_duration(self, component_type: str, action: str) -> float:
        """Estima duração de atividade em horas."""
        durations = {
            "pipe": {"Substituição urgente": 8, "Programar substituição": 8, "Manutenção preventiva": 4, "Inspeção recomendada": 2},
            "valve": {"Substituição urgente": 4, "Programar substituição": 4, "Manutenção preventiva": 2, "Inspeção recomendada": 1},
            "pump": {"Substituição urgente": 16, "Programar substituição": 16, "Manutenção preventiva": 8, "Inspeção recomendada": 2},
        }
        return durations.get(component_type, {}).get(action, 4)
    
    def _analyze_criticality(
        self,
        predictions: List[MaintenancePrediction]
    ) -> Dict[str, Any]:
        """Analisa criticidade dos componentes."""
        analysis = {
            "distribution": {
                "critical": [],
                "high": [],
                "medium": [],
                "low": [],
            },
            "risk_score": 0,
            "top_concerns": [],
        }
        
        for pred in predictions:
            analysis["distribution"][pred.priority].append({
                "id": pred.component_id,
                "health": pred.current_health,
                "remaining_days": pred.estimated_remaining_life,
            })
        
        # Calcular score de risco (0-100)
        weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total_weight = sum(
            weights[pred.priority] for pred in predictions
        )
        max_weight = len(predictions) * 4
        analysis["risk_score"] = round((total_weight / max_weight) * 100, 1) if max_weight > 0 else 0
        
        # Top 5 preocupações
        sorted_preds = sorted(predictions, key=lambda p: p.current_health)
        analysis["top_concerns"] = [
            {
                "id": p.component_id,
                "type": p.component_type,
                "health": p.current_health,
                "action": p.recommended_action,
            }
            for p in sorted_preds[:5]
        ]
        
        return analysis
    
    def _generate_optimization_recommendations(
        self,
        predictions: List[MaintenancePrediction],
        history: List[Dict]
    ) -> List[Dict]:
        """Gera recomendações de otimização."""
        recommendations = []
        
        # Verificar componentes sem histórico
        ids_with_history = set(h.get("component_id") for h in history)
        no_history = [p for p in predictions if p.component_id not in ids_with_history]
        
        if len(no_history) > len(predictions) * 0.5:
            recommendations.append({
                "type": "data_quality",
                "priority": "medium",
                "description": f"{len(no_history)} componentes sem histórico de manutenção",
                "action": "Implementar registro sistemático de manutenções para melhorar predições",
            })
        
        # Verificar clustering de manutenções
        critical = [p for p in predictions if p.priority == "critical"]
        if len(critical) > 3:
            recommendations.append({
                "type": "planning",
                "priority": "high",
                "description": f"{len(critical)} componentes críticos requerem atenção simultânea",
                "action": "Considerar programa de substituição preventiva para evitar acúmulo",
            })
        
        # Verificar componentes com saúde muito baixa
        very_low_health = [p for p in predictions if p.current_health < 20]
        if very_low_health:
            recommendations.append({
                "type": "urgent",
                "priority": "critical",
                "description": f"{len(very_low_health)} componentes abaixo de 20% de saúde",
                "action": "Iniciar processo de substituição imediata",
                "components": [p.component_id for p in very_low_health],
            })
        
        return recommendations


# Registrar IA
ai_registry.register(MaintenancePredictorAI())
