from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Any
from uuid import uuid4

from jarvis.core.events import AsyncEventBus
from jarvis.core.service import Service
from jarvis.memory.service import MemoryService


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
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = field(default_factory=lambda: utc_now().isoformat())
    last_triggered_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AutomationService(Service):
    def __init__(self, bus: AsyncEventBus, memory: MemoryService) -> None:
        super().__init__("jarvis.automation")
        self.bus = bus
        self.memory = memory
        self.jobs: dict[str, AutomationJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self) -> None:
        await super().start()
        await self._restore_jobs()

    async def schedule_reminder(self, message: str, run_at: str) -> dict[str, Any]:
        target = datetime.fromisoformat(run_at)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        job = AutomationJob(message=message, cadence="once", run_at=target.isoformat())
        await self._register_job(job, publish_topic="automation.scheduled")
        return self._job_to_dict(job)

    async def schedule_daily(self, message: str, time_of_day: str) -> dict[str, Any]:
        parsed = time.fromisoformat(time_of_day)
        job = AutomationJob(message=message, cadence="daily", run_at=parsed.isoformat())
        await self._register_job(job, publish_topic="automation.scheduled")
        return self._job_to_dict(job)

    async def schedule_weekly(self, message: str, day_name: str, time_of_day: str) -> dict[str, Any]:
        parsed = time.fromisoformat(time_of_day)
        day_index = WEEKDAY_MAP[day_name.lower()]
        job = AutomationJob(message=message, cadence="weekly", run_at=parsed.isoformat(), day_of_week=day_index)
        await self._register_job(job, publish_topic="automation.scheduled")
        return self._job_to_dict(job)

    async def cancel_job(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.get(job_id)
        if job is None:
            return {"ok": False, "error": f"Job not found: {job_id}"}
        job.status = "cancelled"
        job.updated_at = utc_now().isoformat()
        task = self._tasks.pop(job_id, None)
        if task is not None:
            task.cancel()
        await self.memory.save_automation_job(self._job_to_dict(job))
        await self.bus.publish("automation.cancelled", self._job_to_dict(job))
        return {"ok": True, "job": self._job_to_dict(job)}

    async def snapshot_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        records = await self.memory.automation_jobs(limit=limit)
        snapshots = {record["job_id"]: self._job_to_dict(self._job_from_record(record)) for record in records}
        for job in self.jobs.values():
            snapshots[job.job_id] = self._job_to_dict(job)
        jobs = list(snapshots.values())
        return sorted(jobs, key=lambda item: item["updated_at"], reverse=True)

    async def _restore_jobs(self) -> None:
        records = await self.memory.automation_jobs(status="scheduled", limit=500)
        for record in records:
            job = self._job_from_record(record)
            if job.job_id in self.jobs:
                continue
            self.jobs[job.job_id] = job
            self._tasks[job.job_id] = asyncio.create_task(self._runner(job))
            await self.bus.publish("automation.restored", self._job_to_dict(job))

    async def _register_job(self, job: AutomationJob, publish_topic: str | None = None) -> None:
        self.jobs[job.job_id] = job
        await self.memory.save_automation_job(self._job_to_dict(job))
        self._tasks[job.job_id] = asyncio.create_task(self._runner(job))
        if publish_topic:
            await self.bus.publish(publish_topic, self._job_to_dict(job))

    async def _runner(self, job: AutomationJob) -> None:
        try:
            if job.cadence == "once":
                target = datetime.fromisoformat(job.run_at)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                await self._sleep_until(target)
                await self._trigger(job, complete=True)
                return

            parsed_time = time.fromisoformat(job.run_at)
            while job.status == "scheduled":
                target = self._next_time(parsed_time, job.day_of_week)
                await self._sleep_until(target)
                if job.status != "scheduled":
                    break
                await self._trigger(job, complete=False)
        except asyncio.CancelledError:
            return

    async def _trigger(self, job: AutomationJob, complete: bool) -> None:
        timestamp = utc_now().isoformat()
        job.last_triggered_at = timestamp
        job.updated_at = timestamp
        if complete:
            job.status = "completed"
        await self.memory.save_automation_job(self._job_to_dict(job))
        await self.bus.publish("automation.triggered", self._job_to_dict(job))

    async def _sleep_until(self, target: datetime) -> None:
        delay = max((target - utc_now()).total_seconds(), 0.0)
        await asyncio.sleep(delay)

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
        self._tasks.clear()
        await super().stop()

    def list_jobs(self) -> list[dict[str, Any]]:
        jobs = [self._job_to_dict(job) for job in self.jobs.values()]
        return sorted(jobs, key=lambda item: (item["status"], item["updated_at"]), reverse=True)

    def _job_to_dict(self, job: AutomationJob) -> dict[str, Any]:
        next_run_at = None
        if job.status == "scheduled":
            if job.cadence == "once":
                next_run_at = job.run_at
            else:
                parsed_time = time.fromisoformat(job.run_at)
                next_run_at = self._next_time(parsed_time, job.day_of_week).isoformat()
        return {
            "job_id": job.job_id,
            "message": job.message,
            "cadence": job.cadence,
            "run_at": job.run_at,
            "day_of_week": job.day_of_week,
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "last_triggered_at": job.last_triggered_at,
            "next_run_at": next_run_at,
            "metadata": job.metadata,
        }

    def _job_from_record(self, record: dict[str, Any]) -> AutomationJob:
        return AutomationJob(
            job_id=record["job_id"],
            message=record["message"],
            cadence=record["cadence"],
            run_at=record["run_at"],
            day_of_week=record.get("day_of_week"),
            status=record["status"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            last_triggered_at=record.get("last_triggered_at"),
            metadata=record.get("metadata", {}),
        )
