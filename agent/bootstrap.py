from __future__ import annotations

import argparse
import importlib.util
import logging
import subprocess
import sys
from pathlib import Path
from typing import Iterable

logger = logging.getLogger("forgelocal.bootstrap")

MIN_PYTHON = (3, 8)
REQUIREMENTS_FILE = Path(__file__).resolve().parents[1] / "requirements-agent.txt"


def _python_ok() -> bool:
    return sys.version_info >= MIN_PYTHON


def _package_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _run_pip_install(args: Iterable[str]) -> None:
    cmd = [sys.executable, "-m", "pip", "install", *list(args)]
    logger.info("Running pip: %s", " ".join(cmd))
    subprocess.check_call(cmd)


def _run_pywin32_postinstall() -> None:
    # pywin32 requires this script on some hosts for COM/service registration.
    postinstall_candidates = [
        Path(sys.executable).parent / "Scripts" / "pywin32_postinstall.py",
        Path(sys.executable).parent / "pywin32_postinstall.py",
    ]
    for candidate in postinstall_candidates:
        if candidate.is_file():
            subprocess.check_call([sys.executable, str(candidate), "-install"])
            logger.info("pywin32 postinstall completed via %s", candidate)
            return
    logger.warning("pywin32_postinstall.py not found; continuing")


def install_dependencies() -> bool:
    if not _python_ok():
        print("Python 3.8+ is required.")
        return False

    try:
        _run_pip_install(["--upgrade", "pip"])

        if REQUIREMENTS_FILE.is_file():
            _run_pip_install(["-r", str(REQUIREMENTS_FILE)])
        else:
            _run_pip_install([
                "pywin32>=306,<308",
                "psutil>=5.9,<8.0",
                "httpx>=0.27,<1.0",
                "fastapi>=0.110,<1.0",
                "uvicorn[standard]>=0.29,<1.0",
                "watchdog>=4.0,<5.0",
            ])

        if _package_installed("win32com"):
            _run_pywin32_postinstall()
        else:
            print("pywin32 installation appears incomplete (win32com not importable)")
            return False

        return True
    except subprocess.CalledProcessError as exc:
        print(f"Dependency bootstrap failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Forge local agent bootstrap")
    parser.add_argument("--install-only", action="store_true", help="install dependencies and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [BOOTSTRAP] %(levelname)s %(message)s")

    ok = install_dependencies()
    if not ok:
        return 1

    if args.install_only:
        print("Dependencies installed successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
