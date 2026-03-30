from __future__ import annotations

import re
import subprocess
import sys


TARGET_PORTS = (8000, 5000)


def _run(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, shell=False)
    return (completed.stdout or "") + (completed.stderr or "")


def find_pids_by_port(port: int) -> set[int]:
    output = _run(["netstat", "-ano", "-p", "tcp"])
    pattern = re.compile(rf"^\s*TCP\s+\S+:{port}\s+\S+\s+\S+\s+(\d+)\s*$", re.MULTILINE)
    return {int(match.group(1)) for match in pattern.finditer(output)}


def kill_pid(pid: int) -> None:
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, text=True, shell=False)


def main() -> int:
    killed_any = False
    for port in TARGET_PORTS:
        pids = find_pids_by_port(port)
        if not pids:
            print(f"Porta {port}: livre")
            continue

        for pid in sorted(pids):
            print(f"Porta {port}: encerrando PID {pid}")
            kill_pid(pid)
            killed_any = True

    if killed_any:
        print("Portas 8000 e 5000 limpas.")
    else:
        print("Nenhum processo encontrado nas portas 8000 e 5000.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())