from __future__ import annotations

import sys
import traceback
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Attempt to import the full server, fallback to minimal API on error
try:
    from server import app
except Exception as e:
    # If the full server fails, create a minimal diagnostic API
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="Engenharia CAD - Fallback Mode")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    _import_error = str(e)
    _import_traceback = traceback.format_exc()
    
    @app.get("/")
    async def root():
        return {"status": "fallback", "error": _import_error}
    
    @app.get("/health")
    async def health():
        return {
            "status": "error",
            "mode": "fallback",
            "import_error": _import_error,
            "traceback": _import_traceback.split("\n")
        }
    
    @app.get("/api/cam/materials")
    async def cam_materials_fallback():
        return {"error": "CAM module not available", "reason": _import_error}
