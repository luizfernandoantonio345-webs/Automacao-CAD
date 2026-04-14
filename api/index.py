from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger("engcad.api")

# Initialize app to None first, then assign
app: FastAPI = None  # type: ignore

# Determine allowed origins based on environment
_IS_PRODUCTION = os.getenv("VERCEL_ENV") == "production" or os.getenv("APP_ENV") == "production"
_ALLOWED_ORIGINS = [
    "https://automacao-cad-frontend.vercel.app",
    "https://automacao-cad-backend.vercel.app",
]
if not _IS_PRODUCTION:
    _ALLOWED_ORIGINS.extend(["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"])

# Attempt to import the full server, fallback to minimal API on error
try:
    from server import app as server_app
    app = server_app
    logger.info("Server importado com sucesso")
except Exception as e:
    # If the full server fails, create a minimal diagnostic API (secure)
    _import_error = str(e)
    _import_traceback = ""
    import traceback
    _import_traceback = traceback.format_exc()
    logger.error("Falha ao importar server: %s", _import_error)
    
    app = FastAPI(title="Engenharia CAD - Maintenance Mode")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    
    @app.get("/")
    async def root():
        return {
            "status": "maintenance",
            "message": "Sistema em manutenção. Tente novamente em alguns minutos."
        }
    
    @app.get("/_debug/error")
    async def debug_error():
        """DEBUG: Show import error (only in dev/staging)"""
        debug_on = os.getenv("DEBUG_ENABLED", "").strip().lower() in ("true", "1", "yes")
        if os.getenv("VERCEL_ENV") == "production" and not debug_on:
            return {"error": "Debug disabled in production"}
        return {
            "error": _import_error,
            "traceback": _import_traceback.split("\n") if _import_traceback else []
        }
    
    @app.get("/health")
    async def health():
        return {
            "status": "degraded",
            "mode": "maintenance",
            "message": "Serviço temporariamente indisponível"
        }
    
    @app.get("/healthz")
    async def healthz():
        return {"status": "degraded"}
    
    @app.get("/api/cam/materials")
    async def cam_materials_fallback():
        return {"error": "Serviço CAM temporariamente indisponível", "materials": []}

    @app.get("/api/chatcad/examples")
    async def chatcad_examples_fallback():
        return {
            "basico": [
                {"comando": "Criar círculo com raio 50mm", "descricao": "Desenha um círculo"},
                {"comando": "Desenhar linha de 100mm horizontal", "descricao": "Linha horizontal"},
            ]
        }

    @app.post("/api/chatcad/chat")
    async def chatcad_chat_fallback(request: Request):
        body = await request.json()
        return {
            "success": False,
            "tipo": "erro",
            "resposta": {"response": "Servidor em manutenção. Tente novamente em instantes."},
        }

    @app.post("/api/chatcad/interpret")
    async def chatcad_interpret_fallback(request: Request):
        return {"success": False, "error": "Serviço em manutenção"}

    @app.get("/api/ai/engines")
    async def ai_engines_fallback():
        return {"engines": []}

    @app.get("/api/ai/status")
    async def ai_status_fallback():
        return {"status": "maintenance", "engines": {}}
