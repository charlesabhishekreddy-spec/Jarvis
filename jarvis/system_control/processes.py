from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Protocol

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


class ProcessBackend(Protocol):
    def list_processes(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def terminate_process(self, pid: int) -> dict[str, Any]:
        raise NotImplementedError


class PsutilProcessBackend:
    def list_processes(self) -> list[dict[str, Any]]:
        processes: list[dict[str, Any]] = []
        for process in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            info = process.info
            processes.append(
                {
                    "pid": int(info["pid"]),
                    "name": str(info.get("name") or "unknown"),
                    "cpu_percent": info.get("cpu_percent"),
                    "memory_percent": info.get("memory_percent"),
                    "status": info.get("status"),
                }
            )
        processes.sort(key=lambda item: (str(item["name"]).lower(), int(item["pid"])))
        return processes

    def terminate_process(self, pid: int) -> dict[str, Any]:
        try:
            process = psutil.Process(int(pid))
        except psutil.NoSuchProcess:
            return {"ok": True, "pid": int(pid), "status": "already_exited", "action": "none"}

        name = process.name()
        try:
            process.terminate()
            process.wait(timeout=3)
            return {"ok": True, "pid": int(pid), "name": name, "status": "stopped", "action": "terminated"}
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
            return {"ok": True, "pid": int(pid), "name": name, "status": "stopped", "action": "killed"}
        except psutil.NoSuchProcess:
            return {"ok": True, "pid": int(pid), "name": name, "status": "already_exited", "action": "none"}


@dataclass(slots=True)
class ProcessController:
    backend: ProcessBackend | None = None

    def __post_init__(self) -> None:
        if self.backend is None and psutil is not None:
            self.backend = PsutilProcessBackend()

    async def list_processes(self, limit: int = 20, query: str | None = None) -> dict[str, Any]:
        if self.backend is None:
            return {
                "ok": True,
                "available": False,
                "processes": [],
                "error": "Process telemetry backend unavailable. Install psutil to inspect running processes.",
            }
        processes = await asyncio.to_thread(self.backend.list_processes)
        if query:
            needle = query.strip().lower()
            processes = [
                process
                for process in processes
                if needle in str(process.get("name", "")).lower() or needle == str(process.get("pid"))
            ]
        limited = processes[: max(limit, 1)]
        return {
            "ok": True,
            "available": True,
            "count": len(limited),
            "processes": limited,
        }

    async def terminate_process(self, pid: int | None = None, name: str | None = None) -> dict[str, Any]:
        if self.backend is None:
            return {
                "ok": False,
                "error": "Process control backend unavailable. Install psutil to manage running processes.",
            }

        if pid is None and not (name or "").strip():
            return {"ok": False, "error": "Provide a process pid or exact name."}

        processes = await asyncio.to_thread(self.backend.list_processes)
        matches = self._find_matches(processes, pid=pid, name=name)
        if not matches:
            target = str(pid) if pid is not None else str(name).strip()
            return {"ok": False, "error": f"Process not found: {target}"}
        if len(matches) > 1:
            preview = [{"pid": item["pid"], "name": item["name"]} for item in matches[:10]]
            target = str(name).strip()
            return {
                "ok": False,
                "error": f"Multiple processes matched '{target}'. Provide a pid instead.",
                "matches": preview,
            }

        target = matches[0]
        protected = {os.getpid(), os.getppid()}
        if int(target["pid"]) in protected:
            return {
                "ok": False,
                "error": "Refusing to terminate the current JARVIS process or its parent shell.",
                "pid": int(target["pid"]),
                "name": str(target["name"]),
            }

        try:
            result = await asyncio.to_thread(self.backend.terminate_process, int(target["pid"]))
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Failed to terminate process {int(target['pid'])}: {exc}",
                "pid": int(target["pid"]),
                "name": str(target["name"]),
            }

        message = self._termination_message(result, fallback_name=str(target["name"]))
        return {
            **result,
            "ok": bool(result.get("ok", True)),
            "pid": int(result.get("pid", target["pid"])),
            "name": str(result.get("name", target["name"])),
            "message": message,
        }

    def _find_matches(
        self,
        processes: list[dict[str, Any]],
        pid: int | None = None,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        if pid is not None:
            return [process for process in processes if int(process.get("pid", -1)) == int(pid)]
        if name is None:
            return []
        normalized = name.strip().lower()
        return [process for process in processes if str(process.get("name", "")).lower() == normalized]

    def _termination_message(self, result: dict[str, Any], fallback_name: str) -> str:
        name = str(result.get("name") or fallback_name)
        pid = int(result.get("pid", -1))
        action = str(result.get("action") or "")
        status = str(result.get("status") or "")
        if status == "already_exited":
            return f"Process {name} ({pid}) already exited."
        if action == "killed":
            return f"Killed process {name} ({pid})."
        return f"Terminated process {name} ({pid})."
