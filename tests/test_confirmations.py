import asyncio
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from jarvis.core.config import Settings
from jarvis.core.models import TaskStatus
from jarvis.core.runtime import JarvisRuntime
from jarvis.system_control.desktop import DesktopController


class FakeDesktopBackend:
    def __init__(self) -> None:
        self.actions: list[tuple] = []

    def size(self) -> tuple[int, int]:
        return (1920, 1080)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self.actions.append(("move_to", x, y, duration))

    def click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> None:
        self.actions.append(("click", x, y, clicks, button))

    def write(self, text: str, interval: float = 0.0) -> None:
        self.actions.append(("write", text, interval))

    def press(self, key: str) -> None:
        self.actions.append(("press", key))

    def hotkey(self, *keys: str) -> None:
        self.actions.append(("hotkey", *keys))


class FakeProcessBackend:
    def __init__(self) -> None:
        self.records = [
            {"pid": 3001, "name": "python.exe", "cpu_percent": 1.0, "memory_percent": 2.0, "status": "running"},
            {"pid": 3002, "name": "notepad.exe", "cpu_percent": 0.0, "memory_percent": 0.5, "status": "sleeping"},
        ]
        self.terminated: list[int] = []

    def list_processes(self) -> list[dict[str, object]]:
        return [dict(record) for record in self.records if int(record["pid"]) not in self.terminated]

    def terminate_process(self, pid: int) -> dict[str, object]:
        self.terminated.append(int(pid))
        match = next((record for record in self.records if int(record["pid"]) == int(pid)), None)
        return {
            "ok": True,
            "pid": int(pid),
            "name": match["name"] if match else "unknown",
            "status": "stopped",
            "action": "terminated",
        }


class ConfirmationFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = Path.cwd() / ".test_runtime" / uuid4().hex
        self.tempdir.mkdir(parents=True, exist_ok=True)
        settings = Settings()
        settings.runtime.data_dir = str(self.tempdir)
        settings.memory.sqlite_path = str(self.tempdir / "jarvis.db")
        settings.memory.semantic_index_path = str(self.tempdir / "semantic_memory.json")
        settings.security.allowed_workdirs = [str(self.tempdir), str(Path.cwd())]
        self.runtime = JarvisRuntime(settings)
        self.desktop_backend = FakeDesktopBackend()
        self.runtime.system_controller.desktop = DesktopController(self.desktop_backend)
        self.process_backend = FakeProcessBackend()
        self.runtime.system_controller.processes.backend = self.process_backend
        await self.runtime.start()

    async def asyncTearDown(self) -> None:
        await self.runtime.stop()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    async def test_reject_confirmation(self) -> None:
        response = await self.runtime.execute_text("execute cmd /c echo hello", source="test")
        self.assertEqual(response.status, TaskStatus.REQUIRES_CONFIRMATION)
        confirmation_id = response.data["confirmation_id"]

        result = await self.runtime.confirmations.reject(confirmation_id, decision_note="not now")
        self.assertIsNotNone(result)
        self.assertEqual(result["confirmation"]["status"], "rejected")

    async def test_approve_confirmation_queues_execution(self) -> None:
        response = await self.runtime.execute_text("execute cmd /c echo hello", source="test")
        self.assertEqual(response.status, TaskStatus.REQUIRES_CONFIRMATION)
        confirmation_id = response.data["confirmation_id"]

        result = await self.runtime.confirmations.approve(confirmation_id, decision_note="approved in test")
        self.assertIsNotNone(result)
        execution = result["execution"]
        self.assertIsNotNone(execution)

        for _ in range(100):
            snapshot = self.runtime.command_queue.get(execution["request_id"])
            if snapshot and snapshot["status"] in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.02)

        final = self.runtime.command_queue.get(execution["request_id"])
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "completed")
        self.assertIn("hello", (final["message"] or "").lower())

    async def test_approve_desktop_confirmation_executes_click(self) -> None:
        response = await self.runtime.execute_text("Jarvis click at 15 25", source="test")
        self.assertEqual(response.status, TaskStatus.REQUIRES_CONFIRMATION)
        confirmation_id = response.data["confirmation_id"]

        result = await self.runtime.confirmations.approve(confirmation_id, decision_note="approved in test")
        self.assertIsNotNone(result)
        execution = result["execution"]
        self.assertIsNotNone(execution)

        for _ in range(100):
            snapshot = self.runtime.command_queue.get(execution["request_id"])
            if snapshot and snapshot["status"] in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.02)

        final = self.runtime.command_queue.get(execution["request_id"])
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "completed")
        self.assertIn("clicked", (final["message"] or "").lower())
        self.assertEqual(self.desktop_backend.actions[0], ("click", 15, 25, 1, "left"))

    async def test_approve_process_termination_confirmation_executes_kill(self) -> None:
        response = await self.runtime.execute_text("Jarvis stop process 3002", source="test")
        self.assertEqual(response.status, TaskStatus.REQUIRES_CONFIRMATION)
        confirmation_id = response.data["confirmation_id"]

        result = await self.runtime.confirmations.approve(confirmation_id, decision_note="approved in test")
        self.assertIsNotNone(result)
        execution = result["execution"]
        self.assertIsNotNone(execution)

        for _ in range(100):
            snapshot = self.runtime.command_queue.get(execution["request_id"])
            if snapshot and snapshot["status"] in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.02)

        final = self.runtime.command_queue.get(execution["request_id"])
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "completed")
        self.assertIn("terminated process notepad.exe", (final["message"] or "").lower())
        self.assertIn(3002, self.process_backend.terminated)
