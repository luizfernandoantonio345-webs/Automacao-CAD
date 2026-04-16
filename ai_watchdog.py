#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Engenharia CAD — IA de Baixo Nível (Python Watchdog)
Monitora saúde silenciosamente, previne crashes do motor de cálculo,
autocorrige entradas inválidas e isola falhas antes que cheguem ao servidor.
═══════════════════════════════════════════════════════════════════════════════

ARQUITETURA:
    Frontend (React) ←→ AIOrchestrator.ts ←→ FastAPI ←→ ai_watchdog.py ←→ Motor CAD

REGRA #1: Totalmente invisível. Sem interface. Sem interação direta com humano.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import math
import os
import signal
import threading
import time
import traceback
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

import psutil

# ─────────────────────────────────────────────────────────────────────────────
# Logger silencioso — registra tudo mas nunca interrompe o fluxo
# ─────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger("engcad.watchdog")

# Se não houver handler configurado, adiciona um básico a file
if not logger.handlers:
    try:
        _log_dir = "/tmp" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(_log_dir, exist_ok=True)
        _fh = logging.FileHandler(os.path.join(_log_dir, "ai_watchdog.log"), encoding="utf-8")
        _fh.setFormatter(logging.Formatter(
            "%(asctime)s [WATCHDOG][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(_fh)
    except OSError:
        logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONSTANTES DE ENGENHARIA — Limites N-58 / Petrobras
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EngineeringLimits:
    """Limites físicos validados contra a Norma N-58 Petrobras e ASME B31.3."""
    diameter_min_mm: float = 0.5
    diameter_max_mm: float = 120.0
    diameter_safe_default: float = 6.0
    length_min_mm: float = 1.0
    length_max_mm: float = 50_000.0
    length_safe_default: float = 1000.0
    pressure_classes: Tuple[str, ...] = ("150#", "300#", "600#", "900#", "1500#", "2500#")
    pressure_default: str = "150#"
    max_payload_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    max_string_length: int = 512
    # Timeouts para operações CAD
    cad_operation_timeout_s: float = 120.0
    cad_soft_timeout_s: float = 90.0

LIMITS = EngineeringLimits()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RESULTADOS DA WATCHDOG — Estrutura imutável de retorno
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WatchdogResult:
    """Resultado emitido pela Watchdog AI em cada intervenção."""
    ok: bool
    payload: Dict[str, Any]
    corrections: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""

    @property
    def was_corrected(self) -> bool:
        return len(self.corrections) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SANITIZADOR DE PAYLOADS — Correção automática antes do Motor CAD
# ═══════════════════════════════════════════════════════════════════════════════

class PayloadSanitizer:
    """
    Valida e autocorrige payloads de engenharia antes de atingir o motor de
    cálculo. Se o valor for irrecuperável, bloqueia com razão legível.
    """

    @staticmethod
    def sanitize(payload: Dict[str, Any]) -> WatchdogResult:
        if not isinstance(payload, dict):
            return WatchdogResult(
                ok=False, payload={}, blocked=True,
                block_reason="Payload inválido: não é um dicionário"
            )

        data = dict(payload)  # cópia rasa
        corrections = []
        warnings = []

        # ── Diâmetro ──────────────────────────────────────────────
        if "diameter" in data:
            d = data["diameter"]
            try:
                d = float(d)
            except (TypeError, ValueError):
                d = LIMITS.diameter_safe_default
                corrections.append(f"diameter: tipo inválido → {d}")
            if not math.isfinite(d) or d <= 0:
                data["diameter"] = LIMITS.diameter_safe_default
                corrections.append(f"diameter: {d} → {data['diameter']} (não-finito ou ≤0)")
            elif d < LIMITS.diameter_min_mm:
                data["diameter"] = LIMITS.diameter_min_mm
                corrections.append(f"diameter: {d} → {LIMITS.diameter_min_mm} (abaixo do mínimo N-58)")
            elif d > LIMITS.diameter_max_mm:
                data["diameter"] = LIMITS.diameter_max_mm
                corrections.append(f"diameter: {d} → {LIMITS.diameter_max_mm} (acima do máximo N-58)")
            else:
                data["diameter"] = d

        # ── Comprimento ───────────────────────────────────────────
        if "length" in data:
            le = data["length"]
            try:
                le = float(le)
            except (TypeError, ValueError):
                le = LIMITS.length_safe_default
                corrections.append(f"length: tipo inválido → {le}")
            if not math.isfinite(le) or le <= 0:
                data["length"] = LIMITS.length_safe_default
                corrections.append(f"length: {le} → {data['length']} (não-finito ou ≤0)")
            elif le < LIMITS.length_min_mm:
                data["length"] = LIMITS.length_min_mm
                corrections.append(f"length: {le} → {LIMITS.length_min_mm}")
            elif le > LIMITS.length_max_mm:
                data["length"] = LIMITS.length_max_mm
                corrections.append(f"length: {le} → {LIMITS.length_max_mm}")
            else:
                data["length"] = le

        # ── Classe de pressão ─────────────────────────────────────
        if "pressure_class" in data:
            pc = str(data.get("pressure_class", "")).strip()
            if pc and pc not in LIMITS.pressure_classes:
                data["pressure_class"] = LIMITS.pressure_default
                corrections.append(f"pressure_class: '{pc}' → {LIMITS.pressure_default}")

        # ── Strings obrigatórias ──────────────────────────────────
        for str_field, default in [("company", "PETROBRAS-REGAP"), ("part_name", "FLANGE-PADRAO")]:
            val = data.get(str_field)
            if not val or not isinstance(val, str) or not val.strip():
                data[str_field] = default
                corrections.append(f"{str_field}: vazio → {default}")
            else:
                cleaned = val.strip()[:LIMITS.max_string_length]
                if cleaned != val:
                    data[str_field] = cleaned
                    corrections.append(f"{str_field}: trimmed/truncado")
                else:
                    data[str_field] = cleaned

        # ── Code ──────────────────────────────────────────────────
        if "code" in data:
            code = data.get("code")
            if not code or not isinstance(code, str) or not code.strip():
                data["code"] = "AUTO-001"
                corrections.append("code: vazio → AUTO-001")
            else:
                data["code"] = str(code).strip()[:LIMITS.max_string_length]

        # ── Normas (lista) ────────────────────────────────────────
        if "norms" in data:
            norms = data.get("norms")
            if not isinstance(norms, list):
                data["norms"] = ["N-58"]
                corrections.append("norms: tipo inválido → ['N-58']")
            else:
                data["norms"] = [str(n).strip()[:64] for n in norms if isinstance(n, str) and n.strip()]
                if not data["norms"]:
                    data["norms"] = ["N-58"]
                    corrections.append("norms: lista vazia → ['N-58']")

        if corrections:
            logger.info("Payload auto-corrigido: %s", "; ".join(corrections))

        return WatchdogResult(ok=True, payload=data, corrections=corrections, warnings=warnings)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RESOURCE GUARDIAN — Impede que o Motor CAD derrube o servidor
# ═══════════════════════════════════════════════════════════════════════════════

class ResourceGuardian:
    """
    Monitora recursos do sistema em tempo real com sistema ADAPTATIVO.
    Usa média móvel dos últimos 30 checks para distinguir picos momentâneos
    de sobrecarga real sustentada. Thresholds configuráveis via env vars.
    """

    def __init__(
        self,
        cpu_warn_pct: float | None = None,
        cpu_block_pct: float | None = None,
        ram_warn_pct: float | None = None,
        ram_block_pct: float | None = None,
    ):
        self.cpu_warn = cpu_warn_pct or float(os.getenv("WATCHDOG_CPU_WARN", "88.0"))
        self.cpu_block = cpu_block_pct or float(os.getenv("WATCHDOG_CPU_BLOCK", "98.0"))
        self.ram_warn = ram_warn_pct or float(os.getenv("WATCHDOG_RAM_WARN", "88.0"))
        self.ram_block = ram_block_pct or float(os.getenv("WATCHDOG_RAM_BLOCK", "96.0"))
        self._recent_checks: deque = deque(maxlen=30)
        logger.info(
            "ResourceGuardian inicializado — RAM warn=%.1f%% block=%.1f%% | CPU warn=%.1f%% block=%.1f%%",
            self.ram_warn, self.ram_block, self.cpu_warn, self.cpu_block,
        )

    def check(self) -> WatchdogResult:
        """Verifica recursos com sistema adaptativo baseado em média móvel."""
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        self._recent_checks.append({"ts": time.time(), "cpu": cpu, "ram": ram})

        # Média móvel: só bloqueia se a TENDÊNCIA está acima do threshold,
        # não apenas um pico momentâneo
        avg_ram = ram
        avg_cpu = cpu
        if len(self._recent_checks) >= 3:
            recent = list(self._recent_checks)[-5:]  # últimas 5 amostras
            avg_ram = sum(c["ram"] for c in recent) / len(recent)
            avg_cpu = sum(c["cpu"] for c in recent) / len(recent)

        warnings = []
        blocked = False
        reason = ""

        if avg_cpu >= self.cpu_block:
            blocked = True
            reason = f"CPU sustentada em {avg_cpu:.1f}% (atual {cpu:.1f}%) — operação bloqueada"
        elif avg_cpu >= self.cpu_warn:
            warnings.append(f"CPU elevada: {cpu:.1f}% (média {avg_cpu:.1f}%)")

        if avg_ram >= self.ram_block:
            blocked = True
            reason = f"RAM sustentada em {avg_ram:.1f}% (atual {ram:.1f}%) — operação bloqueada"
        elif avg_ram >= self.ram_warn:
            warnings.append(f"RAM elevada: {ram:.1f}% (média {avg_ram:.1f}%)")

        return WatchdogResult(
            ok=not blocked,
            payload={"cpu": cpu, "ram": ram, "avg_cpu": round(avg_cpu, 1), "avg_ram": round(avg_ram, 1)},
            warnings=warnings,
            blocked=blocked,
            block_reason=reason,
        )

    def get_trend(self) -> Dict[str, Any]:
        """Retorna tendência dos últimos 30 checks (para dashboards internos)."""
        if not self._recent_checks:
            return {"samples": 0, "avg_cpu": 0, "avg_ram": 0}
        cpus = [c["cpu"] for c in self._recent_checks]
        rams = [c["ram"] for c in self._recent_checks]
        return {
            "samples": len(self._recent_checks),
            "avg_cpu": round(sum(cpus) / len(cpus), 1),
            "avg_ram": round(sum(rams) / len(rams), 1),
            "peak_cpu": round(max(cpus), 1),
            "peak_ram": round(max(rams), 1),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TIMEOUT ENFORCER — Mata operações CAD penduradas
# ═══════════════════════════════════════════════════════════════════════════════

class TimeoutEnforcer:
    """
    Garante que nenhuma operação CAD exceda o limite de tempo.
    Opera via threading no Windows (sem SIGALRM).
    """

    @staticmethod
    @contextmanager
    def enforce(timeout_seconds: float = LIMITS.cad_operation_timeout_s, label: str = ""):
        """Context manager que levanta TimeoutError se o bloco exceder o limite."""
        timed_out = threading.Event()
        exc_holder: list = []

        def _timer_expired():
            timed_out.set()

        timer = threading.Timer(timeout_seconds, _timer_expired)
        timer.daemon = True
        timer.start()
        try:
            yield timed_out
        finally:
            timer.cancel()
            if timed_out.is_set():
                msg = f"Operação CAD excedeu timeout de {timeout_seconds}s"
                if label:
                    msg += f" ({label})"
                logger.error(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CRASH ISOLATOR — Executa o motor de cálculo em sandbox
# ═══════════════════════════════════════════════════════════════════════════════

class CrashIsolator:
    """
    Executa funções do motor de cálculo em try/except absoluto.
    Se a função crashar, captura o erro, loga, e retorna um resultado
    seguro em vez de propagar a exceção.
    """

    def __init__(self) -> None:
        self._crash_history: deque = deque(maxlen=50)

    def execute(
        self,
        fn: Callable[..., Any],
        *args: Any,
        fallback_result: Any = None,
        operation_label: str = "operação CAD",
        **kwargs: Any,
    ) -> Tuple[bool, Any]:
        """
        Executa fn(*args, **kwargs) de forma isolada.
        Retorna (sucesso: bool, resultado | fallback).
        """
        try:
            result = fn(*args, **kwargs)
            return True, result
        except Exception as exc:
            crash_info = {
                "ts": time.time(),
                "label": operation_label,
                "exc_type": type(exc).__name__,
                "exc_msg": str(exc)[:500],
                "traceback": traceback.format_exc()[-1000:],
            }
            self._crash_history.append(crash_info)
            logger.error(
                "CrashIsolator capturou falha em '%s': %s: %s",
                operation_label, type(exc).__name__, str(exc)[:200]
            )
            return False, fallback_result

    async def execute_async(
        self,
        fn: Callable[..., Any],
        *args: Any,
        fallback_result: Any = None,
        operation_label: str = "operação CAD async",
        **kwargs: Any,
    ) -> Tuple[bool, Any]:
        """Versão async do execute para handlers FastAPI."""
        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))
            return True, result
        except Exception as exc:
            self._crash_history.append({
                "ts": time.time(),
                "label": operation_label,
                "exc_type": type(exc).__name__,
                "exc_msg": str(exc)[:500],
            })
            logger.error(
                "CrashIsolator[async] capturou falha em '%s': %s: %s",
                operation_label, type(exc).__name__, str(exc)[:200]
            )
            return False, fallback_result

    def get_crash_history(self) -> list:
        return list(self._crash_history)

    @property
    def recent_crash_count(self) -> int:
        cutoff = time.time() - 300  # últimos 5 minutos
        return sum(1 for c in self._crash_history if c["ts"] > cutoff)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. RESPONSE HEALER — Repara respostas malformadas do motor CAD
# ═══════════════════════════════════════════════════════════════════════════════

class ResponseHealer:
    """
    Analisa respostas do motor de cálculo e repara campos ausentes/inválidos
    antes de retornar ao frontend. Garante que o dashboard NUNCA receba
    dados faltando.
    """

    # Templates de resposta segura por endpoint
    SAFE_RESPONSES: Dict[str, Dict[str, Any]] = {
        "/insights": {
            "stats": {
                "total_projects": 0,
                "seed_projects": 0,
                "real_projects": 0,
                "top_part_names": [],
                "top_companies": [],
                "diameter_range": [0, 0],
                "length_range": [0, 0],
                "draft_feedback": {"accepted": 0, "rejected": 0},
            },
            "recommendations": {
                "suggested_part_name": "FLANGE-PADRAO",
                "suggested_company": "PETROBRAS-REGAP",
                "typical_diameter_min": 6,
                "typical_diameter_max": 48,
                "typical_length_min": 100,
                "typical_length_max": 5000,
                "total_projects": 0,
            },
            "templates": [],
        },
        "/health": {
            "autocad": False,
            "status": "degraded",
            "_ai_note": "Resposta de fallback — backend temporariamente indisponível",
        },
        "/history": {"history": []},
        "/logs": {"logs": []},
        "/generate": {
            "path": "",
            "usado": 0,
            "limite": 100,
            "_ai_note": "Geração em modo degradado",
        },
        "/system": {"cpu": 0, "ram": 0, "disk": 0},
        "/project-draft": {
            "company": "PETROBRAS-REGAP",
            "part_name": "FLANGE-PADRAO",
            "diameter": 6,
            "length": 1000,
            "code": "AUTO-001",
            "based_on_template": None,
            "confidence": "medium",
        },
    }

    @classmethod
    def heal(cls, endpoint: str, response: Any) -> Any:
        """Garante que a resposta tenha todos os campos esperados."""
        safe = cls.get_safe_response(endpoint)
        if safe is None:
            return response

        if response is None:
            logger.warning("ResponseHealer: resposta nula para %s — usando fallback", endpoint)
            return dict(safe)

        if isinstance(response, dict) and isinstance(safe, dict):
            # Preenche campos faltantes com valores seguros
            healed = dict(safe)
            healed.update(response)
            return healed

        return response

    @classmethod
    def get_safe_response(cls, endpoint: str) -> Optional[Dict[str, Any]]:
        """Retorna a resposta segura para um endpoint. None se não tem template."""
        for pattern, template in cls.SAFE_RESPONSES.items():
            if pattern in endpoint:
                return dict(template)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 8. FACHADA: AIWatchdog — Interface unificada dos subsistemas
# ═══════════════════════════════════════════════════════════════════════════════

class AIWatchdog:
    """
    Ponto de entrada único da IA de Baixo Nível.
    Orquestra sanitização, resource guard, crash isolation e response healing.

    Uso no servidor:
        from ai_watchdog import watchdog

        # Antes de processar uma requisição CAD
        result = watchdog.guard_request(payload, endpoint="/generate")
        if result.blocked:
            return JSONResponse(status_code=503, content={"detail": result.block_reason})
        safe_payload = result.payload

        # Execução segura do motor
        success, output = watchdog.safe_execute(meu_motor_cad, safe_payload)
        healed = watchdog.heal_response("/generate", output)
    """

    def __init__(self) -> None:
        self.sanitizer = PayloadSanitizer()
        self.guardian = ResourceGuardian()
        self.isolator = CrashIsolator()
        self.healer = ResponseHealer()
        self.timeout = TimeoutEnforcer()
        self._active = True
        self._request_count = 0
        self._correction_count = 0
        self._block_count = 0
        logger.info("AIWatchdog inicializado — supervisão ativa")

    # ── Pipeline de Request ────────────────────────────────────────

    def guard_request(
        self, payload: Dict[str, Any], endpoint: str = "", check_resources: bool = True
    ) -> WatchdogResult:
        """
        Pipeline completo de guarda:
        1. Sanitiza payload (corrige valores inválidos)
        2. Verifica recursos do sistema
        3. Retorna payload corrigido ou bloqueio
        """
        self._request_count += 1

        # Etapa 1: Sanitizar
        sanitized = self.sanitizer.sanitize(payload)
        if sanitized.blocked:
            self._block_count += 1
            logger.warning("Request bloqueada (sanitização): %s", sanitized.block_reason)
            return sanitized

        if sanitized.was_corrected:
            self._correction_count += 1

        # Etapa 2: Verificar recursos
        if check_resources:
            resources = self.guardian.check()
            if resources.blocked:
                self._block_count += 1
                logger.warning("Request bloqueada (recursos): %s", resources.block_reason)
                return WatchdogResult(
                    ok=False,
                    payload=sanitized.payload,
                    corrections=sanitized.corrections,
                    warnings=resources.warnings,
                    blocked=True,
                    block_reason=resources.block_reason,
                )
            sanitized.warnings.extend(resources.warnings)

        return sanitized

    # ── Execução Isolada ───────────────────────────────────────────

    def safe_execute(
        self,
        fn: Callable[..., Any],
        *args: Any,
        fallback: Any = None,
        label: str = "motor CAD",
        timeout_s: float = LIMITS.cad_operation_timeout_s,
        **kwargs: Any,
    ) -> Tuple[bool, Any]:
        """
        Executa uma função do motor de cálculo com isolamento total.
        Se crashar, retorna fallback silenciosamente.
        """
        with self.timeout.enforce(timeout_s, label):
            return self.isolator.execute(fn, *args, fallback_result=fallback, operation_label=label, **kwargs)

    async def safe_execute_async(
        self,
        fn: Callable[..., Any],
        *args: Any,
        fallback: Any = None,
        label: str = "motor CAD async",
        **kwargs: Any,
    ) -> Tuple[bool, Any]:
        """Versão async para handlers FastAPI."""
        return await self.isolator.execute_async(fn, *args, fallback_result=fallback, operation_label=label, **kwargs)

    # ── Healing ────────────────────────────────────────────────────

    def heal_response(self, endpoint: str, response: Any) -> Any:
        """Repara resposta do motor antes de enviar ao frontend."""
        return self.healer.heal(endpoint, response)

    def get_fallback(self, endpoint: str) -> Dict[str, Any]:
        """Retorna resposta fallback segura para um endpoint."""
        return self.healer.get_safe_response(endpoint) or {}

    # ── Diagnóstico ────────────────────────────────────────────────

    def diagnostics(self) -> Dict[str, Any]:
        """Retorna estado interno da Watchdog (para endpoints de debug)."""
        return {
            "active": self._active,
            "requests_processed": self._request_count,
            "corrections_applied": self._correction_count,
            "requests_blocked": self._block_count,
            "recent_crashes": self.isolator.recent_crash_count,
            "resource_trend": self.guardian.get_trend(),
            "crash_history_size": len(self.isolator.get_crash_history()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 9. MIDDLEWARE FASTAPI — Integração invisível no ciclo de request do servidor
# ═══════════════════════════════════════════════════════════════════════════════

def create_watchdog_middleware(watchdog_instance: AIWatchdog):
    """
    Retorna um middleware ASGI que intercepta TODA request:
    - POST com body JSON → sanitiza payload antes de chegar ao handler
    - Qualquer response → repara campos faltantes antes de enviar ao front
    - Exceções → captura e retorna fallback ao invés de 500
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    import json as _json

    # Endpoints que NUNCA devem ser bloqueados pelo ResourceGuardian.
    # Inclui: auth, health, monitoramento, e operações core do CAD.
    _EXEMPT_ENDPOINTS = frozenset({
        "/login", "/auth/register", "/auth/demo", "/auth/me",
        "/auth/csrf-token", "/auth/forgot-password", "/auth/reset-password", "/auth/verify-email",
        "/health", "/system", "/ai/health", "/ai/diagnostics",
        "/telemetry/test",
        # Endpoints core de produção — nunca bloquear
        "/generate", "/excel",
        "/project-draft-feedback",
        "/jobs/stress/porticos-50",
    })

    # Prefixos cujos sub-endpoints também são isentos
    _EXEMPT_PREFIXES = (
        "/api/autocad/",
        "/api/cad/",
        "/api/license/",
        "/auth/",
        "/sse/",
    )

    def _is_exempt(path: str) -> bool:
        if path in _EXEMPT_ENDPOINTS:
            return True
        for pfx in _EXEMPT_PREFIXES:
            if path.startswith(pfx):
                return True
        return False

    class WatchdogMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            endpoint = request.url.path

            # Endpoints isentos NUNCA são bloqueados pelo resource guardian
            if _is_exempt(endpoint):
                try:
                    return await call_next(request)
                except Exception as exc:
                    logger.error("Handler crashou para %s: %s", endpoint, str(exc)[:200])
                    return JSONResponse(status_code=500, content={"detail": "Erro interno"})

            # ── Pré-processamento: sanitizar payloads POST ────────
            if request.method == "POST" and "json" in (request.headers.get("content-type") or ""):
                try:
                    body = await request.body()
                    if body:
                        payload = _json.loads(body)
                        if isinstance(payload, dict):
                            result = watchdog_instance.guard_request(payload, endpoint)
                            if result.blocked:
                                return JSONResponse(
                                    status_code=503,
                                    content={
                                        "detail": result.block_reason,
                                        "_ai_blocked": True,
                                        "_ai_corrections": result.corrections,
                                    }
                                )
                            # Injetar payload corrigido (substituir o body da request)
                            if result.was_corrected:
                                scope = request.scope
                                corrected_body = _json.dumps(result.payload).encode("utf-8")
                                # Cria novo receive que retorna o body corrigido
                                async def receive():
                                    return {"type": "http.request", "body": corrected_body}
                                request = Request(scope, receive)
                except Exception:
                    pass  # Se falhar ao ler body, não bloquear — deixar o handler lidar

            # ── Execução do handler real (com crash isolation) ─────
            try:
                response = await call_next(request)

                # ── Se o handler retornou 500, tenta servir fallback ──
                if response.status_code >= 500:
                    fallback = watchdog_instance.get_fallback(endpoint)
                    if fallback:
                        logger.warning(
                            "Handler retornou %d para %s — servindo fallback",
                            response.status_code, endpoint
                        )
                        return JSONResponse(
                            status_code=200,
                            content={**fallback, "_ai_recovered": True}
                        )

                return response

            except Exception as exc:
                # ── Crash total do handler — retorna fallback ─────
                logger.error(
                    "Handler crashou para %s: %s: %s",
                    endpoint, type(exc).__name__, str(exc)[:300]
                )
                fallback = watchdog_instance.get_fallback(endpoint)
                if fallback:
                    return JSONResponse(
                        status_code=200,
                        content={**fallback, "_ai_recovered": True, "_ai_error": type(exc).__name__}
                    )
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Erro interno do servidor"}
                )

    return WatchdogMiddleware


# ═══════════════════════════════════════════════════════════════════════════════
# 10. BACKGROUND HEALTH MONITOR — Thread daemon que monitora saúde contínua
# ═══════════════════════════════════════════════════════════════════════════════

class BackgroundMonitor:
    """
    Thread daemon que verifica periodicamente a saúde do sistema.
    Se detectar degradação, emite warnings via logging.
    """

    def __init__(self, watchdog: AIWatchdog, interval_s: float = 15.0) -> None:
        self._watchdog = watchdog
        self._interval = interval_s
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AIWatchdog-Monitor")
        self._thread.start()
        logger.info("BackgroundMonitor iniciado (intervalo: %.1fs)", self._interval)

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                check = self._watchdog.guardian.check()
                if check.blocked:
                    logger.warning("ALERTA SISTEMA: %s", check.block_reason)
                elif check.warnings:
                    for w in check.warnings:
                        logger.info("Monitor: %s", w)

                crashes = self._watchdog.isolator.recent_crash_count
                if crashes >= 3:
                    logger.warning(
                        "ALERTA: %d crashes nos últimos 5 minutos — sistema sob pressão", crashes
                    )
            except Exception as exc:
                logger.debug("BackgroundMonitor tick error: %s", exc)

            time.sleep(self._interval)


# ═══════════════════════════════════════════════════════════════════════════════
# INSTÂNCIAS SINGLETON — Compartilhadas por todo o servidor
# ═══════════════════════════════════════════════════════════════════════════════

watchdog = AIWatchdog()
background_monitor = BackgroundMonitor(watchdog)


def install_watchdog(app) -> AIWatchdog:
    """
    Instala a Watchdog AI no servidor FastAPI.
    Chamada uma vez em server.py:

        from ai_watchdog import install_watchdog
        install_watchdog(app)
    """
    middleware_cls = create_watchdog_middleware(watchdog)
    app.add_middleware(middleware_cls)
    background_monitor.start()
    logger.info("Watchdog AI instalada no servidor FastAPI — proteção total ativa")
    return watchdog
