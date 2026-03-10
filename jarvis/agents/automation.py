from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser as date_parser

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
            parsed = date_parser.parse(run_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            run_at = parsed.isoformat()
        job = await context.automation.schedule_reminder(message=message, run_at=run_at)
        return {"message": f"Scheduled reminder for {job['run_at']}.", "job": job}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
