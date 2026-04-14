"""
═══════════════════════════════════════════════════════════════════════════════
  SYSTEM MONITOR — Monitoramento contínuo de saúde e performance
  Coleta métricas, detecta anomalias e gera alertas automaticamente
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

logger = logging.getLogger("engcad.monitor")

ALERT_CHANNELS: List[Callable] = []


@dataclass
class SystemSnapshot:
    """Snapshot do estado do sistema em um momento."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    open_files: int
    active_threads: int
    network_bytes_sent: int
    network_bytes_recv: int
    process_cpu: float
    process_memory_mb: float
    active_connections: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu": {"percent": self.cpu_percent},
            "memory": {
                "percent": self.memory_percent,
                "used_mb": round(self.memory_used_mb, 1),
                "total_mb": round(self.memory_total_mb, 1),
            },
            "disk": {
                "percent": self.disk_percent,
                "used_gb": round(self.disk_used_gb, 1),
                "total_gb": round(self.disk_total_gb, 1),
            },
            "process": {
                "cpu_percent": self.process_cpu,
                "memory_mb": round(self.process_memory_mb, 1),
                "threads": self.active_threads,
                "open_files": self.open_files,
            },
            "network": {
                "bytes_sent": self.network_bytes_sent,
                "bytes_recv": self.network_bytes_recv,
            },
            "active_connections": self.active_connections,
        }


@dataclass
class AlertRule:
    """Regra de alerta."""
    name: str
    metric: str
    threshold: float
    comparison: str  # "gt", "lt", "eq"
    severity: str  # "info", "warning", "critical"
    cooldown_seconds: float = 300.0
    _last_fired: float = 0.0

    def evaluate(self, value: float) -> bool:
        if self.comparison == "gt":
            return value > self.threshold
        elif self.comparison == "lt":
            return value < self.threshold
        return abs(value - self.threshold) < 0.01

    def should_fire(self) -> bool:
        now = time.time()
        if now - self._last_fired < self.cooldown_seconds:
            return False
        self._last_fired = now
        return True


