from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

try:
    import pyautogui
except ImportError:  # pragma: no cover
    pyautogui = None


if pyautogui is not None:  # pragma: no cover
    pyautogui.FAILSAFE = True


class DesktopBackend(Protocol):
    def size(self) -> tuple[int, int]:
        raise NotImplementedError

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        raise NotImplementedError

    def click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> None:
        raise NotImplementedError

    def write(self, text: str, interval: float = 0.0) -> None:
        raise NotImplementedError

    def press(self, key: str) -> None:
        raise NotImplementedError

    def hotkey(self, *keys: str) -> None:
        raise NotImplementedError


class PyAutoGuiBackend:
    def size(self) -> tuple[int, int]:
        width, height = pyautogui.size()
        return int(width), int(height)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        pyautogui.moveTo(x, y, duration=max(duration, 0.0))

    def click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> None:
        pyautogui.click(x=x, y=y, clicks=max(clicks, 1), button=button)

    def write(self, text: str, interval: float = 0.0) -> None:
        pyautogui.write(text, interval=max(interval, 0.0))

    def press(self, key: str) -> None:
        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        pyautogui.hotkey(*keys)


@dataclass(slots=True)
class DesktopController:
    backend: DesktopBackend | None = None

    def __post_init__(self) -> None:
        if self.backend is None and pyautogui is not None:
            self.backend = PyAutoGuiBackend()

    async def status(self) -> dict[str, object]:
        if self.backend is None:
            return {
                "ok": False,
                "available": False,
                "error": "Desktop automation backend unavailable. Install pyautogui to enable mouse and keyboard control.",
            }
        width, height = await asyncio.to_thread(self.backend.size)
        return {"ok": True, "available": True, "screen": {"width": width, "height": height}}

    async def move_mouse(self, x: int, y: int, duration: float = 0.0) -> dict[str, object]:
        validation = await self._validate_backend()
        if validation is not None:
            return validation
        await asyncio.to_thread(self.backend.move_to, int(x), int(y), max(duration, 0.0))
        return {"ok": True, "message": f"Moved mouse to {int(x)}, {int(y)}."}

    async def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict[str, object]:
        validation = await self._validate_backend()
        if validation is not None:
            return validation
        normalized_button = button.lower()
        if normalized_button not in {"left", "right", "middle"}:
            return {"ok": False, "error": f"Unsupported mouse button: {button}"}
        await asyncio.to_thread(self.backend.click, int(x), int(y), max(int(clicks), 1), normalized_button)
        click_word = "Double-clicked" if int(clicks) >= 2 else "Clicked"
        return {"ok": True, "message": f"{click_word} {normalized_button} at {int(x)}, {int(y)}."}

    async def type_text(self, text: str, interval: float = 0.0) -> dict[str, object]:
        validation = await self._validate_backend()
        if validation is not None:
            return validation
        await asyncio.to_thread(self.backend.write, text, max(interval, 0.0))
        return {"ok": True, "message": f"Typed {len(text)} characters."}

    async def press_keys(self, keys: Sequence[str]) -> dict[str, object]:
        validation = await self._validate_backend()
        if validation is not None:
            return validation
        normalized = [self._normalize_key(key) for key in keys if key]
        if not normalized:
            return {"ok": False, "error": "No keys were provided."}
        if len(normalized) == 1:
            await asyncio.to_thread(self.backend.press, normalized[0])
            return {"ok": True, "message": f"Pressed {normalized[0]}."}
        await asyncio.to_thread(self.backend.hotkey, *normalized)
        return {"ok": True, "message": f"Pressed shortcut {' + '.join(normalized)}."}

    async def _validate_backend(self) -> dict[str, object] | None:
        if self.backend is None:
            return {
                "ok": False,
                "error": "Desktop automation backend unavailable. Install pyautogui to enable mouse and keyboard control.",
            }
        return None

    def _normalize_key(self, key: str) -> str:
        lowered = key.strip().lower().replace("-", "")
        aliases = {
            "control": "ctrl",
            "return": "enter",
            "escape": "esc",
            "pagedown": "pgdn",
            "pageup": "pgup",
            "windows": "win",
        }
        return aliases.get(lowered, lowered)
