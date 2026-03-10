from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

from jarvis.core.config import Settings
from jarvis.core.service import Service
from jarvis.security.manager import SecurityManager

from .desktop import DesktopController
from .startup import StartupManager
from .terminal import ShellCommandResult, TerminalExecutor


class SystemController(Service):
    def __init__(self, security: SecurityManager, settings: Settings) -> None:
        super().__init__("jarvis.system")
        self.security = security
        self.desktop = DesktopController()
        self.startup = StartupManager(settings)
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

    async def list_files(
        self,
        path: str | None = None,
        recursive: bool = False,
        limit: int = 50,
        pattern: str | None = None,
    ) -> dict[str, Any]:
        target = Path(path or self.security.settings.allowed_workdirs[0]).expanduser().resolve()
        if not target.exists():
            return {"ok": False, "error": f"Path not found: {target}"}
        if not self.security.is_path_allowed(str(target)):
            return {"ok": False, "error": f"Blocked path: {target}"}
        if target.is_file():
            return {"ok": True, "path": str(target), "files": [str(target)]}

        iterator = target.rglob(pattern or "*") if recursive else target.glob(pattern or "*")
        files = [str(item) for item in iterator if item.is_file()][: max(limit, 1)]
        directories = [str(item) for item in (target.iterdir() if target.is_dir() else []) if item.is_dir()][: max(limit, 1)]
        return {"ok": True, "path": str(target), "files": files, "directories": directories}

    async def read_text_file(self, path: str, max_chars: int = 8000) -> dict[str, Any]:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return {"ok": False, "error": f"Path not found: {target}"}
        if not target.is_file():
            return {"ok": False, "error": f"Not a file: {target}"}
        if not self.security.is_path_allowed(str(target.parent)):
            return {"ok": False, "error": f"Blocked path: {target}"}
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return {"ok": False, "error": f"Failed to read file: {exc}"}
        return {"ok": True, "path": str(target), "content": content[: max(max_chars, 1)]}

    async def list_processes(self, limit: int = 20) -> dict[str, Any]:
        if psutil is None:
            return {"ok": True, "processes": []}
        processes = [
            {
                "pid": process.info["pid"],
                "name": process.info["name"],
                "cpu_percent": process.info.get("cpu_percent"),
                "memory_percent": process.info.get("memory_percent"),
            }
            for process in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"])
        ][: max(limit, 1)]
        return {"ok": True, "processes": processes}

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

    async def startup_status(
        self,
        mode: str | None = None,
        config_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> dict[str, Any]:
        return await self.startup.status(mode=mode, config_path=config_path, host=host, port=port)

    async def install_startup(
        self,
        mode: str | None = None,
        config_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> dict[str, Any]:
        return await self.startup.install(mode=mode, config_path=config_path, host=host, port=port)

    async def uninstall_startup(self) -> dict[str, Any]:
        return await self.startup.uninstall()

    async def desktop_status(self) -> dict[str, Any]:
        return await self.desktop.status()

    async def move_mouse(self, x: int, y: int, duration: float = 0.0) -> dict[str, Any]:
        return await self.desktop.move_mouse(x=x, y=y, duration=duration)

    async def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        return await self.desktop.click(x=x, y=y, button=button, clicks=clicks)

    async def type_text(self, text: str, interval: float = 0.0) -> dict[str, Any]:
        return await self.desktop.type_text(text=text, interval=interval)

    async def press_keys(self, keys: list[str]) -> dict[str, Any]:
        return await self.desktop.press_keys(keys)
