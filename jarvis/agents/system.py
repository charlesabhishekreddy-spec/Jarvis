from __future__ import annotations

from pathlib import Path
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class SystemAgent(BaseAgent):
    name = "system"
    description = "Interacts with the operating system and local files."
    keywords = ("open", "launch", "terminal", "file", "save", "application")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        action = step.metadata.get("action", "resource_usage")
        if action == "write_file":
            result = await context.tools.execute(
                "system.write_file",
                context,
                path=step.metadata["path"],
                content=step.metadata["content"],
            )
            return {"message": f"Saved file to {result.get('path', step.metadata['path'])}.", "result": result}
        if action == "shell":
            result = await context.tools.execute(
                "system.shell",
                context,
                command=step.metadata["command"],
                workdir=step.metadata.get("workdir"),
            )
            return {"message": result["result"]["stdout"] or result["result"]["stderr"], "result": result}
        if action == "open_path":
            result = await context.system_controller.open_path(step.metadata["path"])
            return {"message": result}
        if action == "launch_application":
            result = await context.system_controller.launch_application(step.metadata["application"])
            return {"message": result}
        usage = await context.system_controller.resource_usage()
        return {"message": f"CPU {usage['cpu_percent']}%, memory {usage['memory_percent']}%.", "usage": usage}
