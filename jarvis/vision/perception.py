from __future__ import annotations

from typing import Any

from jarvis.core.service import Service

from .capture import CameraCaptureProvider, ScreenCaptureProvider
from .ocr import OCRService


class VisionService(Service):
    def __init__(self) -> None:
        super().__init__("jarvis.vision")
        self.screen_capture = ScreenCaptureProvider()
        self.camera_capture = CameraCaptureProvider()
        self.ocr = OCRService()

    async def inspect_screen(self) -> dict[str, Any]:
        image = self.screen_capture.capture_screen()
        text = self.ocr.extract_text(image)
        return {
            "screen_available": image is not None,
            "ocr_text": text[:4000],
        }

    async def inspect_camera(self) -> dict[str, Any]:
        frame = self.camera_capture.capture_frame()
        return {"camera_available": frame is not None}
