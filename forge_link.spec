# -*- mode: python ; coding: utf-8 -*-
"""
Engenharia CAD — ForgeLink Agent — PyInstaller Spec File
Gera executável único (.exe) do Proxy de Desenho Local.
Uso: pyinstaller forge_link.spec
═══════════════════════════════════════════════════════════════════════════════
"""
import os
import sys

block_cipher = None

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.dirname(SPECPATH)) if 'SPECPATH' in dir() else os.getcwd()

a = Analysis(
    ['forge_link_agent.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Dados de engenharia necessários em runtime
        ('data', 'data'),
        # Módulos do backend (driver COM + rotas)
        ('backend', 'backend'),
    ],
    hiddenimports=[
        # ── FastAPI + Uvicorn ──
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'uvicorn',
        'uvicorn.config',
        'uvicorn.main',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.logging',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.responses',
        'starlette.requests',
        'starlette.exceptions',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        # ── Pydantic ──
        'pydantic',
        'pydantic.fields',
        'pydantic._internal',
        'pydantic._internal._core_utils',
        # ── AutoCAD COM (pywin32) ──
        'win32com',
        'win32com.client',
        'win32com.server',
        'pythoncom',
        'pywintypes',
        'win32api',
        # ── HTTP client (validação de token) ──
        'httpx',
        'httpx._transports',
        'httpcore',
        # ── Utilitários ──
        'psutil',
        'multiprocessing',
        'encodings',
        'encodings.utf_8',
        'encodings.latin_1',
        'encodings.ascii',
        # ── HWID (licenciamento por máquina) ──
        'backend.hwid',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ── Excluir dependências pesadas do Servidor Central ──
        # O Agente Local NÃO precisa de IA, DB, cache, celery
        'langchain',
        'langchain_ollama',
        'ollama',
        'sqlalchemy',
        'alembic',
        'psycopg2',
        'redis',
        'celery',
        'pandas',
        'openpyxl',
        'pytest',
        'pytest_asyncio',
        'sse_starlette',
        'passlib',
        'bcrypt',
        'jwt',
        'pyjwt',
        'python_dotenv',
        'dotenv',
        # UI / Teste
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'cv2',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ForgeLinkAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # ← Sem janela de terminal (profissional)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # Substituir por 'assets/engcad.ico' se existir
)
