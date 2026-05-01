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


class FakeScreenImage:
    size = (1440, 900)
    mode = "RGB"

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(b"fake-screen-image")


class FakeCameraFrame:
    shape = (480, 640, 3)


class FakeScreenCaptureProvider:
    provider = "fake-screen"
    provider_available = True

    def capture_screen(self) -> FakeScreenImage:
        return FakeScreenImage()

    def save(self, image: FakeScreenImage, path: str) -> str:
        image.save(path)
        return path

    def snapshot(self) -> dict[str, object]:
        return {"provider": self.provider, "available": self.provider_available}


class FakeCameraCaptureProvider:
    provider = "fake-camera"
    provider_available = True

    def capture_frame(self) -> FakeCameraFrame:
        return FakeCameraFrame()

    def save(self, frame: FakeCameraFrame, path: str) -> str:
        Path(path).write_bytes(b"fake-camera-frame")
        return path

    def snapshot(self) -> dict[str, object]:
        return {"provider": self.provider, "available": self.provider_available}


class FakeOCRService:
    provider = "fake-ocr"
    provider_available = True

    def summarize_text(self, image: object, max_chars: int = 4000) -> dict[str, object]:
        text = "Release checklist on screen"
        return {
            "provider": self.provider,
            "available": self.provider_available,
            "text": text[:max_chars],
            "char_count": len(text),
            "line_count": 1,
        }

    def snapshot(self) -> dict[str, object]:
        return {"provider": self.provider, "available": self.provider_available}


