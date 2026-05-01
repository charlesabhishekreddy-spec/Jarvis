from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from jarvis.core.service import Service

from .capture import CameraCaptureProvider, ScreenCaptureProvider
from .ocr import OCRService

if TYPE_CHECKING:
    from jarvis.core.events import AsyncEventBus
    from jarvis.memory.service import MemoryService


class VisionService(Service):
    def __init__(
        self,
        data_dir: str | None = None,
        bus: AsyncEventBus | None = None,
        memory: MemoryService | None = None,
    ) -> None:
        super().__init__("jarvis.vision")
        self.screen_capture = ScreenCaptureProvider()
        self.camera_capture = CameraCaptureProvider()
        self.ocr = OCRService()
        self.bus = bus
        self.memory = memory
        self.output_dir = Path(data_dir or ".jarvis_runtime").resolve() / "vision"
        self._state: dict[str, Any] = {
            "enabled": True,
            "captures": 0,
            "last_source": None,
            "last_capture_at": None,
            "last_artifact_path": None,
            "last_ocr_text": None,
            "last_error": None,
        }

    async def start(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        await super().start()
        await self._log("vision", "Vision service initialized.", details={"output_dir": str(self.output_dir)})
        await self._publish("vision.initialized", self.status_snapshot())

    async def inspect_screen(
        self,
        save_artifact: bool = True,
        include_ocr: bool = True,
        label: str | None = None,
    ) -> dict[str, Any]:
        image = self.screen_capture.capture_screen()
        if image is None:
            result = {
                "ok": False,
                "source": "screen",
                "error": "No screen capture provider is available. Install requirements-optional.txt.",
            }
            await self._record_failure(result["error"])
            return {**result, "status": self.status_snapshot()}

        artifact_path = self._save_screen(image, label=label) if save_artifact else None
        ocr_result = self.ocr.summarize_text(image) if include_ocr else self._empty_ocr_result()
        summary = {
            "ok": True,
            "source": "screen",
            "artifact_path": artifact_path,
            "image": self._describe_image(image),
            "ocr": ocr_result,
            "ocr_text": ocr_result["text"],
        }
        await self._record_capture(summary)
        return summary

    async def inspect_camera(
        self,
        save_artifact: bool = True,
        include_ocr: bool = False,
        label: str | None = None,
    ) -> dict[str, Any]:
        frame = self.camera_capture.capture_frame()
        if frame is None:
            result = {
                "ok": False,
                "source": "camera",
                "error": "No camera frame is available. Install OpenCV and ensure a webcam is connected.",
            }
            await self._record_failure(result["error"])
            return {**result, "status": self.status_snapshot()}

        artifact_path = self._save_camera(frame, label=label) if save_artifact else None
        ocr_result = self.ocr.summarize_text(frame) if include_ocr else self._empty_ocr_result()
        summary = {
            "ok": True,
            "source": "camera",
            "artifact_path": artifact_path,
            "image": self._describe_image(frame),
            "ocr": ocr_result,
            "ocr_text": ocr_result["text"],
        }
        await self._record_capture(summary)
        return summary

    def status_snapshot(self) -> dict[str, Any]:
        return {
            **self._state,
            "output_dir": str(self.output_dir),
            "screen": self.screen_capture.snapshot(),
            "camera": self.camera_capture.snapshot(),
            "ocr": self.ocr.snapshot(),
        }

    async def _record_capture(self, result: dict[str, Any]) -> None:
        self._state["captures"] += 1
        self._state["last_source"] = result["source"]
        self._state["last_capture_at"] = self._utc_iso()
        self._state["last_artifact_path"] = result.get("artifact_path")
        self._state["last_ocr_text"] = result.get("ocr_text") or None
        self._state["last_error"] = None
        await self._log(
            "vision",
            f"{result['source'].title()} capture completed.",
            details={
                "artifact_path": result.get("artifact_path"),
                "ocr_char_count": result.get("ocr", {}).get("char_count", 0),
                "image": result.get("image"),
            },
        )
        await self._publish(f"vision.{result['source']}.captured", result)

    async def _record_failure(self, error: str) -> None:
        self._state["last_error"] = error
        await self._log("vision.error", "Vision capture failed.", details={"error": error})
        await self._publish("vision.capture.failed", {"error": error, "status": self.status_snapshot()})

    def _save_screen(self, image: Any, label: str | None = None) -> str | None:
        filename = self._artifact_name(prefix="screen", label=label, extension="png")
        return self.screen_capture.save(image, str(self.output_dir / filename))

    def _save_camera(self, frame: Any, label: str | None = None) -> str | None:
        filename = self._artifact_name(prefix="camera", label=label, extension="jpg")
        return self.camera_capture.save(frame, str(self.output_dir / filename))

    def _describe_image(self, image: Any) -> dict[str, Any]:
        width, height = self._extract_dimensions(image)
        description = {
            "width": width,
            "height": height,
            "mode": getattr(image, "mode", None),
            "channels": self._extract_channels(image),
        }
        return description

    def _extract_dimensions(self, image: Any) -> tuple[int | None, int | None]:
        size = getattr(image, "size", None)
        if isinstance(size, tuple) and len(size) >= 2:
            return int(size[0]), int(size[1])
        shape = getattr(image, "shape", None)
        if isinstance(shape, tuple) and len(shape) >= 2:
            return int(shape[1]), int(shape[0])
        return None, None

    def _extract_channels(self, image: Any) -> int | None:
        shape = getattr(image, "shape", None)
        if isinstance(shape, tuple) and len(shape) >= 3:
            return int(shape[2])
        mode = getattr(image, "mode", None)
        if isinstance(mode, str):
            return len(mode)
        return None

    def _artifact_name(self, prefix: str, label: str | None, extension: str) -> str:
        safe_label = self._slugify(label) if label else None
        stem = safe_label or uuid4().hex[:12]
        return f"{prefix}-{stem}.{extension}"

    def _slugify(self, value: str) -> str:
        cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
        return "-".join(segment for segment in cleaned.split("-") if segment)[:48] or uuid4().hex[:12]

    def _empty_ocr_result(self) -> dict[str, Any]:
        return {
            "provider": self.ocr.provider,
            "available": self.ocr.provider_available,
            "text": "",
            "char_count": 0,
            "line_count": 0,
        }

    async def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        if self.bus is not None:
            await self.bus.publish(topic, payload)

    async def _log(self, category: str, message: str, details: dict[str, Any] | None = None) -> None:
        if self.memory is not None:
            await self.memory.log_activity(category=category, message=message, details=details or {})

    def _utc_iso(self) -> str:
        from jarvis.core.models import utc_now

        return utc_now().isoformat()
