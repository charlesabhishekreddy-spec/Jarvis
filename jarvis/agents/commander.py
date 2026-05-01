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
        memories = await context.memory.recall(request.text, limit=3)
        projects = await context.memory.project_contexts(limit=3)
        goals = await context.memory.goals(status="active", limit=3)
        if step.metadata.get("include_tools"):
            tools = [f"- {tool['name']}: {tool['description']}" for tool in context.tools.list_tools()]
            return {"message": "Available tools:\n" + "\n".join(tools)}
        if step.metadata.get("write_report"):
            summary = await context.intelligence.summarize(
                goal=request.text,
                fragments=completed_results,
                context={
                    "memories": memories,
                    "projects": projects,
                    "goals": goals,
                    "plan": plan.to_dict(),
                    "results": completed_results,
                },
            )
            return {"message": summary.text, "provider": summary.provider}
        if step.metadata.get("validate_deliverable"):
            latest = completed_results[-1] if completed_results else "No deliverable details available."
            response = await context.intelligence.respond(
                prompt=f"Summarize the completed deliverable for: {request.text}",
                context={
                    "memories": memories,
                    "projects": projects,
                    "goals": goals,
                    "plan": plan.to_dict(),
                    "results": completed_results,
                },
            )
            message = response.text.strip() or latest
            return {"message": message, "provider": response.provider}
        response = await context.intelligence.respond(
            prompt=request.text,
            context={
                "memories": memories,
                "projects": projects,
                "goals": goals,
                "plan": plan.to_dict(),
                "results": completed_results,
            },
        )
        return {"message": response.text, "provider": response.provider}
