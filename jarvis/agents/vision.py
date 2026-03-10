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
        source = step.metadata.get("source", "screen")
        if source == "camera":
            result = await context.vision.inspect_camera()
            return {"message": f"Camera available: {result['camera_available']}", "result": result}
        result = await context.vision.inspect_screen()
        return {
            "message": result["ocr_text"][:500] or "No OCR text detected from the screen.",
            "result": result,
        }
