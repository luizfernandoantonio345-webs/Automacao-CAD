# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    DASHBOARD METRICS - KPIs e Métricas                        ║
║                                                                               ║
║  Sistema de dashboard com métricas em tempo real para gestão da produção.     ║
║  OEE, eficiência, custos, produtividade e indicadores de manutenção.          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class OEEMetrics:
    """
    Overall Equipment Effectiveness (OEE).
    
    OEE = Disponibilidade × Performance × Qualidade
    
    Referência:
    - World Class OEE: > 85%
    - Típico Plasma CNC: 60-70%
    """
    availability: float = 0.0  # % tempo disponível vs tempo planejado
    performance: float = 0.0   # % velocidade real vs velocidade ideal
    quality: float = 0.0       # % peças boas vs total produzido
    oee: float = 0.0           # OEE total
    
    # Tempos base
    planned_time_hours: float = 0.0
    actual_run_time_hours: float = 0.0
    downtime_hours: float = 0.0
    
    # Contagens
    total_pieces: int = 0
    good_pieces: int = 0
    defect_pieces: int = 0
    
    def calculate(self):
        """Calcula OEE a partir dos componentes."""
        self.availability = (self.actual_run_time_hours / self.planned_time_hours * 100) if self.planned_time_hours > 0 else 0
        self.quality = (self.good_pieces / self.total_pieces * 100) if self.total_pieces > 0 else 100
        self.oee = (self.availability * self.performance * self.quality) / 10000
        return self


@dataclass  
class ProductivityMetrics:
    """Métricas de produtividade."""
    pieces_per_hour: float = 0.0
    meters_cut_per_hour: float = 0.0
    pierces_per_hour: float = 0.0
    kg_processed_per_hour: float = 0.0
    
    total_pieces_today: int = 0
    total_meters_today: float = 0.0
    total_pierces_today: int = 0
    
    jobs_completed_today: int = 0
    jobs_in_progress: int = 0
    jobs_pending: int = 0


@dataclass
class CostMetrics:
    """Métricas de custos."""
    total_cost_today: float = 0.0
    cost_per_hour: float = 0.0
    cost_per_meter: float = 0.0
    cost_per_piece: float = 0.0
    
    material_cost: float = 0.0
    consumables_cost: float = 0.0
    labor_cost: float = 0.0
    machine_cost: float = 0.0
    
    # Breakdown percentual
    material_percent: float = 0.0
    consumables_percent: float = 0.0
    labor_percent: float = 0.0
    machine_percent: float = 0.0


@dataclass
class ConsumablesMetrics:
    """Métricas de consumíveis."""
    electrode_life_percent: float = 100.0
    nozzle_life_percent: float = 100.0
    shield_life_percent: float = 100.0
    
    electrode_pierces_remaining: int = 0
    nozzle_pierces_remaining: int = 0
    shield_arc_minutes_remaining: float = 0.0
    
    days_until_electrode_change: float = 0.0
    days_until_nozzle_change: float = 0.0
    
    estimated_consumables_cost_today: float = 0.0
    estimated_consumables_cost_week: float = 0.0


@dataclass
class MaterialMetrics:
    """Métricas de materiais."""
    total_kg_processed: float = 0.0
    waste_kg: float = 0.0
    waste_percent: float = 0.0
    nesting_efficiency: float = 0.0
    
    # Por tipo de material
    materials_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class QualityMetrics:
    """Métricas de qualidade."""
    defect_rate: float = 0.0
    rework_rate: float = 0.0
    first_pass_yield: float = 100.0
    
    # Tipos de defeito
    kerf_deviation_count: int = 0
    dross_count: int = 0
    incomplete_cut_count: int = 0
    dimension_error_count: int = 0


@dataclass
class MachineMetrics:
    """Métricas da máquina."""
    status: str = "idle"  # idle, running, paused, error, maintenance
    uptime_percent: float = 0.0
    arc_on_time_hours: float = 0.0
    arc_on_percent: float = 0.0
    
    current_speed_percent: float = 0.0
    current_amperage: int = 0
    current_voltage: float = 0.0
    
    error_count_today: int = 0
    warning_count_today: int = 0
    
    # Manutenção
    next_maintenance_hours: float = 0.0
    maintenance_overdue: bool = False


