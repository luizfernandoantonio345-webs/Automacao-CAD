from __future__ import annotations

import logging
import socket
import sys
import threading
import importlib
from pathlib import Path

import httpx

from agent.bootstrap import install_dependencies
from agent.cad_manager import build_default_manager
from forge_link_agent import AGENT_PORT, agent_app

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FORGESERVICE] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "service.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("forgelocal.service")


try:
    servicemanager = importlib.import_module("servicemanager")
    win32event = importlib.import_module("win32event")
    win32service = importlib.import_module("win32service")
    win32serviceutil = importlib.import_module("win32serviceutil")
except ImportError:
    servicemanager = None
    win32event = None
    win32service = None
    win32serviceutil = None

try:
    import uvicorn
except ImportError as exc:
    raise RuntimeError("uvicorn is required for ForgeLocalAgent service") from exc


class _ServiceCore:
    def __init__(self) -> None:
        self._manager = build_default_manager()
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._running = False
        self._health_thread: threading.Thread | None = None

    def start(self) -> None:
        logger.info("Starting ForgeLocalAgent core")
        if not install_dependencies():
            raise RuntimeError("Dependency bootstrap failed")

        self._manager.initialize()
        self._manager.start_watchdog()

        # Health check loop (ping central every 30s)
        def health_loop():
            import time
            while self._running:
                try:
                    with httpx.Client(timeout=5) as client:
                        client.get(f"{self._manager.backend_url}/health")
                    logger.debug("Central backend healthy")
                except Exception:
                    logger.warning("Central backend unhealthy - retrying...")
                time.sleep(30)

        self._running = True
        self._health_thread = threading.Thread(target=health_loop, daemon=True)
        self._health_thread.start()

        config = uvicorn.Config(
            app=agent_app,
            host="0.0.0.0",
            port=AGENT_PORT,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        self._server_thread = threading.Thread(target=self._server.run, name="ForgeLinkAPI", daemon=True)
        self._server_thread.start()

    def stop(self) -> None:
        logger.info("Stopping ForgeLocalAgent core")
        self._running = False
        self._manager.shutdown()
        if self._server:
            self._server.should_exit = True
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=10)
        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=5)


if win32serviceutil is not None:
    class ForgeLocalAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = "ForgeLocalAgent"
        _svc_display_name_ = "Forge CAD Local Agent"
        _svc_description_ = "AutoCAD local agent service with COM bridge and backend sync"

        def __init__(self, args):
            super().__init__(args)
            self.h_wait_stop = win32event.CreateEvent(None, 0, 0, None)
            self._core = _ServiceCore()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._core.stop()
            win32event.SetEvent(self.h_wait_stop)

        def SvcDoRun(self):
            servicemanager.LogInfoMsg("ForgeLocalAgent service starting")
            self._core.start()
            win32event.WaitForSingleObject(self.h_wait_stop, win32event.INFINITE)
            servicemanager.LogInfoMsg("ForgeLocalAgent service stopped")


def run_console() -> int:
    logger.info("Running in console mode on host=%s", socket.gethostname())
    core = _ServiceCore()
    try:
        core.start()
        logger.info("Service core running. Press Ctrl+C to stop.")
        while True:
            threading.Event().wait(1.0)
    except KeyboardInterrupt:
        logger.info("Console stop requested")
    except Exception as exc:
        logger.exception("Service core failed: %s", exc)
        return 1
    finally:
        core.stop()
    return 0


def main() -> int:
    if win32serviceutil is None:
        logger.warning("pywin32 service modules unavailable, using console mode")
        return run_console()

    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ForgeLocalAgentService)
        servicemanager.StartServiceCtrlDispatcher()
        return 0

    win32serviceutil.HandleCommandLine(ForgeLocalAgentService)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
