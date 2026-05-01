from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    from PIL import ImageGrab
except ImportError:  # pragma: no cover
    ImageGrab = None


class ScreenCaptureProvider:
    provider = "PIL.ImageGrab"

    @property
    def provider_available(self) -> bool:
        return ImageGrab is not None

    def capture_screen(self) -> Any | None:
        if not self.provider_available:
            return None
        return ImageGrab.grab()

    def save(self, image: Any, path: str) -> str | None:
        if image is None:
            return None
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            image.save(target)
        except Exception:  # pragma: no cover
            return None
        return str(target)

    def snapshot(self) -> dict[str, Any]:
        return {"provider": self.provider, "available": self.provider_available}


class CameraCaptureProvider:
    provider = "opencv"

    @property
    def provider_available(self) -> bool:
        return cv2 is not None

    def capture_frame(self) -> Any | None:
        if not self.provider_available:
            return None
        camera = cv2.VideoCapture(0)
        success, frame = camera.read()
        camera.release()
        if not success:
            return None
        return frame

    def save(self, frame: Any, path: str) -> str | None:
        if frame is None:
            return None
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if cv2 is not None:
            try:
                success = cv2.imwrite(str(target), frame)
            except Exception:  # pragma: no cover
                success = False
            if success:
                return str(target)
        if hasattr(frame, "save"):
            try:
                frame.save(target)
                return str(target)
            except Exception:  # pragma: no cover
                return None
        return None

    def snapshot(self) -> dict[str, Any]:
        return {"provider": self.provider, "available": self.provider_available}