class DashboardMetricsManager:
    """
    Gerenciador de métricas do dashboard.
    
    Coleta dados de jobs, máquinas e consumíveis para gerar KPIs.
    """
    
    def __init__(self, data_path: str = "data/metrics"):
        self.data_path = data_path
        self._ensure_storage()
        
        # Configurações de referência
        self.config = {
            "shift_hours": 8,  # Horas por turno
            "target_oee": 75,  # Meta OEE %
            "target_pieces_per_hour": 20,
            "machine_cost_per_hour": 50,  # R$/hora
            "labor_cost_per_hour": 30,  # R$/hora
            
            # Vida dos consumíveis
            "electrode_max_pierces": 500,
            "nozzle_max_pierces": 300,
            "shield_max_arc_minutes": 120,
            
            # Custos consumíveis
            "electrode_cost": 45,
            "nozzle_cost": 35,
            "shield_cost": 25
        }
    
    def _ensure_storage(self):
        """Garante que o diretório existe."""
        try:
            os.makedirs(self.data_path, exist_ok=True)
        except OSError:
            pass
    
    def get_full_dashboard(self) -> Dict[str, Any]:
        """
        Retorna dashboard completo com todas as métricas.
        
        Returns:
            Dashboard com OEE, produtividade, custos, qualidade, etc.
        """
        now = datetime.now()
        
        # Coletar dados base
        oee = self.calculate_oee()
        productivity = self.get_productivity_metrics()
        costs = self.get_cost_metrics()
        consumables = self.get_consumables_metrics()
        quality = self.get_quality_metrics()
        machine = self.get_machine_status()
        
        return {
            "timestamp": now.isoformat(),
            "period": "today",
            "shift": self._get_current_shift(),
            
            "oee": asdict(oee),
            "productivity": asdict(productivity),
            "costs": asdict(costs),
            "consumables": asdict(consumables),
            "quality": asdict(quality),
            "machine": asdict(machine),
            
            "alerts": self._get_alerts(oee, consumables, machine),
            "trends": self._get_trends(),
            
            "targets": {
                "oee": self.config["target_oee"],
                "pieces_per_hour": self.config["target_pieces_per_hour"],
                "max_defect_rate": 2.0
            }
        }
    
    def _get_current_shift(self) -> Dict[str, Any]:
        """Retorna informações do turno atual."""
        now = datetime.now()
        hour = now.hour
        
        if 6 <= hour < 14:
            shift = "morning"
            start = now.replace(hour=6, minute=0, second=0)
            end = now.replace(hour=14, minute=0, second=0)
        elif 14 <= hour < 22:
            shift = "afternoon"
            start = now.replace(hour=14, minute=0, second=0)
            end = now.replace(hour=22, minute=0, second=0)
        else:
            shift = "night"
            if hour >= 22:
                start = now.replace(hour=22, minute=0, second=0)
                end = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0)
            else:
                start = (now - timedelta(days=1)).replace(hour=22, minute=0, second=0)
                end = now.replace(hour=6, minute=0, second=0)
        
        elapsed = (now - start).total_seconds() / 3600
        remaining = (end - now).total_seconds() / 3600
        
        return {
            "name": shift,
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
            "elapsed_hours": round(elapsed, 1),
            "remaining_hours": round(max(0, remaining), 1),
            "progress_percent": round(min(100, elapsed / 8 * 100), 1)
        }
    
    def calculate_oee(self) -> OEEMetrics:
        """Calcula OEE para o turno atual."""
        oee = OEEMetrics()
        
        # Valores simulados para demonstração
        # Em produção, buscar dados reais dos jobs
        shift = self._get_current_shift()
        elapsed_hours = shift["elapsed_hours"]
        
        oee.planned_time_hours = elapsed_hours
        oee.actual_run_time_hours = elapsed_hours * 0.85  # 85% uptime simulado
        oee.downtime_hours = elapsed_hours - oee.actual_run_time_hours
        
        oee.availability = 85.0  # Simulado
        oee.performance = 78.0   # Simulado
        oee.quality = 97.5       # Simulado
        
        oee.total_pieces = int(elapsed_hours * 15)  # 15 peças/hora média
        oee.good_pieces = int(oee.total_pieces * 0.975)
        oee.defect_pieces = oee.total_pieces - oee.good_pieces
        
        oee.calculate()
        
        return oee
    
    def get_productivity_metrics(self) -> ProductivityMetrics:
        """Retorna métricas de produtividade."""
        prod = ProductivityMetrics()
        
        shift = self._get_current_shift()
        elapsed = max(0.1, shift["elapsed_hours"])
        
        # Valores simulados
        prod.total_pieces_today = int(elapsed * 15)
        prod.total_meters_today = elapsed * 120  # 120m/hora média
        prod.total_pierces_today = prod.total_pieces_today * 4  # 4 furos/peça média
        
        prod.pieces_per_hour = prod.total_pieces_today / elapsed
        prod.meters_cut_per_hour = prod.total_meters_today / elapsed
        prod.pierces_per_hour = prod.total_pierces_today / elapsed
        prod.kg_processed_per_hour = elapsed * 25  # 25kg/hora simulado
        
        prod.jobs_completed_today = int(elapsed / 2)  # 1 job a cada 2 horas
        prod.jobs_in_progress = 1
        prod.jobs_pending = 3
        
        return prod
    
    def get_cost_metrics(self) -> CostMetrics:
        """Retorna métricas de custos."""
        costs = CostMetrics()
        
        shift = self._get_current_shift()
        hours = shift["elapsed_hours"]
        
        # Custos simulados baseados em tempo
        costs.labor_cost = hours * self.config["labor_cost_per_hour"]
        costs.machine_cost = hours * self.config["machine_cost_per_hour"]
        costs.consumables_cost = hours * 15  # R$15/hora média consumíveis
        costs.material_cost = hours * 80  # R$80/hora material
        
        costs.total_cost_today = (
            costs.labor_cost + 
            costs.machine_cost + 
            costs.consumables_cost + 
            costs.material_cost
        )
        
        costs.cost_per_hour = costs.total_cost_today / max(0.1, hours)
        
        productivity = self.get_productivity_metrics()
        costs.cost_per_meter = costs.total_cost_today / max(1, productivity.total_meters_today)
        costs.cost_per_piece = costs.total_cost_today / max(1, productivity.total_pieces_today)
        
        # Breakdown percentual
        total = max(1, costs.total_cost_today)
        costs.material_percent = costs.material_cost / total * 100
        costs.consumables_percent = costs.consumables_cost / total * 100
        costs.labor_percent = costs.labor_cost / total * 100
        costs.machine_percent = costs.machine_cost / total * 100
        
        return costs
    
    def get_consumables_metrics(self) -> ConsumablesMetrics:
        """Retorna métricas de consumíveis."""
        cons = ConsumablesMetrics()
        
        # Simular uso baseado no turno
        shift = self._get_current_shift()
        hours = shift["elapsed_hours"]
        pierces_today = int(hours * 60)  # 60 furos/hora
        arc_minutes = hours * 45  # 45 min arco/hora
        
        # Calcular vida restante
        cons.electrode_pierces_remaining = self.config["electrode_max_pierces"] - (pierces_today % self.config["electrode_max_pierces"])
        cons.nozzle_pierces_remaining = self.config["nozzle_max_pierces"] - (pierces_today % self.config["nozzle_max_pierces"])
        cons.shield_arc_minutes_remaining = self.config["shield_max_arc_minutes"] - (arc_minutes % self.config["shield_max_arc_minutes"])
        
        cons.electrode_life_percent = cons.electrode_pierces_remaining / self.config["electrode_max_pierces"] * 100
        cons.nozzle_life_percent = cons.nozzle_pierces_remaining / self.config["nozzle_max_pierces"] * 100
        cons.shield_life_percent = cons.shield_arc_minutes_remaining / self.config["shield_max_arc_minutes"] * 100
        
        # Dias até troca
        pierces_per_day = 60 * 8  # 8 horas
        cons.days_until_electrode_change = cons.electrode_pierces_remaining / pierces_per_day
        cons.days_until_nozzle_change = cons.nozzle_pierces_remaining / pierces_per_day
        
        # Custos estimados
        trocas_electrode = math.ceil(pierces_today / self.config["electrode_max_pierces"])
        trocas_nozzle = math.ceil(pierces_today / self.config["nozzle_max_pierces"])
        trocas_shield = math.ceil(arc_minutes / self.config["shield_max_arc_minutes"])
        
        cons.estimated_consumables_cost_today = (
            trocas_electrode * self.config["electrode_cost"] +
            trocas_nozzle * self.config["nozzle_cost"] +
            trocas_shield * self.config["shield_cost"]
        )
        cons.estimated_consumables_cost_week = cons.estimated_consumables_cost_today * 5
        
        return cons
    
    def get_quality_metrics(self) -> QualityMetrics:
        """Retorna métricas de qualidade."""
        quality = QualityMetrics()
        
        # Valores simulados com boa qualidade
        quality.first_pass_yield = 97.5
        quality.defect_rate = 2.5
        quality.rework_rate = 0.5
        
        # Contagem de defeitos por tipo
        shift = self._get_current_shift()
        hours = shift["elapsed_hours"]
        total_pieces = int(hours * 15)
        defects = int(total_pieces * 0.025)
        
        quality.kerf_deviation_count = int(defects * 0.3)
        quality.dross_count = int(defects * 0.4)
        quality.incomplete_cut_count = int(defects * 0.2)
        quality.dimension_error_count = int(defects * 0.1)
        
        return quality
    
    def get_machine_status(self) -> MachineMetrics:
        """Retorna status da máquina."""
        machine = MachineMetrics()
        
        # Simular máquina em operação
        machine.status = "running"
        machine.uptime_percent = 85.0
        
        shift = self._get_current_shift()
        hours = shift["elapsed_hours"]
        
        machine.arc_on_time_hours = hours * 0.75  # 75% arc-on
        machine.arc_on_percent = 75.0
        
        machine.current_speed_percent = 82
        machine.current_amperage = 45
        machine.current_voltage = 125.5
        
        machine.error_count_today = 1
        machine.warning_count_today = 3
        
        machine.next_maintenance_hours = 47.5
        machine.maintenance_overdue = False
        
        return machine
    
    def _get_alerts(self, oee: OEEMetrics, consumables: ConsumablesMetrics, machine: MachineMetrics) -> List[Dict[str, Any]]:
        """Gera alertas baseados nas métricas."""
        alerts = []
        
        # OEE abaixo do target
        if oee.oee < self.config["target_oee"] * 0.8:
            alerts.append({
                "level": "warning",
                "type": "oee",
                "message": f"OEE em {oee.oee:.1f}% - abaixo da meta ({self.config['target_oee']}%)",
                "action": "Verificar causas de paradas"
            })
        
        # Consumíveis
        if consumables.electrode_life_percent < 20:
            alerts.append({
                "level": "warning" if consumables.electrode_life_percent > 10 else "critical",
                "type": "consumable",
                "message": f"Eletrodo em {consumables.electrode_life_percent:.0f}%",
                "action": "Preparar troca de eletrodo"
            })
        
        if consumables.nozzle_life_percent < 20:
            alerts.append({
                "level": "warning" if consumables.nozzle_life_percent > 10 else "critical",
                "type": "consumable",
                "message": f"Bocal em {consumables.nozzle_life_percent:.0f}%",
                "action": "Preparar troca de bocal"
            })
        
        # Manutenção
        if machine.next_maintenance_hours < 8:
            alerts.append({
                "level": "info",
                "type": "maintenance",
                "message": f"Manutenção em {machine.next_maintenance_hours:.0f}h",
                "action": "Agendar manutenção preventiva"
            })
        
        if machine.maintenance_overdue:
            alerts.append({
                "level": "critical",
                "type": "maintenance",
                "message": "Manutenção atrasada!",
                "action": "Realizar manutenção imediatamente"
            })
        
        # Erros
        if machine.error_count_today > 5:
            alerts.append({
                "level": "warning",
                "type": "errors",
                "message": f"{machine.error_count_today} erros hoje",
                "action": "Verificar logs de erro"
            })
        
        return alerts
    
    def _get_trends(self) -> Dict[str, Any]:
        """Retorna tendências de métricas."""
        # Tendências simuladas (em produção, calcular de histórico)
        return {
            "oee": {
                "direction": "up",
                "change_percent": 2.5,
                "period": "vs_yesterday"
            },
            "productivity": {
                "direction": "stable",
                "change_percent": 0.3,
                "period": "vs_yesterday"
            },
            "quality": {
                "direction": "up",
                "change_percent": 0.5,
                "period": "vs_yesterday"
            },
            "cost_per_piece": {
                "direction": "down",
                "change_percent": -1.2,
                "period": "vs_yesterday"
            }
        }
    
    def get_weekly_summary(self) -> Dict[str, Any]:
        """Retorna resumo semanal."""
        # Dados simulados para a semana
        days = ["Seg", "Ter", "Qua", "Qui", "Sex"]
        
        return {
            "period": "Esta semana",
            "days": days,
            "oee_daily": [72.5, 75.3, 68.9, 78.2, 74.1],
            "pieces_daily": [120, 135, 98, 142, 128],
            "cost_daily": [1450, 1520, 1380, 1680, 1490],
            
            "totals": {
                "pieces": 623,
                "meters_cut": 4520,
                "hours_worked": 40,
                "cost": 7520
            },
            
            "averages": {
                "oee": 73.8,
                "pieces_per_day": 124.6,
                "cost_per_piece": 12.07
            },
            
            "best_day": "Qui",
            "best_oee": 78.2
        }
    
    def get_monthly_summary(self) -> Dict[str, Any]:
        """Retorna resumo mensal."""
        return {
            "period": "Este mês",
            "weeks": 4,
            
            "totals": {
                "pieces": 2480,
                "meters_cut": 18500,
                "hours_worked": 160,
                "cost": 29800
            },
            
            "averages": {
                "oee": 74.2,
                "pieces_per_day": 124,
                "cost_per_piece": 12.02
            },
            
            "consumables_used": {
                "electrodes": 18,
                "nozzles": 25,
                "shields": 12,
                "total_cost": 2170
            },
            
            "material_processed": {
                "mild_steel_kg": 3200,
                "stainless_kg": 450,
                "aluminum_kg": 180,
                "total_kg": 3830
            },
            
            "comparison_last_month": {
                "oee_change": "+2.3%",
                "production_change": "+8%",
                "cost_change": "-3%"
            }
        }


