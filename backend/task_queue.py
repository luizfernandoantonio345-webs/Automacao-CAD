"""
═══════════════════════════════════════════════════════════════════════════════
  TASK QUEUE MANAGER — Processamento assíncrono de tarefas pesadas
  Garante que operações de IA, nesting e geração de G-code
  não bloqueiem o event loop do FastAPI
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
import uuid
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("engcad.task_queue")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    retries: int = 0
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round(self.duration_ms, 2),
            "retries": self.retries,
            "progress": self.progress,
            "metadata": self.metadata,
        }


@dataclass
class TaskDefinition:
    id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    timeout_seconds: float = 300.0
    user_email: Optional[str] = None
    callback: Optional[Callable] = None
    use_process_pool: bool = False  # CPU-bound tasks


class TaskQueue:
    """Fila de tarefas com prioridade, retry e progress tracking."""

    def __init__(
        self,
        max_thread_workers: int = 8,
        max_process_workers: int = 4,
        max_history: int = 5000,
    ):
        self.max_thread_workers = max_thread_workers
        self.max_process_workers = max_process_workers
        self.max_history = max_history

        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_thread_workers,
            thread_name_prefix="engcad-task",
        )
        self._process_pool: Optional[ProcessPoolExecutor] = None

        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active_tasks: Dict[str, TaskResult] = {}
        self._history: OrderedDict[str, TaskResult] = OrderedDict()
        self._progress_callbacks: Dict[str, Callable] = {}
        self._running = False
        self._workers: List[asyncio.Task] = []

        self._stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retried": 0,
            "avg_duration_ms": 0.0,
            "active_tasks": 0,
            "queue_size": 0,
            "peak_active": 0,
        }
        self._duration_history: list[float] = []

    def _get_process_pool(self) -> ProcessPoolExecutor:
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(
                max_workers=self.max_process_workers,
            )
        return self._process_pool

    async def start(self, num_workers: int = 4) -> None:
        """Inicia os workers da fila."""
        if self._running:
            return
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info("TaskQueue iniciada com %d workers", num_workers)

    async def stop(self) -> None:
        """Para todos os workers."""
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._thread_pool.shutdown(wait=False)
        if self._process_pool:
            self._process_pool.shutdown(wait=False)
        logger.info("TaskQueue parada")

    async def submit(
        self,
        name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: float = 300.0,
        user_email: Optional[str] = None,
        callback: Optional[Callable] = None,
        use_process_pool: bool = False,
        **kwargs,
    ) -> str:
        """Submete uma tarefa para execução assíncrona."""
        task_id = str(uuid.uuid4())
        task_def = TaskDefinition(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            user_email=user_email,
            callback=callback,
            use_process_pool=use_process_pool,
        )

        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            metadata={"name": name, "user_email": user_email},
        )
        self._active_tasks[task_id] = result
        self._stats["total_submitted"] += 1
        self._stats["queue_size"] = self._queue.qsize() + 1

        # Prioridade negativa para que maior prioridade saia primeiro
        await self._queue.put((-priority.value, time.time(), task_def))
        return task_id

    async def get_status(self, task_id: str) -> Optional[TaskResult]:
        """Retorna o status de uma tarefa."""
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]
        return self._history.get(task_id)

    async def cancel(self, task_id: str) -> bool:
        """Cancela uma tarefa pendente."""
        result = self._active_tasks.get(task_id)
        if result and result.status == TaskStatus.PENDING:
            result.status = TaskStatus.CANCELLED
            self._move_to_history(task_id, result)
            return True
        return False

    def update_progress(self, task_id: str, progress: float, metadata: Optional[Dict] = None) -> None:
        """Atualiza o progresso de uma tarefa (chamado de dentro da tarefa)."""
        result = self._active_tasks.get(task_id)
        if result:
            result.progress = min(max(progress, 0.0), 100.0)
            if metadata:
                result.metadata.update(metadata)

    async def _worker(self, worker_id: int) -> None:
        """Worker que processa tarefas da fila."""
        while self._running:
            try:
                priority, submit_time, task_def = await asyncio.wait_for(
                    self._queue.get(), timeout=5.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            result = self._active_tasks.get(task_def.id)
            if not result or result.status == TaskStatus.CANCELLED:
                continue

            result.status = TaskStatus.RUNNING
            result.started_at = datetime.now(UTC).isoformat()
            self._stats["active_tasks"] += 1
            if self._stats["active_tasks"] > self._stats["peak_active"]:
                self._stats["peak_active"] = self._stats["active_tasks"]

            start_time = time.monotonic()
            retries = 0

            while retries <= task_def.max_retries:
                try:
                    loop = asyncio.get_event_loop()
                    if task_def.use_process_pool:
                        pool = self._get_process_pool()
                        future = loop.run_in_executor(
                            pool, task_def.func, *task_def.args
                        )
                    else:
                        if asyncio.iscoroutinefunction(task_def.func):
                            future = task_def.func(*task_def.args, **task_def.kwargs)
                        else:
                            future = loop.run_in_executor(
                                self._thread_pool,
                                lambda: task_def.func(*task_def.args, **task_def.kwargs),
                            )

                    task_result = await asyncio.wait_for(
                        future, timeout=task_def.timeout_seconds
                    )

                    elapsed = (time.monotonic() - start_time) * 1000
                    result.status = TaskStatus.COMPLETED
                    result.result = task_result
                    result.completed_at = datetime.now(UTC).isoformat()
                    result.duration_ms = elapsed
                    result.progress = 100.0
                    self._stats["total_completed"] += 1
                    self._record_duration(elapsed)

                    if task_def.callback:
                        try:
                            if asyncio.iscoroutinefunction(task_def.callback):
                                await task_def.callback(result)
                            else:
                                task_def.callback(result)
                        except Exception as cb_err:
                            logger.error("Callback error for task %s: %s", task_def.id, cb_err)

                    break

                except asyncio.TimeoutError:
                    retries += 1
                    if retries > task_def.max_retries:
                        elapsed = (time.monotonic() - start_time) * 1000
                        result.status = TaskStatus.FAILED
                        result.error = f"Timeout após {task_def.timeout_seconds}s ({retries} tentativas)"
                        result.completed_at = datetime.now(UTC).isoformat()
                        result.duration_ms = elapsed
                        result.retries = retries
                        self._stats["total_failed"] += 1
                    else:
                        result.status = TaskStatus.RETRYING
                        result.retries = retries
                        self._stats["total_retried"] += 1
                        await asyncio.sleep(min(2 ** retries, 30))

                except Exception as e:
                    retries += 1
                    if retries > task_def.max_retries:
                        elapsed = (time.monotonic() - start_time) * 1000
                        result.status = TaskStatus.FAILED
                        result.error = f"{type(e).__name__}: {str(e)}"
                        result.completed_at = datetime.now(UTC).isoformat()
                        result.duration_ms = elapsed
                        result.retries = retries
                        self._stats["total_failed"] += 1
                        logger.error(
                            "Task %s falhou: %s\n%s",
                            task_def.name, e, traceback.format_exc(),
                        )
                    else:
                        result.status = TaskStatus.RETRYING
                        result.retries = retries
                        self._stats["total_retried"] += 1
                        await asyncio.sleep(min(2 ** retries, 30))

            self._stats["active_tasks"] -= 1
            self._stats["queue_size"] = self._queue.qsize()
            self._move_to_history(task_def.id, result)

    def _move_to_history(self, task_id: str, result: TaskResult) -> None:
        self._active_tasks.pop(task_id, None)
        self._history[task_id] = result
        while len(self._history) > self.max_history:
            self._history.popitem(last=False)

    def _record_duration(self, duration_ms: float) -> None:
        self._duration_history.append(duration_ms)
        if len(self._duration_history) > 1000:
            self._duration_history = self._duration_history[-500:]
        self._stats["avg_duration_ms"] = (
            sum(self._duration_history) / len(self._duration_history)
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "active_tasks": len(self._active_tasks),
            "history_size": len(self._history),
        }

    def get_active_tasks(self, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = self._active_tasks.values()
        if user_email:
            tasks = [t for t in tasks if t.metadata.get("user_email") == user_email]
        return [t.to_dict() for t in tasks]

    def get_history(
        self,
        user_email: Optional[str] = None,
        limit: int = 50,
        status: Optional[TaskStatus] = None,
    ) -> List[Dict[str, Any]]:
        items = list(reversed(self._history.values()))
        if user_email:
            items = [t for t in items if t.metadata.get("user_email") == user_email]
        if status:
            items = [t for t in items if t.status == status]
        return [t.to_dict() for t in items[:limit]]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Retorna a instância singleton do task queue."""
    global _task_queue
    if _task_queue is None:
        max_threads = int(os.getenv("TASK_QUEUE_THREADS", "8"))
        max_processes = int(os.getenv("TASK_QUEUE_PROCESSES", "4"))
        _task_queue = TaskQueue(
            max_thread_workers=max_threads,
            max_process_workers=max_processes,
        )
    return _task_queue
