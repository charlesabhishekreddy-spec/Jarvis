from __future__ import annotations

from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class VisionAgent(BaseAgent):
    name = "vision"
    description = "Processes screen and camera context."
    keywords = ("screen", "camera", "ocr", "vision", "read")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        operation = step.metadata.get("operation", "inspect")
        source = step.metadata.get("source", "screen")
        if operation == "status":
            result = context.vision.status_snapshot()
            return {
                "message": (
                    f"Vision status: screen {self._availability(result['screen'])}, "
                    f"camera {self._availability(result['camera'])}, "
                    f"OCR {self._availability(result['ocr'])}."
                ),
                "result": result,
            }

        include_ocr = bool(step.metadata.get("include_ocr", source == "screen"))
        save_artifact = bool(step.metadata.get("save_artifact", True))
        label = step.metadata.get("label")
        if source == "camera":
            result = await context.vision.inspect_camera(
                save_artifact=save_artifact,
                include_ocr=include_ocr,
                label=label,
            )
            message = self._camera_message(result)
            return {"message": message, "result": result}
        result = await context.vision.inspect_screen(
            save_artifact=save_artifact,
            include_ocr=include_ocr,
            label=label,
        )
        return {
            "message": self._screen_message(result),
            "result": result,
        }

    def _availability(self, provider: dict[str, Any]) -> str:
        return "available" if provider.get("available") else "missing"

    def _screen_message(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return str(result.get("error", "Screen inspection failed."))
        text = str(result.get("ocr_text", "")).strip()
        if text:
            return text[:500]
        image = result.get("image", {})
        width = image.get("width")
        height = image.get("height")
        details = f"{width}x{height}" if width and height else "screen image"
        return f"Captured {details}. No OCR text detected."

    def _camera_message(self, result: dict[str, Any]) -> str:
        if not result.get("ok"):
            return str(result.get("error", "Camera inspection failed."))
        image = result.get("image", {})
        width = image.get("width")
        height = image.get("height")
        details = f"{width}x{height}" if width and height else "camera frame"
        artifact = result.get("artifact_path")
        if artifact:
            return f"Captured camera frame {details} and saved it to {artifact}."
        return f"Captured camera frame {details}."