# Instância global
_metrics_manager: Optional[DashboardMetricsManager] = None


def get_metrics_manager() -> DashboardMetricsManager:
    """Retorna instância do gerenciador de métricas."""
    global _metrics_manager
    if _metrics_manager is None:
        _metrics_manager = DashboardMetricsManager()
    return _metrics_manager


# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS FastAPI
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/")
async def get_full_dashboard():
    """
    Dashboard completo com todas as métricas.
    
    Inclui: OEE, produtividade, custos, consumíveis, qualidade, alertas.
    """
    manager = get_metrics_manager()
    return {
        "success": True,
        "dashboard": manager.get_full_dashboard()
    }


@router.get("/oee")
async def get_oee():
    """Retorna métricas OEE atuais."""
    manager = get_metrics_manager()
    oee = manager.calculate_oee()
    
    return {
        "success": True,
        "oee": asdict(oee),
        "target": manager.config["target_oee"],
        "status": "ok" if oee.oee >= manager.config["target_oee"] else "below_target"
    }


@router.get("/productivity")
async def get_productivity():
    """Retorna métricas de produtividade."""
    manager = get_metrics_manager()
    prod = manager.get_productivity_metrics()
    
    return {
        "success": True,
        "productivity": asdict(prod),
        "target_pieces_per_hour": manager.config["target_pieces_per_hour"]
    }


