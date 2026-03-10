from __future__ import annotations

from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class MemoryAgent(BaseAgent):
    name = "memory"
    description = "Stores and retrieves long-term user memory."
    keywords = ("remember", "recall", "preference", "memory")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        operation = step.metadata.get("operation", "remember")
        if operation == "recall":
            results = await context.tools.execute("memory.recall", context, query=step.metadata.get("query", request.text))
            return {
                "message": "\n".join(f"- {item['content']}" for item in results["results"]) or "No matching memories found.",
                "results": results["results"],
            }
        item = await context.tools.execute(
            "memory.remember",
            context,
            content=step.metadata.get("content", request.text),
            category=step.metadata.get("category", "general"),
        )
        return {"message": f"Stored memory: {item['content']}", "item": item}
