import unittest

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


class DesktopControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_reports_screen_size(self) -> None:
        controller = DesktopController(backend=FakeDesktopBackend(), window_backend=FakeWindowBackend())
        status = await controller.status()

        self.assertTrue(status["ok"])
        self.assertTrue(status["available"])
        self.assertEqual(status["screen"]["width"], 1920)
        self.assertEqual(status["screen"]["height"], 1080)
        self.assertTrue(status["window_available"])

    async def test_keyboard_shortcut_uses_hotkey(self) -> None:
        backend = FakeDesktopBackend()
        controller = DesktopController(backend=backend)
        result = await controller.press_keys(["control", "shift", "s"])

        self.assertTrue(result["ok"])
        self.assertIn("ctrl + shift + s", result["message"])
        self.assertEqual(backend.actions[0], ("hotkey", "ctrl", "shift", "s"))

    async def test_click_records_button_and_coordinates(self) -> None:
        backend = FakeDesktopBackend()
        controller = DesktopController(backend=backend)
        result = await controller.click(x=40, y=50, button="right", clicks=1)

        self.assertTrue(result["ok"])
        self.assertEqual(backend.actions[0], ("click", 40, 50, 1, "right"))

    async def test_list_windows_reports_titles(self) -> None:
        controller = DesktopController(backend=FakeDesktopBackend(), window_backend=FakeWindowBackend())
        result = await controller.list_windows()

        self.assertTrue(result["ok"])
        self.assertTrue(result["available"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["windows"][0]["title"], "Visual Studio Code")

    async def test_focus_window_uses_window_backend(self) -> None:
        window_backend = FakeWindowBackend()
        controller = DesktopController(backend=FakeDesktopBackend(), window_backend=window_backend)
        result = await controller.focus_window("visual studio")

        self.assertTrue(result["ok"])
        self.assertIn("Focused window", result["message"])
        self.assertEqual(window_backend.actions[0], ("focus", "Visual Studio Code"))

    async def test_minimize_and_maximize_window_use_window_backend(self) -> None:
        window_backend = FakeWindowBackend()
        controller = DesktopController(backend=FakeDesktopBackend(), window_backend=window_backend)

        minimized = await controller.minimize_window("edge")
        maximized = await controller.maximize_window("edge")

        self.assertTrue(minimized["ok"])
        self.assertTrue(maximized["ok"])
        self.assertEqual(window_backend.actions[0], ("minimize", "Microsoft Edge"))
        self.assertEqual(window_backend.actions[1], ("maximize", "Microsoft Edge"))
