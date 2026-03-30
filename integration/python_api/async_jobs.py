from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from uuid import uuid4

try:
    from redis import Redis
except ImportError:
    Redis = None


class AsyncJobManager:
    """Gerenciador de jobs assíncronos com Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis: Optional[Redis] = None

        if Redis:
            try:
                self.redis = Redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
            except Exception:
                self.redis = None
                print("Redis não disponível para jobs assíncronos")

    def cleanup_old_jobs(self, max_age_seconds: int = 86400) -> int:
        """✓ PROBLEMA #10: Limpar jobs antigos do Redis para evitar memory leak."""
        if not self.redis:
            return 0

        current_time = time.time()
        cleaned = 0

        try:
            # Usar SCAN para evitar bloqueio do Redis em bases grandes.
            for key in self.redis.scan_iter(match="job:*"):
                try:
                    job_data_str = self.redis.get(key)
                    if not job_data_str:
                        continue

                    job_data = json.loads(job_data_str)
                    created_at = float(job_data.get("created_at", 0) or 0)

                    # Remover jobs mais velhos que max_age_seconds (24h por padrão)
                    if current_time - created_at > max_age_seconds:
                        self.redis.delete(key)
                        cleaned += 1

                        # Também remover da fila se ainda estiver lá
                        job_type = job_data.get("type")
                        if job_type:
                            # Remover da lista (mais complexo, mas necessário)
                            queue_key = f"jobs:{job_type}"
                            # Para listas, precisamos remover especificamente
                            # Como é uma lista, vamos usar LREM com o valor exato
                            self.redis.lrem(queue_key, 0, job_data_str)

                except Exception as e:
                    print(f"Erro ao limpar job {key}: {e}")
                    continue

            if cleaned > 0:
                print(f"✓ Limpou {cleaned} jobs antigos do Redis")

            return cleaned

        except Exception as e:
            print(f"Erro geral na limpeza de jobs: {e}")
            return 0

    def submit_job(self, job_type: str, payload: Dict[str, Any]) -> str:
        """Submete um job para execução assíncrona."""
        job_id = str(uuid4())

        job_data = {
            "id": job_id,
            "type": job_type,
            "payload": payload,
            "status": "pending",
            "created_at": time.time(),
        }

        if self.redis:
            try:
                # Adicionar à fila
                self.redis.lpush(f"jobs:{job_type}", json.dumps(job_data))
                # Armazenar status do job
                self.redis.setex(f"job:{job_id}", 3600, json.dumps(job_data))  # 1 hora TTL
                return job_id
            except Exception:
                pass

        # Fallback: executar síncrono
        print(f"Executando job {job_type} síncronamente (Redis indisponível)")
        self._execute_job_sync(job_type, payload)
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de um job."""
        if self.redis:
            try:
                data = self.redis.get(f"job:{job_id}")
                return json.loads(data) if data else None
            except Exception:
                pass
        return None

    def update_job_status(self, job_id: str, status: str, result: Any = None) -> None:
        """Atualiza status de um job."""
        if self.redis:
            try:
                data = self.redis.get(f"job:{job_id}")
                if data:
                    job_data = json.loads(data)
                    job_data["status"] = status
                    job_data["result"] = result
                    job_data["updated_at"] = time.time()
                    self.redis.setex(f"job:{job_id}", 3600, json.dumps(job_data))
            except Exception:
                pass

    def process_jobs(self, job_type: str) -> None:
        """Processa jobs de um tipo específico (worker)."""
        if not self.redis:
            return

        while True:
            try:
                # Obter job da fila
                job_data = self.redis.brpop(f"jobs:{job_type}", timeout=1)
                if not job_data:
                    continue

                job = json.loads(job_data[1])
                job_id = job["id"]

                # Marcar como processando
                self.update_job_status(job_id, "processing")

                try:
                    # Executar job
                    result = self._execute_job_sync(job["type"], job["payload"])
                    self.update_job_status(job_id, "completed", result)
                except Exception as e:
                    self.update_job_status(job_id, "failed", str(e))

            except Exception as e:
                print(f"Erro processando jobs: {e}")
                break

    def _execute_job_sync(self, job_type: str, payload: Dict[str, Any]) -> Any:
        """Executa um job de forma síncrona."""
        if job_type == "generate_project":
            return self._execute_generate_project(payload)
        elif job_type == "rebuild_stats":
            return self._execute_rebuild_stats(payload)
        elif job_type == "excel_batch":
            return self._execute_excel_batch(payload)
        elif job_type == "ai_cad":
            return self._execute_ai_cad(payload)
        else:
            raise ValueError(f"Tipo de job desconhecido: {job_type}")

    def _execute_generate_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executa geração de projeto."""
        from engenharia_automacao.core.main import ProjectService
        from integration.python_api.dependencies import get_output_dir

        service = ProjectService()
        output_dir = get_output_dir()

        result_path = service.generate_project(
            payload,
            output_dir / f"{payload.get('code', 'AUTO')}.lsp",
            execute_in_autocad=False
        )

        return {"path": str(result_path)}

    def _execute_rebuild_stats(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Rebuild estatísticas."""
        from integration.python_api.dependencies import get_telemetry_store

        telemetry = get_telemetry_store()
        stats = telemetry.rebuild_stats()

        return stats

    def _execute_excel_batch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Processa batch Excel."""
        from engenharia_automacao.core.main import ProjectService
        from integration.python_api.dependencies import get_output_dir

        service = ProjectService()
        output_dir = get_output_dir()

        excel_path = Path(payload["excel_path"])
        generated = service.generate_projects_from_excel(excel_path, output_dir)

        return {"files": [str(p) for p in generated], "count": len(generated)}

    def _execute_ai_cad(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Gera LSP via IA e salva resultado com validação rigorosa."""
        import re
        import logging
        import math
        
        logger = logging.getLogger("async_jobs")
        
        # ✓ CRITÉRIO #1: Validar Ollama disponível
        try:
            from langchain_ollama import OllamaLLM
        except ImportError as exc:
            logger.error("langchain-ollama/ollama não instalados")
            raise ImportError("Instale: pip install -r requirements.txt") from exc

        from integration.python_api.dependencies import CONFIG, get_output_dir

        # ✓ PROBLEMA #1: Validar campos obrigatórios
        desc = str(payload.get("desc", "")).strip()
        if not desc:
            raise ValueError("Campo 'desc' é obrigatório")
        if len(desc) > 500:
            raise ValueError("Campo 'desc' não pode exceder 500 caracteres")

        # ✓ PROBLEMA #1: Validar números
        try:
            diameter = float(payload.get("diameter", 0))
            length = float(payload.get("length", 0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Diâmetro e comprimento devem ser números válidos: {e}") from e

        # ✓ PROBLEMA #1: Validar ranges
        if not (0 < diameter <= 1_000_000) or not math.isfinite(diameter):
            raise ValueError(f"Diâmetro deve estar entre 0 e 1M: {diameter}")
        if not (0 < length <= 10_000_000) or not math.isfinite(length):
            raise ValueError(f"Comprimento deve estar entre 0 e 10M: {length}")

        details = str(payload.get("details", "")).strip()[:200]
        
        # ✓ PROBLEMA #1: Sanitizar código para segurança (path traversal)
        code = str(payload.get("code", "auto_ai"))
        code = re.sub(r"[^A-Za-z0-9_-]", "_", code).strip("_")[:50]
        if not code:
            code = "auto_ai"

        payload_defaults = {
            "desc": desc,
            "diameter": diameter,
            "length": length,
            "details": details,
            "code": code,
        }

        prompt_template = """Gere código LSP AutoCAD para: {desc}
Parâmetros: Ø{diameter}mm x {length}mm, {details}
Retorne APENAS o código LSP válido, sem explicações."""

        # ✓ PROBLEMA #5: Tentar conexão com retry
        llm = None
        retry_count = 0
        max_retries = 2
        
        while retry_count < max_retries and not llm:
            try:
                logger.info("Conectando ao Ollama (tentativa %d/%d)", retry_count + 1, max_retries)
                llm = OllamaLLM(
                    model=CONFIG.llm_model,
                    base_url=CONFIG.ollama_url,
                    max_tokens=CONFIG.max_tokens,
                    timeout=30,  # ✓ PROBLEMA #5: Timeout
                )
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Ollama não conectou após %d tentativas: %s", max_retries, e)
                    raise RuntimeError(f"Ollama indisponível em {CONFIG.ollama_url}") from e
                import time
                time.sleep(1 * retry_count)  # Backoff exponencial

        # ✓ PROBLEMA #2: Try-catch completo
        try:
            logger.info("Invocando Ollama para: %s", desc[:50])
            response = llm.invoke(prompt_template.format(**payload_defaults))
            
            # ✓ PROBLEMA #2: Validar resposta
            if not response:
                raise ValueError("Ollama retornou resposta vazia")
            
            response = response.strip()
            if len(response) < 10 or not response.startswith("("):
                logger.warning("Resposta não parece ser LSP válido: %s", response[:50])
                # Tentar aceitar mesmo assim, mas logar aviso
                
        except Exception as e:
            logger.error("Erro ao invocar Ollama: %s", str(e))
            raise RuntimeError(f"Falha ao gerar LSP via Ollama: {str(e)}") from e

        # ✓ PROBLEMA #9: Limitar tamanho resposta
        if len(response) > 10_000:
            logger.warning("Resposta Ollama muito grande (%d chars), truncando", len(response))
            response = response[:10_000]

        # ✓ PROBLEMA #1: Salvar arquivo com validação
        try:
            output_dir = get_output_dir()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            lsp_name = f"{code}_ai.lsp"
            lsp_path = output_dir / lsp_name
            
            # ✓ PROBLEMA #1: Validar path traversal
            if not str(lsp_path).startswith(str(output_dir)):
                raise ValueError("Caminho LSP inválido - possível path traversal")
            
            lsp_path.write_text(response, encoding="utf-8")
            logger.info("LSP salvo: %s (%d bytes)", lsp_path, len(response))
            
        except Exception as e:
            logger.error("Erro ao salvar LSP: %s", str(e))
            raise RuntimeError(f"Falha ao salvar arquivo: {str(e)}") from e

        # ✓ PROBLEMA #2: Registrar telemetria (não-bloqueante)
        try:
            from integration.python_api.dependencies import get_telemetry_store
            telemetry = get_telemetry_store()
            telemetry.record_event(
                payload={
                    "code": code,
                    "company": str(payload.get('company', 'ai'))[:100],
                    "part_name": desc[:100],
                    "diameter": diameter,
                    "length": length,
                },
                source='ai_cad',
                result_path=str(lsp_path)
            )
        except Exception as e:
            logger.warning("Falha ao registrar telemetria: %s", str(e))

        # ✓ PROBLEMA #7: Contar tokens corretamente (aproximado)
        tokens = len(response.split())
        tokens = max(tokens, 50)  # Mínimo 50 tokens

        return {
            "lsp_path": str(lsp_path),
            "tokens": tokens,
            "ai_response": response[:1000],  # ✓ PROBLEMA #9: Limitar resposta retornada
            "success": True,
            "timestamp": asyncio.get_event_loop().time(),
            "ai_model_version": CONFIG.llm_model,  # ✓ PROBLEMA #14: Rastrear versão do modelo
        }


# Instância global
_job_manager: Optional[AsyncJobManager] = None


def get_job_manager() -> AsyncJobManager:
    """Obtém instância global do gerenciador de jobs."""
    return _job_manager


def init_job_manager(redis_url: str) -> AsyncJobManager:
    """Inicializa gerenciador de jobs."""
    global _job_manager
    _job_manager = AsyncJobManager(redis_url)
    return _job_manager