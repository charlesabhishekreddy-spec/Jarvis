import asyncio
import unittest

from jarvis.core.events import AsyncEventBus
from jarvis.core.models import CommandRequest, CommandResponse, TaskStatus
from jarvis.core.task_queue import BackgroundCommandService


class CommandQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_and_complete(self) -> None:
        async def executor(request: CommandRequest) -> CommandResponse:
            await asyncio.sleep(0.01)
            return CommandResponse(status=TaskStatus.COMPLETED, message=f"done: {request.text}")

        service = BackgroundCommandService(AsyncEventBus(), executor)
        await service.start()
        try:
            record = await service.submit(CommandRequest(text="test command", source="test"))
            for _ in range(50):
                snapshot = service.get(record.request_id)
                if snapshot and snapshot["status"] == TaskStatus.COMPLETED.value:
                    break
                await asyncio.sleep(0.01)
            final = service.get(record.request_id)
            self.assertIsNotNone(final)
            self.assertEqual(final["status"], TaskStatus.COMPLETED.value)
            self.assertIn("done: test command", final["message"])
        finally:
            await service.stop()

    async def test_cancel_queued_execution(self) -> None:
        gate = asyncio.Event()

        async def executor(request: CommandRequest) -> CommandResponse:
            await gate.wait()
            return CommandResponse(status=TaskStatus.COMPLETED, message=f"done: {request.text}")

        service = BackgroundCommandService(AsyncEventBus(), executor)
        await service.start()
        try:
            first = await service.submit(CommandRequest(text="first", source="test"))
            second = await service.submit(CommandRequest(text="second", source="test"))

            for _ in range(50):
                snapshot = service.get(first.request_id)
                if snapshot and snapshot["status"] == TaskStatus.IN_PROGRESS.value:
                    break
                await asyncio.sleep(0.01)

            cancelled = await service.cancel(second.request_id)
            self.assertIsNotNone(cancelled)
            self.assertEqual(cancelled.status, TaskStatus.CANCELLED)

            gate.set()
            for _ in range(50):
                snapshot = service.get(first.request_id)
                if snapshot and snapshot["status"] == TaskStatus.COMPLETED.value:
                    break
                await asyncio.sleep(0.01)

            second_snapshot = service.get(second.request_id)
            self.assertIsNotNone(second_snapshot)
            self.assertEqual(second_snapshot["status"], TaskStatus.CANCELLED.value)
        finally:
            gate.set()
            await service.stop()
