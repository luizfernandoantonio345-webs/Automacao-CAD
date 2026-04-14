from __future__ import annotations

import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from backend.autocad_detector import AutoCADDetector
from backend.autocad_driver import DriverStatus, acad_driver
from backend.hwid import generate_hwid

logger = logging.getLogger("forgelocal.cad_manager")


@dataclass
class CadManagerStatus:
    connected: bool
    driver_status: str
    cad_running: bool
    process_id: int | None
    cad_type: str | None
    reconnect_attempts: int


class BridgePoller:
    def __init__(
        self,
        backend_url: str,
        drop_dir: str,
        heartbeat_interval_s: float = 5.0,
        poll_interval_s: float = 3.0,
        timeout_s: float = 10.0,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.drop_dir = Path(drop_dir)
        self.drop_dir.mkdir(parents=True, exist_ok=True)
        self.heartbeat_interval_s = heartbeat_interval_s
        self.poll_interval_s = poll_interval_s
        self.timeout_s = timeout_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_heartbeat = 0.0
        self._hwid = generate_hwid()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="BridgePoller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            now = time.time()
            if now - self._last_heartbeat >= self.heartbeat_interval_s:
                self._send_heartbeat()
                self._last_heartbeat = now

            self._fetch_and_process_commands()
            self._stop_event.wait(self.poll_interval_s)

    def _send_heartbeat(self) -> None:
        payload = {
            "connected": True,
            "cad_type": "AutoCAD",
            "cad_version": "unknown",
            "machine": socket.gethostname(),
            "hwid": self._hwid,
        }
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                client.post(f"{self.backend_url}/api/bridge/connection", json=payload)
        except Exception as exc:
            logger.warning("Bridge heartbeat failed: %s", exc)

    def _fetch_and_process_commands(self) -> None:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout_s) as client:
                    response = client.get(f"{self.backend_url}/api/bridge/pending")
                    response.raise_for_status()
                    payload = response.json() if response.content else {}
                break
            except Exception as exc:
                logger.warning("Bridge fetch attempt %d/%d failed: %s", attempt+1, max_retries, exc)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Bridge fetch failed after %d retries", max_retries)
                    return

        commands = payload.get("commands", [])
        for command in commands:
            cmd_id = command.get("id")
            lisp_code = command.get("lisp_code", "")
            if not cmd_id or not lisp_code:
                continue
            file_path = self.drop_dir / f"cmd_{cmd_id}_{int(time.time())}.lsp"
            if not file_path.exists():  # Idempotent: skip if already processed
                try:
                    file_path.write_text(lisp_code, encoding="utf-8")
                    logger.debug("Bridge command %s written to %s", cmd_id, file_path)
                    self._ack_command(str(cmd_id))
                except Exception as exc:
                    logger.error("Failed writing bridge command %s: %s", cmd_id, exc)
            else:
                logger.debug("Bridge command %s already processed, ACKing", cmd_id)
                self._ack_command(str(cmd_id))

    def _ack_command(self, cmd_id: str) -> None:
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                client.post(f"{self.backend_url}/api/bridge/ack/{cmd_id}")
        except Exception as exc:
            logger.warning("Bridge ack failed for %s: %s", cmd_id, exc)


