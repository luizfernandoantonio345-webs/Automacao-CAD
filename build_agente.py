#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD — Build Script do ForgeLink Agent (.exe)
Limpa artefatos anteriores e gera um executável único via PyInstaller.
Opcionalmente ofusca com PyArmor antes do empacotamento.

Uso:
    python build_agente.py                  → Build padrão (--noconsole)
    python build_agente.py --debug          → Build com console visível
    python build_agente.py --obfuscate      → Ofusca com PyArmor antes do build
    python build_agente.py --obfuscate --debug
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import shutil
import subprocess
import sys
import time

# ─── Configuração ────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SPEC_FILE = os.path.join(ROOT_DIR, "forge_link.spec")
ENTRY_POINT = os.path.join(ROOT_DIR, "forge_link_agent.py")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
OUTPUT_NAME = "ForgeLinkAgent"
ICON_PATH = os.path.join(ROOT_DIR, "assets", "engcad.ico")


def banner(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def clean() -> None:
    """Remove artefatos de build anteriores."""
    banner("LIMPANDO BUILD ANTERIOR")
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            print(f"  Removendo {d}")
            shutil.rmtree(d, ignore_errors=True)
    # Limpa cache do PyInstaller
    pycache = os.path.join(ROOT_DIR, "__pycache__")
    if os.path.exists(pycache):
        shutil.rmtree(pycache, ignore_errors=True)
    print("  Limpo.")


def ensure_pyinstaller() -> None:
    """Instala PyInstaller se não estiver disponível."""
    try:
        import PyInstaller
        print(f"  PyInstaller {PyInstaller.__version__} encontrado.")
    except ImportError:
        banner("INSTALANDO PYINSTALLER")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def ensure_pyarmor() -> bool:
    """Verifica se PyArmor está disponível. Retorna True se encontrado."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pyarmor", "--version"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            print(f"  PyArmor encontrado: {version}")
            return True
    except FileNotFoundError:
        pass
    print("  PyArmor não encontrado. Instale com: pip install pyarmor")
    return False


def obfuscate() -> str:
    """
    Ofusca os arquivos Python com PyArmor antes do empacotamento.
    Retorna o diretório com os arquivos ofuscados.
    """
    banner("OFUSCANDO COM PYARMOR")
    obf_dir = os.path.join(ROOT_DIR, "dist_obf")

    # Limpa ofuscação anterior
    if os.path.exists(obf_dir):
        shutil.rmtree(obf_dir, ignore_errors=True)

    # Ofusca o agente e módulos backend relevantes
    files_to_obfuscate = [
        ENTRY_POINT,
        os.path.join(ROOT_DIR, "backend", "hwid.py"),
        os.path.join(ROOT_DIR, "backend", "autocad_driver.py"),
        os.path.join(ROOT_DIR, "backend", "routes_autocad.py"),
    ]

    cmd = [
        sys.executable, "-m", "pyarmor", "gen",
        "--output", obf_dir,
        "--restrict",           # Impede importação fora do bundle
        "--no-wrap",            # Sem wrapper script
    ] + files_to_obfuscate

    print(f"  Arquivos: {len(files_to_obfuscate)}")
    print(f"  Saída:    {obf_dir}")
    print(f"  Comando:  {' '.join(cmd)}\n")

    subprocess.check_call(cmd, cwd=ROOT_DIR)
    print("  Ofuscação concluída.")
    return obf_dir


def build(debug: bool = False) -> str:
    """Executa o build e retorna o caminho do .exe."""
    banner("BUILDING FORGELINK AGENT")

    use_spec = os.path.exists(SPEC_FILE)

    if use_spec and not debug:
        # Usa o .spec pré-configurado
        print(f"  Usando spec file: {SPEC_FILE}")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            SPEC_FILE,
        ]
    else:
        # Build direto via CLI (fallback ou modo debug)
        print(f"  Build direto: {ENTRY_POINT}")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name", OUTPUT_NAME,
            "--add-data", f"data{os.pathsep}data",
            "--add-data", f"backend{os.pathsep}backend",
            # Hidden imports essenciais
            "--hidden-import", "fastapi",
            "--hidden-import", "uvicorn",
            "--hidden-import", "uvicorn.logging",
            "--hidden-import", "uvicorn.loops.auto",
            "--hidden-import", "uvicorn.protocols.http.auto",
            "--hidden-import", "uvicorn.protocols.websockets.auto",
            "--hidden-import", "uvicorn.lifespan.on",
            "--hidden-import", "win32com",
            "--hidden-import", "win32com.client",
            "--hidden-import", "pythoncom",
            "--hidden-import", "pywintypes",
            "--hidden-import", "psutil",
            "--hidden-import", "httpx",
            "--hidden-import", "httpcore",
            "--hidden-import", "anyio",
            "--hidden-import", "anyio._backends._asyncio",
            "--hidden-import", "pydantic",
            "--hidden-import", "starlette",
            "--hidden-import", "starlette.routing",
            "--hidden-import", "backend.hwid",
            # Excluir o que não é necessário no agente local
            "--exclude-module", "langchain",
            "--exclude-module", "langchain_ollama",
            "--exclude-module", "ollama",
            "--exclude-module", "sqlalchemy",
            "--exclude-module", "alembic",
            "--exclude-module", "redis",
            "--exclude-module", "celery",
            "--exclude-module", "pandas",
            "--exclude-module", "openpyxl",
            "--exclude-module", "pytest",
            "--exclude-module", "tkinter",
            "--exclude-module", "matplotlib",
        ]

        # Console vs noconsole
        if debug:
            cmd.append("--console")
            print("  MODO DEBUG: console visível")
        else:
            cmd.append("--noconsole")
            print("  MODO PRODUÇÃO: console oculto")

        # Ícone (se existir)
        if os.path.isfile(ICON_PATH):
            cmd.extend(["--icon", ICON_PATH])
            print(f"  Ícone: {ICON_PATH}")
        else:
            print("  Ícone: padrão (nenhum .ico encontrado)")

        cmd.append(ENTRY_POINT)

    print(f"\n  Comando: {' '.join(cmd)}\n")
    start = time.time()
    subprocess.check_call(cmd, cwd=ROOT_DIR)
    elapsed = time.time() - start

    exe_path = os.path.join(DIST_DIR, f"{OUTPUT_NAME}.exe")
    return exe_path, elapsed


def verify(exe_path: str) -> None:
    """Verifica se o .exe foi gerado."""
    banner("VERIFICAÇÃO")
    if os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"  SUCESSO: {exe_path}")
        print(f"  Tamanho: {size_mb:.1f} MB")
        print()
        print("  Para testar:")
        print(f'    "{exe_path}"')
        print()
        print("  O agente vai iniciar na porta 8100.")
        print("  Acesse http://localhost:8100/docs para ver a API.")
        print("  Acesse http://localhost:8100/health para verificar status.")
    else:
        print(f"  FALHA: Arquivo não encontrado em {exe_path}")
        sys.exit(1)


def main():
    os.chdir(ROOT_DIR)

    debug = "--debug" in sys.argv
    do_obfuscate = "--obfuscate" in sys.argv

    banner("FORGELINK AGENT — BUILD SYSTEM")
    print(f"  Diretório: {ROOT_DIR}")
    print(f"  Python:    {sys.executable}")
    print(f"  Modo:      {'DEBUG' if debug else 'PRODUÇÃO'}")
    print(f"  Ofuscação: {'SIM (PyArmor)' if do_obfuscate else 'NÃO'}")

    clean()
    ensure_pyinstaller()

    if do_obfuscate:
        if ensure_pyarmor():
            obf_dir = obfuscate()
            print(f"\n  Arquivos ofuscados em: {obf_dir}")
            print("  Use os arquivos ofuscados como entry point no PyInstaller.")
        else:
            print("\n  AVISO: Continuando sem ofuscação.")

    exe_path, elapsed = build(debug)
    verify(exe_path)

    banner(f"BUILD CONCLUÍDO EM {elapsed:.0f}s")


if __name__ == "__main__":
    main()
