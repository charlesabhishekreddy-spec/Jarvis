import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from jarvis.core.config import Settings
from jarvis.core.runtime import JarvisRuntime


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
