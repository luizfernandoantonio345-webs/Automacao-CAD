#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ENGENHARIA CAD - LOAD TESTING SUITE
# ═══════════════════════════════════════════════════════════════════════════════
"""
Suite de testes de carga para validar performance em produção.
Usa Locust (pip install locust) ou executa standalone.

Uso:
    # Standalone (rápido)
    python load_testing.py

    # Com Locust (completo)
    locust -f load_testing.py --host http://localhost:8000 --users 100 --spawn-rate 10

Métricas coletadas:
    - Requisições por segundo (RPS)
    - Latência P50, P95, P99
    - Taxa de erros
    - Throughput de jobs CAM
"""
import asyncio
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Any
import os

# Configuração
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CONCURRENT_USERS = int(os.getenv("LOAD_TEST_USERS", "50"))
DURATION_SECONDS = int(os.getenv("LOAD_TEST_DURATION", "60"))
RAMP_UP_SECONDS = int(os.getenv("LOAD_TEST_RAMP_UP", "10"))

try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    import urllib.request
    import urllib.error
    HTTP_CLIENT = "urllib"


@dataclass
class RequestResult:
    """Resultado de uma requisição."""
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    success: bool
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class LoadTestReport:
    """Relatório de teste de carga."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    start_time: float = 0
    end_time: float = 0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def rps(self) -> float:
        return self.total_requests / max(self.duration, 0.001)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def p50(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.5)
        return sorted_lat[idx]
    
    @property
    def p95(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "duration_seconds": round(self.duration, 2),
            "requests_per_second": round(self.rps, 2),
            "success_rate_percent": round(self.success_rate, 2),
            "latency_p50_ms": round(self.p50, 2),
            "latency_p95_ms": round(self.p95, 2),
            "latency_p99_ms": round(self.p99, 2),
            "latency_avg_ms": round(statistics.mean(self.latencies), 2) if self.latencies else 0,
            "latency_max_ms": round(max(self.latencies), 2) if self.latencies else 0,
            "errors": self.errors,
        }


def make_request(endpoint: str, method: str = "GET", data: dict = None) -> RequestResult:
    """Faz uma requisição HTTP e mede a latência."""
    url = f"{API_BASE_URL}{endpoint}"
    start = time.time()
    
    try:
        if HTTP_CLIENT == "httpx":
            with httpx.Client(timeout=30.0) as client:
                if method == "GET":
                    response = client.get(url)
                else:
                    response = client.post(url, json=data)
                
                latency = (time.time() - start) * 1000
                return RequestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status_code,
                    latency_ms=latency,
                    success=response.status_code < 400
                )
        else:
            # Fallback para urllib
            req = urllib.request.Request(url)
            if data:
                req.add_header("Content-Type", "application/json")
                req.data = json.dumps(data).encode()
            
            with urllib.request.urlopen(req, timeout=30) as response:
                latency = (time.time() - start) * 1000
                return RequestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status,
                    latency_ms=latency,
                    success=True
                )
                
    except Exception as e:
        latency = (time.time() - start) * 1000
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=0,
            latency_ms=latency,
            success=False,
            error=str(e)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CENÁRIOS DE TESTE
# ═══════════════════════════════════════════════════════════════════════════════

def scenario_health_check() -> RequestResult:
    """Cenário: Health check."""
    return make_request("/health")


def scenario_public_endpoints() -> List[RequestResult]:
    """Cenário: Endpoints públicos."""
    endpoints = ["/", "/health", "/openapi.json", "/system"]
    return [make_request(ep) for ep in endpoints]


def scenario_auth_flow() -> List[RequestResult]:
    """Cenário: Fluxo de autenticação."""
    results = []
    
    # Demo login
    results.append(make_request("/auth/demo", "POST"))
    
    return results


def scenario_cam_operations() -> List[RequestResult]:
    """Cenário: Operações CAM."""
    results = []
    
    # Lista de materiais
    results.append(make_request("/api/cam/materials"))
    
    # AI suggest (se disponível)
    results.append(make_request("/api/ai/status"))
    
    return results


def scenario_dashboard_load() -> List[RequestResult]:
    """Cenário: Carga de dashboard."""
    results = []
    
    results.append(make_request("/system"))
    results.append(make_request("/project-stats"))
    
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTOR DE TESTES
# ═══════════════════════════════════════════════════════════════════════════════

def run_load_test(
    concurrent_users: int = CONCURRENT_USERS,
    duration_seconds: int = DURATION_SECONDS,
    ramp_up_seconds: int = RAMP_UP_SECONDS
) -> LoadTestReport:
    """Executa teste de carga completo."""
    
    print(f"\n{'═' * 60}")
    print(f"  ENGENHARIA CAD - LOAD TEST")
    print(f"{'═' * 60}")
    print(f"  Target:     {API_BASE_URL}")
    print(f"  Users:      {concurrent_users}")
    print(f"  Duration:   {duration_seconds}s")
    print(f"  Ramp-up:    {ramp_up_seconds}s")
    print(f"{'═' * 60}\n")
    
    report = LoadTestReport()
    report.start_time = time.time()
    
    # Verificar conectividade
    print("🔍 Verificando conectividade...", end=" ")
    result = make_request("/health")
    if not result.success:
        print(f"❌ FALHOU: {result.error}")
        return report
    print(f"✅ OK ({result.latency_ms:.0f}ms)")
    
    # Cenários de teste
    scenarios = [
        scenario_health_check,
        scenario_public_endpoints,
        scenario_auth_flow,
        scenario_cam_operations,
        scenario_dashboard_load,
    ]
    
    # Executar com ThreadPoolExecutor
    print(f"\n🚀 Iniciando teste de carga com {concurrent_users} usuários...\n")
    
    end_time = time.time() + duration_seconds
    
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = []
        
        while time.time() < end_time:
            # Submeter cenários
            for scenario in scenarios:
                future = executor.submit(scenario)
                futures.append(future)
            
            # Pequeno sleep para não sobrecarregar
            time.sleep(0.1)
            
            # Processar resultados completos
            for future in list(futures):
                if future.done():
                    futures.remove(future)
                    try:
                        result = future.result()
                        if isinstance(result, list):
                            for r in result:
                                report.total_requests += 1
                                if r.success:
                                    report.successful_requests += 1
                                else:
                                    report.failed_requests += 1
                                    error_key = r.error[:50] if r.error else f"HTTP {r.status_code}"
                                    report.errors[error_key] = report.errors.get(error_key, 0) + 1
                                report.latencies.append(r.latency_ms)
                        else:
                            report.total_requests += 1
                            if result.success:
                                report.successful_requests += 1
                            else:
                                report.failed_requests += 1
                            report.latencies.append(result.latency_ms)
                    except Exception as e:
                        report.failed_requests += 1
                        report.total_requests += 1
            
            # Progress
            elapsed = time.time() - report.start_time
            progress = min(100, (elapsed / duration_seconds) * 100)
            rps = report.total_requests / max(elapsed, 0.001)
            print(f"\r  Progress: {progress:5.1f}% | Requests: {report.total_requests:,} | RPS: {rps:.1f}", end="")
    
    report.end_time = time.time()
    
    print("\n")
    return report


def print_report(report: LoadTestReport):
    """Imprime relatório formatado."""
    
    data = report.to_dict()
    
    print(f"\n{'═' * 60}")
    print(f"  RELATÓRIO DE TESTE DE CARGA")
    print(f"{'═' * 60}")
    print(f"  Total Requests:    {data['total_requests']:,}")
    print(f"  Successful:        {data['successful_requests']:,}")
    print(f"  Failed:            {data['failed_requests']:,}")
    print(f"  Duration:          {data['duration_seconds']:.2f}s")
    print(f"{'─' * 60}")
    print(f"  RPS (avg):         {data['requests_per_second']:.2f}")
    print(f"  Success Rate:      {data['success_rate_percent']:.2f}%")
    print(f"{'─' * 60}")
    print(f"  Latency P50:       {data['latency_p50_ms']:.2f}ms")
    print(f"  Latency P95:       {data['latency_p95_ms']:.2f}ms")
    print(f"  Latency P99:       {data['latency_p99_ms']:.2f}ms")
    print(f"  Latency Avg:       {data['latency_avg_ms']:.2f}ms")
    print(f"  Latency Max:       {data['latency_max_ms']:.2f}ms")
    print(f"{'═' * 60}")
    
    # Verificações de SLA
    print("\n📊 VERIFICAÇÕES DE SLA:")
    
    checks = [
        ("RPS > 50", data['requests_per_second'] > 50),
        ("P95 < 500ms", data['latency_p95_ms'] < 500),
        ("P99 < 1000ms", data['latency_p99_ms'] < 1000),
        ("Erros < 1%", data['success_rate_percent'] > 99),
        ("Erros < 5%", data['success_rate_percent'] > 95),
    ]
    
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
    
    # Erros detalhados
    if data['errors']:
        print(f"\n⚠️  ERROS ENCONTRADOS:")
        for error, count in sorted(data['errors'].items(), key=lambda x: -x[1])[:5]:
            print(f"  - {error}: {count}x")
    
    print(f"\n{'═' * 60}\n")
    
    return data


# ═══════════════════════════════════════════════════════════════════════════════
# LOCUST TASKS (para uso com Locust)
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from locust import HttpUser, task, between
    
    class EngCADUser(HttpUser):
        """Usuário virtual para Locust."""
        
        wait_time = between(0.5, 2)
        
        @task(10)
        def health_check(self):
            self.client.get("/health")
        
        @task(5)
        def get_system_metrics(self):
            self.client.get("/system")
        
        @task(3)
        def demo_login(self):
            self.client.post("/auth/demo")
        
        @task(3)
        def get_materials(self):
            self.client.get("/api/cam/materials")
        
        @task(2)
        def get_ai_status(self):
            self.client.get("/api/ai/status")
        
        @task(1)
        def get_project_stats(self):
            self.client.get("/project-stats")
            
except ImportError:
    # Locust não instalado, usar modo standalone
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load Testing para Engenharia CAD")
    parser.add_argument("--users", type=int, default=CONCURRENT_USERS, help="Usuários concorrentes")
    parser.add_argument("--duration", type=int, default=DURATION_SECONDS, help="Duração em segundos")
    parser.add_argument("--url", type=str, default=API_BASE_URL, help="URL base da API")
    parser.add_argument("--output", type=str, help="Arquivo JSON para salvar resultados")
    
    args = parser.parse_args()
    
    API_BASE_URL = args.url
    
    report = run_load_test(
        concurrent_users=args.users,
        duration_seconds=args.duration
    )
    
    data = print_report(report)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"📁 Resultados salvos em: {args.output}")
    
    # Exit code baseado em SLA
    if data['success_rate_percent'] < 95 or data['latency_p95_ms'] > 500:
        sys.exit(1)
    sys.exit(0)