@router.get("/costs")
async def get_costs():
    """Retorna métricas de custos."""
    manager = get_metrics_manager()
    costs = manager.get_cost_metrics()
    
    return {
        "success": True,
        "costs": asdict(costs)
    }


@router.get("/consumables")
async def get_consumables_status():
    """Retorna status dos consumíveis."""
    manager = get_metrics_manager()
    cons = manager.get_consumables_metrics()
    
    return {
        "success": True,
        "consumables": asdict(cons),
        "config": {
            "electrode_max_pierces": manager.config["electrode_max_pierces"],
            "nozzle_max_pierces": manager.config["nozzle_max_pierces"],
            "shield_max_arc_minutes": manager.config["shield_max_arc_minutes"]
        }
    }


@router.get("/quality")
async def get_quality():
    """Retorna métricas de qualidade."""
    manager = get_metrics_manager()
    quality = manager.get_quality_metrics()
    
    return {
        "success": True,
        "quality": asdict(quality)
    }


@router.get("/machine")
async def get_machine_status():
    """Retorna status da máquina."""
    manager = get_metrics_manager()
    machine = manager.get_machine_status()
    
    return {
        "success": True,
        "machine": asdict(machine)
    }


@router.get("/summary/weekly")
async def get_weekly_summary():
    """Retorna resumo semanal."""
    manager = get_metrics_manager()
    return {
        "success": True,
        "summary": manager.get_weekly_summary()
    }


