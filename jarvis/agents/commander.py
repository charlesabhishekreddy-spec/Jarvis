from __future__ import annotations

from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class CommanderAgent(BaseAgent):
    name = "commander"
    description = "Orchestrates tasks and synthesizes final outcomes."
    keywords = ("summarize", "respond", "coordinate", "plan")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        completed_results = [candidate.result for candidate in plan.steps if candidate.result]
        if step.metadata.get("write_report"):
            report = "\n\n".join(completed_results)
            return {"message": report or f"Prepared a response for: {request.text}"}
        return {"message": completed_results[-1] if completed_results else f"Task acknowledged: {request.text}"}
