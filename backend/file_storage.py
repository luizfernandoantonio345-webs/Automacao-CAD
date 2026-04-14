"""
═══════════════════════════════════════════════════════════════════════════════
  FILE STORAGE SERVICE — Armazenamento de arquivos DXF, G-code, relatórios
  Suporta: Local, S3, Azure Blob (auto-detect)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

logger = logging.getLogger("engcad.storage")


class StorageBackend:
    """Interface base para backends de armazenamento."""

    async def save(self, path: str, data: bytes, content_type: str = "") -> str:
        raise NotImplementedError

    async def load(self, path: str) -> bytes:
        raise NotImplementedError

    async def delete(self, path: str) -> bool:
        raise NotImplementedError

    async def exists(self, path: str) -> bool:
        raise NotImplementedError

    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def get_url(self, path: str, expires_seconds: int = 3600) -> str:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Armazenamento em disco local."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        resolved = (self.base_dir / path).resolve()
        if not str(resolved).startswith(str(self.base_dir.resolve())):
            raise ValueError("Tentativa de path traversal detectada")
        return resolved

    async def save(self, path: str, data: bytes, content_type: str = "") -> str:
        full_path = self._resolve(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        logger.info("Arquivo salvo: %s (%d bytes)", path, len(data))
        return path

    async def load(self, path: str) -> bytes:
        full_path = self._resolve(path)
        if not full_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")
        return full_path.read_bytes()

    async def delete(self, path: str) -> bool:
        full_path = self._resolve(path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        base = self._resolve(prefix) if prefix else self.base_dir
        if not base.exists():
            return []
        files = []
        for f in base.rglob("*"):
            if f.is_file():
                rel = f.relative_to(self.base_dir)
                stat = f.stat()
                files.append({
                    "path": str(rel),
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                    "content_type": _guess_content_type(f.suffix),
                })
        return files

    async def get_url(self, path: str, expires_seconds: int = 3600) -> str:
        return f"/api/storage/download/{path}"


class S3Storage(StorageBackend):
    """Armazenamento em AWS S3 / compatible (R2, MinIO)."""

    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=os.getenv("S3_ENDPOINT_URL"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
        return self._client

    async def save(self, path: str, data: bytes, content_type: str = "") -> str:
        import asyncio
        key = f"{self.prefix}{path}" if self.prefix else path
        ct = content_type or _guess_content_type(Path(path).suffix)
        client = self._get_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=ct,
            ),
        )
        return key

    async def load(self, path: str) -> bytes:
        import asyncio
        key = f"{self.prefix}{path}" if self.prefix else path
        client = self._get_client()
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.get_object(Bucket=self.bucket, Key=key),
        )
        return resp["Body"].read()

    async def delete(self, path: str) -> bool:
        import asyncio
        key = f"{self.prefix}{path}" if self.prefix else path
        client = self._get_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.delete_object(Bucket=self.bucket, Key=key),
        )
        return True

    async def exists(self, path: str) -> bool:
        import asyncio
        key = f"{self.prefix}{path}" if self.prefix else path
        client = self._get_client()
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.head_object(Bucket=self.bucket, Key=key),
            )
            return True
        except Exception:
            return False

    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        import asyncio
        full_prefix = f"{self.prefix}{prefix}" if self.prefix else prefix
        client = self._get_client()
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.list_objects_v2(Bucket=self.bucket, Prefix=full_prefix),
        )
        files = []
        for obj in resp.get("Contents", []):
            files.append({
                "path": obj["Key"],
                "size_bytes": obj["Size"],
                "modified_at": obj["LastModified"].isoformat(),
            })
        return files

    async def get_url(self, path: str, expires_seconds: int = 3600) -> str:
        import asyncio
        key = f"{self.prefix}{path}" if self.prefix else path
        client = self._get_client()
        url = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_seconds,
            ),
        )
        return url


class FileStorageService:
    """Serviço de armazenamento com suporte a múltiplos backends e organização por tenant."""

    def __init__(self, backend: StorageBackend):
        self.backend = backend
        self._stats = {"uploads": 0, "downloads": 0, "total_bytes": 0}

    def _user_path(self, user_email: str, category: str, filename: str) -> str:
        safe_user = user_email.replace("@", "_at_").replace(".", "_")
        safe_filename = Path(filename).name  # Prevent path traversal
        return f"{safe_user}/{category}/{safe_filename}"

    async def upload_file(
        self,
        user_email: str,
        category: str,
        filename: str,
        data: bytes,
        content_type: str = "",
    ) -> Dict[str, Any]:
        """Upload com deduplicação por hash."""
        file_hash = hashlib.sha256(data).hexdigest()
        ext = Path(filename).suffix
        unique_name = f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{file_hash[:8]}{ext}"
        path = self._user_path(user_email, category, unique_name)

        stored_path = await self.backend.save(path, data, content_type)
        self._stats["uploads"] += 1
        self._stats["total_bytes"] += len(data)

        return {
            "path": stored_path,
            "original_name": filename,
            "size_bytes": len(data),
            "hash": file_hash,
            "content_type": content_type or _guess_content_type(ext),
            "uploaded_at": datetime.now(UTC).isoformat(),
        }

    async def download_file(self, path: str) -> Tuple[bytes, str]:
        data = await self.backend.load(path)
        self._stats["downloads"] += 1
        content_type = _guess_content_type(Path(path).suffix)
        return data, content_type

    async def delete_file(self, path: str) -> bool:
        return await self.backend.delete(path)

    async def list_user_files(
        self, user_email: str, category: str = ""
    ) -> List[Dict[str, Any]]:
        safe_user = user_email.replace("@", "_at_").replace(".", "_")
        prefix = f"{safe_user}/{category}" if category else safe_user
        return await self.backend.list_files(prefix)

    async def get_download_url(self, path: str, expires: int = 3600) -> str:
        return await self.backend.get_url(path, expires)

    @property
    def stats(self) -> Dict[str, Any]:
        return self._stats


def _guess_content_type(suffix: str) -> str:
    mapping = {
        ".dxf": "application/dxf",
        ".dwg": "application/acad",
        ".nc": "text/plain",
        ".gcode": "text/plain",
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".json": "application/json",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
    }
    return mapping.get(suffix.lower(), "application/octet-stream")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_storage: Optional[FileStorageService] = None


def get_storage() -> FileStorageService:
    """Retorna instância singleton do serviço de armazenamento."""
    global _storage
    if _storage is not None:
        return _storage

    s3_bucket = os.getenv("S3_BUCKET", "").strip()
    if s3_bucket:
        backend = S3Storage(bucket=s3_bucket, prefix=os.getenv("S3_PREFIX", ""))
        logger.info("Storage: S3 (bucket=%s)", s3_bucket)
    else:
        base_dir = os.getenv("STORAGE_DIR", "")
        if not base_dir:
            if os.getenv("VERCEL"):
                base_dir = "/tmp/engcad_files"
            else:
                base_dir = str(Path(__file__).resolve().parents[1] / "data" / "files")
        backend = LocalStorage(base_dir=base_dir)
        logger.info("Storage: Local (dir=%s)", base_dir)

    _storage = FileStorageService(backend=backend)
    return _storage
