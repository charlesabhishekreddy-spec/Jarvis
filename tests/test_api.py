import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from jarvis.api.app import create_app


class FakeScreenImage:
    size = (1280, 720)
    mode = "RGB"

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(b"fake-screen")


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
        Path(path).write_bytes(b"fake-camera")
        return path

    def snapshot(self) -> dict[str, object]:
        return {"provider": self.provider, "available": self.provider_available}


class FakeOCRService:
    provider = "fake-ocr"
    provider_available = True

    def summarize_text(self, image: object, max_chars: int = 4000) -> dict[str, object]:
        text = "Sprint board visible"
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
            {"pid": 4001, "name": "python.exe", "cpu_percent": 1.0, "memory_percent": 2.0, "status": "running"},
            {"pid": 4002, "name": "notepad.exe", "cpu_percent": 0.0, "memory_percent": 0.4, "status": "sleeping"},
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


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = Path.cwd() / ".test_runtime" / uuid4().hex
        self.tempdir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.tempdir / "settings.yaml"
        data_dir = self.tempdir / "runtime"
        sqlite_path = data_dir / "jarvis.db"
        semantic_path = data_dir / "semantic_memory.json"

        self.config_path.write_text(
            "\n".join(
                [
                    "runtime:",
                    f"  data_dir: {data_dir.as_posix()}",
                    "  auto_start_api: false",
                    "memory:",
                    f"  sqlite_path: {sqlite_path.as_posix()}",
                    f"  semantic_index_path: {semantic_path.as_posix()}",
                    "security:",
                    "  allowed_workdirs:",
                    f"    - {self.tempdir.as_posix()}",
                    "intelligence:",
                    "  provider: heuristic",
                    "  model: local-heuristic",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_intelligence_status_endpoint(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            response = client.get("/intelligence")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["configured_provider"], "heuristic")
        self.assertEqual(payload["active_provider"], "heuristic")

    def test_intelligence_respond_endpoint(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            response = client.post(
                "/intelligence/respond",
                json={"prompt": "Reply with exactly: HELLO_API", "context": {}},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["provider"], "heuristic")
        self.assertIn("HELLO_API", payload["text"])

    def test_dashboard_contains_intelligence_console(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            response = client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="intelligence-form"', response.text)
        self.assertIn('id="intelligence-output"', response.text)
        self.assertIn('id="goals-list"', response.text)
        self.assertIn('id="review-goals"', response.text)
        self.assertIn('id="workflows-list"', response.text)
        self.assertIn('id="voice-list"', response.text)
        self.assertIn('id="voice-start"', response.text)
        self.assertIn('id="vision-list"', response.text)
        self.assertIn('id="vision-screen"', response.text)
        self.assertIn('id="processes-list"', response.text)
        self.assertIn('id="windows-list"', response.text)

    def test_insights_related_endpoints(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            client.post("/command", json={"text": "Jarvis remember that my release window is Friday", "confirmed": False})
            suggestions = client.get("/suggestions")
            projects = client.get("/memory/projects")

        self.assertEqual(suggestions.status_code, 200)
        self.assertEqual(projects.status_code, 200)
        self.assertTrue(suggestions.json())
        self.assertTrue(projects.json())

    def test_conversational_proactive_and_project_context_commands(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            client.post("/command", json={"text": "Jarvis remember that my roadmap lives in Linear", "confirmed": False})
            suggestions = client.post("/command", json={"text": "Jarvis what should I do next", "confirmed": False})
            projects = client.post("/command", json={"text": "Jarvis what are we working on", "confirmed": False})

        self.assertEqual(suggestions.status_code, 200)
        self.assertEqual(projects.status_code, 200)
        self.assertIn("Continue", suggestions.json()["message"])
        self.assertIn(self.tempdir.name, projects.json()["message"])

    def test_goal_endpoints(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            created = client.post(
                "/goals",
                json={"title": "Ship the API upgrade", "detail": "Finalize the new platform endpoints", "priority": 80},
            )
            listed = client.get("/goals")
            reviewed = client.post("/goals/review")
            goal_id = created.json()["goal_id"]
            updated = client.post(f"/goals/{goal_id}/status", json={"status": "completed"})

        self.assertEqual(created.status_code, 200)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(listed.json())
        self.assertEqual(updated.json()["status"], "completed")

    def test_workflow_endpoints(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            created = client.post(
                "/workflows",
                json={"title": "Editor memory workflow", "steps": ["remember that my editor is VS Code", "what did I say about editor"]},
            )
            workflow_id = created.json()["workflow_id"]
            listed = client.get("/workflows")
            started = client.post(f"/workflows/{workflow_id}/run")

        self.assertEqual(created.status_code, 200)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(started.status_code, 200)
        self.assertTrue(listed.json())
        self.assertTrue(started.json()["ok"])

    def test_voice_endpoints(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            status = client.get("/voice")
            simulated = client.post("/voice/simulate", json={"text": "Hey Jarvis remember that my codename is Chief"})
            start = client.post("/voice/start")
            stop = client.post("/voice/stop")

        self.assertEqual(status.status_code, 200)
        self.assertEqual(simulated.status_code, 200)
        self.assertEqual(start.status_code, 200)
        self.assertEqual(stop.status_code, 200)
        self.assertIn("audio", status.json())
        self.assertEqual(simulated.json()["status"], "completed")

    def test_vision_endpoints(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            client.app.state.runtime.vision.screen_capture = FakeScreenCaptureProvider()
            client.app.state.runtime.vision.camera_capture = FakeCameraCaptureProvider()
            client.app.state.runtime.vision.ocr = FakeOCRService()

            status = client.get("/vision")
            screen = client.post("/vision/screen", json={"save_artifact": True, "include_ocr": True, "label": "ops"})
            camera = client.post("/vision/camera", json={"save_artifact": True, "include_ocr": False, "label": "webcam"})

        self.assertEqual(status.status_code, 200)
        self.assertEqual(screen.status_code, 200)
        self.assertEqual(camera.status_code, 200)
        self.assertIn("screen", status.json())
        self.assertTrue(screen.json()["ok"])
        self.assertIn("Sprint board visible", screen.json()["ocr_text"])
        self.assertEqual(camera.json()["image"]["width"], 640)
        self.assertEqual(camera.json()["image"]["height"], 480)

    def test_process_endpoints(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            client.app.state.runtime.system_controller.processes.backend = FakeProcessBackend()

            listed = client.get("/processes")
            pending = client.post("/processes/terminate", json={"pid": 4002})
            confirmed = client.post("/processes/terminate", json={"pid": 4002, "confirmed": True})

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(confirmed.status_code, 200)
        self.assertTrue(listed.json()["available"])
        self.assertEqual(pending.json()["status"], "requires_confirmation")
        self.assertEqual(confirmed.json()["status"], "completed")
        self.assertIn("Terminated process notepad.exe", confirmed.json()["message"])

    def test_window_endpoints(self) -> None:
        with TestClient(create_app(str(self.config_path))) as client:
            client.app.state.runtime.system_controller.desktop.window_backend = FakeWindowBackend()

            listed = client.get("/windows")
            focused = client.post("/windows/focus", json={"title": "visual studio"})
            minimized = client.post("/windows/minimize", json={"title": "edge"})
            maximized = client.post("/windows/maximize", json={"title": "edge"})

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(focused.status_code, 200)
        self.assertEqual(minimized.status_code, 200)
        self.assertEqual(maximized.status_code, 200)
        self.assertTrue(listed.json()["available"])
        self.assertEqual(listed.json()["windows"][0]["title"], "Visual Studio Code")
        self.assertIn("Focused window", focused.json()["message"])
        self.assertIn("Minimized window", minimized.json()["message"])
        self.assertIn("Maximized window", maximized.json()["message"])