class SystemMonitor:
    """Monitor contínuo do sistema com alertas e histórico."""

    def __init__(self, history_size: int = 3600, interval_seconds: float = 5.0):
        self.history_size = history_size
        self.interval = interval_seconds
        self._history: deque[SystemSnapshot] = deque(maxlen=history_size)
        self._alerts: deque[Dict[str, Any]] = deque(maxlen=1000)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._process = psutil.Process()
        self._alert_rules = self._default_rules()
        self._request_count = 0
        self._error_count = 0
        self._response_times: deque[float] = deque(maxlen=10000)
        self._endpoints_stats: Dict[str, Dict] = {}

    def _default_rules(self) -> List[AlertRule]:
        return [
            AlertRule("CPU Alta", "cpu_percent", 90.0, "gt", "critical"),
            AlertRule("CPU Elevada", "cpu_percent", 75.0, "gt", "warning"),
            AlertRule("Memória Alta", "memory_percent", 90.0, "gt", "critical"),
            AlertRule("Memória Elevada", "memory_percent", 80.0, "gt", "warning"),
            AlertRule("Disco Cheio", "disk_percent", 95.0, "gt", "critical"),
            AlertRule("Disco Alto", "disk_percent", 85.0, "gt", "warning"),
            AlertRule("Processo Memória", "process_memory_mb", 2048.0, "gt", "warning"),
        ]

    def record_request(self, path: str, method: str, status_code: int, duration_ms: float) -> None:
        """Registra uma requisição HTTP para métricas."""
        self._request_count += 1
        self._response_times.append(duration_ms)
        if status_code >= 500:
            self._error_count += 1

        key = f"{method} {path}"
        if key not in self._endpoints_stats:
            self._endpoints_stats[key] = {
                "count": 0, "errors": 0, "total_ms": 0.0,
                "min_ms": float("inf"), "max_ms": 0.0,
            }
        stats = self._endpoints_stats[key]
        stats["count"] += 1
        stats["total_ms"] += duration_ms
        if status_code >= 500:
            stats["errors"] += 1
        if duration_ms < stats["min_ms"]:
            stats["min_ms"] = duration_ms
        if duration_ms > stats["max_ms"]:
            stats["max_ms"] = duration_ms

    def take_snapshot(self) -> SystemSnapshot:
        """Captura snapshot atual do sistema."""
        cpu = psutil.cpu_percent(interval=0)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.sep)
        net = psutil.net_io_counters()

        try:
            proc_cpu = self._process.cpu_percent(interval=0)
            proc_mem = self._process.memory_info().rss / (1024 * 1024)
            threads = self._process.num_threads()
            open_files = len(self._process.open_files())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_cpu = 0.0
            proc_mem = 0.0
            threads = 0
            open_files = 0

        try:
            conns = len(self._process.connections())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            conns = 0

        snapshot = SystemSnapshot(
            timestamp=datetime.now(UTC).isoformat(),
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_used_mb=mem.used / (1024 * 1024),
            memory_total_mb=mem.total / (1024 * 1024),
            disk_percent=disk.percent,
            disk_used_gb=disk.used / (1024 ** 3),
            disk_total_gb=disk.total / (1024 ** 3),
            open_files=open_files,
            active_threads=threads,
            network_bytes_sent=net.bytes_sent,
            network_bytes_recv=net.bytes_recv,
            process_cpu=proc_cpu,
            process_memory_mb=proc_mem,
            active_connections=conns,
        )
        return snapshot

    def _check_alerts(self, snapshot: SystemSnapshot) -> List[Dict[str, Any]]:
        """Verifica regras de alerta contra o snapshot."""
        fired = []
        metrics = {
            "cpu_percent": snapshot.cpu_percent,
            "memory_percent": snapshot.memory_percent,
            "disk_percent": snapshot.disk_percent,
            "process_memory_mb": snapshot.process_memory_mb,
        }
        for rule in self._alert_rules:
            value = metrics.get(rule.metric)
            if value is not None and rule.evaluate(value) and rule.should_fire():
                alert = {
                    "name": rule.name,
                    "metric": rule.metric,
                    "value": round(value, 1),
                    "threshold": rule.threshold,
                    "severity": rule.severity,
                    "timestamp": snapshot.timestamp,
                }
                fired.append(alert)
                self._alerts.append(alert)
                logger.warning(
                    "ALERTA [%s]: %s = %.1f (limite: %.1f)",
                    rule.severity.upper(), rule.name, value, rule.threshold,
                )
                for channel in ALERT_CHANNELS:
                    try:
                        channel(alert)
                    except Exception:
                        pass
        return fired

    async def start(self) -> None:
        """Inicia monitoramento contínuo."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitor iniciado (intervalo=%.1fs)", self.interval)

    async def stop(self) -> None:
        """Para o monitoramento."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("System monitor parado")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                loop = asyncio.get_event_loop()
                snapshot = await loop.run_in_executor(None, self.take_snapshot)
                self._history.append(snapshot)
                self._check_alerts(snapshot)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Erro no monitor: %s", e)
            await asyncio.sleep(self.interval)

    def get_current(self) -> Dict[str, Any]:
        """Retorna estado atual do sistema."""
        if self._history:
            return self._history[-1].to_dict()
        snapshot = self.take_snapshot()
        return snapshot.to_dict()

    def get_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Retorna histórico dos últimos N minutos."""
        cutoff = time.time() - (minutes * 60)
        return [
            s.to_dict() for s in self._history
            if datetime.fromisoformat(s.timestamp).timestamp() > cutoff
        ]

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna alertas recentes."""
        return list(reversed(list(self._alerts)))[:limit]

    def get_request_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de requisições HTTP."""
        times = list(self._response_times)
        if not times:
            avg = p50 = p95 = p99 = 0.0
        else:
            sorted_times = sorted(times)
            avg = sum(times) / len(times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]

        error_rate = (
            (self._error_count / self._request_count * 100)
            if self._request_count > 0
            else 0.0
        )

        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate_percent": round(error_rate, 2),
            "response_times": {
                "avg_ms": round(avg, 2),
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
            },
        }

    def get_endpoints_stats(self, top: int = 20) -> List[Dict[str, Any]]:
        """Retorna estatísticas por endpoint."""
        result = []
        for key, stats in sorted(
            self._endpoints_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:top]:
            avg = stats["total_ms"] / stats["count"] if stats["count"] > 0 else 0
            result.append({
                "endpoint": key,
                "count": stats["count"],
                "errors": stats["errors"],
                "avg_ms": round(avg, 2),
                "min_ms": round(stats["min_ms"], 2) if stats["min_ms"] != float("inf") else 0,
                "max_ms": round(stats["max_ms"], 2),
            })
        return result

    def get_full_dashboard(self) -> Dict[str, Any]:
        """Retorna todos os dados para o dashboard de monitoramento."""
        return {
            "system": self.get_current(),
            "alerts": self.get_alerts(20),
            "requests": self.get_request_metrics(),
            "top_endpoints": self.get_endpoints_stats(15),
            "history_5min": self.get_history(5),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_monitor: Optional[SystemMonitor] = None


def get_monitor() -> SystemMonitor:
    """Retorna instância singleton do monitor."""
    global _monitor
    if _monitor is None:
        interval = float(os.getenv("MONITOR_INTERVAL", "5"))
        _monitor = SystemMonitor(interval_seconds=interval)
    return _monitor
