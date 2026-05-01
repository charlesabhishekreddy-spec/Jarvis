from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class AutomationAgent(BaseAgent):
    name = "automation"
    description = "Schedules reminders and trigger-based workflows."
    keywords = ("remind", "schedule", "workflow", "every day", "every monday")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        operation = step.metadata.get("operation")
        if operation == "workflow_create":
            workflow = await context.orchestration.create_workflow(
                title=step.metadata.get("title", request.text),
                commands=step.metadata.get("commands", [request.text]),
                goal_id=step.metadata.get("goal_id"),
                metadata={"source": request.source},
            )
            return {
                "message": f"Created workflow '{workflow['title']}' with {len(workflow['steps'])} steps.",
                "workflow": workflow,
            }
        if operation == "workflows":
            workflows = await context.orchestration.workflows(limit=step.metadata.get("limit", 10))
            return {
                "message": "\n".join(
                    f"- {workflow['title']} [{workflow['status']}]: {len(workflow['steps'])} steps"
                    for workflow in workflows
                )
                or "No workflows are stored yet.",
                "workflows": workflows,
            }
        if operation == "workflow_run":
            workflow = await context.memory.find_workflow(
                step.metadata.get("title", request.text),
                statuses=["pending", "queued", "in_progress", "failed", "requires_confirmation", "completed", "cancelled"],
            )
            if workflow is None:
                return {"message": "Workflow not found."}
            result = await context.orchestration.run_workflow(workflow["workflow_id"])
            if not result.get("ok", False):
                return {"message": result.get("error", "Workflow could not be started.")}
            workflow = result["workflow"]
            return {"message": f"Workflow '{workflow['title']}' is queued.", "workflow": workflow}
        if operation == "workflow_cancel":
            workflow = await context.memory.find_workflow(step.metadata.get("title", request.text))
            if workflow is None:
                return {"message": "Workflow not found."}
            result = await context.orchestration.cancel_workflow(workflow["workflow_id"])
            if not result.get("ok", False):
                return {"message": result.get("error", "Workflow could not be cancelled.")}
            workflow = result["workflow"]
            return {"message": f"Workflow '{workflow['title']}' cancelled.", "workflow": workflow}

        schedule_type = step.metadata.get("schedule_type", "once")
        message = step.metadata.get("message", request.text)
        if schedule_type == "daily":
            job = await context.automation.schedule_daily(message=message, time_of_day=step.metadata["time_of_day"])
            return {"message": f"Scheduled daily reminder at {job['run_at']}.", "job": job}
        if schedule_type == "weekly":
            job = await context.automation.schedule_weekly(
                message=message,
                day_name=step.metadata["day_name"],
                time_of_day=step.metadata["time_of_day"],
            )
            return {"message": f"Scheduled weekly reminder for {step.metadata['day_name']} at {job['run_at']}.", "job": job}
        run_at = step.metadata.get("run_at")
        if not run_at:
            target = utc_now() + timedelta(hours=1)
            run_at = target.isoformat()
        else:
            parsed = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            run_at = parsed.isoformat()
        job = await context.automation.schedule_reminder(message=message, run_at=run_at)
        return {"message": f"Scheduled reminder for {job['run_at']}.", "job": job}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