@router.get("/summary/monthly")
async def get_monthly_summary():
    """Retorna resumo mensal."""
    manager = get_metrics_manager()
    return {
        "success": True,
        "summary": manager.get_monthly_summary()
    }


@router.get("/alerts")
async def get_alerts():
    """Retorna alertas ativos."""
    manager = get_metrics_manager()
    dashboard = manager.get_full_dashboard()
    
    return {
        "success": True,
        "alerts": dashboard["alerts"],
        "count": len(dashboard["alerts"])
    }


@router.get("/kpis")
async def get_kpis():
    """
    Retorna KPIs principais em formato resumido.
    
    Ideal para widgets e displays rápidos.
    """
    manager = get_metrics_manager()
    
    oee = manager.calculate_oee()
    prod = manager.get_productivity_metrics()
    costs = manager.get_cost_metrics()
    cons = manager.get_consumables_metrics()
    machine = manager.get_machine_status()
    
    return {
        "success": True,
        "kpis": {
            "oee": {
                "value": round(oee.oee, 1),
                "unit": "%",
                "target": manager.config["target_oee"],
                "status": "green" if oee.oee >= manager.config["target_oee"] else "yellow" if oee.oee >= manager.config["target_oee"] * 0.8 else "red"
            },
            "pieces_today": {
                "value": prod.total_pieces_today,
                "unit": "pcs",
                "rate": f"{prod.pieces_per_hour:.1f}/hr"
            },
            "meters_cut": {
                "value": round(prod.total_meters_today, 1),
                "unit": "m",
                "rate": f"{prod.meters_cut_per_hour:.1f}m/hr"
            },
            "cost_per_piece": {
                "value": round(costs.cost_per_piece, 2),
                "unit": "R$"
            },
            "machine_status": {
                "status": machine.status,
                "uptime": f"{machine.uptime_percent:.0f}%",
                "arc_on": f"{machine.arc_on_percent:.0f}%"
            },
            "consumables": {
                "electrode": f"{cons.electrode_life_percent:.0f}%",
                "nozzle": f"{cons.nozzle_life_percent:.0f}%",
                "alert": cons.electrode_life_percent < 20 or cons.nozzle_life_percent < 20
            }
        }
    }
