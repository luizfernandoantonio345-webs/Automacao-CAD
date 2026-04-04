"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE SLA MONITOR
  Monitoramento de Service Level Agreements
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class SLAMetric(str, Enum):
    """Métricas de SLA monitoradas."""
    UPTIME = "uptime"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    AI_LATENCY = "ai_latency"
    API_LATENCY = "api_latency"
    QUEUE_TIME = "queue_time"


class SLAStatus(str, Enum):
    """Status do SLA."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    VIOLATED = "violated"


@dataclass
class SLATarget:
    """Alvo de SLA."""
    metric: SLAMetric
    target_value: float
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str
    
    def evaluate(self, current_value: float) -> SLAStatus:
        """Avalia o status atual contra os thresholds."""
        if self.metric in [SLAMetric.UPTIME, SLAMetric.THROUGHPUT]:
            # Quanto maior, melhor
            if current_value >= self.target_value:
                return SLAStatus.HEALTHY
            elif current_value >= self.warning_threshold:
                return SLAStatus.WARNING
            elif current_value >= self.critical_threshold:
                return SLAStatus.CRITICAL
            else:
                return SLAStatus.VIOLATED
        else:
            # Quanto menor, melhor (latência, erro)
            if current_value <= self.target_value:
                return SLAStatus.HEALTHY
            elif current_value <= self.warning_threshold:
                return SLAStatus.WARNING
            elif current_value <= self.critical_threshold:
                return SLAStatus.CRITICAL
            else:
                return SLAStatus.VIOLATED


@dataclass
class SLAMeasurement:
    """Medição de SLA."""
    metric: SLAMetric
    value: float
    timestamp: str
    status: SLAStatus
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLAReport:
    """Relatório de SLA."""
    period_start: str
    period_end: str
    measurements: Dict[SLAMetric, List[SLAMeasurement]]
    summaries: Dict[SLAMetric, Dict[str, float]]
    violations: List[Dict[str, Any]]
    overall_compliance: float


# SLAs padrão Enterprise
DEFAULT_SLAS = {
    SLAMetric.UPTIME: SLATarget(
        metric=SLAMetric.UPTIME,
        target_value=99.9,
        warning_threshold=99.5,
        critical_threshold=99.0,
        unit="%",
        description="Disponibilidade do sistema",
    ),
    SLAMetric.RESPONSE_TIME: SLATarget(
        metric=SLAMetric.RESPONSE_TIME,
        target_value=200,
        warning_threshold=500,
        critical_threshold=1000,
        unit="ms",
        description="Tempo de resposta da API",
    ),
    SLAMetric.ERROR_RATE: SLATarget(
        metric=SLAMetric.ERROR_RATE,
        target_value=0.1,
        warning_threshold=1.0,
        critical_threshold=5.0,
        unit="%",
        description="Taxa de erros",
    ),
    SLAMetric.AI_LATENCY: SLATarget(
        metric=SLAMetric.AI_LATENCY,
        target_value=500,
        warning_threshold=1000,
        critical_threshold=2000,
        unit="ms",
        description="Latência das IAs",
    ),
    SLAMetric.API_LATENCY: SLATarget(
        metric=SLAMetric.API_LATENCY,
        target_value=100,
        warning_threshold=300,
        critical_threshold=500,
        unit="ms",
        description="Latência da API REST",
    ),
    SLAMetric.THROUGHPUT: SLATarget(
        metric=SLAMetric.THROUGHPUT,
        target_value=1000,
        warning_threshold=500,
        critical_threshold=100,
        unit="req/min",
        description="Throughput de requisições",
    ),
}


class SLAMonitor:
    """Monitor de SLAs."""
    
    _instance: Optional['SLAMonitor'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.targets: Dict[SLAMetric, SLATarget] = dict(DEFAULT_SLAS)
        self.measurements: Dict[SLAMetric, List[SLAMeasurement]] = defaultdict(list)
        self.violations: List[Dict[str, Any]] = []
        self.max_measurements = 10000
        self._seed_demo_data()
        logger.info("SLAMonitor initialized")
    
    def _seed_demo_data(self):
        """Adiciona dados de demonstração."""
        import random
        now = datetime.now(UTC)
        
        # Gerar medições das últimas 24 horas
        for hours_ago in range(24, -1, -1):
            timestamp = (now - timedelta(hours=hours_ago)).isoformat()
            
            # Uptime (geralmente alto)
            uptime = random.uniform(99.5, 100.0)
            self.record(SLAMetric.UPTIME, uptime, timestamp)
            
            # Response time (varia)
            response_time = random.uniform(80, 300)
            self.record(SLAMetric.RESPONSE_TIME, response_time, timestamp)
            
            # Error rate (geralmente baixo)
            error_rate = random.uniform(0, 1.5)
            self.record(SLAMetric.ERROR_RATE, error_rate, timestamp)
            
            # AI latency
            ai_latency = random.uniform(200, 800)
            self.record(SLAMetric.AI_LATENCY, ai_latency, timestamp)
            
            # Throughput
            throughput = random.uniform(500, 1500)
            self.record(SLAMetric.THROUGHPUT, throughput, timestamp)
    
    def record(
        self,
        metric: SLAMetric,
        value: float,
        timestamp: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SLAMeasurement:
        """Registra uma medição."""
        if timestamp is None:
            timestamp = datetime.now(UTC).isoformat()
        
        target = self.targets.get(metric)
        status = target.evaluate(value) if target else SLAStatus.HEALTHY
        
        measurement = SLAMeasurement(
            metric=metric,
            value=value,
            timestamp=timestamp,
            status=status,
            details=details or {},
        )
        
        self.measurements[metric].append(measurement)
        
        # Rotação
        if len(self.measurements[metric]) > self.max_measurements:
            self.measurements[metric] = self.measurements[metric][-self.max_measurements:]
        
        # Registrar violação se necessário
        if status == SLAStatus.VIOLATED:
            self.violations.append({
                "metric": metric.value,
                "value": value,
                "target": target.target_value if target else None,
                "timestamp": timestamp,
            })
        
        return measurement
    
    def get_current_status(self) -> Dict[SLAMetric, Dict[str, Any]]:
        """Retorna status atual de todos os SLAs."""
        status = {}
        
        for metric, target in self.targets.items():
            measurements = self.measurements.get(metric, [])
            
            if not measurements:
                status[metric] = {
                    "current_value": None,
                    "status": SLAStatus.HEALTHY.value,
                    "target": target.target_value,
                    "unit": target.unit,
                }
                continue
            
            # Última medição
            latest = measurements[-1]
            
            # Média das últimas medições
            recent_values = [m.value for m in measurements[-10:]]
            avg_value = statistics.mean(recent_values) if recent_values else 0
            
            status[metric] = {
                "current_value": round(latest.value, 2),
                "average_value": round(avg_value, 2),
                "status": latest.status.value,
                "target": target.target_value,
                "warning_threshold": target.warning_threshold,
                "critical_threshold": target.critical_threshold,
                "unit": target.unit,
                "description": target.description,
                "last_updated": latest.timestamp,
            }
        
        return status
    
    def get_metric_history(
        self,
        metric: SLAMetric,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Retorna histórico de uma métrica."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        measurements = self.measurements.get(metric, [])
        
        history = []
        for m in measurements:
            try:
                m_time = datetime.fromisoformat(m.timestamp)
                if m_time >= cutoff:
                    history.append({
                        "value": m.value,
                        "status": m.status.value,
                        "timestamp": m.timestamp,
                    })
            except:
                continue
        
        return history
    
    def generate_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SLAReport:
        """Gera relatório de SLA."""
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        period_measurements: Dict[SLAMetric, List[SLAMeasurement]] = {}
        summaries: Dict[SLAMetric, Dict[str, float]] = {}
        period_violations: List[Dict[str, Any]] = []
        
        for metric, measurements in self.measurements.items():
            filtered = []
            for m in measurements:
                try:
                    m_time = datetime.fromisoformat(m.timestamp)
                    if start_date <= m_time <= end_date:
                        filtered.append(m)
                        if m.status == SLAStatus.VIOLATED:
                            period_violations.append({
                                "metric": metric.value,
                                "value": m.value,
                                "timestamp": m.timestamp,
                            })
                except:
                    continue
            
            period_measurements[metric] = filtered
            
            if filtered:
                values = [m.value for m in filtered]
                summaries[metric] = {
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "avg": round(statistics.mean(values), 2),
                    "median": round(statistics.median(values), 2),
                    "count": len(values),
                }
            else:
                summaries[metric] = {"min": 0, "max": 0, "avg": 0, "median": 0, "count": 0}
        
        # Calcular compliance geral
        total_measurements = sum(len(m) for m in period_measurements.values())
        total_compliant = sum(
            sum(1 for m in measures if m.status in [SLAStatus.HEALTHY, SLAStatus.WARNING])
            for measures in period_measurements.values()
        )
        overall_compliance = (total_compliant / max(total_measurements, 1)) * 100
        
        return SLAReport(
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            measurements=period_measurements,
            summaries=summaries,
            violations=period_violations,
            overall_compliance=round(overall_compliance, 2),
        )
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Retorna dados para dashboard."""
        current_status = self.get_current_status()
        
        # Contar status
        healthy_count = sum(1 for s in current_status.values() if s["status"] == "healthy")
        warning_count = sum(1 for s in current_status.values() if s["status"] == "warning")
        critical_count = sum(1 for s in current_status.values() if s["status"] == "critical")
        violated_count = sum(1 for s in current_status.values() if s["status"] == "violated")
        
        return {
            "metrics": {k.value: v for k, v in current_status.items()},
            "summary": {
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count,
                "violated": violated_count,
                "total": len(current_status),
            },
            "recent_violations": self.violations[-10:],
            "overall_health": "healthy" if violated_count == 0 and critical_count == 0 else (
                "critical" if critical_count > 0 or violated_count > 0 else "warning"
            ),
        }


# Singleton instance
sla_monitor = SLAMonitor()
