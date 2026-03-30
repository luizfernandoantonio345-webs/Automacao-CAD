from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr

# Load and validate environment variables
LICENSE_SECRET = os.getenv("LICENSE_SECRET", "default-license-secret-change-me")
if LICENSE_SECRET == "default-license-secret-change-me":
    raise ValueError("LICENSE_SECRET must be set to a secure value in .env file")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LICENSE_FILE = DATA_DIR / "licenses.json"
if not LICENSE_FILE.exists():
    LICENSE_FILE.write_text("[]", encoding="utf-8")

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_LICENSING_REQUESTS_PER_MINUTE", "60"))
_RATE_LIMIT = defaultdict(deque)
_RATE_LOCK = threading.Lock()
_FILE_LOCK = threading.Lock()
LICENSE_KEY_PATTERN = re.compile(r"^[A-Z0-9-]{6,64}$")
MACHINE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{3,128}$")


class LicenseRequest(BaseModel):
    license_key: constr(strip_whitespace=True, min_length=6, max_length=64)
    machine_id: constr(strip_whitespace=True, min_length=3, max_length=128)


app = FastAPI(title="Licensing Server")


def _load_data() -> list[dict]:
    with _FILE_LOCK:
        return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))


def _save_data(data: list[dict]) -> None:
    with _FILE_LOCK:
        LICENSE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _sign_license_data(license_key: str, machine_id: str, activated_at: str) -> str:
    """Sign license data with HMAC-SHA256"""
    data = f"{license_key}|{machine_id}|{activated_at}"
    return hmac.new(LICENSE_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()


def _verify_license_signature(license_data: dict, signature: str) -> bool:
    """Verify license data signature"""
    license_key = license_data.get("license_key", "")
    machine_id = license_data.get("machine_id", "")
    activated_at = license_data.get("activated_at", "")
    expected_signature = _sign_license_data(license_key, machine_id, activated_at)
    return hmac.compare_digest(signature, expected_signature)


def _validate_input(payload: LicenseRequest) -> None:
    if not LICENSE_KEY_PATTERN.fullmatch(payload.license_key.upper()):
        raise HTTPException(status_code=400, detail="Formato de licenca invalido")
    if not MACHINE_ID_PATTERN.fullmatch(payload.machine_id):
        raise HTTPException(status_code=400, detail="Formato de machine_id invalido")


def _enforce_rate_limit(client_ip: str) -> None:
    now = time.time()
    with _RATE_LOCK:
        bucket = _RATE_LIMIT[client_ip]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(status_code=429, detail="Limite de requisicoes excedido")
        bucket.append(now)


@app.middleware("http")
async def middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(client_ip)
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "Erro interno de licenciamento"})


@app.post("/activate")
def activate(payload: LicenseRequest):
    _validate_input(payload)
    license_key = payload.license_key.upper()
    machine_id = payload.machine_id
    data = _load_data()

    for item in data:
        if item["license_key"] == license_key and item["machine_id"] == machine_id:
            # Verify existing signature
            if _verify_license_signature(item, item.get("signature", "")):
                return {"status": "active"}
            else:
                # Invalid signature, remove corrupted entry
                data.remove(item)
                _save_data(data)

    activated_at = str(uuid4())
    entry = {
        "license_key": license_key,
        "machine_id": machine_id,
        "activated_at": activated_at,
        "signature": _sign_license_data(license_key, machine_id, activated_at)
    }
    data.append(entry)
    _save_data(data)
    return {"status": "active"}


@app.post("/validate")
def validate(payload: LicenseRequest):
    _validate_input(payload)
    license_key = payload.license_key.upper()
    machine_id = payload.machine_id
    data = _load_data()
    for item in data:
        if item["license_key"] == license_key and item["machine_id"] == machine_id:
            # Verify signature
            if _verify_license_signature(item, item.get("signature", "")):
                return {"status": "valid"}
            else:
                # Invalid signature, remove corrupted entry
                data.remove(item)
                _save_data(data)
                raise HTTPException(status_code=401, detail="License corrupted")
    raise HTTPException(status_code=401, detail="License invalid")

