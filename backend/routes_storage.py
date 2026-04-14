"""
═══════════════════════════════════════════════════════════════════════════════
  FILE STORAGE ROUTES — Upload, download e gestão de arquivos
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import Response

from backend.file_storage import get_storage

logger = logging.getLogger("engcad.routes.storage")
router = APIRouter(prefix="/api/storage", tags=["storage"])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _get_user_email(request: Request) -> str:
    """Extrai email do usuário autenticado via middleware."""
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        return user.get("sub", "anonymous")
    return "anonymous"


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = Query("general", regex="^[a-zA-Z0-9_-]+$"),
):
    """Upload de arquivo com organização por usuário e categoria."""
    user_email = _get_user_email(request)
    data = await file.read()

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"Arquivo muito grande. Máximo: {MAX_UPLOAD_SIZE // (1024*1024)} MB")

    if not file.filename:
        raise HTTPException(400, "Nome do arquivo é obrigatório")

    storage = get_storage()
    result = await storage.upload_file(
        user_email=user_email,
        category=category,
        filename=file.filename,
        data=data,
        content_type=file.content_type or "",
    )
    return {"status": "ok", "file": result}


@router.get("/files")
async def list_files(
    request: Request,
    category: str = Query("", regex="^[a-zA-Z0-9_-]*$"),
):
    """Lista arquivos do usuário autenticado."""
    user_email = _get_user_email(request)
    storage = get_storage()
    files = await storage.list_user_files(user_email, category)
    return {"files": files, "count": len(files)}


@router.get("/download/{path:path}")
async def download_file(path: str, request: Request):
    """Download de arquivo."""
    user_email = _get_user_email(request)
    # Verificar que o arquivo pertence ao usuário
    safe_user = user_email.replace("@", "_at_").replace(".", "_")
    if not path.startswith(safe_user) and user_email != "anonymous":
        raise HTTPException(403, "Acesso negado a este arquivo")

    storage = get_storage()
    try:
        data, content_type = await storage.download_file(path)
    except FileNotFoundError:
        raise HTTPException(404, "Arquivo não encontrado")

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{path.split("/")[-1]}"'},
    )


@router.delete("/files/{path:path}")
async def delete_file(path: str, request: Request):
    """Remove arquivo do usuário."""
    user_email = _get_user_email(request)
    safe_user = user_email.replace("@", "_at_").replace(".", "_")
    if not path.startswith(safe_user):
        raise HTTPException(403, "Acesso negado a este arquivo")

    storage = get_storage()
    deleted = await storage.delete_file(path)
    if not deleted:
        raise HTTPException(404, "Arquivo não encontrado")
    return {"status": "ok", "deleted": path}


@router.get("/stats")
async def storage_stats():
    """Estatísticas de armazenamento."""
    storage = get_storage()
    return storage.stats
