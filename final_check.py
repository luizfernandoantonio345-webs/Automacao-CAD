#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD v1.0 Gold — Teste de Fogo (Final Check)
Verifica se TODOS os serviços essenciais estão operacionais antes do deploy.
═══════════════════════════════════════════════════════════════════════════════

Uso:
    python final_check.py
    python final_check.py --bridge-path "Z:/AutoCAD_Drop/"

Retorna exit code 0 se tudo OK, 1 se algum serviço falhou.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time

# ── Cores ANSI para terminal Windows/Linux ──────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    """Testa se uma porta TCP está aceitando conexões."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


def check_http(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Faz GET em uma URL e retorna (sucesso, detalhes)."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(2048).decode("utf-8", errors="replace")
            return resp.status == 200, body[:200]
    except Exception as exc:
        return False, str(exc)


def check_bridge_path(path: str) -> tuple[bool, str]:
    """Verifica se a pasta da ponte de rede existe e é acessível."""
    if not path:
        return False, "Caminho não configurado"
    if not os.path.isdir(path):
        return False, f"Pasta não encontrada: {path}"
    # Testar escrita
    test_file = os.path.join(path, ".engcad_check_tmp")
    try:
        with open(test_file, "w") as f:
            f.write("check")
        os.remove(test_file)
        return True, f"Pasta acessível (leitura + escrita): {path}"
    except OSError as exc:
        return False, f"Pasta existe mas sem permissão de escrita: {exc}"


def main():
    parser = argparse.ArgumentParser(description="Engenharia CAD v1.0 — Teste de Fogo")
    parser.add_argument(
        "--bridge-path",
        default=os.getenv("AUTOCAD_BRIDGE_PATH", ""),
        help="Caminho da pasta Bridge (padrão: env AUTOCAD_BRIDGE_PATH)",
    )
    parser.add_argument("--api-host", default="localhost", help="Host da API FastAPI")
    parser.add_argument("--api-port", default=8000, type=int, help="Porta da API FastAPI")
    parser.add_argument("--redis-host", default="localhost", help="Host do Redis")
    parser.add_argument("--redis-port", default=6379, type=int, help="Porta do Redis")
    parser.add_argument("--rabbit-host", default="localhost", help="Host do RabbitMQ")
    parser.add_argument("--rabbit-port", default=5672, type=int, help="Porta AMQP do RabbitMQ")
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   Engenharia CAD v1.0 Gold — TESTE DE FOGO                    ║{RESET}")
    print(f"{BOLD}{CYAN}╠══════════════════════════════════════════════════════════╣{RESET}")
    print(f"{BOLD}{CYAN}║   Verificação pré-deploy de todos os serviços           ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}\n")

    results: list[tuple[str, bool, str]] = []
    total_start = time.time()

    # ── 1. Redis ─────────────────────────────────────────────────────────
    print(f"  [1/8] Verificando Redis ({args.redis_host}:{args.redis_port})...", end=" ", flush=True)
    ok = check_tcp(args.redis_host, args.redis_port)
    detail = "TCP conectado" if ok else "Conexão recusada — Redis está rodando?"
    results.append(("Redis", ok, detail))
    print(f"{GREEN}OK{RESET}" if ok else f"{RED}FALHOU{RESET}")

    # ── 2. RabbitMQ ──────────────────────────────────────────────────────
    print(f"  [2/8] Verificando RabbitMQ ({args.rabbit_host}:{args.rabbit_port})...", end=" ", flush=True)
    ok = check_tcp(args.rabbit_host, args.rabbit_port)
    detail = "AMQP conectado" if ok else "Conexão recusada — RabbitMQ está rodando?"
    results.append(("RabbitMQ", ok, detail))
    print(f"{GREEN}OK{RESET}" if ok else f"{RED}FALHOU{RESET}")

    # ── 3. FastAPI ───────────────────────────────────────────────────────
    api_url = f"http://{args.api_host}:{args.api_port}/system"
    print(f"  [3/8] Verificando FastAPI ({api_url})...", end=" ", flush=True)
    ok, detail = check_http(api_url)
    results.append(("FastAPI", ok, detail))
    print(f"{GREEN}OK{RESET}" if ok else f"{RED}FALHOU{RESET}")

    # ── 4. AutoCAD Driver (health endpoint) ──────────────────────────────
    health_url = f"http://{args.api_host}:{args.api_port}/api/autocad/health"
    print(f"  [4/8] Verificando AutoCAD Driver ({health_url})...", end=" ", flush=True)
    ok, detail = check_http(health_url)
    results.append(("AutoCAD Driver", ok, detail))
    print(f"{GREEN}OK{RESET}" if ok else f"{RED}FALHOU{RESET}")

    # ── 5. Bridge Path ───────────────────────────────────────────────────
    bridge = args.bridge_path
    print(f"  [5/8] Verificando Bridge Path ({bridge or '(não configurado)'})...", end=" ", flush=True)
    if bridge:
        ok, detail = check_bridge_path(bridge)
    else:
        ok, detail = False, "Nenhum caminho de bridge configurado (--bridge-path ou AUTOCAD_BRIDGE_PATH)"
    results.append(("Bridge Path", ok, detail))
    print(f"{GREEN}OK{RESET}" if ok else f"{YELLOW}SKIP{RESET}" if not bridge else f"{RED}FALHOU{RESET}")

    # ── 6. Frontend React ────────────────────────────────────────────────
    print(f"  [6/8] Verificando Frontend React (localhost:3000)...", end=" ", flush=True)
    ok_front, detail_front = check_http("http://localhost:3000", timeout=3.0)
    results.append(("Frontend React", ok_front, "Porta 3000 respondendo" if ok_front else "Não acessível — cd frontend && npm start"))
    print(f"{GREEN}OK{RESET}" if ok_front else f"{YELLOW}SKIP{RESET}")

    # ── 7. Vigilante .lsp v2.0 ───────────────────────────────────────────
    print(f"  [7/8] Verificando forge_vigilante.lsp v2.0...", end=" ", flush=True)
    vigilante_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "forge_vigilante.lsp")
    if os.path.isfile(vigilante_path):
        with open(vigilante_path, "r", encoding="utf-8") as f:
            header = f.read(600)
        if "2.0" in header:
            ok_v, detail_v = True, f"v2.0 encontrado em backend/"
        else:
            ok_v, detail_v = False, "Arquivo existe mas NÃO é v2.0"
    else:
        ok_v, detail_v = False, "forge_vigilante.lsp não encontrado em backend/"
    results.append(("Vigilante v2.0", ok_v, detail_v))
    print(f"{GREEN}OK{RESET}" if ok_v else f"{RED}FALHOU{RESET}")

    # ── 8. Layers N-58 Petrobras ─────────────────────────────────────────
    print(f"  [8/8] Verificando layers N-58 Petrobras...", end=" ", flush=True)
    try:
        parent = os.path.dirname(os.path.abspath(__file__))
        if parent not in sys.path:
            sys.path.insert(0, parent)
        from backend.autocad_driver import N58_LAYER_SPEC
        expected_layers = {
            "PIPE-PROCESS", "PIPE-UTILITY", "PIPE-INSTRUMENT",
            "EQUIP-VESSEL", "EQUIP-PUMP", "VALVE", "FLANGE",
            "SUPPORT", "ANNOTATION", "DIMENSION", "ISOMETRIC",
        }
        # Cores obrigatórias N-58 Petrobras por categoria
        n58_color_rules = {
            "PIPE-PROCESS":    1,   # Tubulação → Cor 1
            "EQUIP-VESSEL":    4,   # Equipamentos → Cor 4
            "EQUIP-PUMP":      4,   # Equipamentos → Cor 4
            "PIPE-INSTRUMENT": 6,   # Instrumentação → Cor 6
            "VALVE":           6,   # Instrumentação → Cor 6
            "SUPPORT":         8,   # Civil → Cor 8
            "ANNOTATION":      7,   # Texto/Cotas → Cor 7
            "DIMENSION":       7,   # Texto/Cotas → Cor 7
        }
        found = set(N58_LAYER_SPEC.keys())
        missing = expected_layers - found
        color_errors = []
        for layer, expected_color in n58_color_rules.items():
            spec = N58_LAYER_SPEC.get(layer, {})
            actual_color = spec.get("color")
            if actual_color != expected_color:
                color_errors.append(f"{layer}: cor {actual_color} (esperado {expected_color})")
        if missing:
            ok_n, detail_n = False, f"Layers faltando: {missing}"
        elif color_errors:
            ok_n, detail_n = False, f"Cores N-58 incorretas: {'; '.join(color_errors)}"
        else:
            ok_n, detail_n = True, f"Todos os {len(found)} layers N-58 definidos — cores N-58 conformes"
    except ImportError as e:
        ok_n, detail_n = False, f"Erro de import: {e}"
    results.append(("Layers N-58", ok_n, detail_n))
    print(f"{GREEN}OK{RESET}" if ok_n else f"{RED}FALHOU{RESET}")

    # ── Resumo ───────────────────────────────────────────────────────────
    elapsed = time.time() - total_start
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    critical_failed = any(
        not ok for name, ok, _ in results if name in ("Redis", "RabbitMQ", "FastAPI")
    )

    print(f"\n{BOLD}{'═' * 58}{RESET}")
    print(f"{BOLD}  RESULTADO: {passed}/{total} serviços operacionais  ({elapsed:.1f}s){RESET}")
    print(f"{'═' * 58}")

    for name, ok, detail in results:
        icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {icon}  {name:20s} — {detail}")

    print()

    if critical_failed:
        print(f"{RED}{BOLD}  ✗ FALHA CRÍTICA — Serviços essenciais offline.{RESET}")
        print(f"{RED}    Suba o docker-compose e o FastAPI antes da demonstração.{RESET}\n")
        sys.exit(1)
    elif passed == total:
        print(f"{GREEN}{BOLD}  ✓ TODOS OS SERVIÇOS OPERACIONAIS — Pronto para deploy!{RESET}\n")
        sys.exit(0)
    else:
        print(f"{YELLOW}{BOLD}  ⚠ Serviços parciais — funcionalidade reduzida.{RESET}")
        print(f"{YELLOW}    O sistema pode operar, mas Bridge Path não verificado.{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
