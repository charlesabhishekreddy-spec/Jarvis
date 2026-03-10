from __future__ import annotations

from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class CoderAgent(BaseAgent):
    name = "coder"
    description = "Produces code-oriented plans and development actions."
    keywords = ("code", "build", "debug", "test", "refactor")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        if step.metadata.get("shell_command"):
            result = await context.tools.execute(
                "system.shell",
                context,
                command=step.metadata["shell_command"],
                workdir=step.metadata.get("workdir"),
            )
            return {"message": f"Executed development command with status {result['result']['returncode']}.", "result": result}
        return {
            "message": "Coder agent prepared a development-oriented response. Connect an LLM-backed coding model for autonomous code generation.",
        }