class CadManager:
    def __init__(
        self,
        backend_url: str,
        lsp_path: str = r"C:\EngenhariaCAD\forge_vigilante.lsp",
        drop_path: str = r"C:\AutoCAD_Drop",
        health_interval_s: float = 30.0,
    ) -> None:
        self.backend_url = backend_url
        self.lsp_path = lsp_path
        self.drop_path = drop_path
        self.health_interval_s = health_interval_s

        self.detector = AutoCADDetector(lsp_path=lsp_path, drop_path=drop_path)
        self.poller = BridgePoller(backend_url=backend_url, drop_dir=drop_path)

        self._reconnect_attempts = 0
        self._stop_event = threading.Event()
        self._watchdog_thread: threading.Thread | None = None

    def initialize(self) -> bool:
        Path(self.drop_path).mkdir(parents=True, exist_ok=True)

        # Force COM mode in local agent (bridge remains handled by BridgePoller).
        acad_driver.set_mode(False)

        if not self.launch_if_not_running(wait_seconds=5):
            logger.warning("AutoCAD launch skipped or unavailable; continuing")

        connected = self.connect_with_retry(max_wait_s=300)
        if connected:
            self.load_lsp_on_connect()

        self.poller.start()
        return connected

    def shutdown(self) -> None:
        self._stop_event.set()
        self.poller.stop()
        acad_driver.disconnect()

    def launch_if_not_running(self, wait_seconds: int = 30) -> bool:
        logger.info("Checking if AutoCAD is running...")
        is_running, _, _ = self.detector.is_cad_running()
        if is_running:
            logger.info("AutoCAD already running")
            return True

        logger.info("AutoCAD not running - launching (timeout %ds)...", wait_seconds)
        launch = self.detector.launch_cad(wait_seconds=wait_seconds)
        if not launch.success:
            logger.warning("AutoCAD launch failed: %s", launch.message)
            return False
        logger.info("✅ AutoCAD launched successfully")
        return True

    def connect_with_retry(self, max_wait_s: int = 60, retry_interval_s: int = 5) -> bool:
        deadline = time.time() + max_wait_s
        attempt = 0
        while time.time() < deadline and not self._stop_event.is_set():
            attempt += 1
            result = acad_driver.connect()
            if result.success and acad_driver.status in (
                DriverStatus.CONNECTED.value,
                DriverStatus.BRIDGE.value,
            ):
                logger.info("AutoCAD connection ready (attempt %d): %s", attempt, result.message)
                return True

            self._reconnect_attempts += 1
            delay = min(retry_interval_s * (2 ** (attempt - 1)), 30)  # Exponential backoff max 30s
            logger.warning("Connect attempt %d failed (retry in %.1fs): %s", attempt, delay, result.message)
            self._stop_event.wait(delay)

        logger.error("Connect retry timeout after %ds", max_wait_s)
        return False

    def load_lsp_on_connect(self) -> None:
        lsp_path = Path(self.lsp_path)
        if not lsp_path.exists():
            logger.warning("LSP file not found: %s", lsp_path)
            return

        normalized = str(lsp_path).replace("\\", "/")
        acad_driver.send_command(f'(load "{normalized}")')
        acad_driver.send_command("(FORGE_START)")

    def start_watchdog(self) -> None:
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return

        self._stop_event.clear()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, name="CadWatchdog", daemon=True)
        self._watchdog_thread.start()

    def _watchdog_loop(self) -> None:
        while not self._stop_event.is_set():
            health = acad_driver.health_check()
            driver_status = str(health.get("driver_status", ""))
            healthy = driver_status in {DriverStatus.CONNECTED.value, DriverStatus.BRIDGE.value}

            if not healthy:
                logger.warning("Driver unhealthy (%s), attempting reconnect", driver_status)
                self.connect_with_retry(max_wait_s=120, retry_interval_s=10)

            self._stop_event.wait(self.health_interval_s)

    def status(self) -> dict[str, Any]:
        running, pid, cad_type = self.detector.is_cad_running()
        health = acad_driver.health_check()
        return CadManagerStatus(
            connected=bool(health.get("driver_status") in {DriverStatus.CONNECTED.value, DriverStatus.BRIDGE.value}),
            driver_status=str(health.get("driver_status", "unknown")),
            cad_running=running,
            process_id=pid,
            cad_type=cad_type.value if cad_type else None,
            reconnect_attempts=self._reconnect_attempts,
        ).__dict__


def build_default_manager() -> CadManager:
    backend_url = os.getenv("FORGELINK_CENTRAL_URL", "http://localhost:8000")
    lsp_path = os.getenv("FORGELINK_LSP_PATH", r"C:\EngenhariaCAD\forge_vigilante.lsp")
    drop_path = os.getenv("AUTOCAD_DROP_PATH", r"C:\AutoCAD_Drop")
    return CadManager(backend_url=backend_url, lsp_path=lsp_path, drop_path=drop_path)
