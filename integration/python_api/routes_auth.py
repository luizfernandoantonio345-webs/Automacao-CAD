from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engenharia_automacao.app.auth import AuthService, AuthenticationError, UserRegistrationError

from integration.python_api.config import AppConfig
from integration.python_api.dependencies import get_app_config, get_auth_service, get_current_user, issue_token
from integration.python_api.schemas import LoginRequest, RegisterRequest


router = APIRouter()


@router.post("/login")
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        user = auth_service.authenticate(payload.email, payload.senha)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Credenciais invalidas")

    if not auth_service.verificar_limite(user):
        raise HTTPException(status_code=403, detail="Limite de uso atingido")

    token = issue_token(user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user["email"],
        "empresa": user["empresa"],
        "limite": user["limite"],
        "usado": user["usado"],
    }


@router.post("/auth/register")
def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        user = auth_service.register_user(payload.email, payload.senha, payload.empresa)
    except UserRegistrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = issue_token(user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user["email"],
        "empresa": user["empresa"],
        "limite": user["limite"],
        "usado": user["usado"],
    }


@router.post("/auth/demo")
def demo_login(config: AppConfig = Depends(get_app_config)):
    if not config.allow_demo_login:
        raise HTTPException(status_code=403, detail="Modo demo desabilitado neste ambiente")
    demo_user = {
        "email": "public@system.com",
        "empresa": "Usuario Publico",
        "limite": 100,
        "usado": 0,
    }
    token = issue_token(demo_user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": demo_user["email"],
        "empresa": demo_user["empresa"],
        "limite": demo_user["limite"],
        "usado": demo_user["usado"],
    }


@router.get("/auth/me")
def auth_me(user: dict = Depends(get_current_user)):
    return {
        "email": user["email"],
        "empresa": user["empresa"],
        "limite": user["limite"],
        "usado": user["usado"],
    }
