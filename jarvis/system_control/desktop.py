from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

try:
    import pyautogui
except ImportError:  # pragma: no cover
    pyautogui = None

try:
    import pygetwindow
except ImportError:  # pragma: no cover
    pygetwindow = None


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


class WindowBackend(Protocol):
    def list_windows(self) -> list[dict[str, object]]:
        raise NotImplementedError

    def focus_window(self, title: str) -> bool:
        raise NotImplementedError

    def minimize_window(self, title: str) -> bool:
        raise NotImplementedError

    def maximize_window(self, title: str) -> bool:
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


class PyGetWindowBackend:
    def list_windows(self) -> list[dict[str, object]]:
        active_window = pygetwindow.getActiveWindow()
        active_title = active_window.title if active_window is not None else None
        windows: list[dict[str, object]] = []
        for window in pygetwindow.getAllWindows():
            title = (window.title or "").strip()
            if not title:
                continue
            windows.append(
                {
                    "title": title,
                    "left": int(getattr(window, "left", 0)),
                    "top": int(getattr(window, "top", 0)),
                    "width": int(getattr(window, "width", 0)),
                    "height": int(getattr(window, "height", 0)),
                    "is_minimized": bool(getattr(window, "isMinimized", False)),
                    "is_maximized": bool(getattr(window, "isMaximized", False)),
                    "is_active": title == active_title,
                }
            )
        return windows

    def focus_window(self, title: str) -> bool:
        window = self._resolve_window(title)
        if window is None:
            return False
        window.activate()
        return True

    def minimize_window(self, title: str) -> bool:
        window = self._resolve_window(title)
        if window is None:
            return False
        window.minimize()
        return True

    def maximize_window(self, title: str) -> bool:
        window = self._resolve_window(title)
        if window is None:
            return False
        window.maximize()
        return True

    def _resolve_window(self, title: str):
        for window in pygetwindow.getAllWindows():
            if (window.title or "").strip() == title:
                return window
        return None


@dataclass(slots=True)
class DesktopController:
    backend: DesktopBackend | None = None
    window_backend: WindowBackend | None = None

    def __post_init__(self) -> None:
        if self.backend is None and pyautogui is not None:
            self.backend = PyAutoGuiBackend()
        if self.window_backend is None and pygetwindow is not None:
            self.window_backend = PyGetWindowBackend()

    async def status(self) -> dict[str, object]:
        if self.backend is None:
            return {
                "ok": False,
                "available": False,
                "error": "Desktop automation backend unavailable. Install pyautogui to enable mouse and keyboard control.",
                "window_available": self.window_backend is not None,
            }
        width, height = await asyncio.to_thread(self.backend.size)
        return {
            "ok": True,
            "available": True,
            "screen": {"width": width, "height": height},
            "window_available": self.window_backend is not None,
        }

    async def list_windows(self, limit: int = 20, query: str | None = None) -> dict[str, object]:
        if self.window_backend is None:
            return {
                "ok": True,
                "available": False,
                "windows": [],
                "error": "Window management backend unavailable. Install pygetwindow to inspect desktop windows.",
            }
        windows = await asyncio.to_thread(self.window_backend.list_windows)
        if query:
            needle = query.strip().lower()
            windows = [window for window in windows if needle in str(window.get("title", "")).lower()]
        return {"ok": True, "available": True, "count": len(windows[: max(limit, 1)]), "windows": windows[: max(limit, 1)]}

    async def focus_window(self, title: str) -> dict[str, object]:
        target = await self._resolve_window_title(title)
        if isinstance(target, dict):
            return target
        success = await asyncio.to_thread(self.window_backend.focus_window, target)
        if not success:
            return {"ok": False, "error": f"Failed to focus window '{target}'."}
        return {"ok": True, "title": target, "message": f"Focused window '{target}'."}

    async def minimize_window(self, title: str) -> dict[str, object]:
        target = await self._resolve_window_title(title)
        if isinstance(target, dict):
            return target
        success = await asyncio.to_thread(self.window_backend.minimize_window, target)
        if not success:
            return {"ok": False, "error": f"Failed to minimize window '{target}'."}
        return {"ok": True, "title": target, "message": f"Minimized window '{target}'."}

    async def maximize_window(self, title: str) -> dict[str, object]:
        target = await self._resolve_window_title(title)
        if isinstance(target, dict):
            return target
        success = await asyncio.to_thread(self.window_backend.maximize_window, target)
        if not success:
            return {"ok": False, "error": f"Failed to maximize window '{target}'."}
        return {"ok": True, "title": target, "message": f"Maximized window '{target}'."}

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

    async def _resolve_window_title(self, title_query: str) -> str | dict[str, object]:
        if self.window_backend is None:
            return {
                "ok": False,
                "error": "Window management backend unavailable. Install pygetwindow to control windows.",
            }
        windows = await asyncio.to_thread(self.window_backend.list_windows)
        needle = title_query.strip().lower()
        matches = [window for window in windows if needle in str(window.get("title", "")).lower()]
        if not matches:
            return {"ok": False, "error": f"No window matched '{title_query}'."}
        if len(matches) > 1:
            return {
                "ok": False,
                "error": f"Multiple windows matched '{title_query}'. Be more specific.",
                "matches": [str(window.get("title", "")) for window in matches[:10]],
            }
        return str(matches[0]["title"])

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
