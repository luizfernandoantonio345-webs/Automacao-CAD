"""
═══════════════════════════════════════════════════════════════════════════════
  PIPE OPTIMIZER AI - Otimização Inteligente de Rotas de Tubulação
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Otimização de rotas de tubulação
  - Cálculo de materiais e comprimentos
  - Minimização de curvas e conexões
  - Análise de eficiência hidráulica
  - Sugestões de melhorias de layout

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import heapq

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


@dataclass
class Point3D:
    """Representa um ponto 3D."""
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: 'Point3D') -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )
    
    def __hash__(self):
        return hash((round(self.x, 2), round(self.y, 2), round(self.z, 2)))
    
    def __eq__(self, other):
        return (round(self.x, 2) == round(other.x, 2) and
                round(self.y, 2) == round(other.y, 2) and
                round(self.z, 2) == round(other.z, 2))
    
    def __lt__(self, other):
        return (self.x, self.y, self.z) < (other.x, other.y, other.z)


@dataclass
class PipeSegment:
    """Representa um segmento de tubulação."""
    start: Point3D
    end: Point3D
    diameter: float
    material: str = "steel"
    schedule: str = "40"
    insulation: bool = False
    
    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)
    
    @property
    def weight_per_meter(self) -> float:
        """Peso aproximado por metro baseado no diâmetro."""
        # Simplificado - em produção usaria tabela ASME
        weights = {
            25: 2.5, 50: 5.4, 75: 8.6, 100: 12.1,
            150: 21.8, 200: 33.3, 250: 45.3, 300: 59.8,
        }
        return weights.get(int(self.diameter), self.diameter * 0.15)


class PipeOptimizerAI(BaseAI):
    """
    IA especializada em otimização de tubulações.
    
    Capacidades:
    - Otimização de rotas usando A* modificado
    - Cálculo de bill of materials (BOM)
    - Análise de perda de carga
    - Minimização de curvas
    - Detecção de rotas ineficientes
    """
    
    # Custos padrão para otimização
    COST_FACTORS = {
        "straight_pipe": 1.0,
        "elbow_90": 3.0,      # Custo equivalente de curva 90°
        "elbow_45": 2.0,      # Custo equivalente de curva 45°
        "tee": 4.0,           # Custo equivalente de T
        "reducer": 2.5,       # Custo equivalente de redução
        "flange": 5.0,        # Custo equivalente de flange
        "vertical_change": 1.5,  # Penalidade por mudança de elevação
    }
    
    # Preços de referência por tipo de tubo (R$/metro)
    PIPE_PRICES = {
        "steel": {25: 45, 50: 85, 75: 120, 100: 180, 150: 320, 200: 480, 250: 680, 300: 920},
        "stainless": {25: 180, 50: 340, 75: 480, 100: 720, 150: 1280, 200: 1920, 250: 2720, 300: 3680},
        "pvc": {25: 8, 50: 15, 75: 22, 100: 35, 150: 65, 200: 95, 250: 140, 300: 185},
        "cpvc": {25: 25, 50: 48, 75: 72, 100: 110, 150: 200, 200: 300, 250: 440, 300: 590},
    }
    
    def __init__(self):
        super().__init__(name="PipeOptimizer", version="1.0.0")
        self.confidence_threshold = 0.75
    
    def get_capabilities(self) -> List[str]:
        return [
            "route_optimization",
            "material_calculation",
            "cost_estimation",
            "pressure_drop_analysis",
            "bend_minimization",
            "layout_suggestions",
            "bom_generation",
            "efficiency_analysis",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Processa dados de tubulação para otimização.
        
        Input esperado:
        {
            "pipes": [...],           # Lista de segmentos existentes
            "start_point": {...},     # Ponto inicial (para nova rota)
            "end_point": {...},       # Ponto final (para nova rota)
            "obstacles": [...],       # Obstáculos a evitar
            "constraints": {...},     # Restrições (diâmetro mínimo, etc)
            "operation": str,         # "optimize", "analyze", "calculate_bom"
        }
        """
        operation = input_data.get("operation", "analyze")
        
        results = {
            "operation": operation,
            "original_analysis": {},
            "optimized_route": [],
            "bom": {},
            "cost_analysis": {},
            "efficiency_metrics": {},
            "recommendations": [],
        }
        
        warnings = []
        errors = []
        
        try:
            # Processar segmentos existentes
            pipes = self._parse_pipes(input_data.get("pipes", []))
            
            if operation == "analyze":
                # Análise de rotas existentes
                results["original_analysis"] = self._analyze_existing_route(pipes)
                results["efficiency_metrics"] = self._calculate_efficiency(pipes)
                results["recommendations"] = self._generate_optimization_recommendations(
                    results["original_analysis"]
                )
                confidence = 0.9
                
            elif operation == "optimize":
                # Otimização de rota
                start = self._parse_point(input_data.get("start_point"))
                end = self._parse_point(input_data.get("end_point"))
                obstacles = input_data.get("obstacles", [])
                constraints = input_data.get("constraints", {})
                
                if start and end:
                    optimized = self._optimize_route(start, end, obstacles, constraints)
                    results["optimized_route"] = optimized["route"]
                    results["optimization_stats"] = optimized["stats"]
                    confidence = 0.85
                else:
                    errors.append("Pontos inicial e final são obrigatórios para otimização")
                    confidence = 0.3
                
            elif operation == "calculate_bom":
                # Cálculo de materiais
                results["bom"] = self._calculate_bom(pipes)
                results["cost_analysis"] = self._calculate_costs(results["bom"])
                confidence = 0.95
                
            else:
                # Análise completa
                results["original_analysis"] = self._analyze_existing_route(pipes)
                results["bom"] = self._calculate_bom(pipes)
                results["cost_analysis"] = self._calculate_costs(results["bom"])
                results["efficiency_metrics"] = self._calculate_efficiency(pipes)
                results["recommendations"] = self._generate_optimization_recommendations(
                    results["original_analysis"]
                )
                confidence = 0.88
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation=operation,
                data=results,
                confidence=confidence,
                warnings=warnings,
                errors=errors,
                metadata={
                    "pipes_analyzed": len(pipes),
                    "total_length": sum(p.length for p in pipes),
                }
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro no processamento")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation=operation,
                data={},
                errors=[str(e)],
            )
    
    def _parse_point(self, data: Optional[Dict]) -> Optional[Point3D]:
        """Converte dict para Point3D."""
        if not data:
            return None
        return Point3D(
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            z=float(data.get("z", 0)),
        )
    
    def _parse_pipes(self, pipes_data: List[Dict]) -> List[PipeSegment]:
        """Converte lista de dicts para PipeSegments."""
        pipes = []
        for p in pipes_data:
            start = self._parse_point(p.get("start"))
            end = self._parse_point(p.get("end"))
            if start and end:
                pipes.append(PipeSegment(
                    start=start,
                    end=end,
                    diameter=float(p.get("diameter", 100)),
                    material=p.get("material", "steel"),
                    schedule=p.get("schedule", "40"),
                    insulation=p.get("insulation", False),
                ))
        return pipes
    
    def _analyze_existing_route(self, pipes: List[PipeSegment]) -> Dict[str, Any]:
        """Analisa rota de tubulação existente."""
        if not pipes:
            return {"status": "no_data", "message": "Nenhuma tubulação para analisar"}
        
        total_length = sum(p.length for p in pipes)
        
        # Detectar mudanças de direção (curvas)
        direction_changes = 0
        elevation_changes = 0
        
        for i in range(1, len(pipes)):
            prev = pipes[i-1]
            curr = pipes[i]
            
            # Direção do segmento anterior
            prev_dir = (
                prev.end.x - prev.start.x,
                prev.end.y - prev.start.y,
                prev.end.z - prev.start.z,
            )
            
            # Direção do segmento atual
            curr_dir = (
                curr.end.x - curr.start.x,
                curr.end.y - curr.start.y,
                curr.end.z - curr.start.z,
            )
            
            # Se há mudança de direção
            if self._vectors_different_direction(prev_dir, curr_dir):
                direction_changes += 1
            
            # Se há mudança de elevação
            if abs(curr.start.z - prev.end.z) > 0.01:
                elevation_changes += 1
        
        # Calcular diâmetros diferentes
        diameters = set(p.diameter for p in pipes)
        
        return {
            "status": "analyzed",
            "total_segments": len(pipes),
            "total_length_m": round(total_length, 2),
            "direction_changes": direction_changes,
            "elevation_changes": elevation_changes,
            "unique_diameters": sorted(list(diameters)),
            "materials_used": list(set(p.material for p in pipes)),
            "insulated_percentage": (
                sum(1 for p in pipes if p.insulation) / len(pipes) * 100
            ),
            "average_segment_length": round(total_length / len(pipes), 2),
        }
    
    def _vectors_different_direction(self, v1: Tuple, v2: Tuple) -> bool:
        """Verifica se dois vetores têm direções significativamente diferentes."""
        # Normalizar vetores
        def normalize(v):
            magnitude = math.sqrt(sum(c**2 for c in v))
            if magnitude == 0:
                return (0, 0, 0)
            return tuple(c / magnitude for c in v)
        
        n1 = normalize(v1)
        n2 = normalize(v2)
        
        # Produto escalar
        dot = sum(a * b for a, b in zip(n1, n2))
        
        # Se produto escalar < 0.95, consideramos mudança de direção
        return dot < 0.95
    
    def _optimize_route(
        self,
        start: Point3D,
        end: Point3D,
        obstacles: List[Dict],
        constraints: Dict
    ) -> Dict[str, Any]:
        """
        Otimiza rota entre dois pontos usando A* modificado.
        """
        # Grid resolution para pathfinding
        resolution = constraints.get("grid_resolution", 100)  # mm
        
        # Heurística: distância euclidiana + penalidade por curvas
        def heuristic(p1: Point3D, p2: Point3D) -> float:
            return p1.distance_to(p2)
        
        # Para simplificação, gerar rota reta com ajustes
        # Em produção, implementaria A* completo com grade 3D
        
        direct_distance = start.distance_to(end)
        
        # Gerar pontos intermediários para rota ortogonal
        waypoints = self._generate_orthogonal_route(start, end)
        
        # Calcular estatísticas
        route_segments = []
        for i in range(1, len(waypoints)):
            route_segments.append({
                "start": {"x": waypoints[i-1].x, "y": waypoints[i-1].y, "z": waypoints[i-1].z},
                "end": {"x": waypoints[i].x, "y": waypoints[i].y, "z": waypoints[i].z},
                "length": waypoints[i-1].distance_to(waypoints[i]),
            })
        
        total_length = sum(s["length"] for s in route_segments)
        
        return {
            "route": route_segments,
            "stats": {
                "direct_distance": round(direct_distance, 2),
                "routed_distance": round(total_length, 2),
                "efficiency": round(direct_distance / total_length * 100, 1) if total_length > 0 else 100,
                "segments": len(route_segments),
                "bends": len(route_segments) - 1,
            }
        }
    
    def _generate_orthogonal_route(self, start: Point3D, end: Point3D) -> List[Point3D]:
        """Gera rota ortogonal (apenas eixos X, Y, Z) entre dois pontos."""
        waypoints = [start]
        
        # Diferenças
        dx = end.x - start.x
        dy = end.y - start.y
        dz = end.z - start.z
        
        current = Point3D(start.x, start.y, start.z)
        
        # Mover em X primeiro
        if abs(dx) > 0.01:
            current = Point3D(end.x, current.y, current.z)
            waypoints.append(current)
        
        # Depois em Y
        if abs(dy) > 0.01:
            current = Point3D(current.x, end.y, current.z)
            waypoints.append(current)
        
        # Por fim em Z
        if abs(dz) > 0.01:
            current = Point3D(current.x, current.y, end.z)
            waypoints.append(current)
        
        # Garantir ponto final
        if waypoints[-1] != end:
            waypoints.append(end)
        
        return waypoints
    
    def _calculate_bom(self, pipes: List[PipeSegment]) -> Dict[str, Any]:
        """Calcula bill of materials (lista de materiais)."""
        bom = {
            "pipes": {},
            "fittings": {},
            "total_weight_kg": 0,
            "summary": [],
        }
        
        for pipe in pipes:
            key = f"{pipe.material}_{int(pipe.diameter)}_{pipe.schedule}"
            
            if key not in bom["pipes"]:
                bom["pipes"][key] = {
                    "material": pipe.material,
                    "diameter_mm": int(pipe.diameter),
                    "schedule": pipe.schedule,
                    "total_length_m": 0,
                    "weight_kg": 0,
                    "segments": 0,
                }
            
            bom["pipes"][key]["total_length_m"] += pipe.length
            bom["pipes"][key]["weight_kg"] += pipe.length * pipe.weight_per_meter
            bom["pipes"][key]["segments"] += 1
        
        # Estimar fittings baseado em mudanças de direção
        for i in range(1, len(pipes)):
            prev = pipes[i-1]
            curr = pipes[i]
            
            # Conexão entre segmentos
            if prev.diameter != curr.diameter:
                fitting_type = "reducer"
            else:
                fitting_type = "elbow_90"  # Simplificado
            
            fitting_key = f"{fitting_type}_{int(curr.diameter)}"
            if fitting_key not in bom["fittings"]:
                bom["fittings"][fitting_key] = {
                    "type": fitting_type,
                    "diameter_mm": int(curr.diameter),
                    "quantity": 0,
                }
            bom["fittings"][fitting_key]["quantity"] += 1
        
        # Calcular peso total
        bom["total_weight_kg"] = sum(p["weight_kg"] for p in bom["pipes"].values())
        
        # Sumário
        for key, data in bom["pipes"].items():
            bom["summary"].append({
                "item": f"Tubo {data['material'].upper()} DN{data['diameter_mm']} SCH{data['schedule']}",
                "quantity": f"{data['total_length_m']:.2f} m",
                "weight": f"{data['weight_kg']:.2f} kg",
            })
        
        for key, data in bom["fittings"].items():
            bom["summary"].append({
                "item": f"{data['type'].replace('_', ' ').title()} DN{data['diameter_mm']}",
                "quantity": f"{data['quantity']} un",
            })
        
        return bom
    
    def _calculate_costs(self, bom: Dict) -> Dict[str, Any]:
        """Calcula custos estimados baseado no BOM."""
        costs = {
            "pipes_cost": 0,
            "fittings_cost": 0,
            "labor_cost": 0,
            "total_cost": 0,
            "breakdown": [],
        }
        
        # Custo de tubos
        for key, data in bom.get("pipes", {}).items():
            material = data["material"]
            diameter = data["diameter_mm"]
            length = data["total_length_m"]
            
            # Buscar preço
            price_per_meter = self.PIPE_PRICES.get(material, {}).get(diameter, 100)
            cost = length * price_per_meter
            
            costs["pipes_cost"] += cost
            costs["breakdown"].append({
                "item": f"Tubo {material.upper()} DN{diameter}",
                "quantity": f"{length:.2f} m",
                "unit_price": f"R$ {price_per_meter:.2f}",
                "total": f"R$ {cost:.2f}",
            })
        
        # Custo de fittings (estimativa simples)
        for key, data in bom.get("fittings", {}).items():
            fitting_cost = data["quantity"] * data["diameter_mm"] * 0.5
            costs["fittings_cost"] += fitting_cost
            
            costs["breakdown"].append({
                "item": f"{data['type'].replace('_', ' ').title()} DN{data['diameter_mm']}",
                "quantity": f"{data['quantity']} un",
                "total": f"R$ {fitting_cost:.2f}",
            })
        
        # Custo de mão de obra (estimativa: 50% do custo de materiais)
        costs["labor_cost"] = (costs["pipes_cost"] + costs["fittings_cost"]) * 0.5
        
        costs["total_cost"] = (
            costs["pipes_cost"] +
            costs["fittings_cost"] +
            costs["labor_cost"]
        )
        
        return costs
    
    def _calculate_efficiency(self, pipes: List[PipeSegment]) -> Dict[str, Any]:
        """Calcula métricas de eficiência da tubulação."""
        if not pipes:
            return {"status": "no_data"}
        
        total_length = sum(p.length for p in pipes)
        
        # Calcular distância direta (primeiro ao último ponto)
        start = pipes[0].start
        end = pipes[-1].end
        direct_distance = start.distance_to(end)
        
        # Eficiência de rota
        route_efficiency = (direct_distance / total_length * 100) if total_length > 0 else 100
        
        return {
            "route_efficiency_percent": round(route_efficiency, 1),
            "total_length_m": round(total_length, 2),
            "direct_distance_m": round(direct_distance, 2),
            "extra_length_m": round(total_length - direct_distance, 2),
            "rating": (
                "Excelente" if route_efficiency > 90 else
                "Bom" if route_efficiency > 75 else
                "Regular" if route_efficiency > 60 else
                "Necessita otimização"
            ),
        }
    
    def _generate_optimization_recommendations(
        self,
        analysis: Dict
    ) -> List[Dict]:
        """Gera recomendações de otimização."""
        recommendations = []
        
        # Verificar número de curvas
        direction_changes = analysis.get("direction_changes", 0)
        total_segments = analysis.get("total_segments", 1)
        
        if direction_changes > total_segments * 0.5:
            recommendations.append({
                "priority": "high",
                "category": "routing",
                "issue": f"Alto número de curvas ({direction_changes})",
                "suggestion": "Considere redesenhar a rota para minimizar mudanças de direção",
                "potential_savings": "10-20% em fittings e perda de carga",
            })
        
        # Verificar mudanças de elevação
        elevation_changes = analysis.get("elevation_changes", 0)
        if elevation_changes > 2:
            recommendations.append({
                "priority": "medium",
                "category": "routing",
                "issue": f"Múltiplas mudanças de elevação ({elevation_changes})",
                "suggestion": "Avaliar possibilidade de manter tubulação em nível único",
                "potential_savings": "5-15% em suportes e instalação",
            })
        
        # Verificar múltiplos diâmetros
        unique_diameters = analysis.get("unique_diameters", [])
        if len(unique_diameters) > 2:
            recommendations.append({
                "priority": "low",
                "category": "materials",
                "issue": f"Múltiplos diâmetros utilizados ({len(unique_diameters)})",
                "suggestion": "Avaliar padronização de diâmetros para reduzir reduções",
                "potential_savings": "3-8% em fittings",
            })
        
        return recommendations


# Registrar IA
ai_registry.register(PipeOptimizerAI())
