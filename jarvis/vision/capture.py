from __future__ import annotations

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
    def capture_screen(self) -> Any | None:
        if ImageGrab is None:
            return None
        return ImageGrab.grab()


class CameraCaptureProvider:
    def capture_frame(self) -> Any | None:
        if cv2 is None:
            return None
        camera = cv2.VideoCapture(0)
        success, frame = camera.read()
        camera.release()
        if not success:
            return None
        return frame
