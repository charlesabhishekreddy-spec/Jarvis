from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

from jarvis.core.service import Service
from jarvis.security.manager import SecurityManager

from .terminal import ShellCommandResult, TerminalExecutor


class SystemController(Service):
    def __init__(self, security: SecurityManager) -> None:
        super().__init__("jarvis.system")
        self.security = security
        self.terminal = TerminalExecutor(security)

    async def open_path(self, path: str) -> str:
        candidate = Path(path).expanduser().resolve()
        if not candidate.exists():
            return f"Path not found: {candidate}"
        try:
            os.startfile(str(candidate))  # type: ignore[attr-defined]
            return f"Opened {candidate}"
        except Exception as exc:
            return f"Failed to open {candidate}: {exc}"

    async def launch_application(self, application: str) -> str:
        try:
            subprocess.Popen([application])
            return f"Launched {application}"
        except Exception as exc:
            return f"Failed to launch {application}: {exc}"

    async def run_command(self, command: str, workdir: str | None = None) -> dict[str, Any]:
        result: ShellCommandResult = self.terminal.run(command=command, workdir=workdir)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    async def resource_usage(self) -> dict[str, Any]:
        if psutil is None:
            return {"cpu_percent": None, "memory_percent": None, "processes": []}
        processes = [
            {"pid": process.info["pid"], "name": process.info["name"]}
            for process in psutil.process_iter(["pid", "name"])
        ][:10]
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "processes": processes,
        }
