import shutil
import asyncio
import unittest
from pathlib import Path
from uuid import uuid4

from jarvis.core.config import Settings
from jarvis.core.runtime import JarvisRuntime
from jarvis.core.models import TaskStatus
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


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
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
        await self.runtime.start()

    async def asyncTearDown(self) -> None:
        await self.runtime.stop()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    async def test_remember_and_recall_round_trip(self) -> None:
        remember = await self.runtime.execute_text("Jarvis remember that my favorite editor is VS Code", source="test")
        recall = await self.runtime.execute_text("What did I say about editor", source="test")

        self.assertIn("Stored memory", remember.message)
        self.assertIn("VS Code", recall.message)

        graph = await self.runtime.memory.graph_snapshot(10)
        predicates = {edge["predicate"] for edge in graph["edges"]}
        self.assertIn("favorite_editor", predicates)

    async def test_plugins_register_tools(self) -> None:
        tools = {tool["name"] for tool in self.runtime.tools.list_tools()}
        self.assertIn("plugin.workspace_inventory", tools)

        response = await self.runtime.execute_text("What can you do", source="test")
        self.assertIn("plugin.workspace_inventory", response.message)

    async def test_async_submission_completes(self) -> None:
        record = await self.runtime.submit_text("Jarvis remember that my favorite language is Python", source="test")
        for _ in range(100):
            snapshot = self.runtime.command_queue.get(record["request_id"])
            if snapshot and snapshot["status"] == "completed":
                break
            await asyncio.sleep(0.02)

        final = self.runtime.command_queue.get(record["request_id"])
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "completed")
        self.assertIn("Stored memory", final["message"])

    async def test_autonomous_file_read(self) -> None:
        sample = self.tempdir / "sample.txt"
        sample.write_text("autonomous file content", encoding="utf-8")

        response = await self.runtime.execute_text(f"Read file {sample}", source="test")
        self.assertIn("autonomous file content", response.message)

    async def test_autonomous_file_listing(self) -> None:
        (self.tempdir / "alpha.txt").write_text("a", encoding="utf-8")
        (self.tempdir / "beta.txt").write_text("b", encoding="utf-8")

        response = await self.runtime.execute_text(f"List files in {self.tempdir}", source="test")
        self.assertIn("alpha.txt", response.message)

    async def test_desktop_command_requires_confirmation(self) -> None:
        response = await self.runtime.execute_text("Jarvis click at 10 20", source="test")
        self.assertEqual(response.status, TaskStatus.REQUIRES_CONFIRMATION)
        self.assertEqual(response.data["sensitive_step"], "Click mouse")

    async def test_desktop_tool_requires_confirmation(self) -> None:
        blocked = await self.runtime.tools.execute("system.mouse_click", self.runtime.context, x=10, y=20)
        self.assertFalse(blocked["ok"])
        self.assertTrue(blocked["requires_confirmation"])

        allowed = await self.runtime.tools.execute(
            "system.mouse_click",
            self.runtime.context,
            confirmed=True,
            x=10,
            y=20,
            button="left",
            clicks=1,
        )
        self.assertTrue(allowed["ok"])
        self.assertEqual(self.desktop_backend.actions[0], ("click", 10, 20, 1, "left"))
