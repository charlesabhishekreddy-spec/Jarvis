from __future__ import annotations

from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class SecurityAgent(BaseAgent):
    name = "security"
    description = "Evaluates risk, permissions, and execution safety."
    keywords = ("security", "permission", "safe", "sandbox")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        assessment = context.security.assess_command(step.metadata.get("command", request.text))
        return {
            "message": f"Risk: {assessment.level.value}. {assessment.reason}",
            "risk": {
                "level": assessment.level.value,
                "reason": assessment.reason,
                "requires_confirmation": assessment.requires_confirmation,
            },
        }