class FakeProcessBackend:
    def __init__(self) -> None:
        self.records = [
            {"pid": 2001, "name": "python.exe", "cpu_percent": 2.5, "memory_percent": 4.0, "status": "running"},
            {"pid": 2002, "name": "notepad.exe", "cpu_percent": 0.2, "memory_percent": 1.1, "status": "sleeping"},
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


class FakeWindowBackend:
    def __init__(self) -> None:
        self.actions: list[tuple[str, str]] = []
        self.windows = [
            {"title": "Visual Studio Code", "width": 1400, "height": 900, "is_active": True, "is_minimized": False, "is_maximized": False},
            {"title": "Microsoft Edge", "width": 1280, "height": 720, "is_active": False, "is_minimized": False, "is_maximized": False},
        ]

    def list_windows(self) -> list[dict[str, object]]:
        return [dict(window) for window in self.windows]

    def focus_window(self, title: str) -> bool:
        self.actions.append(("focus", title))
        return True

    def minimize_window(self, title: str) -> bool:
        self.actions.append(("minimize", title))
        return True

    def maximize_window(self, title: str) -> bool:
        self.actions.append(("maximize", title))
        return True


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = Path.cwd() / ".test_runtime" / uuid4().hex
        self.tempdir.mkdir(parents=True, exist_ok=True)
        settings = Settings()
        settings.runtime.data_dir = str(self.tempdir)
        settings.memory.sqlite_path = str(self.tempdir / "jarvis.db")
        settings.memory.semantic_index_path = str(self.tempdir / "semantic_memory.json")
        settings.security.allowed_workdirs = [str(self.tempdir), str(Path.cwd())]
        self.settings = settings
        self.runtime = JarvisRuntime(settings)
        self.desktop_backend = FakeDesktopBackend()
        self.runtime.system_controller.desktop = DesktopController(self.desktop_backend)
        self.window_backend = FakeWindowBackend()
        self.runtime.system_controller.desktop.window_backend = self.window_backend
        self.process_backend = FakeProcessBackend()
        self.runtime.system_controller.processes.backend = self.process_backend
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

    async def test_status_snapshot_includes_intelligence(self) -> None:
        snapshot = await self.runtime.status_snapshot()
        self.assertIn("intelligence", snapshot)
        self.assertIn("voice", snapshot)
        self.assertIn("vision", snapshot)
        self.assertIn("processes", snapshot)
        self.assertIn("windows", snapshot)
        self.assertEqual(snapshot["intelligence"]["configured_provider"], "heuristic")
        self.assertEqual(snapshot["intelligence"]["active_provider"], "heuristic")

    async def test_learning_generates_project_context_and_suggestions(self) -> None:
        await self.runtime.execute_text("Jarvis remember that my deployment target is staging", source="test")
        insights = await self.runtime.learning.insights()

        self.assertTrue(insights["projects"])
        self.assertTrue(insights["suggestions"])
        self.assertEqual(insights["projects"][0]["project_name"], self.tempdir.name)
        self.assertIn("Latest request", insights["projects"][0]["summary"])

    async def test_compound_workflow_executes_with_dependencies(self) -> None:
        response = await self.runtime.execute_text(
            "Jarvis remember that my task board is Linear then what did I say about task board",
            source="test",
        )
        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Linear", response.message)
        self.assertEqual(response.data["plan"]["metadata"]["plan_type"], "workflow")
        self.assertIn(
            response.data["plan"]["steps"][0]["step_id"],
            response.data["plan"]["steps"][1]["depends_on"],
        )

    async def test_next_step_command_uses_proactive_suggestions(self) -> None:
        await self.runtime.execute_text("Jarvis remember that my release checklist lives in Notion", source="test")
        response = await self.runtime.execute_text("Jarvis what should I do next", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Continue", response.message)

    async def test_project_context_command_reports_active_project(self) -> None:
        await self.runtime.execute_text("Jarvis remember that our deployment target is staging", source="test")
        response = await self.runtime.execute_text("Jarvis what are we working on", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn(self.tempdir.name, response.message)
        self.assertIn("Latest request", response.message)

    async def test_goal_creation_and_focus_command(self) -> None:
        create = await self.runtime.execute_text("Jarvis track goal ship the API upgrade", source="test")
        focus = await self.runtime.execute_text("Jarvis what should I focus on", source="test")

        self.assertEqual(create.status, TaskStatus.COMPLETED)
        self.assertIn("Tracking goal", create.message)
        self.assertEqual(focus.status, TaskStatus.COMPLETED)
        self.assertIn("ship the API upgrade", focus.message)

        goals = await self.runtime.memory.goals(status="active", limit=5)
        self.assertTrue(goals)
        self.assertEqual(goals[0]["title"], "ship the API upgrade")

    async def test_goal_review_updates_next_action(self) -> None:
        await self.runtime.execute_text("Jarvis track goal stabilize the deployment pipeline", source="test")

        review = await self.runtime.proactive.review_now(source="test")
        goals = await self.runtime.memory.goals(status="active", limit=5)

        self.assertEqual(review["goal_count"], 1)
        self.assertTrue(goals[0]["next_action"])
        self.assertIn("last_review_at", goals[0]["metadata"])

    async def test_goal_completion_command_updates_status(self) -> None:
        await self.runtime.execute_text("Jarvis track goal ship the API upgrade", source="test")
        response = await self.runtime.execute_text("Jarvis complete goal ship the API upgrade", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("completed", response.message)

        goals = await self.runtime.memory.goals(limit=5)
        self.assertEqual(goals[0]["status"], "completed")

    async def test_workflow_create_and_run(self) -> None:
        create = await self.runtime.execute_text(
            "Jarvis create workflow remember that my editor is VS Code then what did I say about editor",
            source="test",
        )
        self.assertEqual(create.status, TaskStatus.COMPLETED)
        self.assertIn("Created workflow", create.message)

        workflows = await self.runtime.memory.workflows(limit=5)
        self.assertTrue(workflows)
        workflow_id = workflows[0]["workflow_id"]

        run = await self.runtime.execute_text(f"Jarvis run workflow {workflows[0]['title']}", source="test")
        self.assertEqual(run.status, TaskStatus.COMPLETED)
        self.assertIn("queued", run.message.lower())

        for _ in range(200):
            workflow = await self.runtime.memory.workflow(workflow_id)
            if workflow and workflow["status"] == TaskStatus.COMPLETED.value:
                break
            await asyncio.sleep(0.02)

        workflow = await self.runtime.memory.workflow(workflow_id)
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow["status"], TaskStatus.COMPLETED.value)
        self.assertEqual(workflow["steps"][0]["status"], TaskStatus.COMPLETED.value)
        self.assertEqual(workflow["steps"][1]["status"], TaskStatus.COMPLETED.value)
        self.assertIn("VS Code", workflow["steps"][1]["result"])

    async def test_workflow_restores_after_restart(self) -> None:
        await self.runtime.execute_text(
            "Jarvis create workflow remember that my editor is VS Code then what did I say about editor",
            source="test",
        )
        workflow = (await self.runtime.memory.workflows(limit=1))[0]
        workflow["status"] = TaskStatus.QUEUED.value
        await self.runtime.memory.save_workflow(workflow)

        await self.runtime.stop()

        restarted = JarvisRuntime(self.settings)
        restarted.system_controller.desktop = DesktopController(self.desktop_backend)
        self.runtime = restarted
        await self.runtime.start()

        for _ in range(200):
            restored = await self.runtime.memory.workflow(workflow["workflow_id"])
            if restored and restored["status"] == TaskStatus.COMPLETED.value:
                break
            await asyncio.sleep(0.02)

        restored = await self.runtime.memory.workflow(workflow["workflow_id"])
        self.assertIsNotNone(restored)
        self.assertEqual(restored["status"], TaskStatus.COMPLETED.value)
        self.assertIn("restored_at", restored["metadata"])

    async def test_voice_simulation_with_wake_word_executes_command(self) -> None:
        response = await self.runtime.voice.simulate_heard_text(
            "Hey Jarvis remember that my codename is Chief",
            strict_wake=True,
        )
        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Stored memory", response.message)

        recall = await self.runtime.execute_text("What did I say about codename", source="test")
        self.assertIn("Chief", recall.message)

    async def test_voice_status_snapshot(self) -> None:
        snapshot = self.runtime.voice.status_snapshot()
        self.assertEqual(snapshot["wake_word"], "hey jarvis")
        self.assertIn("audio", snapshot)
        self.assertIn("stt", snapshot)
        self.assertIn("tts", snapshot)

    async def test_screen_vision_command_captures_artifact(self) -> None:
        self.runtime.vision.screen_capture = FakeScreenCaptureProvider()
        self.runtime.vision.ocr = FakeOCRService()

        response = await self.runtime.execute_text("Jarvis capture the screen", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Release checklist", response.message)
        result = response.data["plan"]["steps"][0]["result"]
        self.assertIn("Release checklist", result)
        snapshot = self.runtime.vision.status_snapshot()
        self.assertEqual(snapshot["last_source"], "screen")
        self.assertTrue(snapshot["last_artifact_path"])
        self.assertTrue(Path(snapshot["last_artifact_path"]).exists())

    async def test_camera_vision_command_reports_frame(self) -> None:
        self.runtime.vision.camera_capture = FakeCameraCaptureProvider()
        self.runtime.vision.ocr = FakeOCRService()

        response = await self.runtime.execute_text("Jarvis inspect the camera", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Captured camera frame 640x480", response.message)
        snapshot = self.runtime.vision.status_snapshot()
        self.assertEqual(snapshot["last_source"], "camera")

    async def test_vision_status_command_reports_provider_state(self) -> None:
        self.runtime.vision.screen_capture = FakeScreenCaptureProvider()
        self.runtime.vision.camera_capture = FakeCameraCaptureProvider()
        self.runtime.vision.ocr = FakeOCRService()

        response = await self.runtime.execute_text("Jarvis vision status", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Vision status", response.message)
        self.assertIn("available", response.message)

    async def test_process_listing_command_reports_running_apps(self) -> None:
        response = await self.runtime.execute_text("Jarvis list running processes", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("notepad.exe", response.message)
        self.assertIn("python.exe", response.message)

    async def test_process_termination_command_requires_confirmation(self) -> None:
        response = await self.runtime.execute_text("Jarvis stop process 2002", source="test")

        self.assertEqual(response.status, TaskStatus.REQUIRES_CONFIRMATION)
        self.assertEqual(response.data["sensitive_step"], "Terminate process")

    async def test_process_termination_command_executes_when_confirmed(self) -> None:
        response = await self.runtime.execute_text("Jarvis stop process 2002", source="test", confirmed=True)

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Terminated process notepad.exe (2002).", response.message)
        self.assertIn(2002, self.process_backend.terminated)

    async def test_window_listing_command_reports_open_windows(self) -> None:
        response = await self.runtime.execute_text("Jarvis list open windows", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Visual Studio Code", response.message)
        self.assertIn("Microsoft Edge", response.message)

    async def test_window_focus_command_executes(self) -> None:
        response = await self.runtime.execute_text("Jarvis focus window visual studio", source="test")

        self.assertEqual(response.status, TaskStatus.COMPLETED)
        self.assertIn("Focused window 'Visual Studio Code'.", response.message)
        self.assertEqual(self.window_backend.actions[0], ("focus", "Visual Studio Code"))

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
