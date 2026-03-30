#!/usr/bin/env python3
"""
Engenharia CAD — Servidor de Produção (Rede)
Inicia o FastAPI em 0.0.0.0:8000 para acesso a partir de outras máquinas.

Uso:
    python run_server.py                  → Produção (0.0.0.0:8000)
    python run_server.py --dev            → Desenvolvimento (127.0.0.1:8000, reload)
    python run_server.py --port 9000      → Porta customizada
"""

import argparse
import socket
import sys


def get_local_ip() -> str:
    """Detecta o IP privado desta máquina na rede local."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Engenharia CAD — Iniciar Servidor")
    parser.add_argument("--host", default="0.0.0.0", help="Host de bind (padrão: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Porta (padrão: 8000)")
    parser.add_argument("--dev", action="store_true", help="Modo dev (localhost + reload)")
    args = parser.parse_args()

    host = "127.0.0.1" if args.dev else args.host
    local_ip = get_local_ip()

    print()
    print("=" * 60)
    print("  Engenharia CAD v1.0 Gold — Servidor Central")
    print("=" * 60)
    print(f"  Modo:       {'DESENVOLVIMENTO' if args.dev else 'REDE (produção)'}")
    print(f"  Bind:       {host}:{args.port}")
    print(f"  IP local:   {local_ip}")
    print()
    if not args.dev:
        print(f"  No PC B (cliente), abra no navegador:")
        print(f"    http://{local_ip}:3000")
        print()
        print(f"  API docs:")
        print(f"    http://{local_ip}:{args.port}/docs")
    else:
        print(f"  Local: http://localhost:{args.port}/docs")
    print("=" * 60)
    print()

    try:
        import uvicorn
    except ImportError:
        print("ERRO: uvicorn não instalado. Execute: pip install uvicorn[standard]")
        sys.exit(1)

    uvicorn.run(
        "server:app",
        host=host,
        port=args.port,
        reload=args.dev,
        log_level="info",
    )


if __name__ == "__main__":
    main()
