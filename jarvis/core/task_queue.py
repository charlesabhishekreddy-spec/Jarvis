from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress

from .events import AsyncEventBus
from .models import CommandRequest, CommandResponse, ExecutionRecord, TaskStatus, utc_now
from .service import Service


ExecutorCallable = Callable[[CommandRequest], Awaitable[CommandResponse]]


class BackgroundCommandService(Service):
    def __init__(self, bus: AsyncEventBus, executor: ExecutorCallable) -> None:
        super().__init__("jarvis.command_queue")
        self.bus = bus
        self.executor = executor
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._records: dict[str, ExecutionRecord] = {}
        self._worker: asyncio.Task[None] | None = None
        self._running: dict[str, asyncio.Task[CommandResponse]] = {}

    async def start(self) -> None:
        await super().start()
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker
        for task in self._running.values():
            task.cancel()
        self._running.clear()
        await super().stop()

    async def submit(self, request: CommandRequest) -> ExecutionRecord:
        record = ExecutionRecord(
            request_id=request.request_id,
            text=request.text,
            source=request.source,
            metadata=dict(request.metadata),
        )
        self._records[request.request_id] = record
        await self._queue.put(request.request_id)
        await self.bus.publish("command.execution.queued", record.to_dict())
        return record

    async def cancel(self, request_id: str) -> ExecutionRecord | None:
        record = self._records.get(request_id)
        if record is None:
            return None
        if record.status == TaskStatus.QUEUED:
            record.status = TaskStatus.CANCELLED
            record.finished_at = utc_now()
            await self.bus.publish("command.execution.cancelled", record.to_dict())
            return record
        task = self._running.get(request_id)
        if task is not None and not task.done():
            task.cancel()
        return record

    def get(self, request_id: str) -> dict | None:
        record = self._records.get(request_id)
        return record.to_dict() if record else None

    def list(self, limit: int = 50) -> list[dict]:
        records = sorted(self._records.values(), key=lambda item: item.queued_at, reverse=True)
        return [record.to_dict() for record in records[:limit]]

    def snapshot(self) -> dict:
        queued = sum(1 for record in self._records.values() if record.status == TaskStatus.QUEUED)
        running = sum(1 for record in self._records.values() if record.status == TaskStatus.IN_PROGRESS)
        return {
            "queued": queued,
            "running": running,
            "total": len(self._records),
            "recent": self.list(10),
        }

    async def _worker_loop(self) -> None:
        while True:
            request_id = await self._queue.get()
            record = self._records.get(request_id)
            if record is None or record.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue

            request = CommandRequest(
                text=record.text,
                source=record.source,
                metadata=dict(record.metadata),
                request_id=record.request_id,
                timestamp=record.queued_at,
            )
            record.status = TaskStatus.IN_PROGRESS
            record.started_at = utc_now()
            await self.bus.publish("command.execution.started", record.to_dict())

            task = asyncio.create_task(self.executor(request))
            self._running[request_id] = task
            try:
                response = await task
                record.status = response.status
                record.finished_at = utc_now()
                record.task_id = response.task_id
                record.message = response.message
                record.response_data = response.data
                record.error = response.message if response.status == TaskStatus.FAILED else None
                topic = "command.execution.completed" if response.status == TaskStatus.COMPLETED else "command.execution.updated"
                await self.bus.publish(topic, record.to_dict())
            except asyncio.CancelledError:
                record.status = TaskStatus.CANCELLED
                record.finished_at = utc_now()
                record.error = "Execution cancelled."
                await self.bus.publish("command.execution.cancelled", record.to_dict())
            except Exception as exc:
                record.status = TaskStatus.FAILED
                record.finished_at = utc_now()
                record.error = str(exc)
                record.message = str(exc)
                await self.bus.publish("command.execution.failed", record.to_dict())
            finally:
                self._running.pop(request_id, None)
                self._queue.task_done()
