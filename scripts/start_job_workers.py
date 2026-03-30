#!/usr/bin/env python3
"""
Script para iniciar workers de jobs assíncronos.
"""

import argparse
import multiprocessing
import signal
import sys
import time
from pathlib import Path

# Adicionar caminhos ao sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
ENGINEERING_ROOT = PROJECT_ROOT / "engenharia_automacao"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(ENGINEERING_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINEERING_ROOT))

from integration.python_api.config import load_config
from integration.python_api.async_jobs import AsyncJobManager


def worker_process(job_type: str, redis_url: str):
    """Processo worker para um tipo específico de job."""
    print(f"Iniciando worker para {job_type}")

    manager = AsyncJobManager(redis_url)

    def signal_handler(signum, frame):
        print(f"Worker {job_type} recebendo sinal de parada")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        manager.process_jobs(job_type)
    except KeyboardInterrupt:
        print(f"Worker {job_type} interrompido")
    except Exception as e:
        print(f"Erro no worker {job_type}: {e}")
        sys.exit(1)


def check_worker_health(processes: list, redis_url: str) -> list:
    """✓ PROBLEMA #12: Verificar saúde dos workers e reiniciar se necessário."""
    import psutil
    
    healthy_processes = []
    restarted = []
    
    for p in processes:
        try:
            # Verificar se processo ainda existe
            if not p.is_alive():
                print(f"⚠️ Worker {p.name} morto - reiniciando...")
                # Tentar reiniciar
                job_type = p.name.split('-')[1]  # worker-{job_type}-{i}
                new_p = multiprocessing.Process(
                    target=worker_process,
                    args=(job_type, redis_url),
                    name=p.name
                )
                new_p.start()
                restarted.append(new_p)
                print(f"✓ Worker {p.name} reiniciado (PID: {new_p.pid})")
                continue
            
            # Verificar uso de CPU/memória (opcional, mas útil)
            try:
                proc = psutil.Process(p.pid)
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_mb = proc.memory_info().rss / 1024 / 1024
                
                if cpu_percent > 90:
                    print(f"⚠️ Worker {p.name} alta CPU: {cpu_percent:.1f}%")
                if memory_mb > 500:  # 500MB
                    print(f"⚠️ Worker {p.name} alta memória: {memory_mb:.1f}MB")
                    
            except psutil.NoSuchProcess:
                print(f"⚠️ Worker {p.name} processo não encontrado")
                continue
            
            healthy_processes.append(p)
            
        except Exception as e:
            print(f"Erro ao verificar saúde de {p.name}: {e}")
            healthy_processes.append(p)  # Manter na lista mesmo com erro
    
    return healthy_processes + restarted


def cleanup_old_jobs_if_needed(manager: AsyncJobManager) -> None:
    """✓ PROBLEMA #10: Limpeza periódica de jobs antigos."""
    try:
        cleaned = manager.cleanup_old_jobs(max_age_seconds=86400)  # 24h
        if cleaned > 0:
            print(f"✓ Limpou {cleaned} jobs antigos do Redis")
    except Exception as e:
        print(f"Erro na limpeza de jobs: {e}")


def main():
    parser = argparse.ArgumentParser(description="Iniciar workers de jobs assíncronos")
    parser.add_argument("--job-types", nargs="+", default=["generate_project", "rebuild_stats", "excel_batch", "ai_cad"],
                       help="Tipos de jobs para processar")
    parser.add_argument("--workers-per-type", type=int, default=2,
                       help="Número de workers por tipo de job")
    parser.add_argument("--redis-url", help="URL do Redis para jobs")
    parser.add_argument("--health-check-interval", type=int, default=60,
                       help="Intervalo em segundos para health checks")

    args = parser.parse_args()

    config = load_config()
    redis_url = args.redis_url or config.jobs_redis_url

    print(f"Iniciando workers com Redis: {redis_url}")
    print(f"Tipos de jobs: {args.job_types}")
    print(f"Workers por tipo: {args.workers_per_type}")
    print(f"Health check a cada: {args.health_check_interval}s")

    processes = []
    manager = AsyncJobManager(redis_url)

    try:
        # Criar workers para cada tipo de job
        for job_type in args.job_types:
            for i in range(args.workers_per_type):
                p = multiprocessing.Process(
                    target=worker_process,
                    args=(job_type, redis_url),
                    name=f"worker-{job_type}-{i}"
                )
                p.start()
                processes.append(p)
                print(f"Worker {job_type}-{i} iniciado (PID: {p.pid})")

        print(f"\n{len(processes)} workers iniciados. Pressione Ctrl+C para parar.")

        # Aguardar sinais
        def shutdown_handler(signum, frame):
            print("\nEncerrando workers...")
            for p in processes:
                if p.is_alive():
                    p.terminate()
            for p in processes:
                p.join(timeout=5)
                if p.is_alive():
                    p.kill()
            print("Todos os workers encerrados.")
            sys.exit(0)

        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)

        # ✓ PROBLEMA #12: Loop principal com health checks
        last_health_check = time.time()
        last_cleanup = time.time()
        
        while True:
            time.sleep(1)
            
            current_time = time.time()
            
            # Health check periódico
            if current_time - last_health_check >= args.health_check_interval:
                processes = check_worker_health(processes, redis_url)
                last_health_check = current_time
            
            # Limpeza de jobs antigos (uma vez por hora)
            if current_time - last_cleanup >= 3600:
                cleanup_old_jobs_if_needed(manager)
                last_cleanup = current_time
            
            # Verificar se algum processo morreu (check rápido)
            for p in processes[:]:
                if not p.is_alive():
                    print(f"⚠️ Worker {p.name} morreu - será reiniciado no próximo health check")
                    processes.remove(p)

    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()