from __future__ import annotations

import asyncio
import platform
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jarvis.core.config import Settings


@dataclass(slots=True)
class StartupCommandResult:
    command: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


class StartupManager:
    def __init__(
        self,
        settings: Settings,
        *,
        platform_name: str | None = None,
        runner: Callable[[list[str]], StartupCommandResult] | None = None,
    ) -> None:
        self.settings = settings
        self.platform_name = (platform_name or platform.system()).lower()
        self.project_root = Path(__file__).resolve().parents[2]
        self.main_script = self.project_root / "main.py"
        self.runner = runner or self._run

    def plan(
        self,
        *,
        mode: str | None = None,
        config_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
        python_executable: str | None = None,
    ) -> dict[str, Any]:
        resolved_mode = self._normalize_mode(mode)
        launch_command = self._build_launch_command(
            mode=resolved_mode,
            config_path=config_path,
            host=host,
            port=port,
            python_executable=python_executable,
        )
        task_action = subprocess.list2cmdline(launch_command)
        install_command = self._build_install_command(task_action)
        uninstall_command = self._build_uninstall_command()
        status_command = self._build_status_command()
        return {
            "platform": self.platform_name,
            "supported": self.platform_name == "windows",
            "task_name": self.settings.startup.task_name,
            "mode": resolved_mode,
            "main_script": str(self.main_script),
            "launch_command": launch_command,
            "task_action": task_action,
            "install_command": install_command,
            "uninstall_command": uninstall_command,
            "status_command": status_command,
        }

    async def status(
        self,
        *,
        mode: str | None = None,
        config_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> dict[str, Any]:
        plan = self.plan(mode=mode, config_path=config_path, host=host, port=port)
        if not plan["supported"]:
            return {
                **plan,
                "installed": False,
                "details": {},
                "command_result": None,
                "message": "Startup registration is currently implemented for Windows scheduled tasks.",
            }

        result = await asyncio.to_thread(self.runner, plan["status_command"])
        installed = result.returncode == 0
        details = self._parse_query_output(result.stdout) if installed else {}
        message = "JARVIS startup is registered." if installed else "JARVIS startup is not registered."
        return {
            **plan,
            "installed": installed,
            "details": details,
            "command_result": result.to_dict(),
            "message": message,
        }

    async def install(
        self,
        *,
        mode: str | None = None,
        config_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> dict[str, Any]:
        plan = self.plan(mode=mode, config_path=config_path, host=host, port=port)
        if not plan["supported"]:
            return {
                "ok": False,
                "message": "Startup registration is currently implemented for Windows scheduled tasks.",
                "startup": await self.status(mode=mode, config_path=config_path, host=host, port=port),
                "command_result": None,
            }

        result = await asyncio.to_thread(self.runner, plan["install_command"])
        status = await self.status(mode=mode, config_path=config_path, host=host, port=port)
        ok = result.returncode == 0 and status["installed"]
        message = "Configured JARVIS to start on login." if ok else (result.stderr.strip() or status["message"])
        return {
            "ok": ok,
            "message": message,
            "startup": status,
            "command_result": result.to_dict(),
        }

    async def uninstall(self) -> dict[str, Any]:
        plan = self.plan()
        if not plan["supported"]:
            return {
                "ok": False,
                "message": "Startup registration is currently implemented for Windows scheduled tasks.",
                "startup": await self.status(),
                "command_result": None,
            }

        result = await asyncio.to_thread(self.runner, plan["uninstall_command"])
        status = await self.status()
        removed = result.returncode == 0 or not status["installed"]
        message = "Removed JARVIS startup registration." if removed else (result.stderr.strip() or status["message"])
        return {
            "ok": removed,
            "message": message,
            "startup": status,
            "command_result": result.to_dict(),
        }

    def _normalize_mode(self, mode: str | None) -> str:
        value = (mode or self.settings.startup.default_mode).strip().lower()
        if value not in {"api", "background"}:
            raise ValueError(f"Unsupported startup mode: {mode}")
        return value

    def _build_launch_command(
        self,
        *,
        mode: str,
        config_path: str | None,
        host: str | None,
        port: int | None,
        python_executable: str | None,
    ) -> list[str]:
        command = [python_executable or sys.executable, str(self.main_script)]
        if config_path:
            command.extend(["--config", str(Path(config_path).expanduser().resolve())])
        if mode == "api":
            command.append("--api")
            command.extend(["--host", host or self.settings.runtime.host])
            command.extend(["--port", str(port or self.settings.runtime.port)])
        return command

    def _build_install_command(self, task_action: str) -> list[str]:
        return [
            "schtasks",
            "/Create",
            "/SC",
            "ONLOGON",
            "/TN",
            self.settings.startup.task_name,
            "/TR",
            task_action,
            "/F",
        ]

    def _build_uninstall_command(self) -> list[str]:
        return ["schtasks", "/Delete", "/TN", self.settings.startup.task_name, "/F"]

    def _build_status_command(self) -> list[str]:
        return ["schtasks", "/Query", "/TN", self.settings.startup.task_name, "/V", "/FO", "LIST"]

    def _parse_query_output(self, stdout: str) -> dict[str, str]:
        details: dict[str, str] = {}
        for line in stdout.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized = key.strip().lower().replace(" ", "_")
            details[normalized] = value.strip()
        return details

    def _run(self, command: list[str]) -> StartupCommandResult:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        return StartupCommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )
