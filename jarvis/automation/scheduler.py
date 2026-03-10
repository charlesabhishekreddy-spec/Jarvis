from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Any
from uuid import uuid4

from jarvis.core.events import AsyncEventBus
from jarvis.core.service import Service


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(slots=True)
class AutomationJob:
    message: str
    cadence: str
    run_at: str
    day_of_week: int | None = None
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "scheduled"


class AutomationService(Service):
    def __init__(self, bus: AsyncEventBus) -> None:
        super().__init__("jarvis.automation")
        self.bus = bus
        self.jobs: dict[str, AutomationJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def schedule_reminder(self, message: str, run_at: str) -> dict[str, Any]:
        target = datetime.fromisoformat(run_at)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        job = AutomationJob(message=message, cadence="once", run_at=target.isoformat())
        self.jobs[job.job_id] = job
        self._tasks[job.job_id] = asyncio.create_task(self._run_once(job, target))
        await self.bus.publish("automation.scheduled", self._job_to_dict(job))
        return self._job_to_dict(job)

    async def schedule_daily(self, message: str, time_of_day: str) -> dict[str, Any]:
        parsed = time.fromisoformat(time_of_day)
        job = AutomationJob(message=message, cadence="daily", run_at=parsed.isoformat())
        self.jobs[job.job_id] = job
        self._tasks[job.job_id] = asyncio.create_task(self._run_daily(job, parsed))
        await self.bus.publish("automation.scheduled", self._job_to_dict(job))
        return self._job_to_dict(job)

    async def schedule_weekly(self, message: str, day_name: str, time_of_day: str) -> dict[str, Any]:
        parsed = time.fromisoformat(time_of_day)
        day_index = WEEKDAY_MAP[day_name.lower()]
        job = AutomationJob(message=message, cadence="weekly", run_at=parsed.isoformat(), day_of_week=day_index)
        self.jobs[job.job_id] = job
        self._tasks[job.job_id] = asyncio.create_task(self._run_weekly(job, day_index, parsed))
        await self.bus.publish("automation.scheduled", self._job_to_dict(job))
        return self._job_to_dict(job)

    async def _run_once(self, job: AutomationJob, target: datetime) -> None:
        delay = max((target - utc_now()).total_seconds(), 0.0)
        await asyncio.sleep(delay)
        job.status = "completed"
        await self.bus.publish("automation.triggered", self._job_to_dict(job))

    async def _run_daily(self, job: AutomationJob, time_of_day: time) -> None:
        while True:
            target = self._next_time(time_of_day=time_of_day)
            await asyncio.sleep(max((target - utc_now()).total_seconds(), 0.0))
            await self.bus.publish("automation.triggered", self._job_to_dict(job))

    async def _run_weekly(self, job: AutomationJob, day_of_week: int, time_of_day: time) -> None:
        while True:
            target = self._next_time(time_of_day=time_of_day, day_of_week=day_of_week)
            await asyncio.sleep(max((target - utc_now()).total_seconds(), 0.0))
            await self.bus.publish("automation.triggered", self._job_to_dict(job))

    def _next_time(self, time_of_day: time, day_of_week: int | None = None) -> datetime:
        now = utc_now()
        target = now.replace(hour=time_of_day.hour, minute=time_of_day.minute, second=time_of_day.second, microsecond=0)
        if day_of_week is None:
            if target <= now:
                target += timedelta(days=1)
            return target
        days_ahead = (day_of_week - now.weekday()) % 7
        if days_ahead == 0 and target <= now:
            days_ahead = 7
        return target + timedelta(days=days_ahead)

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        await super().stop()

    def list_jobs(self) -> list[dict[str, Any]]:
        return [self._job_to_dict(job) for job in self.jobs.values()]

    def _job_to_dict(self, job: AutomationJob) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "message": job.message,
            "cadence": job.cadence,
            "run_at": job.run_at,
            "day_of_week": job.day_of_week,
            "status": job.status,
        }
