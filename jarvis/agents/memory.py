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
        if operation == "projects":
            results = await context.tools.execute(
                "memory.projects",
                context,
                status=step.metadata.get("status"),
                limit=step.metadata.get("limit", 5),
            )
            return {
                "message": "\n".join(
                    f"- {item['project_name']} [{item['status']}]: {item['summary']}"
                    for item in results["results"]
                )
                or "No project context is available yet.",
                "results": results["results"],
            }
        if operation == "suggestions":
            results = await context.tools.execute(
                "memory.suggestions",
                context,
                status=step.metadata.get("status"),
                limit=step.metadata.get("limit", 5),
            )
            return {
                "message": "\n".join(
                    f"- {item['title']}: {item['detail']}"
                    for item in results["results"]
                )
                or "No proactive suggestions are available yet.",
                "results": results["results"],
            }
        if operation == "goals":
            results = await context.tools.execute(
                "memory.goals",
                context,
                status=step.metadata.get("status"),
                limit=step.metadata.get("limit", 5),
            )
            return {
                "message": "\n".join(
                    f"- {item['title']} [{item['status']}] (priority {item['priority']}): {item.get('next_action') or item['detail']}"
                    for item in results["results"]
                )
                or "No persistent goals are available yet.",
                "results": results["results"],
            }
        if operation == "goal_create":
            latest_project = None
            if context.learning is not None:
                projects = await context.memory.project_contexts(limit=1)
                latest_project = projects[0] if projects else None
            result = await context.tools.execute(
                "memory.goal_create",
                context,
                title=step.metadata.get("title", request.text),
                detail=step.metadata.get("detail", request.text),
                priority=step.metadata.get("priority", 50),
                project_id=step.metadata.get("project_id") or (latest_project or {}).get("project_id"),
                next_action=step.metadata.get("next_action"),
                metadata=step.metadata.get("goal_metadata", {}),
            )
            goal = result["goal"]
            return {
                "message": (
                    f"Tracking goal '{goal['title']}' with priority {goal['priority']}."
                    + (f" Next action: {goal['next_action']}" if goal.get("next_action") else "")
                ),
                "goal": goal,
            }
        if operation == "goal_update":
            result = await context.tools.execute(
                "memory.goal_update",
                context,
                goal_id=step.metadata.get("goal_id"),
                title=step.metadata.get("title"),
                statuses=step.metadata.get("statuses"),
                status=step.metadata.get("status"),
                priority=step.metadata.get("priority"),
                next_action=step.metadata.get("next_action"),
                metadata=step.metadata.get("goal_metadata"),
            )
            if not result.get("ok", False):
                return {"message": result.get("error", "Goal update failed.")}
            goal = result["goal"]
            return {
                "message": f"Goal '{goal['title']}' is now {goal['status']}.",
                "goal": goal,
            }
        if operation == "review_goals":
            if context.proactive is None:
                return {"message": "Proactive goal review is not available."}
            review = await context.proactive.review_now(source="command")
            updated = review.get("updated_goals", [])
            return {
                "message": (
                    f"Reviewed {review['goal_count']} goals."
                    + (f" Updated {len(updated)} goal records." if updated else " No goal updates were required.")
                ),
                "review": review,
            }
        item = await context.tools.execute(
            "memory.remember",
            context,
            content=step.metadata.get("content", request.text),
            category=step.metadata.get("category", "general"),
        )
        return {"message": f"Stored memory: {item['content']}", "item": item}
