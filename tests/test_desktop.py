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


class DesktopControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_reports_screen_size(self) -> None:
        controller = DesktopController(backend=FakeDesktopBackend())
        status = await controller.status()

        self.assertTrue(status["ok"])
        self.assertTrue(status["available"])
        self.assertEqual(status["screen"]["width"], 1920)
        self.assertEqual(status["screen"]["height"], 1080)

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
